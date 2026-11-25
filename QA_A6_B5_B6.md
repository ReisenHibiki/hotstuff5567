# A6 / B5 / B6 答辩备考（分支 `taskB6_recover`）

> 个人备考笔记，2026-11-25 写，没有加入 git。打包提交时不要放进 zip。

## 0. 现状

| 项 | 分值 | 状态 | 证据 |
|---|---:|---|---|
| A6 恢复 | 2 | 完成：timeout 换 leader（1 分），recover 追赶并保留投票历史（1 分） | `extensions_tests/test_recovery.py`，8 个测试 |
| B5 批量 | 2 | 完成：通过 API 配置，1、2、5 都能用，非法值被拒 | `extensions_tests/test_batch.py`，2 个测试 |
| B6 签名 | 3 | 功能完成（签名 2 分，nonce 与重放 1 分）。**还缺篡改和重放的独立测试** | `test_recover_preserves_signed_state`，`test_dashboard_signing.py` 中 3 个测试 |

2026-11-25 实测：`tests/` 17 个、`extensions_tests/` 14 个，共 31 个全部通过。下面答案里提到的行为都用脚本跑过，包括篡改、错误账户、提交前后重放、nonce 跳号、伪造签名和全部节点崩溃后恢复。

## 1. 赛前要做的事（按优先级）

1. **修超时日志**：`backend/hotstuff.py:387` 少了 `f`，演示 Crash Leader 时，事件日志会原样显示 `view {self.view}: timeout expired…`，TA 一眼就能看到。`hotstuff.py:338` 的日志也少一个空格，会显示成 `QC(B1)scheduling timeout`。
2. **补 `extensions_tests/test_security.py`**：README 要求 B6 自己写测试，覆盖篡改、错误账户、提交前后重放和 nonce 递增。现在只有恢复测试和前端签名测试。被问“B6 的测试在哪”时要能直接跑出来。
3. **填 `changes.md`**，要写四样：已完成的扩展（A6、B5、B6 及测试命令）、你的贡献行、未完成项（A7 的 `inject_attack` 仍是 TODO）、**未来 nonce 的处理策略**（规格要求写明）。
4. `backend/main.py:95` 调用 recover 时没有捕获 `ValueError`。4 个节点全部崩溃后点 Recover Nodes，实测返回 HTTP 500。改成返回 400 只要两行。
5. 演示当天用哪个浏览器，就提前用它打开 `http://127.0.0.1:8000`，真签一笔转账。WebCrypto 需要安全上下文和 Ed25519 支持，用局域网 IP 打开会签不了名。
6. 带 AI 标注的函数要能逐行讲清楚，见第 6 节。

**回答模板**：先用一句话讲机制，再用一句话讲原因，最后指向测试或代码行，每题 20–30 秒。Q&A 全组只有 2 分钟。

## 2. 现场演示脚本（被要求“show me”时用）

```bash
cd /Users/siyue/Downloads/study/hotstuff5567
source venv/bin/activate
python backend/main.py          # 打开 http://127.0.0.1:8000
python -m unittest discover -s tests -v
python -m unittest discover -s extensions_tests -v
```

**A6（约 60 秒）**
1. 点 Reset，紧接着点 Crash Leader，这时崩溃的是 view 1 的 leader N1。先点 Next Step 的话 leader 会轮换，下面的节点名就对不上了。
2. 连点 5 次 Next Step。日志依次出现 `Leader N1 crashed; scheduling timeout`、倒计时 3/2/1，然后 VIEW 变成 02，LEADER 变成 N2。N1 卡片显示 `CRASHED · FROZEN`。
3. 点 Start。区块详情里 QC 的投票者是 N2、N3、N4，提交链继续增长，N1 的余额停在旧值。
4. （可选，展示停滞）Byzantine 下拉框选 “Node 4 withholds votes”。这时只剩 2 个投票者，view 一直超时，但不会出现新的 QC。
5. 点 Recover Nodes，日志显示 `N1 recovered from N2`。N1 的 HighQC、LockedQC、Commit block 和余额都与其他节点一致，标记显示 “Live nodes agree”。

**B5（约 30 秒）**：面板上没有批量设置控件，用 FastAPI 自带的 `/docs` 页面配置。
1. 打开 `http://127.0.0.1:8000/docs`，找到 `POST /api/config/batch`，点 Try it out，提交 `{"max_txs_per_block": 2}`，返回 200。再提交 `0`，返回 422。
2. 回到面板连续提交 3 笔转账（nonce 会自动递增），点 Next Step。第一个区块显示 “2 tx”，下一个显示 “1 tx”。演示完点 Reset，上限恢复为 5。

