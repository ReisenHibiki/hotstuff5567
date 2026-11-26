# COMP5567 HotStuff 演讲讲稿（分 Part，标注任务编号）

对应 PPT：`COMP5567_HotStuff_Presentation_revised.pptx`（与 PPT 演讲者备注内容一致）
总时长：3 分 40 秒（规定 4 分钟，留 20 秒余量）

标注说明：每句话前的 **[A1]**、**[B3]** 等表示这句话讲的是哪个评分项；**[通用]** 表示系统整体说明，不对应单个评分项。

## 总览

| Part | 页 | 主题 | 时间 | 覆盖的任务 |
| --- | --- | --- | --- | --- |
| 1 | 1 | 开场 | 0:00–0:10（10 秒） | — |
| 2 | 2 | 系统设计 | 0:10–0:35（25 秒） | 通用、A3、B3 |
| 3 | 3 | **Task A** 认证与提交 | 0:35–1:20（45 秒） | **A1、A2、A3、A4、A5** |
| 4 | 4 | **Task B** 只有提交才改余额 | 1:20–2:20（60 秒） | **B1、B2、B3、B4** |
| 5 | 5 | 扩展功能 | 2:20–2:45（25 秒） | **B5、A6、B6** |
| 6 | 6 | 测试结果 | 2:45–3:15（30 秒） | 全部测试、B3/B4 失败用例 |
| 7 | 7 | 局限性 | 3:15–3:40（25 秒） | A7、A2/A4、集成 |

A7（恶意节点）没有完成，所以只在 Part 7 作为局限性提到。

---

## Part 1 · 开场（第 1 页，10 秒）

> Hello everyone. Our HotStuff project connects consensus commitment to account transactions. We will show how that works, followed by our results and limitations.

中文大意：我们的项目把共识提交和账户交易连接起来，接下来讲它怎么工作，再讲结果和局限。

---

## Part 2 · 系统设计（第 2 页，25 秒）

> **[通用]** A client sends a transaction into the pending pool.
> **[通用 / A3]** Four replicas run inside one Python process, and a fixed quorum of three certifies a block.
> **[通用]** Consensus first decides the committed history.
> **[B3]** Each replica then executes that history on its own balances and receipts.
> **[通用]** The figure shows logical flow, not a real network.

中文大意：客户端把交易放进交易池；一个进程里模拟 4 个副本，3 票成证；先由共识决定提交哪些块，再由每个副本各自执行、各自维护余额和回执。

讲的时候指图：从左到右依次是 Client → Pending pool → 4 replicas（Quorum = 3）→ Committed block → Accounts。

---

## Part 3 · Task A：认证与提交（第 3 页，45 秒）

> **[A5]** Leaders rotate by view
> **[A1]** and select a parent using HighQC. Each new proposal carries its parent's QC.
> **[A2]** A replica votes at most once per view and follows the locked-branch or newer-QC rule.
> **[A3]** Three distinct voters certify the same block and view.
> **[A4]** In this snapshot, B1, B2 and B3 occupy consecutive views and link directly. When the QC for B3 forms, B1 becomes committed, together with any uncommitted ancestors in order. B2 and B3 are only certified. So a QC alone never commits its own block.

| 标注 | 评分项 | 对应函数 | 讲解要点 |
| --- | --- | --- | --- |
| A1 | 提案（6 分） | `HotStuffDemo.propose` | 按 HighQC 选父块，提案带上父块的 QC |
| A2 | 安全投票（8 分） | `vote`、`Node.extends`、`Node.can_vote` | 每个视图最多投一票；要么扩展锁定分支，要么带更新的 QC |
| A3 | 法定证书（6 分） | `form_qc` | 同一块、同一视图、3 个不同投票者才成 QC |
| A4 | 锁定与提交（8 分） | `Node.receive_qc` | 连续视图、直接相连的三链，第三个 QC 提交第一个块 |
| A5 | 视图切换（2 分） | `next_view`、`Node.enter_view` | 每轮成功后视图加一，leader 轮换 |

讲 A4 时指图：B1 绿色 COMMITTED，B2、B3 蓝色 CERTIFIED，底部箭头 “commits B1”。

---

## Part 4 · Task B：只有提交才改余额（第 4 页，60 秒）

> **[B1]** Consider one transfer of ten from Alice to Bob. Admission checks the account names and that the amount is a strict integer, assigns an ID, and puts it in the pool. It does not check or spend funds.
> **[B2]** When a leader proposes, it takes up to five pending transactions, skipping only those already on the chosen parent chain, so a transaction from an abandoned proposal can be proposed again.
> **[B3]** Balances stay at one hundred, even when the QC for B2 forms. Only when the QC for B3 commits B1 does each replica execute it: Alice becomes ninety and Bob one hundred and ten. Execution follows block and payload order
> **[B4]** and writes a final receipt. If the same ID arrives again, the replica returns that receipt and does not transfer twice. A rejected transfer also gets a receipt, and both kinds then leave the pool.

