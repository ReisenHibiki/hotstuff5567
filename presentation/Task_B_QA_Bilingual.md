# Task B1–B5 答辩问答（中英双语）

答辩只有一个问题，通常是基础的功能实现、逻辑解释或设计思路。下面按你负责的五项整理，每个问题给出可以直接说的英文回答和对应中文。

回答技巧：先一句结论，再一句原因，最后（可选）一句例子或代码位置。控制在 20–30 秒。

---

## 〇、万能开场：Task B 整体是怎么工作的？

**Q: Can you explain how your part of Task B works?**
**问：你负责的 Task B 部分是怎么工作的？**

> **EN:** A transaction goes through four steps. First, `submit` validates it and puts it in the pool without touching balances. Second, when a leader proposes, `select_transactions` picks up to five pending transactions that are not already on the parent chain. Third, only after consensus commits the block, each replica runs `execute_committed`, which applies the transactions in order. Finally, every transaction gets a receipt, and `finalize_transactions` removes it from the pool.
>
> **中文：** 一笔交易经过四步。第一，`submit` 校验后放进交易池，不碰余额。第二，leader 出块时，`select_transactions` 选最多 5 笔不在父链上的交易。第三，只有区块被共识提交后，每个副本才调用 `execute_committed` 按顺序执行。最后，每笔交易都得到回执，`finalize_transactions` 把它移出交易池。

**一句话记忆：准入不碰钱，出块不删交易，提交才执行，执行必有回执。**

---

## ★ 阶段类问题（TA 实际问过：“rejection 发生在哪个阶段？”）

这类问题考的是：一笔交易从提交到结束，**每件事发生在哪一步**。先记住交易的生命周期：

| 阶段 | 函数 | 交易状态 | 余额 | 回执 | 交易池 |
| --- | --- | --- | --- | --- | --- |
| ① 准入 | `submit` | pending（待处理） | 不变 | 无 | 加入 |
| ② 出块 | `select_transactions` | proposed（已打包） | 不变 | 无 | 仍在 |
| ③ 认证 | Task A：QC(B2) 形成 | certified（已认证） | 不变 | 无 | 仍在 |
| ④ 提交 + 执行 | Task A 提交 → `execute_committed` → `apply` | committed / rejected | 成功才变 | 生成 | 仍在 |
| ⑤ 清理 | `finalize_transactions` | 结束 | — | 保留 | 移出 |

### S1. 拒绝（rejection）发生在哪个阶段？（TA 原题）
**At which stage does rejection happen?**

> **EN:** Rejection can happen at two stages. At admission, `submit` rejects malformed requests, such as an unknown account or a non-integer amount. It raises a ValueError, so the transaction never enters the pool and gets no receipt. Insufficient funds are only detected at execution, after the block is committed, because the balance is not known before that. Then `apply` changes no balance and records a rejected receipt, and the transaction leaves the pool like a successful one.
>
> **中文：** 拒绝可能发生在两个阶段。准入时，`submit` 拒绝格式错误的请求，比如未知账户或金额不是整数，直接抛 ValueError，交易不会进入交易池，也没有回执。余额不足要到区块提交后执行时才能发现，因为在那之前余额还不确定。这时 `apply` 不改余额，记录 rejected 回执，交易和成功的交易一样被移出交易池。

| 拒绝阶段 | 拒绝原因 | 结果 |
| --- | --- | --- |
| 准入（B1） | 未知账户、自转账、金额不合法 | ValueError / HTTP 400，不进池，无编号，无回执 |
| 执行（B3） | 余额不足（也会再查账户和金额） | 余额不变，rejected 回执，移出交易池 |

### S2. 余额在哪个阶段改变？
**When do balances change?**

> **EN:** Only at execution, after the block is committed. Admission, proposal and the first two QCs do not change balances. In our example, balances stay at one hundred when the QC for block B2 forms, and change only when the QC for block B3 commits block B1.
>
> **中文：** 只在区块提交后的执行阶段改变。准入、出块和前两个 QC 都不改余额。例子里，区块 B2 的 QC 形成时余额仍是 100，区块 B3 的 QC 提交区块 B1 后才改变。

### S3. 回执在哪个阶段生成？存在哪里？
**When is a receipt created, and where is it stored?**

> **EN:** A receipt is created at execution, in `apply`, for both successful and rejected transactions. It is stored in each replica's own state machine, next to its balances, because each replica executes independently.
>
> **中文：** 回执在执行阶段由 `apply` 生成，成功和失败的交易都有。它存在每个副本自己的状态机里，和余额放在一起，因为每个副本独立执行。