**B6（约 60 秒）**
1. 先点 Reset，让 nonce 从 0 开始。用表单提交 Alice → Bob 10（nonce 自动填 0），点 Sign & Submit。交易池里出现 `tx-…` 和 nonce 0。
2. 演示提交前重放：另开一个终端，在项目根目录激活 venv 后运行 `python sign_client.py Alice Bob 10 0`，返回同一个 `transaction_id`，交易池里仍然只有一笔。
3. 演示 nonce 错误：Nonce 手动改成 5，提示 `Not admitted · Expected nonce 1, got 5`。
4. 演示提交后重放：点 Start，等回执出现后点 Pause（回执在折叠的 Transaction receipts 里）。把 Nonce 改回 0、金额仍填 10 再提交。提示 `already has a final receipt (committed) · The identical signed request was not executed again`，余额不变。
5. 演示余额不足：提交 Alice → Bob 500，提交后回执显示 `Execution failed: Insufficient balance…`，committed nonce 照样加 1。
6. 篡改和错误账户的情况在 UI 上不好操作，跑 `test_security.py` 展示，或者口头说明。

## 3. A6 恢复（timeout 1 分，recover 1 分）

**Q1. Walk me through what happens when the leader crashes.**
> When `propose()` finds the leader crashed, it schedules a logical timeout of 3 ticks. When it expires we schedule `next_view("timeout")`: the view increments, so the leader rotates to N2. N2 builds on its HighQC, and the three live replicas still make a quorum of 3, so commits continue. The crashed node stays frozen: no votes, no QCs, no execution.

代码位置：`hotstuff.py:197-202`、`367-389`、`391-400`。崩溃节点在 `node.py:24` 的 `enter_view` 里冻结。测试：`test_crash_leader_timeout_and_recovery`。

**Q2. Where else can a round fail, and how do you detect it?**
> Three places: (1) the leader is already crashed at proposal time — `propose()`; (2) the last queued vote is processed and the block still has fewer than 3 votes — `vote()`; (3) the collector crashed after the votes arrived but before the QC — `form_qc()` returns without a QC and schedules a timeout.

代码位置：`hotstuff.py:198`、`314`、`335-345`。测试：`test_collector_crash_before_qc`。

**Q3. Why not lower the quorum when a node is down?**
> Safety relies on quorum intersection. With n = 4 and f = 1, any two quorums of 3 overlap in at least 2 nodes, so at least one honest node, which never votes twice in a view — two conflicting blocks can't both get a QC. With a quorum of 2, {N1, N2} and {N3, N4} could certify conflicting blocks. So with only two available voters we deliberately stall: views time out, but no QC is formed.

测试：`test_two_unavailable_voters_stall_without_false_qc`。一个节点崩溃、一个节点扣票，跑 60 步后仍然只有 B0 的 QC。

**Q4. What does `recover()` copy, and what doesn't it copy?**
> It picks a trusted live peer and deep-copies blocks, HighQC, LockedQC, the committed chain and the whole state machine — balances, receipts and B6 nonces. It keeps the node's own `id` and `last_voted_view`. Then it clears `crashed` and calls `enter_view` with the current view and leader. It also clears the vote-withholding fault.

代码位置：`hotstuff.py:418-463`。细节：必须先把 `crashed` 设为 False 再调用 `enter_view`，因为 `enter_view` 会跳过崩溃节点。

**Q5. Why keep `last_voted_view` instead of copying the peer's?**
> Voting history belongs to the replica itself. A node that voted in view v, crashed, and recovered in the same view could otherwise vote again in view v — that's double voting. Copying a peer's value would be faking history. Keeping it preserves "at most one vote per view".

实测：同一个 view 内恢复后，`can_vote(B1)` 返回 False。测试：`test_recover_catches_up_empty_chain` 断言 `last_voted_view` 不变。

**Q6. Which peer do you recover from, and why?**
> The live node with the longest committed chain, with ties broken by the highest HighQC view. Correct nodes' committed chains are prefixes of each other, so the longest is the most up to date.

**Q7. Why deep copies?**
> Otherwise the recovered node and the source would share the same dict objects, and one node's execution would silently change the other's balances. Each replica must own independent state.

测试里用 `assertIsNot` 检查 blocks、machine、nonces、receipts 都是独立对象。

**Q8. Can the recovered node execute a transaction twice?**
> No. We transfer state rather than replay it — and even if committed blocks are delivered again, receipts are keyed by transaction ID, so `apply()` returns the old receipt without another debit.

