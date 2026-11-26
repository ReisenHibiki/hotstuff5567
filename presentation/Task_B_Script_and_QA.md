# Task B（B1–B5）讲稿与答辩准备

对应 PPT：`presentation/COMP5567_HotStuff_Presentation_revised.pptx`
讲稿已写进每页的演讲者备注；下面是你负责部分的完整讲稿和答辩准备。

---

## 一、整体时间安排（4 分钟内，留 20 秒余量）

| 页 | 内容 | 时间 | 时长 |
| --- | --- | --- | --- |
| 1 | 标题 | 0:00–0:10 | 10 秒 |
| 2 | 系统设计 | 0:10–0:35 | 25 秒 |
| 3 | Task A：QC 与提交 | 0:35–1:20 | 45 秒 |
| **4** | **Task B：只有提交才改余额（你）** | **1:20–2:20** | **60 秒** |
| 5 | 扩展（B5 批量是你的） | 2:20–2:45 | 25 秒 |
| 6 | 测试结果 | 2:45–3:15 | 30 秒 |
| 7 | 局限性 | 3:15–3:40 | 25 秒 |

和原版相比的改动：第 6 页签名版测试数从 28/28 改为 31/31；第 7 页删掉了已经完成的 “Browser signing”，把 “Parent-QC validation” 改成更准确的 “QC evidence checks”；第 4 页讲稿补上了原来没讲到的 B2（选交易）；全部讲稿压缩到 3:40；删掉了备注里的本机路径。

---

## 二、你的讲稿

### 第 4 页（60 秒）

> Consider one transfer of ten from Alice to Bob. Admission checks the account names and that the amount is a strict integer, assigns an ID, and puts it in the pool. It does not check or spend funds.
>
> When a leader proposes, it takes up to five pending transactions, skipping only those already on the chosen parent chain, so a transaction from an abandoned proposal can be proposed again.
>
> Balances stay at one hundred, even when the QC for B2 forms. Only when the QC for B3 commits B1 does each replica execute it: Alice becomes ninety and Bob one hundred and ten.
>
> Execution follows block and payload order and writes a final receipt. If the same ID arrives again, the replica returns that receipt and does not transfer twice. A rejected transfer also gets a receipt, and both kinds then leave the pool.

每段对应的功能，讲的时候可以指着页面：

| 段落 | 对应 | 函数 |
| --- | --- | --- |
| 第 1 段 | B1 准入 | `HotStuffDemo.submit` |
| 第 2 段 | B2 选交易 | `HotStuffDemo.select_transactions` |
| 第 3 段 | B3 执行，指图表 | `Node.execute_committed`、`StateMachine.apply` |
| 第 4 段 | B4 回执与清理，指右侧 “Same ID on retry” | `StateMachine.apply`、`finalize_transactions` |

### 第 5 页中 B5 那一句（如果这页也由你讲）

> The batch limit is configurable. With the default of five, seven pending transactions are split into blocks of five and two.

### 第 6 页的失败用例（如果这页也由你讲）

> Alice starts with one hundred and sends eighty to Bob, leaving twenty. A second transfer of eighty to Charlie is rejected. Alice stays at twenty, and that transaction still receives a final rejected receipt.

这个例子就是 `tests/test_task_b.py` 里的 `test_insufficient_balance_and_same_id_retry`。

---

## 三、可能的提问与回答要点

按被问到的可能性排序。回答尽量先给一句结论，再给原因。

### B1 准入

**Q1. 为什么提交交易时不检查余额？**
因为提交时还不知道这笔交易前面会执行哪些交易，余额只有在区块被共识提交、按顺序执行时才确定。如果准入时检查，可能 Alice 提交时有 100，但同一区块里排在前面的交易先把钱花了。所以余额不足在执行时判定，产生 `rejected` 回执。

**Q2. 为什么用 `type(amount) is int` 而不是 `isinstance`？**
Python 里 `bool` 是 `int` 的子类，`isinstance(True, int)` 为真，会把 `True` 当成 1 接受。`type(...) is int` 能同时拒绝 `True` 和 `1.5`。测试会传 `0, -1, 1.5, True, 1000001`。

**Q3. 非法请求会不会改动状态？**
不会。所有校验都在创建交易、写入交易池之前完成，任何一项失败直接抛 `ValueError`（API 返回 400），交易编号也不会被占用。

**Q4. 交易 ID 怎么分配？重置后会怎样？**
`len(self.transactions) + 1`，即 Tx1、Tx2…。`transactions` 是只增不减的登记表，所以编号不会重复；`reset()` 清空它，编号回到 Tx1。

**Q5. 能不能自己转给自己？**
我们拒绝了。规范没有规定，这是我们的设计决定：自转账不改变任何余额，没有意义。

### B2 选交易

**Q6. 为什么不直接把已经打包过的交易排除掉？**（最可能被追问）
打包不等于提交。一个提案可能拿不到 QC 或 leader 崩溃，这个块就被废弃了。如果排除所有打包过的交易，废弃块里的交易就永远不会再被打包。所以我们只排除**所选父块这条链上**的交易 ID：从父块沿父指针走回创世块，收集链上的交易 ID。

**Q7. 选中的交易为什么不从交易池里删掉？**
因为提案可能被废弃。如果选中就删，交易就丢了。只有在交易所在区块真正提交后，`finalize_transactions` 才把它移出交易池。

**Q8. 同一笔交易会不会出现在两个分支上，被执行两次？**
可能出现在两个分支上，但只有一条分支会被提交，提交的那条链上同一 ID 只出现一次（选交易时排除了父链上已有的）。即使重复投递，`apply` 发现已有回执就直接返回，不会再扣款。