### S4. 交易在哪个阶段离开交易池？
**When does a transaction leave the pool?**

> **EN:** Only after its block is committed and executed, in `finalize_transactions`. Being selected into a proposal does not remove it. Both successful and rejected transactions leave the pool at this point.
>
> **中文：** 只有在区块提交并执行之后，由 `finalize_transactions` 移出。被选进提案不会移出。成功和失败的交易都在这一步离开交易池。

### S5. 余额检查发生在哪个阶段？为什么不在准入时检查？
**At which stage are funds checked, and why not at admission?**

> **EN:** Funds are checked at execution. At admission we do not know which transactions will be executed before this one, so the balance at that moment may not be the balance at execution time.
>
> **中文：** 余额在执行阶段检查。准入时还不知道哪些交易会排在它前面先执行，那时的余额不一定等于执行时的余额。

### S6. 如果提案被废弃，里面的交易在哪个阶段、怎么处理？
**If a proposal is abandoned, what happens to its transactions?**

> **EN:** Nothing is lost. They were never removed from the pool, and they were never executed. On the next proposal, `select_transactions` only skips IDs on the new parent chain, so these transactions can be selected again.
>
> **中文：** 不会丢失。它们从没被移出交易池，也从没被执行。下一次出块时，`select_transactions` 只跳过新父链上的 ID，所以这些交易可以被重新选中。

### S7. 去重发生在哪个阶段？
**At which stage is duplicate execution prevented?**

> **EN:** At execution. The first step of `apply` is to look up the receipt for this ID. If it exists, the old receipt is returned and no transfer happens. During selection, skipping IDs on the parent chain also keeps each ID once on a committed chain.
>
> **中文：** 在执行阶段。`apply` 第一步查这个 ID 的回执，有就返回原回执，不转账。另外在出块阶段，跳过父链上已有的 ID，也保证同一条已提交链上每个 ID 只出现一次。

### S8. 共识（Task A）和执行（Task B）在哪里交接？
**Where does Task A hand over to Task B?**

> **EN:** In `dispatch_qc`. Task A's `receive_qc` returns the newly committed block IDs. Then `dispatch_qc` calls `execute_committed` on each replica and finally `finalize_transactions`. Task A never executes transactions, and Task B never decides what is committed.
>
> **中文：** 在 `dispatch_qc`。Task A 的 `receive_qc` 返回新提交的区块 ID，然后 `dispatch_qc` 对每个副本调用 `execute_committed`，最后调用 `finalize_transactions`。Task A 从不执行交易，Task B 从不决定提交什么。

---

## 一、Task B1 准入与交易池（`submit`）

### Q1. `submit` 做了什么？
**What does `submit` do?**

> **EN:** It checks that the sender and receiver are known accounts and the amount is a strict integer between 1 and 1,000,000. If all checks pass, it creates a transaction with an ID like Tx1, stores it, and appends the ID to the pending pool. If any check fails, it raises a ValueError and changes nothing.
>
> **中文：** 检查发送方和接收方是已知账户、金额是 1 到 1000000 的严格整数。全部通过后，创建一个编号为 Tx1 这样的交易，登记并把编号加入交易池。任何一项不通过就抛 ValueError，不改任何状态。

### Q2. 为什么提交时不检查余额？（最可能被问）
**Why don't you check the balance at admission?**

> **EN:** Because the balance is not known until execution. Other transactions may be committed before this one, so a balance check at admission could be wrong. We check funds only when the block is committed and executed. If funds are insufficient then, the transaction gets a rejected receipt.
>
> **中文：** 因为余额要到执行时才确定。这笔交易前面可能还有别的交易先被提交，提交时检查余额可能是错的。所以我们只在区块提交、执行时检查余额；如果那时余额不足，交易得到 rejected 回执。

### Q3. 为什么用 `type(amount) is int` 而不是 `isinstance`？
**Why `type(amount) is int` instead of `isinstance`?**

> **EN:** In Python, `bool` is a subclass of `int`, so `isinstance(True, int)` is true. Using `type(...) is int` rejects `True` as well as floats like 1.5.
>
> **中文：** Python 里 bool 是 int 的子类，`isinstance(True, int)` 为真，会把 True 当成 1。用 `type(...) is int` 能同时拒绝 True 和 1.5 这样的小数。

### Q4. 非法请求为什么不会改变状态？
**How do you make sure an invalid request changes nothing?**

