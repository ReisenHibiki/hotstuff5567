# COMP5567 HotStuff 全项目答辩准备材料

依据：`taskB6_recover` 分支最新代码（`a79e2ef`，包含 A1–A6、B1–B6）。`main` 分支只到 B5，没有 B6。
配套文档：`Task_B_QA_Bilingual.md`（B1–B5 细节）、`Demo_QA_Bilingual.md`（四个演示场景）、组员的 `QA_A6_B5_B6.md`（A6/B5/B6 细节）和 `DEMO_GUIDE.md`（演示操作）。

---

## 0. 一页总览

**一句话（EN）：** We simulate four HotStuff replicas in one Python process with a quorum of three. Task A decides which blocks are committed using the three-chain rule; Task B executes only committed blocks, deterministically, on each replica's own account state.
**一句话（中文）：** 一个 Python 进程模拟 4 个 HotStuff 副本，法定人数 3。Task A 用三链规则决定哪些块被提交；Task B 只执行已提交的块，每个副本在自己的账户状态上确定性地执行。

| 项 | 分值 | 状态 | 负责人 | 主要函数 | 文件 |
| --- | ---: | --- | --- | --- | --- |
| A1 提案 | 6 | 完成 | 蒋恒宇 | `propose` | hotstuff.py |
| A2 安全投票 | 8 | 完成 | 蒋恒宇 | `vote`、`_valid_proposal`、`Node.can_vote`、`Node.extends` | hotstuff.py、node.py |
| A3 QC | 6 | 完成 | 蒋恒宇 | `form_qc` | hotstuff.py |
| A4 锁定与提交 | 8 | 完成 | 蒋恒宇 | `Node.receive_qc` | node.py |
| A5 视图切换 | 2 | 完成 | 蒋恒宇 | `next_view`、`Node.enter_view` | hotstuff.py、node.py |
| A6 恢复（可选） | 2 | 完成 | 组员 | `timeout`、`recover` | hotstuff.py |
| A7 恶意节点（可选） | 3 | **未完成**：只有按接收者投递的 `_deliver_proposal`，`inject_attack` 仍是 TODO | 谭尚谋 | `_deliver_proposal` | hotstuff.py |
| B1 准入 | 5 | 完成 | **李佳阳（你）** | `submit` | hotstuff.py |
| B2 选交易 | 5 | 完成 | **你** | `select_transactions` | hotstuff.py |
| B3 执行 | 8 | 完成 | **你** | `Node.execute_committed`、`StateMachine.apply` | node.py、blockchain.py |
| B4 回执与去重 | 7 | 完成 | **你** | `apply`（`_apply_transfer`）、`finalize_transactions` | blockchain.py、hotstuff.py |
| B5 批量（可选） | 2 | 完成 | **你** | `configure_batch` | hotstuff.py |
| B6 签名与 nonce（可选） | 3 | 完成（缺独立的 `test_security.py`） | 组员 | `security.py`、`submit`、`apply` | security.py 等 |

负责人一栏请和组员核对后再写进贡献表。

---

## 1. 系统结构

### 1.1 文件分层

| 文件 | 作用 |
| --- | --- |
| `frontend/app.js`、`index.html`、`signing.js` | 浏览器面板；B6 用 WebCrypto 在浏览器签名 |
| `backend/main.py` | FastAPI 接口：状态、控制（start/step/reset/crash/recover）、提交交易、拜占庭开关、批量配置、攻击 |
| `backend/hotstuff.py` | 协调器 `HotStuffDemo`：事件队列、提案、投票、QC、视图、交易池 |
| `backend/node.py` | 每个副本 `Node`：投票规则、锁、提交判断、执行入口 |
| `backend/blockchain.py` | `StateMachine`：余额、回执、nonce |
| `backend/models.py` | 数据结构 `Transaction`、`QC`、`Block` |
| `backend/security.py` | B6：规范化载荷、交易 ID、验签 |

### 1.2 数据结构

