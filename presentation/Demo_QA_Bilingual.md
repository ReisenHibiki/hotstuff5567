# 现场演示四个场景的可能提问（中英双语）

依据：组员定的四个演示场景、修正版 PPT、`taskB6_recover` 分支代码（2026-11-25 的 `a79e2ef`）和组员写的 `DEMO_GUIDE.md`。

标注：**★ 你的部分**（B1–B5），其余是组员的部分，但 TA 可以问任何人，至少要能说出一句结论。

| 场景 | 内容 | 主要涉及 |
| --- | --- | --- |
| 一 | Alice 转 Bob 80，再转 Charlie 80，一成一败 | **★ B1–B4**、A1–A5 |
| 二 | 重放 nonce | B6、**★ B4** |
| 三 | Crash leader，剩 3 个节点继续完成交易 | A6、**★ B2、B3** |
| 四 | Reset，设节点 1 为拜占庭节点，完成交易 | 法定人数、A7 的边界 |

---

## 场景一：Alice → Bob 80，Alice → Charlie 80（★ 你的主场）

演示中会看到：两笔都进交易池，余额不变；两笔被打包进同一个区块 B1；QC(B1)、QC(B2) 时余额仍是 100；QC(B3) 提交 B1 后，第一笔成功、第二笔 rejected；最终 Alice 20、Bob 180、Charlie 100，交易池清空。

### D1. ★ 两笔加起来 160，超过 Alice 的 100，为什么两笔都能提交成功？
**Both transfers total 160, more than Alice's 100. Why were both admitted?**

> **EN:** Admission only checks the format: known accounts and a valid integer amount. It does not check funds, because the balance at admission is not the balance at execution. Funds are checked only after the block is committed.
>
> **中文：** 准入只检查格式：账户存在、金额是合法整数。不检查余额，因为准入时的余额不等于执行时的余额。余额要等区块提交后才检查。

### D2. ★ 为什么是第二笔失败，而不是第一笔？谁决定顺序？
**Why did the second transfer fail, not the first? Who decides the order?**

> **EN:** The order inside the block. `select_transactions` takes transactions in pool order, which is submission order, and every replica executes the block in that payload order. Bob's transfer comes first and leaves Alice with 20, so Charlie's transfer fails. Because the order is fixed in the block, all replicas reach the same result.
>
> **中文：** 由区块内的顺序决定。`select_transactions` 按交易池顺序（即提交顺序）选交易，每个副本都按这个顺序执行。转给 Bob 的在前，执行后 Alice 只剩 20，所以转给 Charlie 的失败。顺序写在区块里，所以所有副本结果相同。

### D3. ★ QC(B1) 和 QC(B2) 形成时余额为什么不变？
**Why didn't balances change when QC(B1) and QC(B2) formed?**

> **EN:** A QC only certifies a block, it does not commit it. HotStuff commits block B1 only when block B3's QC completes a three-chain in consecutive views. Task B executes only committed blocks, so balances change at QC(B3).
>
> **中文：** QC 只是认证区块，不是提交。HotStuff 要等区块 B3 的 QC 形成连续视图的三链，才提交区块 B1。Task B 只执行已提交的块，所以余额在 QC(B3) 时才变。

### D4. ★ 区块 B2、B3 是空块，有什么用？
**Blocks B2 and B3 are empty. What are they for?**

> **EN:** They carry QCs that move the chain forward. Their certificates lock and then commit block B1. Empty blocks are allowed: when the pool has nothing new to pack, the leader still proposes with an empty payload.
>
> **中文：** 它们携带 QC，推动链往前走，正是它们的证书让区块 B1 先被锁定、再被提交。空块是允许的：交易池没有可打包的交易时，leader 仍然出一个没有交易的块。

### D5. ★ 失败的交易在已提交的区块里，这个区块算不算无效？
**The failed transaction is in a committed block. Does that make the block invalid?**

> **EN:** No. Consensus finality and execution success are separate. The block is final, and its payload is executed deterministically. One transaction succeeds and one is rejected, and both results are final receipts. The block itself is not undone.
>
> **中文：** 不算。共识的最终性和执行是否成功是两回事。区块是最终的，里面的交易按确定的规则执行，一笔成功、一笔被拒，两个结果都是最终回执，区块本身不会被撤销。

### D6. ★ 失败的交易为什么也从交易池里消失了？
**Why did the failed transaction also leave the pool?**

