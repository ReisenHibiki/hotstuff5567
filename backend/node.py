from .blockchain import StateMachine
from .models import Block, QC


class Node:
    def __init__(self, node_id: int, genesis: Block, genesis_qc: QC):
        self.id = node_id
        self.view = 1
        self.role = "Leader" if node_id == 1 else "Replica"
        self.high_qc = genesis_qc
        self.locked_qc = genesis_qc
        self.blocks = {genesis.id: genesis}
        self.committed_blocks = [genesis.id]
        self.machine = StateMachine()
        self.last_voted_view = 0
        self.crashed = False
        self.withhold_vote = False

    def enter_view(self, view: int, leader_id: int):
        """A5 update local view and role for a live replica.
        A crashed replica remains frozen. Never erase voting history or locks."""

        # 同理，存活副本更新自己的 view 和角色
        if self.crashed:
            return                                 # 崩溃副本保持冻结
        self.view = view
        self.role = "Leader" if self.id == leader_id else "Replica"

        # raise NotImplementedError('TODO A5 update local view and role for a live replica.')

    def extends(self, block_id: str, ancestor_id: str) -> bool:
        """A2 test whether block_id descends from ancestor_id, including itself.
        Use local parent links. Unknown or malformed ancestry must not be
        accepted as an extension. Return a Boolean without modifying state."""

        # 两个块都必须在本节点已知的块里，否则视作非法祖先关系
        if block_id not in self.blocks or ancestor_id not in self.blocks:
            return False

        current = block_id
        seen = set()  # AI建议的改进防止异常数据造成死循环(this line: AI assist Improvement for possible bug)
        # 沿 parent 链往上走，边走边找 ancestor
        while current is not None and current not in seen:
            if current == ancestor_id:
                return True          # 走到祖先, 或一开始就是它本身
            seen.add(current)
            current = self.blocks[current].parent_id
        return False

        # raise NotImplementedError('TODO A2 test whether block_id descends from ancestor_id, including itself.')

    def can_vote(self, block: Block) -> bool:
        """A2 decide whether this replica may vote for a proposal.
        Enforce availability, current view, one vote per view and the safe-node
        lock rule. Return a Boolean; vote() records the actual cast vote.
        The coordinator validates the proposal leader and parent certificate."""

        # 崩溃的、或被设为“扣票”的副本不投
        if self.crashed or self.withhold_vote:
            return False

        # VIEW必须一致
        if block.view != self.view:
            return False

        # IMPORTANT 每个视图最多投一票
        if self.last_voted_view == block.view:
            return False

        # 新提案接在“锁定分支”后面（含直接接在锁定块上）
        if block.parent_id is not None and self.extends(block.parent_id, self.locked_qc.block_id):
            return True

        # 如果提案自带一张 view 更高的 QC，允许换分支
        if block.qc is not None and block.qc.view > self.locked_qc.view:
            return True

        return False

        # raise NotImplementedError('TODO A2 decide whether this replica may vote for a proposal.')

    def receive_qc(self, qc: QC) -> list[str]:
        """A4 update certificate/lock state and decide committed block IDs.
        Return newly committed IDs in ancestor-first order; a crashed node
        returns no progress. Check the linked, consecutive-view three-chain
        contract. Preserve existing commits and prevent repeated commitment.
        Do not execute transactions here: dispatch_qc() invokes Task B.
        A7 may add certificate validation at this boundary as needed."""
        # 负责一个副本收到一张证书后决定 要不要更新状态
        # 并且根据连续的三链规则，判断哪些区块可以正式提交
        # 崩溃副本停止工作，不产生新进度
        if self.crashed:
            return []

        # 找到这张 QC 认证的块；块未知或视图对不上 → 拒绝（A7 的无效 QC 防线）
        certified = self.blocks.get(qc.block_id)
        if certified is None or certified.view != qc.view:
            return []

        # 更新 HighQC：只接受更高的视图
        if qc.view > self.high_qc.view:
            self.high_qc = qc

        # 父块必须已知
        p1 = self.blocks.get(certified.parent_id) if certified.parent_id else None
        if p1 is None:
            return []

        # 更新 LockedQC：锁定“父块的证书” 我记得幻灯片课件中是这样要求的，后续需要检查
        # 因为 Block.qc 认证的就是自己的父块，所以父块的证书 = certified.qc
        if certified.qc is not None and certified.qc.view > self.locked_qc.view:
            self.locked_qc = certified.qc

        # 祖父块
        p2 = self.blocks.get(p1.parent_id) if p1.parent_id else None
        if p2 is None:
            return []

        # 三链提交条件：X、父、祖父必须是“连续视图”
        # certified.view == p1.view + 1 == p2.view + 2
        if certified.view == p1.view + 1 == p2.view + 2:
            newly = []
            cur = p2
            # 从祖父往上收未提交的祖先（祖先在链更早的位置）
            while cur is not None and cur.id not in self.committed_blocks:
                newly.append(cur.id)
                cur = self.blocks.get(cur.parent_id)
            newly.reverse()  # 反转成“祖先在前”的顺序
            self.committed_blocks.extend(newly)
            return newly
        return []

    # raise NotImplementedError('TODO A4 update certificate/lock state and decide committed block IDs.')



    def execute_committed(self, block_ids: list[str]):
        """B3 execute only blocks already in this replica's committed history.
        Reject uncommitted IDs before applying any transaction. Preserve block
        and payload order; call machine.apply() and rely on B4 receipt semantics
        for repeat delivery. A crashed replica must not execute new work.
        """
        raise NotImplementedError("TODO B3 implement execute_committed")