| 结构 | 字段 | 说明 |
| --- | --- | --- |
| `Transaction`（不可变） | id、sender、receiver、amount、nonce、signature | 基础版 ID 为 Tx1…；B6 为 `tx-` + 载荷的 SHA-256 |
| `QC`（不可变） | block_id、view、voters | 认证某个块的证书 |
| `Block` | id、parent_id、view、proposer、transactions、qc | **`qc` 是父块的证书，不是自己的** |
| `Node` | view、role、high_qc、locked_qc、blocks、committed_blocks、machine、last_voted_view、crashed、withhold_vote | 每个副本各自一份 |
| `StateMachine` | accounts、receipts、nonces | 每个副本各自一份 |

初始状态：创世块 B0（view 0），创世 QC 由 4 个节点认证；三个账户各 100；view 1，leader N1。

### 1.3 事件队列

`step()` 每次取出一个事件执行，一步就是一个可见的协议动作。五种事件：

| 事件 | 函数 | 作用 |
| --- | --- | --- |
| `propose` | `propose` | leader 出块 |
| `vote` | `vote` | 一个副本投票 |
| `qc` | `form_qc` | 生成 QC |
| `next_view` | `next_view` | 进入下一视图 |
| `timeout` | `timeout` | 逻辑超时倒计时 |

队列为空时自动补一个 `propose`。遇到 TODO（`NotImplementedError`）会回滚到执行前的状态并暂停。

**为什么用事件队列？** 确定性：同样的操作每次结果一样，方便测试和逐步演示；没有真实网络，所以用队列模拟消息传递。

### 1.4 共识 → 执行的连接（最核心）

```
form_qc → dispatch_qc → 每个副本 receive_qc（Task A 决定新提交了哪些块）
                      → 有交易就调 execute_committed（Task B 执行）
                      → finalize_transactions（清理交易池）
```

`dispatch_qc` 是课程提供的，不算任何人的分。

---

## 2. 一轮完整流程（以两笔转账演示为例）

| 步 | 事件 | 发生了什么 | 余额 |
| --- | --- | --- | --- |
| 0 | — | 提交两笔交易进入交易池 | 100 |
| 1 | propose | N1 出块 B1（父 B0，带 QC(B0)），打包两笔交易 | 100 |
| 2–5 | vote | N1–N4 依次投票 | 100 |
| 6 | qc | QC(B1) 形成，HighQC = B1 | 100 |
| 7 | next_view | view 2，leader N2 | 100 |
| 8–13 | … | N2 出空块 B2，QC(B2) 形成，**LockedQC = QC(B1)** | 100 |
| 15–20 | … | N3 出空块 B3，**QC(B3) 形成 → B1 提交 → 执行** | Alice 20、Bob 180 |

---

## 3. Task A 逐项讲解

### A1 提案 `propose`

**做什么：** leader 崩溃就安排超时（A6）；否则父块 = leader 的 HighQC 所认证的块；新块 ID 为 `B{块数}`，`qc` 字段放 HighQC（即父块的证书）；交易池非空才调 `select_transactions`，否则空块；通过 `_deliver_proposal` 发给存活节点，并为每个存活节点排一个投票事件。

**为什么按 HighQC 选父块？** HighQC 是已知最新的已认证块，在它上面出块能继承最新进度，也最容易让锁定在较新分支的副本投票。

> **EN:** The leader builds on the block certified by its highest QC and attaches that QC as the justification. This extends the latest certified progress.
> **中文：** leader 在自己最高 QC 认证的块上出块，并把这个 QC 作为依据附上，从而延续最新的已认证进度。

### A2 安全投票 `vote` + `_valid_proposal` + `can_vote` + `extends`

**两层检查：**

1. 协调器 `_valid_proposal`：view 等于当前 view；提案人是当前 leader 且存活；父块已知；提案带的 QC 认证的正是父块，且该 QC 已登记。
2. 副本 `can_vote`：未崩溃、未设拒投；块的 view 等于自己的 view；**本 view 没投过票**（`last_voted_view`）；**安全规则**：父块扩展自己锁定的块，或者提案带的 QC 比自己的锁更新。

**`extends`**：沿父指针往上走，找到祖先返回 True；带 `seen` 集合防止异常数据死循环；块未知返回 False。

**投票后：** 用集合记录投票者（去重）；达到 3 票只排一次 `qc` 事件；票不够且队列里没有更多投票，就安排超时。

