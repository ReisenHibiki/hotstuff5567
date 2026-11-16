import unittest
from backend.hotstuff import HotStuffDemo
from backend.models import Block, QC

class HotStuffTests(unittest.TestCase):
    def setUp(self):
        self.demo = HotStuffDemo()

    def advance_until(self, predicate, limit=300):
        for _ in range(limit):
            if predicate():
                return
            self.demo.step()
        self.fail("Protocol did not reach expected state")

    def assert_agreement(self):
        live = [node for node in self.demo.nodes if not node.crashed]
        for node in live[1:]:
            self.assertEqual(node.committed_blocks, live[0].committed_blocks)
            self.assertEqual(node.machine.accounts, live[0].machine.accounts)
            self.assertEqual(node.machine.receipts, live[0].machine.receipts)
        for qc in self.demo.qcs.values():
            self.assertGreaterEqual(len(set(qc.voters)), 3)

    def test_crash_leader_timeout_and_recovery(self):
        self.demo.crash_leader()
        self.demo.submit("Alice", "Bob", 10)
        self.advance_until(lambda: self.demo.view == 2)
        self.assertEqual(self.demo.leader_id, 2)
        self.assertEqual(self.demo.nodes[0].view, 1)
        self.advance_until(lambda: self.demo.nodes[1].machine.accounts["Alice"] == 90)
        self.assertEqual(self.demo.nodes[0].machine.accounts["Alice"], 100)
        self.assert_agreement()
        self.demo.recover()
        self.assertTrue(all(not node.crashed for node in self.demo.nodes))
        self.assert_agreement()

    def test_one_byzantine_replica_and_leader_rotation(self):
        self.demo.set_byzantine(4)
        self.demo.submit("Alice", "Bob", 10)
        self.advance_until(lambda: self.demo.view >= 6)
        for block_id, qc in self.demo.qcs.items():
            if block_id != "B0":
                self.assertEqual(qc.voters, (1, 2, 3))
        self.assertEqual(self.demo.nodes[3].machine.accounts["Alice"], 90)
        self.assert_agreement()

    def test_two_unavailable_voters_stall_without_false_qc(self):
        self.demo.crash_leader()
        self.demo.set_byzantine(4)
        for _ in range(60):
            self.demo.step()
        self.assertGreater(self.demo.view, 2)
        self.assertEqual(list(self.demo.qcs), ["B0"])
        self.assert_agreement()

    def test_orphaned_transaction_is_reproposed(self):
        tx = self.demo.submit("Alice", "Bob", 10)
        self.demo.step()  # B1 proposed, but its leader dies before QC.
        self.demo.crash_leader()
        self.advance_until(lambda: self.demo.nodes[1].machine.accounts["Alice"] == 90)
        self.assertNotIn("B1", self.demo.qcs)
        self.assertIn(tx, self.demo.blocks["B2"].transactions)
        self.assertNotIn(tx.id, self.demo.mempool)
        self.demo.recover()
        self.assert_agreement()

    def test_view_gap_delays_commit_until_consecutive_chain(self):
        self.advance_until(lambda: self.demo.view == 2)
        self.demo.crash_leader()  # Skip view 2; next chain has views 1,3,4.
        self.advance_until(lambda: self.demo.view == 5)
        self.assertEqual(self.demo.nodes[0].committed_blocks, ["B0"])
        self.advance_until(lambda: self.demo.view == 6)
        # The 3,4,5 chain commits view 3 and also its view 1 ancestor.
        self.assertEqual(self.demo.nodes[0].committed_blocks, ["B0", "B1", "B2"])
        self.assert_agreement()

# 整体进程
#     N1 提出 B1
#     ↓
# N1、N2、N3 投票，已经有三票
#     ↓
# 队列中出现 ("qc", "B1")，但还没有执行
#     ↓
# N1 崩溃
#     ↓
# 处理 qc 事件时发现收票 leader 已崩溃
#     ↓
# 安排 timeout，停止本次 QC 生成
#     ↓
# 换成 N2，后续共识恢复推进
    def test_collector_crash_before_qc(self):
        # N1 提出 B1:
        self.demo.step()

        # N1, N2, N3 分别投票:
        for _ in range(3):
            self.demo.step()

        self.assertEqual(self.demo.votes["B1"], {1, 2, 3})
        self.assertNotIn("B1", self.demo.qcs)

        # 收齐三票, 但 N1 在 QC 执行前崩溃
        self.demo.crash_leader()

        # N4 刚开始投票 
        self.demo.step()
        self.assertEqual(self.demo.events[0], ("qc", "B1"))

        # 处理 QC: 超时, 而不是生成 B1 的 QC
        self.demo.step()
        self.assertNotIn("B1", self.demo.qcs)
        self.assertEqual(
            list(self.demo.events),
            [("timeout", self.demo.TIMEOUT_TICKS)]
        )

        # 在超时后进入 view 2,  N1 仍然锁定 view 1
        self.advance_until(lambda: self.demo.view == 2)
        self.assertEqual(self.demo.leader_id, 2)
        self.assertEqual(self.demo.nodes[0].view, 1)

        # N2, N3. N4 继续提交新的 block
        self.advance_until(
            lambda: len(self.demo.nodes[1].committed_blocks) > 1
        )
        self.assertNotIn("B1", self.demo.qcs)
        self.assertNotIn("B1", self.demo.nodes[1].committed_blocks)
        self.assert_agreement()

    def test_recover_catches_up_empty_chain(self):

        # N1 提出 B1 并投给自己
        self.demo.step()
        self.demo.step()

        recovered = self.demo.nodes[0]
        old_vote = recovered.last_voted_view
        self.assertEqual(old_vote, 1)

        # N1 崩溃, 其他几个节点继续
        self.demo.crash_leader()
        self.advance_until(
            lambda: len(self.demo.nodes[1].committed_blocks) > 1
        )

        peer = self.demo.nodes[1]

        # 恢复前 仍冻结 N1

        self.assertEqual(recovered.committed_blocks, ["B0"])
        self.assertEqual(recovered.view, 1)

        self.demo.recover()

        # 恢复后, 查看自己历史 log
        self.assertFalse(recovered.crashed)
        self.assertEqual(recovered.id, 1)
        self.assertEqual(recovered.view, self.demo.view)

        self.assertEqual(recovered.last_voted_view, old_vote)

        # 查看区块, 证书以及锁 同步更新追上存活节点
        self.assertEqual(recovered.high_qc, peer.high_qc)
        self.assertEqual(recovered.blocks, peer.blocks)

        # 数据独立, 两个节点不能同享一个可变状态对象
        self.assertIsNot(recovered.blocks, peer.blocks)
        self.assertIsNot(recovered.machine, peer.machine)
        self.assert_agreement

        #恢复后的节点继续跟进
        old_length = len(recovered.committed_blocks)
        self.advance_until(
            lambda: len(recovered.committed_blocks)> old_length
        )
        self.assert_agreement