测试：`test_recover_preserves_signed_state` 恢复后重新执行整条已提交链，余额和 nonce 都不变。

**Q9. What if no node is alive?**
> `recover()` raises "no live peer available" — we refuse to invent state.

（如果还没修第 1 节第 4 条，HTTP 层会返回 500。被问到就说是已知问题。）

**Q10. What happens to transactions in the abandoned block?**
> `select_transactions()` never removes anything from the pool; only finalization after commit does. The next leader builds on HighQC, so the abandoned block isn't on its parent chain, and its transactions are packed again.

测试：`test_orphaned_transaction_is_reproposed`。交易进了 B1，B1 始终没拿到 QC，最后由 B2 执行。

**Q11. There were QCs after the crash, but nothing committed. Why?**
> The three-chain must be in consecutive views. Skipping view 2 gives a 1-3-4 chain, which doesn't commit. Once 3-4-5 is certified, view 3's block commits together with its uncommitted view-1 ancestor.

测试：`test_view_gap_delays_commit_until_consecutive_chain`。

**Q12. Is the timeout a real timer?**
> No — logical ticks: `TIMEOUT_TICKS = 3`, one tick per step. It's deterministic for tests and freezes while the demo is paused.

**Q13. How is this different from HotStuff's real pacemaker?**
> In real HotStuff each replica times out locally and sends NEW-VIEW with its HighQC, and the next leader takes the highest QC out of 2f+1 messages. Here the coordinator simulates one logical timer, and since `dispatch_qc` delivers every QC to all live replicas, the new leader's own HighQC already is the highest — same effect.

**Q14. What if the peer you recover from is Byzantine?**
> The spec says to recover from a trusted live peer, under trusted simulator identities. A real system would verify each block's QC and ask f+1 peers, or compare state hashes. Also, a crashed node only misses updates, so its lock can only be older than the peer's; adopting the peer's newer certified lock never moves it backwards.

**Q15. Why did the view still change right after I clicked Recover?**
> That round had already failed and its timeout was armed. Recovery doesn't cancel it — like a real pacemaker, the view is abandoned once the timer expires.

## 4. B5 批量配置（2 分）

> B5 由队友在提交 `74ee60f`（taskB1-5）中实现，但 Q&A 中每个人都可能被问到。

**Q1. How do you configure the batch size? Show me.**
> Through the API: `POST /api/config/batch` with `{"max_txs_per_block": 2}`; FastAPI's `/docs` page lets us call it from the browser. `configure_batch()` stores it in `max_txs_per_block`, and `select_transactions()` stops after that many.

代码位置：`hotstuff.py:551-561`，`select_transactions` 在 `519` 行用到这个上限，`main.py:122-139`。

**Q2. Which inputs are rejected, and how?**
> Two layers. The API model is a strict int ≥ 1 with extra fields forbidden, so `0`, `true`, `"2"` and `1.5` get 422 before our code runs. `configure_batch()` checks again with `type(limit) is int` — not `isinstance`, because `bool` is a subclass of `int`, so `True` would pass as 1. Invalid input raises `ValueError` and leaves the state unchanged.

实测：API 层对 0、true、"2"、1.5 和多余字段都返回 422。测试：`test_reject_invalid`。

**Q3. Does changing the limit affect safety or replica consistency?**
> No. It's a proposal policy used only by the leader when packing new blocks, not a voting or validity rule. Blocks already proposed keep their payload, and replicas execute whatever committed blocks contain, in order.

**Q4. With limit 1 and 5 pending transactions, what happens?**
> Five consecutive blocks with one transaction each — every new block skips IDs already on its parent chain — then two more empty blocks, so the last one gets a consecutive three-chain and commits.

实测各区块的交易数：limit 1 为 `[1,1,1,1,1,0,0]`，limit 2 为 `[2,2,1,0,0]`，limit 5 为 `[5,0,0]`。最后 Alice 都剩 95。

**Q5. How does `select_transactions` avoid packing a transaction twice?**
> It walks from the chosen parent back to genesis, collecting IDs already packed on that chain, and skips them. It reads the pool in submission order and removes nothing. Transactions on abandoned branches aren't excluded, so they can be re-proposed.

**Q6. What do Reset and the upper bound do?**
> Reset restores 5. There's no upper bound because the spec only requires positive integers; a very large value just means "take everything eligible". A real chain would cap it by block size.

## 5. B6 交易安全（签名 2 分，nonce 与重放 1 分）