**为什么一个 view 只投一票？** 防止同一个副本给同一 view 的两个冲突块都投票，这是 QC 不冲突的前提。

**为什么有“或者 QC 更新”这条？** 这是活性：如果只能扩展锁定分支，锁在旧分支上的副本可能永远投不出票。看到更高 view 的 QC，说明已有法定人数接受了新分支，可以安全切换。

> **EN:** A replica votes at most once per view, and only for a block that extends its locked block or carries a QC newer than its lock. The first part gives safety, the second gives liveness.
> **中文：** 副本每个 view 最多投一票，只给扩展其锁定块、或带有比锁更新的 QC 的块投票。前者保证安全，后者保证活性。

### A3 QC `form_qc`

**做什么：** 块必须已知；收集者（提案人）崩溃就安排超时、不出 QC（A6）；只统计 1–4 号节点、去重；不足 3 票抛错，绝不生成 QC；生成 `QC(块, view, 投票者)`，登记，调 `dispatch_qc`，再排 `next_view`。

> **EN:** A QC needs at least three distinct valid voters for the same block and view. With fewer, no QC is created.
> **中文：** QC 需要同一个块、同一个 view 至少 3 个不同的有效投票者，不足就不生成。

### A4 锁定与提交 `receive_qc`

**做什么（收到 QC(X) 时）：**

1. 崩溃副本不处理；X 未知或 view 不符就拒绝。
2. QC 的 view 更高就更新 HighQC。
3. **锁定**：把锁更新为 X 携带的父块证书（即锁定 X 的父块），只往更高的 view 走。
4. **提交**：若 X、父块、祖父块的 view 连续（v、v-1、v-2）且直接相连，就提交祖父块，连同所有未提交的祖先，按祖先在前的顺序返回。
5. **不在这里执行交易。**

例：收到 QC(B2) 时锁定 B1；收到 QC(B3) 时提交 B1。

**为什么要三个块？** 见第 5 节。**为什么要连续 view？** 有间隔说明中间某个 view 可能在别的分支上形成过 QC，锁定的论证不成立。

> **EN:** QC(B2) locks B1; QC(B3) proves a quorum has locked B1, so B1 can never be reverted and is committed. A QC never commits its own block.
> **中文：** QC(B2) 锁定 B1；QC(B3) 证明已有法定数量的副本锁定了 B1，B1 不可能再被推翻，于是提交。QC 永远不会提交它自己的块。

### A5 视图切换 `next_view` + `enter_view`

view 加一；leader = `(view - 1) % 4 + 1`，即 N1→N2→N3→N4 轮换；每个存活副本更新 view 和角色，**不清除锁和投票记录**；崩溃副本保持冻结；排下一个 `propose`。

**为什么轮换 leader？** 避免单个 leader 长期控制系统；一个坏 leader 最多耽误自己的那个 view。

### A6 恢复 `timeout` + `recover`（组员，详见 `QA_A6_B5_B6.md`）

- **三处发现失败**：提案时 leader 已崩溃、票不够且没有更多投票、收集者在 QC 前崩溃。
- **超时**：逻辑计数 3 步，然后 `next_view("timeout")`，换下一个 leader。
- **恢复**：从提交链最长（并列看 HighQC）的存活副本**深拷贝**区块、HighQC、LockedQC、提交链和整个状态机（余额、回执、nonce）；**保留自己的 `last_voted_view`**，防止同一 view 投两次；同时清除拒投故障。没有存活节点就拒绝恢复。
- **法定人数永不降低**：只剩 2 个投票者就停滞，不形成假 QC。

### A7 恶意节点（未完成）

- 已做：`_deliver_proposal` 可以只发给指定接收者，同一块 ID 不允许不同内容（测试 `test_deliver_only_to_selected_live_nodes`）。
- 未做：`inject_attack`（冲突提案、重复投票或无效 QC 注入），调用会返回 501。
- 面板上的“拜占庭”开关只是**拒绝投票**，规范明确说这不算 A7 的分。
- 被问到如实说：A7 不申报分数。

---

## 4. Task B 逐项讲解（你的部分，细节见 `Task_B_QA_Bilingual.md`）