> **EN:** It has been committed and has a final result. If it stayed in the pool, it could be packed again and executed again. `finalize_transactions` removes every transaction of a committed block, successful or rejected.
>
> **中文：** 它已经被提交、有了最终结果。留在池里就可能被再次打包、再次执行。`finalize_transactions` 会把已提交区块里的所有交易移出，不管成功还是失败。

### D7. ★ 回执存在哪里？四个节点都有吗？
**Where are receipts stored? Does every node have them?**

> **EN:** Each replica stores receipts in its own state machine, next to its balances. All four replicas execute the same committed block in the same order, so they all hold the same receipts and balances. The "Live nodes agree" badge shows this.
>
> **中文：** 每个副本把回执存在自己的状态机里，和余额放在一起。四个副本按同样顺序执行同一个已提交区块，所以回执和余额都相同，右上角的 “Live nodes agree” 就是证明。

### D8. ★ 总余额是多少？有什么意义？
**What is the total balance, and why does it matter?**

> **EN:** 20 plus 180 plus 100 is still 300. A transfer only moves money and the failed one changes nothing, so the total is conserved. It is a quick check that execution is correct.
>
> **中文：** 20 + 180 + 100 仍然是 300。转账只是挪钱，失败的交易不改任何余额，所以总额不变。这是检查执行是否正确的简单方法。

### D9. ★ 如果先转 Charlie、再转 Bob，结果会怎样？
**What if Alice sent to Charlie first, then to Bob?**

> **EN:** Then Charlie's transfer succeeds and Bob's is rejected. The rule is the same: whichever comes first in the block executes first.
>
> **中文：** 那就是转给 Charlie 的成功、转给 Bob 的被拒。规则一样：区块里排在前面的先执行。

### D10. ★ 两笔为什么在同一个区块？
**Why are both transfers in the same block?**

> **EN:** The default batch limit is five, and both were pending when the leader proposed, so both were selected into block B1.
>
> **中文：** 默认批量上限是 5，leader 出块时两笔都在交易池里，所以都被选进区块 B1。

### D11. 失败的交易为什么也消耗了 nonce？（B6 版本，Alice 的 committed nonce 变成 2）
**Why did the failed transfer also consume a nonce?**

> **EN:** The specification says an authenticated, committed transaction consumes its nonce even if it fails for insufficient funds. Its result is final, so the nonce must move on; otherwise Alice's next transaction could never use the next nonce.
>
> **中文：** 规范规定：已认证、已提交的交易，即使因余额不足失败，也要消耗 nonce。它的结果是最终的，nonce 必须往前走，否则 Alice 的下一笔交易就无法使用下一个 nonce。

---

## 场景二：重放 nonce（B6，组员的部分；去重和你的 B4 有关）

演示中会看到：用同样的内容和 nonce 0 再提交一次，返回 “already has a final receipt”，余额不变；把 nonce 改成 5，被拒 “Expected nonce 2, got 5”。

### D12. ★ B4 已经有按 ID 去重了，为什么还要 nonce？
**B4 already deduplicates by ID. Why do you also need nonces?**

> **EN:** B4 stops the same ID from executing twice, but in the basic version the ID is just Tx1, Tx2, so the same request submitted twice becomes two different IDs. B6 derives the ID from the signed payload, including the nonce, so an identical request always has the same ID. The nonce also forces each account's transactions into order and lets a user send the same amount twice on purpose by using a new nonce.
>
> **中文：** B4 防止同一个 ID 执行两次，但基础版的 ID 只是 Tx1、Tx2，同一个请求提交两次会变成两个不同 ID。B6 用包含 nonce 的签名载荷推导 ID，相同请求永远是同一个 ID。nonce 还强制每个账户的交易按顺序执行，用户想再转一笔同样金额时，换一个新 nonce 即可。

### D13. 重放的请求发生了什么？
**What happened to the replayed request?**

> **EN:** It has the same payload, so it gets the same payload-derived ID. That ID already has a final receipt, so the system returns the old receipt and does not execute it again.
>
> **中文：** 载荷相同，推导出的 ID 也相同。这个 ID 已有最终回执，系统直接返回旧回执，不再执行。

### D14. 为什么 ID 由载荷推导，而不是由签名推导？
**Why derive the ID from the payload instead of the signature?**

> **EN:** The payload is what the user means: sender, receiver, amount and nonce. If the ID came from the signature, a different signature on the same payload would create a new ID and bypass deduplication.
>
> **中文：** 载荷才是用户真正的意图：发送方、接收方、金额和 nonce。如果 ID 来自签名，同一个载荷换一个签名就会得到新 ID，绕过去重。