> **EN:** All checks run before any state is written. We only create the transaction and add it to the pool after every check passes.
>
> **中文：** 所有检查都在写入状态之前完成，只有全部通过才创建交易、加入交易池。

---

## 二、Task B2 区块载荷（`select_transactions`）

### Q5. 怎么选交易？
**How do you select transactions for a block?**

> **EN:** We walk from the parent block back to genesis and collect the transaction IDs already on that chain. Then we go through the pool in order and pick transactions that are not on the chain, up to the batch limit, which is five by default.
>
> **中文：** 从父块沿父指针走回创世块，收集这条链上已有的交易 ID。然后按交易池的顺序，挑出不在链上的交易，最多取到批量上限，默认 5 笔。

### Q6. 为什么只排除父链上的交易，而不是所有打包过的交易？（核心设计）
**Why exclude only the parent chain, not every transaction that was ever proposed?**

> **EN:** Because being proposed is not the same as being committed. A proposal may fail to get a QC, for example when the leader crashes, and then it is abandoned. If we excluded every proposed transaction, those in abandoned blocks would never be proposed again. Excluding only the parent chain lets them be re-proposed on the new branch.
>
> **中文：** 因为被打包不等于被提交。提案可能拿不到 QC，比如 leader 崩溃，这个块就被废弃了。如果排除所有打包过的交易，废弃块里的交易就永远不会再被打包。只排除父链上的，它们就能在新分支上重新被打包。

### Q7. 选中的交易为什么不从交易池删除？
**Why don't you remove selected transactions from the pool?**

> **EN:** Because the proposal might be abandoned. If we removed them at selection, they would be lost. We remove them only after the block is committed, in `finalize_transactions`.
>
> **中文：** 因为提案可能被废弃，选中就删的话交易会丢失。我们只在区块提交后，在 `finalize_transactions` 里删除。

### Q8. 同一笔交易会被执行两次吗？
**Can a transaction be executed twice?**

> **EN:** No. Only one branch is committed, and on that branch each ID appears once because we skip IDs already on the parent chain. Even if a block is delivered again, `apply` finds the existing receipt and does not transfer again.
>
> **中文：** 不会。只有一条分支被提交，选交易时跳过了父链上已有的 ID，所以这条链上每个 ID 只出现一次。即使区块被重复投递，`apply` 发现已有回执也不会再转账。

---

## 三、Task B3 状态执行（`execute_committed`、`apply`）

### Q9. 怎么保证只执行已提交的交易？
**How do you make sure only committed transactions are executed?**

> **EN:** `execute_committed` first checks that every block ID is in this replica's committed history. If any block is not committed, it raises an error before touching any balance. Only after all checks pass does it execute the transactions.
>
> **中文：** `execute_committed` 先检查每个区块 ID 都在本副本的已提交历史里。只要有一个没提交，就在改动任何余额之前报错。全部通过后才执行交易。

### Q10. 为什么先全部检查，再执行？
**Why check all blocks first instead of checking while executing?**

> **EN:** To avoid a half-updated state. If we executed block by block and found a bad block later, earlier blocks would already have changed balances. Checking first means either everything runs or nothing does.
>
> **中文：** 为了避免状态只改了一半。如果边查边执行，后面发现不合法的块时，前面的块已经改了余额。先全部检查，就能保证要么全执行，要么一笔都不动。

### Q11. 四个副本的余额怎么保持一致？
**How do the four replicas stay consistent?**

> **EN:** Each replica has its own state machine and executes on its own. They stay consistent because execution is deterministic: they commit the same blocks and run the transactions in the same block order and payload order, with no randomness.
>
> **中文：** 每个副本有自己的状态机，各自执行。它们保持一致是因为执行是确定性的：提交同样的块，按同样的区块顺序和块内顺序执行，没有随机因素。

### Q12. 余额不足时怎么处理？
**What happens when the sender has insufficient funds?**

> **EN:** No balance changes. The transaction gets a receipt with status "rejected" and an error message. It still belongs to the committed block, so it is also removed from the pool.
>
> **中文：** 不改任何余额，交易得到状态为 rejected、带错误信息的回执。它仍属于已提交的区块，所以同样会被移出交易池。

### Q13. 准入时已经检查过了，为什么执行时还要再检查？
**You already validated at admission. Why validate again at execution?**

> **EN:** The execution layer does not trust the admission layer. A block's content comes from the leader, which could be faulty. Checking again makes every replica apply the same rules and reach the same result.
>
> **中文：** 执行层不信任准入层。区块内容来自 leader，leader 可能有问题。再检查一遍，保证每个副本按同样的规则得出同样的结果。

