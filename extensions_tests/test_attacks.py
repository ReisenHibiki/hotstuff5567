import unittest
from backend.hotstuff import HotStuffDemo
from backend.models import Block

# 指定接收者:[N1, N3, N4]
# N4 已崩溃
#     ↓
# 实际收到区块: [N1, N3]
# 新增投票事件: [N1 的 vote, N3 的 vote]

class AttackTests(unittest.TestCase):
	def test_deliver_only_to_selected_live_nodes(self):
		demo = HotStuffDemo()
		block = Block("B1", "B0", 1, 1, [], demo.qcs["B0"])
	
		demo.nodes[3].crashed = True
		events_before = list(demo.events)
		
		demo._deliver_proposal(block, [1, 3, 4])

		#区块已经登记, 但没有在投递时候自己产生投票或者 QC
		self.assertIn("B1", demo.blocks)
		self.assertEqual(demo.votes["B1"], set())
		self.assertNotIn("B1", demo.qcs)

		# 实际只有 N1, N3收到 block
		for node_id in (1, 3):
			self.assertIn("B1", demo.nodes[node_id - 1].blocks)
		
		for node_id in (2, 4):
			self.assertNotIn("B1", demo.nodes[node_id - 1].blocks)
		
		# 实际收到的 block 的节点开始投票
		self.assertEqual(
			list(demo.events),
			events_before + [
				("vote", (1, "B1")),
				("vote", (3, "B1")),
			],
		)

		# 接受到的两个节点保存独立的 block:
		self.assertIsNot(
			demo.nodes[0].blocks["B1"],
			demo.nodes[2].blocks["B1"],
		)