**Q9. 每次都从父块走回创世块，效率如何？**
复杂度和链长成正比。在本项目的演示规模下没有问题；真实系统需要缓存每个块的祖先交易集合。这可以算作局限性。

**Q10. 交易按什么顺序打包？**
按提交到交易池的顺序（先来先打包），最多 `max_txs_per_block` 笔，默认 5。

### B3 执行

**Q11. 怎么保证只执行已提交的交易？**
两层：第一，`dispatch_qc` 只把 `receive_qc` 返回的新提交块交给执行；第二，`execute_committed` 自己再检查每个块 ID 都在本副本的 `committed_blocks` 里，只要有一个不在，就在改动任何余额**之前**抛 `ValueError`。测试 `test_uncommitted_payload_not_executed` 验证了这一点。

**Q12. 为什么要“先全部检查，再执行”，而不是边检查边执行？**
如果边查边执行，前面的块已经扣了款，后面某个块不合法再报错，状态就只改了一半。先整体校验，保证要么全执行，要么一笔都不动。

**Q13. 四个副本的余额怎么保证一致？**
每个副本有自己的 `StateMachine`，各自执行。一致性来自确定性：所有副本提交同样的块序列，按同样的块顺序和块内交易顺序执行，执行规则里没有随机数或时间，所以结果一定相同。

**Q14. 为什么执行时还要再校验账户和金额？准入时不是查过了吗？**
执行层不信任准入层。区块的内容来自 leader，恶意 leader 可能放入未经准入的交易。在执行时再查一遍，保证每个副本按同样的规则得出同样的结论。

**Q15. 余额不足时会发生什么？**
不改任何余额，记录 `{"status": "rejected", "error": "Insufficient balance ..."}` 回执。交易仍属于已提交区块，同样会被移出交易池。

**Q16. 崩溃的副本会执行吗？**
不会，`execute_committed` 对崩溃副本直接返回。它恢复时由 A6 的 `recover` 从存活副本复制余额和回执来追赶。

### B4 回执与去重

**Q17. 同一个交易 ID 再来一次会怎样？**
`apply` 第一步就查 `receipts`，有回执就直接返回原回执，不再扣款。测试里同一笔交易调用两次 `execute_committed`，Alice 仍然只扣一次。

**Q18. 为什么失败的交易也要写回执？**
失败的交易也是已提交区块的一部分，它的结果是确定的、最终的。写回执一是让客户端知道结果，二是去重：如果不写，同一笔交易再投递时会被重新判断一次。

**Q19. 为什么去重检查要放在 `apply` 的最前面？**
如果先查余额再查回执，一笔之前成功的交易重试时，可能因为现在余额不足被判成 `rejected`，覆盖原来的结果。先查回执保证同一 ID 的结果永远不变。

**Q20. `finalize_transactions` 调用两次会出问题吗？**
不会。已经不在交易池里的 ID 直接跳过，第二次调用什么都不做，也不会重复写日志。

**Q21. 回执存在哪里？为什么不存在协调器里？**
存在每个副本自己的 `StateMachine.receipts` 里。执行是每个副本独立做的，回执是执行结果，应该和余额放在一起；协调器只负责交易池和日志。

### B5 批量

**Q22. 批量上限怎么设置？哪些值会被拒绝？**
`POST /api/config/batch`，body 是 `{"max_txs_per_block": 2}`。只接受正整数，拒绝 bool、0、负数、小数和字符串，拒绝时不改状态。重置后回到 5。

**Q23. 改了上限后，已经在交易池里的交易会怎样？**
不受影响，仍在池里等待。下一次出块时按新上限选取，比如 7 笔交易在上限 2 时会分成 2、2、2、1 四个块。

### 综合问题

**Q24. 共识提交是怎么触发执行的？**（项目核心，一定要能讲清）
`form_qc` 形成 QC 后调用 `dispatch_qc`。它对每个副本调用 `receive_qc`，由 Task A 的三链规则判断哪些块新提交；如果新提交的块里有交易，就调用该副本的 `execute_committed` 执行；最后调用 `finalize_transactions` 清理交易池。共识只决定“哪些块提交”，执行只处理“已提交的块”，两者通过这个函数连接。

**Q25. 为什么 QC(B2) 形成时余额还不变？**
HotStuff 需要连续视图里直接相连的三个认证块才能提交第一个。QC(B2) 形成时 B1 只有两层认证，还没提交；QC(B3) 形成时 B1 才提交，这时才执行 B1 里的交易。

**Q26. 你负责的部分用了 AI 吗？**
如实回答。B1–B5 的函数是在 AI（Claude）辅助下写的，代码里有 `[AI-assisted]` 标注，报告里也声明了；然后说明你自己理解并验证了哪些部分，并能当场解释任意一个函数。

---

## 四、上场前需要确认的事

1. **第 4、5 页的图表**：原版图表缺少内嵌数据表，Keynote 里显示为空白；已按原数据、位置和颜色重建，Keynote 中显示正常。
2. **演示用哪条分支**：第 5 页讲了 Ed25519 签名，但签名功能只在 `taskB6_recover` 分支，`main` 上没有。演示前和组员确认，最好先合并进 `main`。
3. **第 7 页的局限性**是根据 2026-11-24 的代码写的；如果组员在演示前补上了 A7 攻击注入，要再改一次。
4. **现场演示中你的部分**：提交一笔转账 → 一步步推进，指出 QC(B2) 时余额不变 → QC(B3) 后余额变化 → 看回执 → 提交一笔余额不足的转账，展示 `rejected` 回执。提前在自己电脑上完整练一遍。