---

## 四、Task B4 回执与重试（`apply`、`finalize_transactions`）

### Q14. 同一个交易 ID 再来一次会怎样？
**What happens if the same transaction ID arrives again?**

> **EN:** The first thing `apply` does is look up the receipts. If a receipt exists, it returns that receipt directly and does not transfer again.
>
> **中文：** `apply` 第一步就查回执。如果已有回执，直接返回原回执，不会再转一次账。

### Q15. 为什么去重检查放在最前面？
**Why is the duplicate check the first step?**

> **EN:** So the result for an ID never changes. If we checked the balance first, a transaction that succeeded before might be rejected on retry because the balance is now lower, which would overwrite the original result.
>
> **中文：** 保证同一个 ID 的结果永远不变。如果先查余额，之前成功的交易重试时可能因为余额已经变少而被判为失败，覆盖了原来的结果。

### Q16. 为什么失败的交易也要写回执？
**Why do failed transactions also get receipts?**

> **EN:** A rejected transaction is still part of a committed block, so its result is final. The receipt tells the client what happened, and it also prevents the transaction from being judged again on a retry.
>
> **中文：** 被拒绝的交易仍是已提交区块的一部分，它的结果是最终的。回执告诉客户端结果，也防止重试时被重新判断一次。

### Q17. `finalize_transactions` 做什么？调用两次会怎样？
**What does `finalize_transactions` do, and is it safe to call twice?**

> **EN:** It removes the committed transactions from the pool, both successful and rejected ones, and writes a log entry. It skips IDs that are no longer in the pool, so calling it twice does nothing extra.
>
> **中文：** 把已提交的交易移出交易池，成功和失败的都移出，并写日志。已经不在池里的 ID 直接跳过，所以调用两次不会有额外效果。

---

## 五、Task B5 批量配置（`configure_batch`）

### Q18. 批量上限怎么设置？会拒绝哪些值？
**How is the batch limit configured, and what values are rejected?**

> **EN:** Through `POST /api/config/batch`, which calls `configure_batch`. It accepts only positive integers and rejects booleans, zero, negatives and non-integers, without changing the current setting. Reset restores the default of five.
>
> **中文：** 通过 `POST /api/config/batch` 接口，它会调用 `configure_batch`。只接受正整数，拒绝布尔值、0、负数和非整数，拒绝时不改当前设置。重置后恢复默认值 5。

### Q19. 上限改变后效果是什么？
**What is the effect of changing the limit?**

> **EN:** The next proposals use the new limit. For example, seven pending transactions are split into five and two with the default limit, but into two, two, two and one with a limit of two. Transactions already in the pool are not affected.
>
> **中文：** 之后的出块按新上限选交易。比如 7 笔交易，默认上限下分成 5 和 2，上限为 2 时分成 2、2、2、1。已在交易池里的交易不受影响。

---

## 六、总结问题：共识和执行是怎么连接的？

**Q20. How does consensus commitment trigger execution?**
**问：共识提交是怎么触发执行的？**

> **EN:** When a QC forms, `dispatch_qc` calls `receive_qc` on each replica. Task A decides which blocks are newly committed by the three-chain rule. If those blocks contain transactions, `dispatch_qc` calls `execute_committed` on that replica, and then `finalize_transactions` cleans the pool. So consensus decides what is committed, and Task B only executes what is committed.
>
> **中文：** QC 形成时，`dispatch_qc` 对每个副本调用 `receive_qc`，由 Task A 按三链规则决定哪些块新被提交。如果这些块里有交易，`dispatch_qc` 就调用该副本的 `execute_committed`，然后 `finalize_transactions` 清理交易池。共识决定“提交什么”，Task B 只执行“已提交的”。

---

## 速查表（考前五分钟看）

| 任务 | 函数 | 一句话 | 关键词 |
| --- | --- | --- | --- |
| B1 | `submit` | 只校验格式，不碰余额 | strict integer、no balance change |
| B2 | `select_transactions` | 只跳过父链上的，选中不删 | parent chain、abandoned proposal |
| B3 | `execute_committed`、`apply` | 只执行已提交的，先查后执行，顺序固定 | committed only、deterministic |
| B4 | `apply`、`finalize_transactions` | 先查回执，失败也有回执，提交后移出池 | receipt、idempotent |
| B5 | `configure_batch` | 只接受正整数，默认 5 | positive integer、default 5 |