**Q1. Which signature scheme and library, and why?**
> Ed25519 from the Python `cryptography` library; the browser uses WebCrypto's Ed25519. It's standard, small (32-byte keys, 64-byte signatures) and deterministic — there's no random nonce to get wrong, unlike ECDSA. Being deterministic also lets our test check that the browser and Python produce byte-identical signatures.

**Q2. What exactly is signed?**
> A canonical JSON payload — domain, sender, receiver, amount, nonce — with sorted keys, no spaces and ASCII only, so every client produces exactly the same bytes. The domain string `COMP5567-HotStuff-2026/transfer/v1` separates our chain and message type, so a signature made for another system or version can't be replayed here.

代码位置：`security.py:7`、`28-41`。

**Q3. Where do you verify, and why twice?**
> At admission in `submit()`, so forgeries never enter the pool, and again in `StateMachine.apply()` on every replica at execution. Replicas must not trust the admission layer or the leader — a faulty leader could put an unverified transaction into a block. Verification is deterministic, so all honest replicas reach the same result.

代码位置：`hotstuff.py:98-102`、`blockchain.py:110-118`。

**Q4. How is the transaction ID computed? Why not include the signature?**
> `tx-` plus the SHA-256 of the canonical payload; the signature is excluded. The same transfer always gets the same ID, so retries map to one ID and one receipt. If the ID included the signature, an alternative valid signature (malleability) would give the same payment a new ID, and it could execute twice. At execution we recompute the ID and reject a mismatch.

代码位置：`security.py:43-45`、`blockchain.py:96-108`。

**Q5. Explain your nonce rules.**
> Every account starts at 0. Only committed execution consumes a nonce, exactly once — including an authenticated insufficient-funds failure. Invalid signatures and wrong nonces consume nothing. Admission requires nonce = committed nonce + this sender's pending signed transactions, so a client can pipeline 0, 1, 2 before commit; gaps and reuse are rejected.

| 执行时的情况 | 转账 | nonce +1 | 存最终回执 |
|---|---|---|---|
| 字段类型错误、ID 与载荷不符 | 否 | 否 | 否 |
| 签名错误 | 否 | 否 | 否 |
| 合法交易，ID 已有回执 | 否 | 否 | 返回旧回执 |
| 签名有效，nonce 过旧 | 否 | 否 | 是（rejected） |
| 签名有效，nonce 超前 | 否 | 否 | 否 |
| 签名有效，nonce 匹配，余额不足 | 否 | 是 | 是（rejected） |
| 签名有效，nonce 匹配，成功 | 是 | 是 | 是（committed） |

**Q6. What if I send the same signed request twice — before and after commit?**
> Same payload, same ID. Before commit, `submit()` returns the existing pending transaction and the pool still holds one copy. After commit it returns the same transaction with its final receipt; the balance is debited once and the nonce goes up once. Even if a duplicate reached execution, `apply()` would return the existing receipt.

**Q7. What if I change the amount, or sign Alice's transfer with Bob's key?**
> We verify against the sender's registered public key over the exact payload. Changing any field changes the bytes, and Bob's signature doesn't verify under Alice's key — both are rejected as "Invalid signature", and the pool, balances and nonces don't change.

**Q8. What's your policy for future nonces?**（规格要求写进文档）
> We don't queue them: admission rejects any nonce other than the expected one. If a future nonce ever reaches execution — only possible by bypassing admission — `apply()` rejects it without a final receipt, because it might become valid later. An old nonce can never become valid, so its rejection is stored as final.

**Q9. Why doesn't a forged signature get a receipt?**
> The ID comes from the payload, so a forgery can carry the real transaction's ID. If we stored "rejected" for it, the genuine transaction with that ID would later look like a duplicate and be blocked forever. Only authenticated results become final receipts.

实测：先执行一笔伪造签名的交易，不会留下回执；之后真交易照常执行。

**Q10. Why should an insufficient-funds failure consume the nonce?**
> The transaction is authenticated and committed, so its result is final and every replica agrees on it. If it didn't consume the nonce, the same signed transfer could suddenly execute later, once the account was topped up — a delayed replay the user never intended. To retry, the user signs a new nonce.

**Q11. Where are the private keys? Is this secure?**
> The backend only loads public keys. The private keys are deterministic classroom test keys — the seed is the SHA-256 of `COMP5567 classroom test key/<name>` — used only by the clients, `sign_client.py` and the browser form. Anyone can derive them, so they're demo fixtures only; a real system keeps private keys in the user's wallet.