| 项 | 核心逻辑 | 关键设计 |
| --- | --- | --- |
| B1 `submit` | 校验账户、不允许自转账、金额是 1–1000000 的严格整数；全部通过才创建交易、入池 | 不查余额；`type(x) is int` 排除 bool；先校验后写状态 |
| B2 `select_transactions` | 从父块走回创世块收集已打包 ID；按池顺序选不在其中的，最多上限笔 | 只排除父链（废弃分支可重新打包）；只读不删 |
| B3 `execute_committed` | 崩溃直接返回；先检查所有块都已提交，再按块顺序和块内顺序调 `apply` | 先查后执行，避免改一半；确定性顺序保证一致 |
| B3/B4 `_apply_transfer` | 先查回执（去重）；再查账户、金额、余额；成功扣款入账写 committed，失败写 rejected | 去重放最前，结果永不改变；失败也是最终回执 |
| B4 `finalize_transactions` | 把已提交块里的交易移出池（成功失败都移），写日志 | 已移出的跳过，重复调用无害 |
| B5 `configure_batch` | 只接受正整数，失败不改状态，Reset 恢复 5 | 只是出块策略，不影响安全 |

**拒绝发生在两个阶段（TA 问过）：** 准入拒绝格式错误（ValueError，不进池，无回执）；执行拒绝余额不足（rejected 回执，移出池）。

---

## 5. 理论：为什么这样设计是安全的

### 5.1 n = 4、f = 1、法定人数 3

BFT 需要 n ≥ 3f + 1。n = 4 时 f = 1，法定人数 2f + 1 = 3。**任意两个 3 人集合至少重叠 2 人，其中至少 1 个诚实**。诚实节点每个 view 只投一票，所以同一 view 不会有两个冲突块都拿到 QC。

> **EN:** Any two quorums of three out of four share at least one honest replica, so two conflicting blocks cannot both be certified in the same view.
> **中文：** 4 个里任意两个 3 人集合至少共享一个诚实副本，所以同一 view 的两个冲突块不可能都被认证。

### 5.2 为什么是三链

| QC | 证明了什么 |
| --- | --- |
| QC(B1) | B1 被认证：view 1 不会有冲突块的 QC |
| QC(B2) | 投 B2 的副本看到了 QC(B1)，开始**锁定** B1 |
| QC(B3) | 投 B3 的 3 个副本都看到了 QC(B2)，即**法定数量的副本已锁定 B1**。此后任何 QC 都要经过一个锁定 B1 的诚实副本，冲突块再也拿不到 QC，B1 不可逆 → 提交 |

**为什么不是两链？** 两阶段协议（PBFT、Tendermint）换 leader 时有“隐藏的锁”：新 leader 不知道某个副本锁在更高的 QC 上，只能等一个最大网络延迟。HotStuff 多一个阶段，新 leader 只需拿自己最高的 QC 就能出块，换来**响应性**（按网络实际速度推进）和**线性**的视图切换。

### 5.3 安全优先于活性

只剩 2 个投票者时宁可停滞，也不降低法定人数形成假 QC。降低到 2 的话，{N1, N2} 和 {N3, N4} 可以认证冲突的块。

### 5.4 共识与执行分离

共识只决定“提交什么”，执行只处理“已提交的”。所以 QC(B1)、QC(B2) 时余额不变；失败的交易不影响区块有效性；各副本按同样顺序执行，结果一致。

---

## 6. B6 要点（组员，详见 `QA_A6_B5_B6.md`）

- **签名**：Ed25519（Python `cryptography` 库；浏览器 WebCrypto）。确定性签名，浏览器和 Python 签出的结果逐字节一致。
- **签什么**：规范化 JSON：domain（`COMP5567-HotStuff-2026/transfer/v1`）、sender、receiver、amount、nonce，排序键、无空格。domain 防止跨系统重放。
- **交易 ID**：`tx-` + 载荷的 SHA-256，**不含签名**，防止换签名得到新 ID 重复执行。
- **两次验签**：准入 `submit` 一次，执行 `apply` 一次（不信任 leader）。
- **nonce**：每个账户从 0 开始；只有提交后的执行消耗，且只消耗一次，**包括已认证但余额不足的失败**；签名错误、nonce 错误不消耗。
- **重放**：相同请求得到相同 ID，提交前返回原交易，提交后返回原回执。
- **未来 nonce 策略**：准入只接受恰好下一个；执行时若遇到未来 nonce，拒绝但不存最终回执；过旧 nonce 存最终 rejected。
- **伪造签名不存回执**：否则伪造者可以用真交易的 ID 抢先占用，让真交易永远被当成重复。