### D15. nonce 错了在哪个阶段被拒？会消耗什么吗？
**At which stage is a wrong nonce rejected, and does it consume anything?**

> **EN:** At admission. A new signed transaction must use exactly the next expected nonce. A wrong nonce is rejected with a ValueError and consumes nothing.
>
> **中文：** 在准入阶段。新的签名交易必须使用下一个期望的 nonce，错了就抛 ValueError 被拒，不消耗任何东西。

### D16. 签名在哪些阶段验证？
**When are signatures verified?**

> **EN:** Twice: once at admission in `submit`, and again at execution in `apply`. The second check is needed because block content comes from the leader and might not have gone through admission.
>
> **中文：** 两次：准入时在 `submit` 里验一次，执行时在 `apply` 里再验一次。第二次是因为区块内容来自 leader，可能没经过准入。

---

## 场景三：Crash leader，剩下 3 个节点完成交易（A6，组员的部分；交易部分和你的 B2、B3 有关）

演示中会看到：leader 崩溃后显示 CRASHED、VIEW FROZEN；逻辑超时倒计时 3、2、1；换 view、换 leader；QC 只有 3 个投票者；存活节点完成交易，崩溃节点余额停在旧值；Recover 后追上。

### D17. 系统怎么知道 leader 崩溃了？
**How does the system detect that the leader crashed?**

> **EN:** It doesn't detect it directly. If a round cannot get a quorum, a logical timeout counts down three ticks, then the view advances and the next node becomes leader.
>
> **中文：** 不是直接检测。如果这一轮拿不到法定票数，就启动逻辑超时，倒数 3 步，然后视图加一，下一个节点当 leader。

### D18. 为什么剩 3 个节点还能继续？
**Why can the system continue with three nodes?**

> **EN:** The quorum is three out of four, so we tolerate one faulty node. Three live replicas can still form a QC. If only two were available, the system would stall instead of forming a false QC.
>
> **中文：** 法定人数是 4 个里的 3 个，能容忍 1 个故障节点。3 个存活副本仍能形成 QC；如果只剩 2 个，系统会停住，而不是形成假的 QC。

### D19. ★ leader 崩溃时已经打包的交易会丢吗？
**If the leader crashes after proposing, are its transactions lost?**

> **EN:** No. Transactions stay in the pool until their block is committed. The crashed leader's block never gets a QC and is abandoned. The next leader builds on the last certified block, and `select_transactions` only skips IDs on that parent chain, so the transaction is proposed again and executed once.
>
> **中文：** 不会。交易在所在区块提交前一直留在交易池里。崩溃 leader 的块拿不到 QC，被废弃。新 leader 在最后一个已认证的块上出块，`select_transactions` 只跳过新父链上的 ID，所以这笔交易会被重新打包，并且只执行一次。

### D20. ★ 崩溃的节点会执行交易吗？它的余额为什么没变？
**Does the crashed node execute transactions? Why didn't its balances change?**

> **EN:** No. `execute_committed` returns immediately on a crashed replica, so it does no new work and its balances freeze. After recovery, it copies the state from a live replica and catches up.
>
> **中文：** 不会。`execute_committed` 对崩溃的副本直接返回，不做任何新工作，所以它的余额冻结。恢复后，它从存活副本复制状态追上来。

### D21. 恢复时复制了什么？它会不会在同一个 view 投两次票？
**What does recovery copy, and can the node vote twice in a view?**

> **EN:** It copies blocks, QCs, locks, the committed chain, balances, receipts and nonces from the most advanced live replica. It keeps its own voting history, so it cannot vote twice in the same view.
>
> **中文：** 从进度最新的存活副本复制区块、QC、锁、已提交链、余额、回执和 nonce，但保留自己的投票记录，所以不会在同一个 view 投两次票。

### D22. 崩溃后为什么交易没有马上提交？
**Why wasn't the transaction committed right after the crash?**

> **EN:** The timeout skips a view, and the commit rule needs three blocks in consecutive views. After a view gap, we wait for a new clean three-chain before committing.
>
> **中文：** 超时会跳过一个视图，而提交规则需要连续视图里的三个块。出现视图间隔后，要等新的完整三链才提交。

### D23. 轮换到崩溃的节点当 leader 时怎么办？
**What happens when the rotation reaches the crashed node again?**