**Q12. How does the dashboard sign?**
> `signing.js` builds the same canonical bytes and signs with WebCrypto Ed25519 in the browser; the server only receives the signed request. A test runs the JS in Node and checks the signatures are identical to the Python client's.

测试：`test_browser_signature_matches_python_client`。

**Q13. How do recovery and nonces interact?**
> `recover()` deep-copies the whole state machine, so balances, receipts and nonces come over together. The test crashes N1, commits two signed transfers (one success, one insufficient funds), recovers, checks nonces = 2 on every node, then re-delivers the history with no double debit.

测试：`test_recover_preserves_signed_state`。

**Q14. Why is there still an unsigned path?**
> The public B1–B4 tests submit unsigned transfers and must keep passing. The server runs `HotStuffDemo(require_signatures=True)`, and in that mode unsigned transfers are rejected both at admission and at execution.

代码位置：`main.py:19`。实测：未签名请求返回 400 `Signature required`。

**Q15. After Reset, can I replay an old signed request?**
> Yes — Reset starts a new genesis with nonces back at 0, so an old nonce-0 request is valid again. That's a limitation; a real deployment would put a chain ID or genesis hash into the signed domain.

**Q16. What if a malicious leader modifies a transaction inside a block?**
> The payload no longer matches the signature or the ID, so every honest replica rejects it in `apply()`, deterministically, without changing balances or nonces and without storing a receipt.

被追问时再补充这个局限：`finalize_transactions()` 不看有没有回执，照样把这个 ID 移出交易池，所以同 ID 的真交易会一直停在 pending。修法是只移除已有最终回执的 ID。现在没有恶意 leader 的注入路径（A7 未完成），所以实际触发不到。

**Q17. How does admission know the committed nonce? The coordinator isn't a replica.**
> `expected_nonce()` takes the committed nonce from the most up-to-date live replica and adds the sender's pending signed transactions. With no live replica it returns None, and admission is refused.

代码位置：`hotstuff.py:136-162`。

## 6. 容易被追问的坑

- **A7**：提交说明写的是 “complete A7”，但 `inject_attack` 仍然抛 `NotImplementedError`（`hotstuff.py:571`），只完成了按接收者投递的 `_deliver_proposal`。被问时如实说 A7 只做了一部分，不申报分数，并写进 `changes.md` 的未完成项。
- **你写的、带 AI 标注的部分**要能逐行讲：`StateMachine.apply` 的认证包装（`blockchain.py:58`）、`classroom_private_key`、`sign_client.py`、`expected_nonce`、`signing.js`、`app.js` 的签名表单，以及 `test_dashboard_signing.py`。课程规定：讲不清 AI 辅助写的函数，最多扣掉该函数的全部分数。
- **AI 声明要前后一致**：已提交到仓库的 `HANDOFF.md` 写着 B1–B5 的 6 个函数都由 Claude 辅助写成，并带 `[AI-assisted]` 标注。但代码里一个标注都没有，`taskB1-5` 那次提交里就没有。如果 `HANDOFF.md` 随源码一起提交，报告里的 AI 声明要和它一致，需要和写 B1–B5 的队友对齐。
- **“为什么只有 2 个节点时不让它继续出块？”** 回答见 A6 Q3。这是规格明确要求的行为，不是 bug。

## 7. 代码速查

| 功能 | 位置 |
|---|---|
| 崩溃 leader 排超时 | `backend/hotstuff.py:197-202` |
| 最后一票仍不够法定数时排超时 | `backend/hotstuff.py:313-316` |
| 收票 leader 崩溃，不出 QC | `backend/hotstuff.py:332-345` |
| `timeout()` 倒计时 | `backend/hotstuff.py:367-389` |
| `next_view()` 换 leader | `backend/hotstuff.py:391-400` |
| `recover()` | `backend/hotstuff.py:418-463` |
| 崩溃节点冻结 | `backend/node.py:24`（enter_view）、`92`（receive_qc）、`144`（execute_committed） |
| 每个 view 只投一票 | `backend/node.py:66-68` |
| `select_transactions()` 和 `configure_batch()` | `backend/hotstuff.py:501-523`、`551-561` |
| B5 API | `backend/main.py:122-139` |
| 签名准入与 `expected_nonce()` | `backend/hotstuff.py:92-128`、`136-162` |
| 执行层认证与 nonce | `backend/blockchain.py:55-146` |
| 载荷、ID、验签、签名 | `backend/security.py` |
| 测试用密钥、命令行客户端、浏览器签名 | `client_keys.py`、`sign_client.py`、`frontend/signing.js` |