---

## 7. 测试（31 个全部通过，2026-11-25 组员实测）

| 文件 | 测试 | 证明什么 |
| --- | --- | --- |
| test_framework.py | `test_initial_snapshot`、`test_missing_event_can_be_retried`、`test_reset_framework` | 框架初始状态、TODO 可重试、Reset |
| test_task_a.py | `test_empty_chain_commits` | 空块也能三链提交 |
| | `test_one_qc_does_not_commit_own_block` | 一个 QC 不提交自己的块（A4） |
| | `test_quorum_not_reached` | 不足 3 票不出 QC（A3） |
| test_task_b.py | `test_admission_does_not_execute` | 准入不改余额（B1） |
| | `test_pool_excludes_only_selected_ancestry` | 只排除父链（B2） |
| | `test_insufficient_balance_and_same_id_retry` | 余额不足被拒、同 ID 返回原回执（B3/B4） |
| | `test_committed_execution_and_cleanup` | 已提交执行、重复执行无害、清池（B3/B4） |
| | `test_uncommitted_payload_not_executed` | 未提交的不执行（B3） |
| test_integration.py | `test_three_chain_and_transfer` | 完整三链 + 转账 |
| | `test_insufficient_funds_rejected_at_commit` | 余额不足在提交时被拒 |
| | `test_lock_and_one_vote_per_view` | 锁和一 view 一票（A2/A4） |
| | `test_batching_and_ancestor_deduplication` | 7 笔分成 5 + 2（B2） |
| | `test_reset_clears_faults_events_and_accounts` | Reset 清除一切 |
| | `test_invalid_transaction_inputs` | 非法输入被拒（B1） |
| test_recovery.py（8 个） | 崩溃 leader 超时恢复、拜占庭拒投与轮换、两个投票者停滞、孤儿交易重新打包、view 间隔延迟提交、收集者 QC 前崩溃、恢复追赶空链、恢复保留签名状态 | A6 |
| test_batch.py（2 个） | `test_limits`、`test_reject_invalid` | B5 |
| test_attacks.py（1 个） | `test_deliver_only_to_selected_live_nodes` | A7 的投递部分 |
| test_dashboard_signing.py（3 个） | 浏览器签名与 Python 一致、快照报告 nonce、无存活节点时 nonce 为空 | B6 前端 |

PPT 上的 27 = `main`（17 + 10）；31 = `taskB6_recover`（17 + 14）。

---

## 8. 已知局限（如实回答，不要回避）

| 局限 | 说明 |
| --- | --- |
| A7 未完成 | `inject_attack` 是 TODO；拜占庭开关只是拒投 |
| QC 证据检查 | 接受 QC 时只核对它是否登记、块和 view 是否匹配，不独立重验投票者 |
| 单进程模拟 | 没有真实网络、没有持久化，超时是逻辑步数 |
| 可信恢复 | 从“可信”存活节点复制状态；真实系统要验证 QC 或向 f+1 个节点核对 |
| 选交易效率 | 每次从父块走回创世块，复杂度和链长成正比 |
| B6 测试 | 缺独立的 `test_security.py`（篡改、错误账户、重放、nonce 递增） |
| Reset 后重放 | Reset 清空 nonce，旧签名可以再次提交 |
| 全部崩溃后恢复 | 接口没捕获异常，返回 500（应为 400） |
| 分支 | B6 不在 `main` 上；`changes.md` 尚未填完 |

---

## 9. 全项目快问快答（中英）

**Q1. What is HotStuff's main advantage? / HotStuff 的主要优点？**
> EN: Linear view change and responsiveness: a new leader only needs the highest QC, and the protocol moves at actual network speed.
> 中文：视图切换是线性的，且具有响应性：新 leader 只需最高 QC，协议按实际网络速度推进。

