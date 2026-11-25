"""Deterministic event queue. One step is one visible protocol action.

Transport and the timeout pacemaker are simulated by this coordinator. Votes,
locks, blocks, committed chains and account execution remain per-node state.
"""
from collections import deque
from copy import deepcopy
from dataclasses import asdict

from .blockchain import INITIAL_BALANCES
from .models import Block, QC, Transaction
from .node import Node
from .security import transaction_id, verify_transaction

class HotStuffDemo:
    NODE_COUNT = 4
    QUORUM = 3
    TIMEOUT_TICKS = 3

    def __init__(self, require_signatures: bool = False):
        self.require_signatures = require_signatures
        self.reset()

    @property
    def leader_id(self):
        return (self.view - 1) % self.NODE_COUNT + 1

    def log(self, message: str, kind: str = "info"):
        self.log_sequence += 1
        self.logs.append({"id": self.log_sequence, "step": self.steps,
                          "view": self.view, "kind": kind, "message": message})

    def reset(self):
        genesis = Block("B0", None, 0, 0)
        genesis_qc = QC("B0", 0, (1, 2, 3, 4))
        self.view = 1
        self.nodes = [Node(i, genesis, genesis_qc) for i in range(1, 5)]

        for node in self.nodes:
            node.machine.require_signatures = self.require_signatures
        self._basic_tx_sequence = 0
        self.blocks = {genesis.id: genesis}
        self.qcs = {genesis.id: genesis_qc}
        self.transactions: dict[str, Transaction] = {}
        self.mempool: list[str] = []
        self.votes: dict[str, set[int]] = {}
        self.qc_scheduled: set[str] = set()
        self.events = deque([("propose", None)])
        self.logs = deque(maxlen=400)
        self.log_sequence = 0
        self.steps = 0
        self.running = False
        self.max_txs_per_block = 5
        self.phase = "Ready for proposal"
        self.log("Genesis B0 committed · Enter View 1 · Leader N1", "view")

    def submit(
            self, 
            sender: str, 
            receiver: str, 
            amount: int,
            nonce: int | None = None,
            signature: str | None = None,
        ) -> Transaction:
        """B1 implement transaction admission and mempool insertion.
        Return a Transaction; validate account names and a strict integer amount
        in [1, 1000000]. Invalid requests must not modify state. Allocate Tx1,
        Tx2, ... for the basic task. B6 may extend this interface for signed input.
        Do not execute transfers here."""
        # 1) 先做全部校验，任何一项失败都在修改状态之前抛出 ValueError。
        if type(sender) is not str or type(receiver) is not str:
            raise ValueError("Account names must be strs")
        if sender not in INITIAL_BALANCES or receiver not in INITIAL_BALANCES:
            raise ValueError("Unknown sender or receiver account")
        if sender == receiver:
            # 设计决定：规范未规定，自转账没有意义，这里拒绝。
            raise ValueError("Sender and receiver must be different")
        # type(...) is int 而不是 isinstance：bool 是 int 的子类，True 必须被拒绝。
        if type(amount) is not int or not 1 <= amount <= 1_000_000:
            raise ValueError("Amount must be an integer between 1 and 1000000")
        unsigned = nonce is None and signature is None

        if unsigned:
            if self.require_signatures:
                raise ValueError("Signature required")

            self._basic_tx_sequence += 1
            tx = Transaction(
                f"Tx{self._basic_tx_sequence}", sender, receiver, amount
            )

        else:
            if nonce is None or signature is None:
                raise ValueError("Nonce and signature must be provided together")
            if type(nonce) is not int or nonce < 0:
                raise ValueError("Nonce must be a non-negative integer")

            # 1. 先验签。
            if not verify_transaction(
                sender, receiver, amount, nonce, signature
            ):
                raise ValueError("Invalid signature")

            # 2. 按载荷确定身份。
            tx_id = transaction_id(sender, receiver, amount, nonce)

            # 3. 合法重试先返回原交易，不重新检查 nonce，不重复入池。
            if tx_id in self.transactions:
                return self.transactions[tx_id]

            # 4. 新交易才检查 nonce。
            expected_nonce = self.expected_nonce(sender)
            if expected_nonce is None:
                raise ValueError("Cannot admit a new signed transaction: no live replica")

            if nonce != expected_nonce:
                raise ValueError(
                    f"Expected nonce {expected_nonce}, got {nonce}"
                )
        # 2) 分配 ID。transactions 只增不减，所以长度+1 就是下一个编号；reset 后回到 Tx1。
            tx = Transaction(
                id = tx_id,
                sender = sender,
                receiver= receiver,
                amount= amount,
                nonce= nonce,
                signature= signature,
            )

        # 3) 登记并进入待处理池。这里只做准入，不检查余额、不改余额（那是 B3 执行时的事）。
        self.transactions[tx.id] = tx
        self.mempool.append(tx.id)
        self.log(f"{tx.id} admitted: {sender} -> {receiver} {amount}", "tx")
        return tx

    def expected_nonce(self, sender: str) -> int | None:
        """Nonce that admission requires for the sender's next new signed transfer:
        the committed nonce on the most advanced live replica plus the sender's
        signed transactions still pending in the pool. None when no replica is live."""
        # [AI-assisted] Extracted unchanged from submit() so the dashboard form can
        # pre-fill the same value that admission checks.
        live = [node for node in self.nodes if not node.crashed]
        if not live:
            return None

        source = max(
            live,
            key=lambda node: (
                len(node.committed_blocks),
                node.high_qc.view,
            ),
        )
        machine = source.machine

        pending = sum(
            1
            for pending_id in self.mempool
            if self.transactions[pending_id].sender == sender
            and self.transactions[pending_id].nonce is not None
            and pending_id not in machine.receipts
        )
        return machine.nonces[sender] + pending

    def step(self):
        """Provided event dispatcher; a missing TODO pauses without losing work."""
        checkpoint = deepcopy(self.__dict__)
        try:
            if not self.events:
                self.events.append(("propose", None))
            action, data = self.events.popleft()
            self.steps += 1
            
            # 这里根据5个事件名调用对应的函数，传入数据
            {"propose": self.propose, "vote": self.vote, "qc": self.form_qc,
             "next_view": self.next_view, "timeout": self.timeout}[action](data)
        except NotImplementedError as exc:
            self.__dict__.clear()
            self.__dict__.update(checkpoint)
            self.running = False
            self.phase = str(exc)
            self.log(str(exc), "todo")
            raise

    def propose(self, _):
        """A1 implement a leader proposal for the current view.
        Select a justified parent, allocate a unique block ID, populate the
        proposal and distribute it to live replicas. Register an empty vote set
        and enqueue ("vote", (node_id, block_id)) for the intended recipients.
        Call select_transactions(parent) only when the mempool is nonempty;
        otherwise use an empty payload, allowing independent Task A work.
        A6: handle a crashed leader using the timeout event. No balances change."""

        # Hengyu
        # 取出当前view的 leader
        leader = self.nodes[self.leader_id - 1]

        # 如果 leader 已崩溃：这次propose做不了，改排一个超时事件（未来做A6 的入口）
        if leader.crashed:
            self.log(f"Leader N{self.leader_id} crashed; scheduling timeout", "timeout")
            self.events.append(("timeout", self.TIMEOUT_TICKS))
            self.phase = "Leader crashed"
            return

        # 父块 = leader 已知最高证书记录的块, 继承已认证进度
        parent_id = leader.high_qc.block_id
        parent = self.blocks[parent_id]

        # 造新块：ID 顺序编号；qc 字段放“父块的证书”；
        # 只有 mempool 非空才去选交易，否则用空块
        block = Block(
            id=f"B{len(self.blocks)}",
            parent_id=parent_id,
            view=self.view,
            proposer=self.leader_id,
            transactions=self.select_transactions(parent) if self.mempool else [],
            qc=leader.high_qc,
        )

        # 协调器登记这个块 + 初始化空投票集合
        self.blocks[block.id] = block
        self.votes[block.id] = set()

        # 正常提案发给全部节点；辅助函数会跳过崩溃节点。
        self._deliver_proposal(
            block,
            [node.id for node in self.nodes],
        )

        self.log(
            f"N{self.leader_id} proposed {block.id} "
            f"(view {self.view}, parent {parent_id})",
            "propose",
        )
        self.phase = f"Proposed {block.id}"

        # self.log(f"N{self.leader_id} proposed {block.id} (view {self.view}, parent {parent_id})", "propose")
        # self.phase = f"Proposed {block.id}"

        # 避免重复排队打乱 `test_collector_crash_before_qc` 预期的事件顺序
        # 给 4 个副本各排一个投票事件, 崩溃节点也会排，但投票时会被判为无效，相当于空操作
        # for node in self.nodes:
        #     self.events.append(("vote", (node.id, block.id)))

    # raise NotImplementedError('TODO A1 implement a leader proposal for the current view.')

    def _deliver_proposal(self, block, recipient_ids):
        """ Register a proposal and deliver it to selected live nodes"""

        # 先检查所哟接收者的 ID, 避免输入非法
        recipients = list(recipient_ids)
        if any(
            type(node_id) is not int
            or node_id not in range(1, self.NODE_COUNT + 1)
            for node_id in recipients
        ):
            raise ValueError("Recipient ID must be an integer from 1 to 4")
    # 同一个区块 ID 不允许对应不同内容:
        existing = self.blocks.get(block.id)

        # if existing : self.blocks.get(block.id)

        if existing is not None and existing != block:
            raise ValueError(
                "Conflicting contents for an existing block ID"
            )

        # 全局登记区块: 再一次投递同一个区块保留已有票数:
        self.blocks.setdefault(block.id, deepcopy(block))
        self.votes.setdefault(block.id, set())

        # 只向存活节点投递:
        for node_id in recipients:
            node = self.nodes[node_id - 1]

            if node.crashed:
                continue
            node.blocks[block.id] = deepcopy(block)
            self.events.append(("vote", (node.id, block.id)))

    def vote(self, data):
        """A2 implement proposal validation and one safe vote per replica/view.
        data is (node_id, block_id). Validate current leader, view, parent and
        its registered QC, then consult Node.can_vote(). Track voting state and
        distinct voters. Once a quorum is reached, enqueue a single ("qc", id)
        event. Reject invalid proposals without changing voting or account state.
        A6: schedule a timeout if this round cannot obtain a QC."""

        # 负责 coordinator 收到vote处理vote
        # data结构 是 投票节点号和块号
        node_id, block_id = data
        block = self.blocks.get(block_id)
        node = self.nodes[node_id - 1]

        # 检查提案本身合法 → 该副本允许投票 → 才记这一票
        if block is not None and self._valid_proposal(block) and node.can_vote(block):
            self.votes.setdefault(block_id, set()).add(node_id)  # 用 set 去重
            node.last_voted_view = block.view                    # 记录“我在这个视图投过票了”
            self.log(f"N{node_id} voted for {block_id} (view {block.view})", "vote")

        # 投票结束后，判断是否可以出 QC / 是否该超时
        if block is not None:
            voters = self.votes.get(block_id, set())

            # 已经安排过 QC 了，直接返回（避免重复）
            if block_id in self.qc_scheduled:
                return

            # 不同投票者达到法定人数（3）→ 排一个 QC 事件
            if len(voters) >= self.QUORUM:
                self.qc_scheduled.add(block_id)
                self.events.append(("qc", block_id))

            # 还没够票、并且队列里没有更多投票事件了 → 这一轮救不回来，排超时
            elif not any(e[0] == "vote" for e in self.events):
                self.events.append(("timeout", self.TIMEOUT_TICKS))
                self.log(f"Timeout: view {self.view} cannot reach quorum", "timeout")

    # raise NotImplementedError('TODO A2 implement proposal validation and one safe vote per replica/view.')

    def form_qc(self, block_id):
        """A3 construct a certificate from distinct valid matching votes.
        Validate the block, view and authorized voters; fewer than QUORUM must
        never create a QC. Register the valid certificate, call dispatch_qc(qc),
        and enqueue ("next_view", "QC"). A6 handles a crashed collector.
        Do not implement transaction processing in this function."""

        # 负责 票收集齐全后判断要不要正式签发一张QC
        block = self.blocks.get(block_id)
        if block is None:
            raise ValueError(f"form_qc: unknown block {block_id}")

        # for A6: 检查这次 view 的 leader 是否已经崩溃
        collector = self.nodes[block.proposer - 1]
        # def timeout(self, remaining):
        if collector.crashed:
            self.phase = "collector crashed: waiting for timeout check"
            self.log(
                f"leader N{collector.id} crashed before QC({block_id})"
                "scheduling timeout",
                "timeout",
            )

            self.events.append(("timeout", self.TIMEOUT_TICKS))

            return #如果没有 return 程序安排完超时之后会继续进行生成 QC

        # 只统计 1~4 号合法节点，且用集合去重（同一人投多次只算一次）
        voters = sorted({v for v in self.votes.get(block_id, set()) if 1 <= v <= self.NODE_COUNT})

        # 不足法定人数3 不签 QC
        if len(voters) < self.QUORUM:
            raise ValueError(f"form_qc: need {self.QUORUM} voters, got {len(voters)}")

        # 签发证书：块号、块视图、投票者元组
        qc = QC(block_id, block.view, tuple(voters))
        self.qcs[block_id] = qc
        self.log(f"QC({block_id}) view {qc.view} voters {qc.voters}", "qc")

        # 把 QC 下发给所有副本（Node.receive_qc 在这里被调用）
        self.dispatch_qc(qc)

        # 进入下一个视图
        self.events.append(("next_view", "QC"))

    # raise NotImplementedError('TODO A3 construct a certificate from distinct valid matching votes.')

    def timeout(self, remaining):
        """A6 implement logical timeout countdown and leader replacement.
        remaining is the number of logical ticks left. Eventually schedule
        ("next_view", "timeout") while preserving the quorum and safety state."""

        # timeout(3)
        #   → timeout(2)
        #   → timeout(1)
        #   → next_view("timeout")
        #   → propose(None)
        # 显示并且记录该次倒计时
        self.phase = f"Timeout: {remaining} tick(s) remaining"
        self.log(f"view {self.view}: timeout countdown {remaining}", "timeout", )

        # 没哟到最后一次 tick: 剩余次数减少 1， step() 继续处理
        if remaining > 1:
            self.events.append(("timeout", remaining - 1))
        else:
        # 安排进行 view 的更换, 下一步调用 next_view()
            self.phase = "Timeout expired and wait for next view"
            self.log(f"view {self.view}: timeout expired and schedule view change", "timeout", )
            self.events.append(("next_view", "timeout"))
        # raise NotImplementedError('TODO A6 implement logical timeout countdown and leader replacement.')

    def next_view(self, reason):
        """A5 implement view increment, leader rotation and replica updates.
        Preserve QCs, locks and committed history. Call each node's enter_view
        as appropriate and enqueue the next proposal event."""

        # 这个比较简单，视图加一，然后通知 4 个副本
        self.view += 1                                     # 视图 +1
        for node in self.nodes:
            node.enter_view(self.view, self.leader_id)     # 让每个副本进入新视图
        self.events.append(("propose", None))              # 排下一个提案事件

    # raise NotImplementedError('TODO A5 implement view increment, leader rotation and replica updates.')

    def crash_leader(self):
        leader = self.nodes[self.leader_id - 1]
        if not leader.crashed:
            leader.crashed = True
            self.log(f"Leader N{leader.id} crashed", "fault")

    def set_byzantine(self, node_id: int | None):
        if node_id is not None and node_id not in range(1, 5):
            raise ValueError("Node ID must be 1–4")
        for node in self.nodes:
            node.withhold_vote = node.id == node_id
        self.log(f"N{node_id} Byzantine: withholds votes only" if node_id else
                 "All nodes vote normally", "fault")

    def recover(self):
        # """A6 restore crashed replicas from a trusted live peer.
        # Catch up blocks, QCs, locks, committed chain and application state.
        # Preserve voting history so a replica cannot vote twice in one view.
        # Restore balances and receipts, and B6 nonces if implemented. If no live
        # peer is available, reject recovery without inventing state. No disk
        # persistence is required. Clear simulated faults and rejoin safely."""
        # raise NotImplementedError('TODO A6 restore crashed replicas from a trusted live peer.')

        # 寻找存活节点
        live = [node for node in self.nodes if not node.crashed]

        if not live:
            raise ValueError("cannot recover: no live peer available")

        # 从存活节点同步来源 优先选择提交链最长 HighQC 的 view
        source = max(
            live,
            key = lambda node: (
                len(node.committed_blocks),
                node.high_qc.view,
            ),
        )

        # 为崩溃节点恢复状态

        for node in self.nodes:
            if node.crashed:
                node.blocks = deepcopy(source.blocks)
                node.high_qc = deepcopy(source.high_qc)
                node.locked_qc = deepcopy(source.locked_qc)
                node.committed_blocks = source.committed_blocks.copy()
                node.machine = deepcopy(source.machine)
                # 不修改 node.id 和 node.last_voted_view

                #先解除状态 再进入 view
                node.crashed = False
                node.enter_view(self.view, self.leader_id)

                self.log(
                    f"N{node.id} recovered from N{source.id}",
                    "fault",
                )
            # 恢复操作清楚扣票故障 包括未崩溃节点
            node.withhold_vote = False
        self.phase = "recovery complete: faults cleared"


    def snapshot(self):
        source = max(self.nodes, key=lambda n: len(n.committed_blocks))
        committed = set(source.committed_blocks)
        node_states = []
        for node in self.nodes:
            node_states.append({
                "id": node.id, "view": node.view, "role": node.role,
                "crashed": node.crashed, "withhold_vote": node.withhold_vote,
                "high_qc": asdict(node.high_qc), "locked_qc": asdict(node.locked_qc),
                "latest_block": max(node.blocks.values(), key=lambda b: b.view).id,
                "committed_blocks": node.committed_blocks.copy(),
                "accounts": node.machine.accounts.copy(),
            })
        blocks = [{**asdict(block), "certificate": asdict(self.qcs[block.id]) if block.id in self.qcs else None,
                   "committed": block.id in committed,
                   "votes": sorted(self.votes.get(block.id, []))}
                  for block in self.blocks.values()]
        transactions = [{**asdict(tx), **source.machine.receipts.get(tx.id, {"status": "pending", "error": None})}
                        for tx in self.transactions.values()]
        live = [n for n in self.nodes if not n.crashed]
        consistent = bool(live) and all(n.machine.accounts == live[0].machine.accounts
                                       and n.committed_blocks == live[0].committed_blocks for n in live)
        return {"view": self.view, "leader_id": self.leader_id, "running": self.running,
                "steps": self.steps, "phase": self.phase, "nodes": node_states,
                "blocks": blocks, "mempool": [asdict(self.transactions[t]) for t in self.mempool],
                "transactions": transactions, "accounts": source.machine.accounts.copy(),
                # B6: committed nonces, and the nonce the next signed transfer must use.
                "nonces": source.machine.nonces.copy(),
                "next_nonces": {account: self.expected_nonce(account) for account in INITIAL_BALANCES},
                "committed_chain": source.committed_blocks.copy(), "consistent": consistent,
                "logs": list(self.logs), "quorum": self.QUORUM,
                "next_event": self.events[0][0] if self.events else "propose"}



    def select_transactions(self, parent: Block) -> list[Transaction]:
        """B2 select eligible pending transactions without consuming them.
        Return at most max_txs_per_block (default 5), excluding transaction IDs
        on the selected parent chain. An abandoned branch does not exclude an ID.
        Empty input returns an empty list. Keep IDs in the pool until commit.
        """
        # 1) 从 parent 沿父指针一路走回创世块，收集这条链上已经打包过的交易 ID。
        #    只看“这条父链”：别的（被废弃的）分支上的交易不在其中，所以仍可重新打包。
        used = set()
        current = parent
        while current is not None:
            used.update(tx.id for tx in current.transactions)
            current = self.blocks.get(current.parent_id) if current.parent_id else None

        # 2) 按提交顺序（mempool 的顺序）挑出不在父链上的交易，最多 max_txs_per_block 笔。
        #    只读不删：交易要等提交后才由 finalize_transactions() 清出池子。
        selected = []
        for tx_id in self.mempool:
            if len(selected) >= self.max_txs_per_block:
                break
            if tx_id not in used:
                selected.append(self.transactions[tx_id])
        return selected  # 没有可选交易时返回 []，即空块

    def finalize_transactions(self, committed_ids: list[str]):
        """B4 finalize pool entries after per-replica execution.
        committed_ids is ordered and contains newly committed blocks. Remove
        their transaction IDs from the pool, including rejected executions,
        and record useful transaction events. Repeated finalization is harmless.
        This method does not execute transfers or decide consensus.
        """
        # 回执存在各副本自己的状态机里；这里取一个存活副本的回执只用于写日志。
        live = next((n for n in self.nodes if not n.crashed), None)
        for block_id in committed_ids:
            block = self.blocks.get(block_id)
            if block is None:
                continue
            for tx in block.transactions:
                # 已经清理过的交易直接跳过，所以重复调用不会出错、也不会重复记日志。
                if tx.id not in self.mempool:
                    continue
                # 成功和被拒绝的交易都移出池子：两者都已有最终回执，不该再被打包。
                self.mempool.remove(tx.id)
                receipt = live.machine.receipts.get(tx.id) if live else None
                if receipt and receipt["status"] == "rejected":
                    self.log(f"{tx.id} rejected in {block_id}: {receipt['error']}", "fault")
                else:
                    self.log(f"{tx.id} executed in {block_id}: "
                             f"{tx.sender} -> {tx.receiver} {tx.amount}", "commit")

    def configure_batch(self, limit):
        """B5 set a positive integer batch limit and return the accepted value.
        Reject bool, zero, negatives and non-integers without changing state.
        Reset restores the default value 5 in this starter contract.
        """
        # type(...) is int 同时挡住 bool、浮点数和字符串；校验失败时不改状态。
        if type(limit) is not int or limit < 1:
            raise ValueError("Batch limit must be a positive integer")
        self.max_txs_per_block = limit
        self.log(f"Batch limit set to {limit} transactions per block", "info")
        return limit

    def inject_attack(self, kind: str, node_id: int):
        """A7 inject an active Byzantine action in the current experiment.
        Implement equivocation by the current leader plus duplicate_vote OR
        invalid_qc. Extend message delivery as needed so honest replicas receive
        the attack through normal validation paths. Log the action and supply
        assertions. Do not count the supplied withholding switch as this task.
        A malicious replica controls only its own simulator identity.
        """
        raise NotImplementedError("TODO A7 implement inject_attack")

    def dispatch_qc(self, qc: QC):
        """Provided integration wiring. Caller must validate/register the QC.

        Task A reports committed IDs; Task B executes their payload and cleans
        the pool. Empty payloads bypass Task B, not consensus validation.
        """
        newly_committed = set()
        for node in self.nodes:
            committed = node.receive_qc(qc)
            newly_committed.update(committed)
            if committed and any(node.blocks[b].transactions for b in committed):
                node.execute_committed(committed)
        ordered = sorted(newly_committed, key=lambda b: self.blocks[b].view)
        for block_id in ordered:
            self.log(f"{block_id} committed", "commit")
        if any(self.blocks[b].transactions for b in ordered):
            self.finalize_transactions(ordered)
        return ordered

    # 增加A2的检查 proposal validation
    def _valid_proposal(self, block: Block) -> bool:
        # 视图必须和协调器当前视图一致
        if block.view != self.view:
            return False
        # 提案人必须是当前视图的 leader
        if block.proposer != self.leader_id:
            return False
        # 提案人必须存活（否则这个提案是“死提案”，不能继续收集票）
        if self.nodes[block.proposer - 1].crashed:
            return False
        # 父块必须已知
        if block.parent_id is None or block.parent_id not in self.blocks:
            return False
        # 必须携带“父块的证书”，且该证书确实认证的是父块
        if block.qc is None or block.qc.block_id != block.parent_id:
            return False
        # 该证书必须已在协调器登记过
        if block.qc.block_id not in self.qcs:
            return False
        return True