> **EN:** That view cannot get a proposal, so it times out again and the leader moves to the next node. Progress is slower but still safe.
>
> **中文：** 那个视图没有提案，会再次超时，leader 换到下一个节点。进度会慢一些，但仍然安全。

---

## 场景四：设节点 1 为拜占庭节点，仍然完成交易

演示中会看到：选 “Node 1 withholds votes”，N1 不投票，QC 的投票者是 (2, 3, 4)，交易照常提交。

**先说清楚：** 面板上的 Byzantine 开关（`set_byzantine`）只让该节点**拒绝投票**，是课程提供的功能。规范写明 “Vote withholding alone earns no A7 marks”。真正的拜占庭行为（发冲突提案）属于 A7 的 `inject_attack`，我们没有完成。TA 问起时要如实说，不要说成完成了 A7。

### D24. 你们的拜占庭节点具体做了什么？
**What exactly does your Byzantine node do?**

> **EN:** In our demo it only withholds its votes, using the supplied switch. That shows one faulty replica cannot block progress. It is not full Byzantine behavior: sending conflicting proposals is part of A7, and our `inject_attack` is not complete.
>
> **中文：** 演示里它只是拒绝投票，用的是课程提供的开关。这证明一个故障副本挡不住系统前进。但它不是完整的拜占庭行为：发送冲突提案属于 A7，我们的 `inject_attack` 没有完成。

### D25. 为什么一个节点不投票，交易还能完成？
**Why can transactions still complete with one node not voting?**

> **EN:** Three distinct votes form a QC. The other three replicas vote, so every round still reaches the quorum, and the three-chain commit works as normal.
>
> **中文：** 3 张不同的票就能形成 QC。其余 3 个副本正常投票，每一轮都能达到法定人数，三链提交照常进行。

### D26. 为什么 4 个节点只能容忍 1 个拜占庭节点？
**Why can four nodes tolerate only one Byzantine node?**

> **EN:** BFT needs n ≥ 3f + 1. With n = 4, f = 1. A quorum of 2f + 1 = 3 guarantees that any two quorums share at least one honest replica, which prevents conflicting commits.
>
> **中文：** BFT 需要 n ≥ 3f + 1，n = 4 时 f = 1。法定人数 2f + 1 = 3，保证任意两个法定集合至少有一个诚实副本重叠，从而不会出现冲突的提交。

### D27. 如果再崩溃一个节点呢？
**What if another node crashes as well?**

> **EN:** Then only two voters remain, below the quorum of three. The system keeps timing out and stalls, but it never forms a false QC. We choose safety over liveness and never lower the quorum.
>
> **中文：** 那就只剩 2 个投票者，低于法定人数 3。系统会不断超时、停滞，但绝不会形成假的 QC。我们选择安全优先于活性，从不降低法定人数。

### D28. ★ 拜占庭节点的余额会不会和其他节点不一样？
**Can the Byzantine node end up with different balances?**

> **EN:** Not in our demo. Withholding votes does not change how it executes. It still receives the QCs, commits the same blocks and executes them in the same order, so its balances match the others.
>
> **中文：** 在我们的演示里不会。拒绝投票不改变它的执行。它仍然收到 QC、提交同样的块、按同样顺序执行，所以余额和其他节点一致。

---

## 速记：四个场景各记一句

| 场景 | 一句话（中文） | One line (EN) |
| --- | --- | --- |
| 一 | 准入不查余额，提交后按块内顺序执行，失败也有最终回执 | Admission doesn't check funds; committed blocks execute in order; failures get final receipts |
| 二 | ID 由载荷推导，重放返回旧回执；nonce 错了在准入被拒 | Payload-derived ID returns the old receipt; a wrong nonce is rejected at admission |
| 三 | 超时换 leader，3 票仍成 QC；被废弃块里的交易会重新打包 | Timeout rotates the leader; three votes still form a QC; orphaned transactions are re-proposed |
| 四 | 只是拒绝投票，3 票仍成 QC；真正的拜占庭攻击 A7 未完成 | Only vote withholding; three votes still suffice; full A7 attacks are not done |

## 你最该准备的五题

1. **D2** 为什么是第二笔失败（顺序）
2. **D1** 为什么两笔都能提交（准入不查余额）
3. **D5** 失败交易在已提交区块里，区块是否无效
4. **D19** leader 崩溃时交易会不会丢（你的 B2）
5. **D20** 崩溃节点会不会执行（你的 B3）