**Q2. What is HighQC vs LockedQC? / HighQC 和 LockedQC 的区别？**
> EN: HighQC is the newest QC a replica has seen; the leader builds on it. LockedQC is the QC a replica will protect; it only votes for blocks extending it unless shown a newer QC.
> 中文：HighQC 是副本见过的最新 QC，leader 在它上面出块；LockedQC 是副本要保护的 QC，除非看到更新的 QC，否则只给扩展它的块投票。

**Q3. Why does a block carry its parent's QC, not its own? / 块为什么带父块的 QC？**
> EN: Its own QC doesn't exist yet when it is proposed. The parent's QC justifies that the block extends certified progress.
> 中文：出块时自己的 QC 还不存在。带父块的 QC 是证明这个块延续了已认证的进度。

**Q4. What if two leaders propose in the same view? / 同一 view 两个提案怎么办？**
> EN: Only the current leader's proposal passes validation, and each honest replica votes once per view, so at most one block per view gets a QC.
> 中文：只有当前 leader 的提案能通过校验，诚实副本每个 view 只投一票，所以每个 view 最多一个块拿到 QC。

**Q5. Why does the commit include ancestors? / 提交为什么包含祖先？**
> EN: If a block commits, all its ancestors are also final. Earlier blocks that never got their own three-chain, for example after a view gap, are committed together, ancestor first.
> 中文：一个块提交了，它的祖先也必然是最终的。之前因 view 间隔没形成三链的块，会一起按祖先在前的顺序提交。

**Q6. Why can't receive_qc execute transactions? / receive_qc 为什么不执行交易？**
> EN: Separation of concerns: consensus decides order and finality; execution is a separate deterministic step. It keeps voting and lock rules independent of application state.
> 中文：职责分离：共识决定顺序和最终性，执行是独立的确定性步骤，这样投票和锁的规则不受应用状态影响。

**Q7. How do you know all replicas agree? / 怎么知道副本一致？**
> EN: Same committed chain plus deterministic execution in the same order. The dashboard compares live balances and chains, and our tests also check receipts and nonces.
> 中文：提交链相同，加上按同样顺序确定性执行。面板比较存活节点的余额和链，测试还检查回执和 nonce。

**Q8. Is the leader trusted? / leader 可信吗？**
> EN: No. Replicas validate the proposal, check the lock rule, and re-validate transactions and signatures at execution.
> 中文：不可信。副本校验提案、检查锁规则，执行时还会重新校验交易和签名。

**Q9. Why logical timeouts? / 为什么用逻辑超时？**
> EN: Determinism: tests and step-by-step demos give the same result every time and pause cleanly.
> 中文：确定性：测试和逐步演示每次结果一样，暂停也不受影响。

**Q10. What would you improve next? / 下一步改进什么？**
> EN: Finish A7 attack injection, independently re-verify QC voters, add security tests for B6, and run on a real network with persistence.
> 中文：完成 A7 攻击注入，独立重验 QC 投票者，为 B6 补安全测试，并在真实网络和持久化存储上运行。

**Q11. Did you use AI? / 用了 AI 吗？**
> EN: Yes, for assistance with individual functions, marked in the code and disclosed in the report. Each of us can explain our functions.
> 中文：用了，用于辅助单个函数，代码中有标注，报告中有声明。每个人都能讲清自己负责的函数。

---

## 10. 考前 5 分钟速记

1. **4 个节点、容错 1、法定 3**：任意两个法定集合有一个诚实副本重叠。
2. **QC(B2) 锁 B1，QC(B3) 提交 B1**：一个 QC 不提交自己的块；必须连续 view、直接相连。
3. **一 view 一票 + 锁规则**：扩展锁定块，或带更新的 QC。
4. **共识决定提交什么，执行只处理已提交的**：`dispatch_qc` 是连接点。
5. **准入不查余额；只排除父链；先查回执；失败也有最终回执；提交后才出池。**
6. **崩溃：超时换 leader，3 票照常；恢复深拷贝状态但保留自己的投票记录；只剩 2 票就停。**
7. **B6：ID 由载荷算、不含签名；验签两次；nonce 只在提交执行时消耗，余额不足也消耗。**
8. **A7 没做完，拜占庭开关只是拒投，如实说。**