| 标注 | 评分项 | 对应函数 | 讲解要点 |
| --- | --- | --- | --- |
| B1 | 准入与交易池（5 分） | `HotStuffDemo.submit` | 校验账户和严格整数金额，分配 Tx1、Tx2…；不查也不改余额 |
| B2 | 区块载荷（5 分） | `HotStuffDemo.select_transactions` | 最多 5 笔；只排除所选父链上的交易，废弃提案里的交易可重新打包 |
| B3 | 状态执行（8 分） | `Node.execute_committed`、`StateMachine.apply` | 只执行已提交的块，按块顺序和块内顺序；余额不足不改余额 |
| B4 | 回执与去重（7 分） | `StateMachine.apply`、`finalize_transactions` | 成功和失败都写最终回执；同一 ID 返回原回执；提交后移出交易池 |

讲 B3 时指图表：灰色柱是提交前（100 / 100），绿色柱是提交后（90 / 110）。讲 B4 时指右侧 “Same ID on retry”。

---

## Part 5 · 扩展功能（第 5 页，25 秒）

> **[B5]** The batch limit is configurable. With the default of five, seven pending transactions are split into blocks of five and two.
> **[A6]** Recovery copies history, balances, receipts and nonces from a trusted live replica, and never lowers the quorum: two available voters must stall.
> **[B6]** Ed25519 signatures and account nonces protect transaction identity on retries.

| 标注 | 评分项 | 对应函数 | 讲解要点 |
| --- | --- | --- | --- |
| B5 | 批量配置（可选 2 分） | `configure_batch`、`select_transactions` | 正整数上限，支持 1、2、5；指左侧柱状图 5 + 2 |
| A6 | 崩溃恢复（可选 2 分） | `timeout`、`recover` | 从存活副本复制状态；法定人数永远是 3，只剩 2 个就停住 |
| B6 | 交易安全（可选 3 分） | `sign_transaction`、`verify_transaction`、`transaction_id` | 准入和执行时各验一次签名；nonce 防重放；ID 由载荷推导 |

注意：B6 目前只在 `taskB6_recover` 分支上，演示前要确认是否已合并到 `main`。

---

## Part 6 · 测试结果（第 6 页，30 秒）

> **[全部]** We tested two versions separately. The basic version passes all twenty-seven public and extension tests; the signature version passes all thirty-one.
> **[B3 / B4]** The table shows a rejected transfer. Alice starts with one hundred and sends eighty to Bob, leaving twenty. A second transfer of eighty to Charlie is rejected. Alice stays at twenty, and that transaction still receives a final rejected receipt.

讲解要点：

- 27 = `main` 分支（A1–A6、B1–B5）：公开测试 17 个 + 扩展测试 10 个。
- 31 = `taskB6_recover` 分支（再加 B6）：公开测试 17 个 + 扩展测试 14 个。
- 表格里的失败用例同时证明了 B3（余额不足不扣款）和 B4（失败也有最终回执），对应测试 `test_insufficient_balance_and_same_id_retry`。

---

## Part 7 · 局限性（第 7 页，25 秒）

> **[A2 / A4]** Some limits remain. QCs are accepted from our registry, but their voters are not re-verified.
> **[A7]** Active attack injection is incomplete.
> **[集成]** We still need end-to-end tests across all extensions, and the prototype has no real network or persistent storage.
> We will now demonstrate the system live.

| 标注 | 讲解要点 |
| --- | --- |
| A2 / A4 | 提案校验只检查 QC 是否在协调器里登记过，不重新核验 QC 里的投票者 |
| A7 | `inject_attack` 未实现，冲突提案注入没有完成（可选 3 分未拿） |
| 集成 | 签名版和基础版分开测试，还没有覆盖全部扩展的端到端测试；没有真实网络和持久化存储 |

最后一句直接衔接 4 分钟现场演示。

---

## 分工建议（按 Part 切分）

| Part | 内容 | 建议讲者 |
| --- | --- | --- |
| 1–2 | 开场、系统设计 | 待定 |
| 3 | Task A（A1–A5） | 负责 Task A 的组员 |
| 4 | Task B（B1–B4） | LI Jiayang（你） |
| 5 | 扩展（B5、A6、B6） | B5 可由你讲，A6、B6 由对应组员讲 |
| 6–7 | 测试、局限性 | 待定 |

换人时不用说 “now my teammate will…”，直接接下一句，能省几秒。
