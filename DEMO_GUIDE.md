# HotStuff 现场演示操作笔记

> 来源：`COMP5567_HotStuff_Project_2026.pdf`（规格）、`COMP5567_HotStuff_Part2.pdf`（Part 2 课件）、`COMP5567_HotStuff_Project_QA_2026.pdf`（Q&A 课件），以及分支 `taskB6_recover` 上的代码（提交 `1d7320c`）。
> 文中每个 STEP 编号、余额、日志文字都在 2026-11-25 直接调用后端跑过一遍，与代码一致。交易 ID 由载荷算出，所以同样的转账每次都是同一个 ID（如 `tx-aa37eb28…`）。
> 答辩问答见 `QA_A6_B5_B6.md`，本笔记只管“怎么操作、看哪里、说什么”。

---

## 0. 一眼看懂：评分要求和现场勾选单

**时间**：2026-11-29 18:30–21:30，Z504。每组 10 分钟 = 4 分钟 PPT + **4 分钟现场操作** + 2 分钟问答，三段分开。

**现场演示 10 分**（规格第 4 页、Q&A 课件第 7 页）：

- 必须现场操作运行中的系统。用录屏代替得 0/10，截图不得分。
- 上场前把系统准备好（服务已启动、页面已打开、已 Reset）。
- 可选扩展（A6/A7/B5/B6）不影响现场演示满分，只在 Task A/B 的实现分里评。

演示时按这张单子逐项打勾，全部勾完就拿满 10 分：

| # | 分项 | 评分点 | 本笔记中的位置 | 屏幕证据 |
|---|---|---|---|---|
| 1 | Task A | proposal | 主线 ④ STEP 1 | 日志 `N1 proposed B1`，B1 虚线框 PROPOSED |
| 2 | Task A | replica votes | 主线 ⑤ STEP 2–5 | 日志 4 条 `Nx voted for B1` |
| 3 | Task A | QC formation | 主线 ⑥ STEP 6 | 日志 `QC(B1) view 1 voters (1, 2, 3, 4)`，B1 变蓝 |
| 4 | Task A | commitment | 主线 ⑧ STEP 20 | 日志 `B1 committed`，B1 变绿，COMMITTED CHAIN `B0 → B1` |
| 5 | Task B | submit transactions | 主线 ②③ | MEMPOOL 2 笔 |
| 6 | Task B | balances before commit | 主线 ③ 和 ⑥ | 4 张节点卡都是 100 / 100 / 100 |
| 7 | Task B | balances after commit | 主线 ⑨ | 4 张节点卡都是 20 / 180 / 100 |
| 8 | Task B | receipts | 主线 ⑩ | 展开 Transaction receipts |
| 9 | Task B | one failing case | 主线 ⑩ | `Execution failed: Insufficient balance: Alice has 20, needs 80` |
| 10 | 加分印象 | 副本一致 | 主线 ⑨ | 右上角 `Live nodes agree`，四张卡 HighQC / LockedQC / Commit block 相同 |

主线就是 Q&A 课件第 8 页的 “Suggested Demo Run”：Alice 先转 80 给 Bob，再转 80 给 Charlie，两笔进同一个区块，第一笔成功、第二笔余额不足。一次跑完就覆盖上面全部 10 项。

---

## 1. 上场前准备（提前 10 分钟做完）

### 1.1 启动

一定要在含 B6 的分支上演示。`main` 目前停在 `0cefab5`，没有 B6，面板上没有 Nonce 输入框，交易 ID 也是 `Tx1` 这种格式，和本笔记对不上。如果组里在演示前把 B6 合进了 `main`，就用 `main`，打开页面后确认表单里有 Nonce 输入框和 Sign & Submit 按钮。

```bash
cd /Users/siyue/Downloads/study/hotstuff5567
```

```bash
git checkout taskB6_recover
```

```bash
source venv/bin/activate
```

```bash
python backend/main.py
```

- `venv` 里是 Python 3.10.15。系统自带的 `python3` 是 3.9，跑不了（`str | None` 语法报错）。
- 浏览器打开 **http://127.0.0.1:8000**（或 `http://localhost:8000`）。不要用局域网 IP：浏览器签名依赖 WebCrypto，只在安全上下文可用，用 IP 打开会签不了名。服务也只监听 127.0.0.1。

### 1.2 彩排一笔真签名

用演示当天的那台电脑、那个浏览器，提交一笔 Alice → Bob 10，确认提示 `… is pending in the mempool`，再点 Reset。如果报 `This browser cannot create Ed25519 signatures`，换新版 Chrome / Safari / Firefox，或者用第 6 节的命令行客户端兜底。

### 1.3 屏幕布局

- 投影分辨率下，把浏览器缩放调到能同时看到：顶部状态栏、01 的四张节点卡、02 的区块和 03 的余额。04 事件日志在右侧，滚动时注意别把节点卡滚出屏幕。
- 事件日志**最新的在最上面**。
- 想展示 B5 的话，另开一个标签页打开 `http://127.0.0.1:8000/docs`。
- 再开一个终端，激活 venv 留在项目根目录，备用（跑测试、命令行签名）。

### 1.4 开始前最后一步

点 **↺ Reset**。确认：`PAUSED · STEP 0`、CURRENT VIEW `01`、LEADER `N1`、三个账户都是 100、committed nonce 都是 0、MEMPOOL 0。

### 1.5 分工

Q&A 课件要求事先定好谁讲哪部分、谁操作。建议一人点鼠标，一人念台词，节奏不会乱。

---

## 2. 屏幕区域速查

| 区域 | 看什么 | 对应的要求 |
|---|---|---|
| 顶部状态栏 | CURRENT VIEW、LEADER、`PAUSED · STEP n`、右侧 `Live nodes agree` 标签 | A5 换 view / 换 leader；副本一致 |
| **01 Consensus in Action** 四张节点卡 | 每个副本的 HighQC、LockedQC、Latest block、Commit block、三人余额；崩溃时显示 CRASHED / `VIEW · FROZEN` | A4 锁定与提交；B3 各副本余额一致 |
| **02 Blockchain** 区块按钮 | 虚线 = PROPOSED，蓝 = CERTIFIED，绿 = COMMITTED；`View n · k tx`、`parent Bx` | A1 提案、A3 QC、A4 提交 |
| 02 点一个区块看详情 | Parent / View / Leader；Parent QC (proposal.qc)；Block QC voters（未出 QC 时显示 `Not formed · Votes n/3`）；块内交易 | A1 用 HighQC 选父块；A3 投票人 |
| 02 COMMITTED CHAIN | 如 `B0 → B1` | A4 |
| **03 State Machine** 余额 | 三人余额 + `committed nonce n` | B3、B6 |
| 03 表单 | From / To / Amount / Nonce（自动填）/ Sign & Submit；下方灰字是提交结果 | B1、B6 |
| 03 MEMPOOL | 待处理交易，显示 `tx-xxxxxxxx…`、nonce、金额 | B1、B2、B4 清池 |
| 03 Transaction receipts（折叠，要点开） | `✓ Committed · Executed` 或 `Execution failed: …` | B4 回执，失败用例 |
| **04 Event log** | `STEP 006 · VIEW 1 · QC` 加消息，最新在上 | 全部 |

**三个显示上的小毛病，演示时别被带偏：**

1. 状态栏中间的 phase 文字在出 QC 后不会更新，会一直停在 `Proposed B1`。讲解时以事件日志和区块颜色为准。
2. 换 view（`next_view`）不写日志，STEP 7 时日志没有新行，只能看状态栏 VIEW 和 LEADER 的变化。
3. 第 4 张票到了以后，区块详情显示 `Votes 4/3`，这是正常的：第 3 票时已达法定人数，排好了 QC 事件，第 4 票的事件早已在队列里。

---

## 3. 主线演示（4 分钟，覆盖全部 10 分）

时间分配建议：①–③ 约 40 秒，④–⑦ 约 70 秒，⑧ 约 20 秒，⑨–⑩ 约 60 秒，剩约 30–50 秒留给第 4 节的加分展示（可不做）。

| # | 操作 | 屏幕上应看到 | 台词（英文，照念即可） |
|---|---|---|---|
| ① | 点 **↺ Reset** | STEP 0，View 01，Leader N1；四张卡余额都是 100；COMMITTED CHAIN `B0` | "One process simulates four replicas, quorum three. Everyone starts with 100." |
| ② | 表单：From **Alice**，To **Bob**，Amount **80**，Nonce 自动为 **0** → **Sign & Submit** | 表单下方灰字：`tx-aa37eb28… (nonce 0) is pending in the mempool`；MEMPOOL 1 | "The browser signs the transfer with Alice's test key. It enters the pool as pending." |
| ③ | To 改成 **Charlie**，Amount **80**，Nonce 自动为 **1** → **Sign & Submit** | MEMPOOL 2（`tx-aa37eb28…` nonce 0，`tx-23ca5737…` nonce 1）；**余额仍全是 100**；STEP 仍是 0；committed nonce 仍是 0 | "Together these spend 160, but admission does not check or change balances. Submission doesn't even start the protocol: still step 0." |
| ④ | **↦ Next Step** ×1 → STEP 1 | 日志 `N1 proposed B1 (view 1, parent B0)`；B1 虚线框 `PROPOSED · View 1 · 2 tx`。**点 B1** 看详情：Parent/View/Leader = `B0 / 1 / N1`，Parent QC = `B0 · voters N1, N2, N3, N4`，Block QC voters = `Not formed · Votes 0/3`，两笔交易按提交顺序排列 | "**Proposal (A1):** leader N1 extends its HighQC, which is B0, and packs both pending transfers, up to five per block." |
| ⑤ | **↦ Next Step** ×4 → STEP 2–5 | 日志依次出现 `N1 voted for B1 (view 1)` … `N4 voted for B1 (view 1)`；详情里 Votes 计数增加 | "**Votes (A2):** each replica checks leader, view and parent QC, votes at most once per view, and only if the block extends its locked branch or carries a newer QC." |
| ⑥ | **↦ Next Step** ×1 → STEP 6 | 日志 `QC(B1) view 1 voters (1, 2, 3, 4)`；B1 变蓝 CERTIFIED；四张卡 HighQC = `B1 v1`，LockedQC 仍是 `B0`，Commit block 仍是 `B0`；**余额仍是 100**；receipts 0 | "**QC (A3):** at least three distinct valid votes for the same block and view. But a QC alone does not commit its own block, so balances are still 100." |
| ⑦ | **↦ Next Step** ×1 → STEP 7 | 日志没有新行；状态栏 VIEW `02`，LEADER `N2`；节点卡 N2 标为 LEADER | "**View change (A5):** after a successful round the view advances and the leader rotates to N2. Locks and certificates are kept." |
| ⑧ | 点 **▶ Start**，盯着 B1 和余额；**Alice 变成 20、B1 变绿时立刻点 Ⅱ Pause**（约 10 秒） | 过程中：STEP 8 `N2 proposed B2 (view 2, parent B1)`（0 tx 空块）→ STEP 13 `QC(B2)`，LockedQC 变 `B1` → STEP 15 `N3 proposed B3` → **STEP 20** 出现提交 | "Blocks B2 and B3 are empty, but their certificates still advance finality." |
| ⑨ | 已暂停，讲提交 | 日志 STEP 020 四行（从下往上读）：`QC(B3) view 3 voters (1, 2, 3, 4)` → `B1 committed` → `tx-aa37eb28… executed in B1: Alice -> Bob 80` → `tx-23ca5737… rejected in B1: Insufficient balance: Alice has 20, needs 80`。B1 绿色 COMMITTED；COMMITTED CHAIN `B0 → B1`。**四张卡都是** HighQC `B3`、LockedQC `B2`、Commit block `B1`、`Alice 20 · Bob 180 · Charlie 100`；右上角 `Live nodes agree`；MEMPOOL 0；Alice committed nonce `2` | "**Commit (A4):** QC(B3) completes the three-chain B1 ← B2 ← B3 in consecutive views 1, 2, 3, so B1 commits. Only now does the state machine execute B1's payload, in order, on every replica. All four replicas show the same chain and balances. 20 + 180 + 100 is still 300." |
| ⑩ | 点开 **Transaction receipts 2** | 两条回执：`Alice → Charlie 80` 显示 `Execution failed: Insufficient balance: Alice has 20, needs 80`；`Alice → Bob 80` 显示 `✓ Committed · Executed` | "**Failing case (B3/B4):** the second transfer fails at execution because the first already spent Alice's balance. It still gets a final receipt, it's removed from the pool, and no balance changes. Consensus finality and application success are separate." |

**关于 ⑧ 的两种做法**：

- 想精确停在 STEP 20：不点 Start，继续点 **Next Step** 13 次。更稳但费时。
- 点 Start：暂停晚几步没关系，余额和回执都不会变，只是 STEP 大于 20、可能多出 B4/B5。若晚到 STEP 27 以后，HighQC / LockedQC / Commit block 会往后移（如 B4 / B3 / B2），但四张卡仍然相同。讲的时候指着日志说“STEP 20 时 QC(B3) 提交了 B1”即可。

**B6 已开、提到也加分的一句**（第 ⑨ 步可顺带说）："Both transfers consumed a nonce — committed nonce is 2 — including the failed one, because it was authenticated and committed."

---

## 4. 主线之后的加分展示（不用 Reset，接着做，二选一）

### 4a. B6 重放与 nonce（约 30 秒，推荐）

| 操作 | 应看到 | 台词 |
|---|---|---|
| From Alice，To **Bob**，Amount **80**，**最后**手动把 Nonce 改成 **0** → Sign & Submit | 灰字：`tx-aa37eb28… already has a final receipt (committed) · The identical signed request was not executed again`；余额仍是 20 / 180 / 100 | "Replaying the identical signed request maps to the same payload-derived ID, so it returns the existing receipt and is not executed twice." |
| Nonce 改成 **5** → Sign & Submit | 顶部红色错误条，灰字 `Not admitted · Expected nonce 2, got 5` | "A wrong nonce is rejected at admission and consumes nothing." |

注意：改 From 会把 Nonce 重置成自动值，所以先选账户和金额，**最后**再改 Nonce。

### 4b. A6 崩溃、继续出块、恢复追赶（约 60 秒）

已在暂停点 STEP 20–30 之间逐一验证过，不管停在哪里都能跑通。

| 操作 | 应看到 | 台词 |
|---|---|---|
| 记下状态栏 LEADER（如 N3），点 **Crash Leader** | 该节点卡显示 CRASHED、`VIEW · FROZEN`、`Offline · No messages sent or received`；日志 `Leader N3 crashed` | "We crash the current leader." |
| 提交 **Bob → Charlie 30**（nonce 自动 0） | MEMPOOL 1 | |
| 点 **▶ Start**，约 15–20 秒，看到存活节点 Bob = 150 后 **Ⅱ Pause** | 日志 `timeout countdown 3/2/1` → 换 view、换 leader；QC 的投票人只有三个存活节点，如 `voters (1, 2, 4)`；存活节点 `Bob 150 · Charlie 130`，**崩溃节点仍是 Bob 180、Charlie 100** | "A logical timeout rotates the leader. Three live replicas still form a quorum of three, so commits continue. The crashed replica is frozen and lags behind." |
| 点 **Recover Nodes** | 日志 `N3 recovered from N1`（编号随情况不同）；四张卡都是 Bob 150；`Live nodes agree` | "Recovery copies blocks, QCs, locks, the committed chain, balances, receipts and nonces from a trusted live peer, but keeps the node's own voting history, so it can't vote twice in a view." |

---

## 5. 被老师点名 “show me” 时的扩展演示（先 Reset）

### 5a. 法定人数正好 3 票

Reset → 下拉框选 **Node 4 withholds votes** → Next Step ×6。

- STEP 2–4：N1、N2、N3 投票；STEP 5：没有日志（N4 拒投）；STEP 6：`QC(B1) view 1 voters (1, 2, 3)`。
- 演示完下拉框改回 **Byzantine: Off**。
- 台词："Three distinct votes are enough, so one silent replica cannot block progress. Vote withholding by itself is not counted as A7 work."

### 5b. A6：leader 一开始就崩溃

Reset → **Crash Leader**（崩的是 N1）→ Next Step ×6。**不要先点 Next Step 再崩**，否则 leader 已轮换，节点名对不上。

| STEP | 日志 / 屏幕 |
|---|---|
| 1 | `Leader N1 crashed; scheduling timeout` |
| 2–4 | `view 1: timeout countdown 3`、`2`、`1`，第 4 步还有 `timeout expired and schedule view change` |
| 5 | 无日志；VIEW `02`，LEADER `N2` |
| 6 | `N2 proposed B1 (view 2, parent B0)` |

之后点 Start，QC 投票人是 `(2, 3, 4)`，提交链继续增长，N1 停在 B0。

### 5c. 只剩 2 个投票者时停滞（接着 5b）

下拉框选 **Node 4 withholds votes** → Start。view 一直超时、递增，但**没有新的 QC**（实测 40 步没有新 QC）。

台词："We never lower the quorum. With only two available voters the system stalls safely instead of forming a false QC."

然后点 **Recover Nodes**：同时清除崩溃和拒投，再 Start，四个节点重新一起出块、提交。

### 5d. 孤儿交易被重新打包（Part 2 课件 Demo 6）

Reset → 提交 Alice → Bob **10** → Next Step ×1（B1 提出，含 1 笔交易）→ **Crash Leader** → Start。

| STEP | 现象 |
|---|---|
| 2–4 | 无日志（提案人已崩溃，提案无效，没人投票） |
| 5 | `Timeout: view 1 cannot reach quorum` |
| 6–8 | 倒计时 3/2/1 |
| 10 | `N2 proposed B2 (view 2, parent B0)`，B2 里**还是那笔交易** |
| 14 | `QC(B2) view 2 voters (2, 3, 4)` |
| 26 | `QC(B4)` → `B2 committed`，交易执行；N2–N4 为 Alice 90 / Bob 110，N1 冻结在 100 |

B1 一直是 PROPOSED（没有 QC），B2 的 parent 是 B0。课件写的是基线 STEP 30，我们的实现是 STEP 26，被问就说步数取决于实现，现象一致。

台词："Transactions stay in the pool until their block commits, and packing only excludes IDs on the chosen parent chain. B1 was abandoned, so its transfer is re-proposed in B2 and executed exactly once."

### 5e. B5 批量上限

面板上没有控件，用 `/docs`：

1. 打开 `http://127.0.0.1:8000/docs` → `POST /api/config/batch` → Try it out → `{"max_txs_per_block": 2}` → 200。
2. 再试 `{"max_txs_per_block": 0}` → 422（`true`、`"2"`、`1.5`、负数同样被拒）。
3. 回到面板，提交 Alice → Bob 1、2、3（nonce 自动 0、1、2）→ Start。B1 显示 `2 tx`，B2 显示 `1 tx`，全部提交后 Alice 94、Bob 106。
4. 点 Reset，上限恢复为 5。

### 5f. B6 篡改和错误签名

面板上做不出来，在备用终端（已激活 venv、位于项目根目录）运行：

```bash
python -c "
from backend.hotstuff import HotStuffDemo
from backend.security import sign_transaction
from client_keys import classroom_private_key as key
d = HotStuffDemo(require_signatures=True)
b = sign_transaction('Alice', 'Bob', 10, 0, private_key=key('Alice')); b['amount'] = 99
try: d.submit(**b)
except ValueError as e: print('tampered amount ->', e)
b = sign_transaction('Alice', 'Bob', 10, 0, private_key=key('Bob'))
try: d.submit(**b)
except ValueError as e: print('signed with Bob key ->', e)
try: d.submit('Alice', 'Bob', 10)
except ValueError as e: print('unsigned ->', e)
print('mempool', d.mempool, 'balances', d.nodes[0].machine.accounts, 'nonces', d.nodes[0].machine.nonces)
"
```

预期输出：

```text
tampered amount -> Invalid signature
signed with Bob key -> Invalid signature
unsigned -> Signature required
mempool [] balances {'Alice': 100, 'Bob': 100, 'Charlie': 100} nonces {'Alice': 0, 'Bob': 0, 'Charlie': 0}
```

### 5g. B6 提交前重放（命令行客户端）

面板里提交 Alice → Bob 10（nonce 0）后**先不推进**，在备用终端运行：

```bash
python sign_client.py Alice Bob 10 0
```

返回的 `transaction_id` 和面板里那笔相同，MEMPOOL 仍只有 1 笔。

### 5h. A7：不要演示

`inject_attack()` 仍是 TODO，调用 `POST /api/attacks` 会返回 501，页面顶部出现 TODO 错误条。被问到就如实说：A7 只完成了按接收者投递提案的 `_deliver_proposal()`，`inject_attack()` 没有完成，不申报这部分分数。

---

## 6. 出问题时怎么办

| 现象 | 处理 |
|---|---|
| 启动时报 `address already in use` | 端口 8000 被占用。运行 `lsof -i :8000` 找到 PID，`kill <PID>` 后重启 |
| 页面上没有 Nonce 输入框 | 分支不对（见 1.1），或浏览器用了旧缓存：强制刷新 |
| `Signing needs a secure page` | 地址改成 `http://127.0.0.1:8000` |
| `This browser cannot create Ed25519 signatures` | 换浏览器，或用 `python sign_client.py Alice Bob 80 0` 和 `python sign_client.py Alice Charlie 80 1` 提交，面板会自动刷新 |
| 页面顶部出现 TODO / 501 错误 | 误触了未实现的功能（A7）。点 Reset 重来 |
| 节点全崩溃后点 Recover Nodes 报错 | 已知问题：没有存活节点可复制，`main.py` 没捕获异常，返回 500。点 Reset 即可 |
| Start 后忘了暂停，STEP 跑到几十 | 没关系，B1 的余额、回执、提交链不会变，指着节点卡和回执讲即可 |
| 任何地方乱了 | 点 Reset，主线 ①–⑩ 一分半钟内可以重做 |
| 日志出现 `QC(B5)scheduling timeout` 少了空格 | `hotstuff.py:338` 的字符串拼接少一个空格，只影响显示。只有在“投票已齐、QC 前 leader 崩溃”时才会出现 |

---

## 7. 4 分钟 PPT 的顺序（Q&A 课件第 5 页，顺序是硬性要求）

| 主题 | 建议时长 | 要讲的内容 |
|---|---:|---|
| System design | 30 秒 | 五层：`frontend/app.js` → `backend/main.py` → `backend/hotstuff.py`（队列、提案、投票、QC）→ `backend/node.py`（投票规则、锁、提交）→ `backend/blockchain.py`（余额、回执）。从共识到执行的路径：`form_qc` → `dispatch_qc` → `Node.receive_qc` 给出新提交的块 → `execute_committed` → `StateMachine.apply` → `finalize_transactions` |
| Task A | 60 秒 | 提案、安全投票、QC 需 3 张不同的有效票、连续 view 的三链提交规则。**一张 QC 不能提交它自己的块** |
| Task B | 60 秒 | 交易池、只执行已提交的交易、成功与失败都有回执、按 ID 去重 |
| Test results | 60 秒 | 成功执行和失败用例的证据（见第 8 节），以及副本一致性 |
| Limitations | 30 秒 | 未完成：A7 的 `inject_attack`。已完成扩展：A6、B5、B6。其他局限：单进程模拟、无持久化、Reset 后旧签名可重放 |

Q&A 课件第 6 页的提醒：展示你完成的函数和背后的设计决定；给出预期输出和实际输出，包括失败回执和副本一致性；图要清楚；说明未完成的功能。

---

## 8. 测试结果（PPT 用，被问到也能现场跑）

```bash
python -m unittest discover -s tests -v
```

```bash
python -m unittest discover -s extensions_tests -v
```

2026-11-25 实测：`tests/` 17 个全部通过（框架 2、Task A、Task B、集成 6），`extensions_tests/` 14 个全部通过（`test_recovery.py`、`test_batch.py`、`test_attacks.py`、`test_dashboard_signing.py`），共 31 个。

单独展示某一项扩展：

```bash
python -m unittest discover -s extensions_tests -p 'test_recovery.py' -v
```

```bash
python -m unittest discover -s extensions_tests -p 'test_batch.py' -v
```

注意：README 要求 B6 自带测试（篡改、错误账户、提交前后重放、nonce 递增），目前还没有 `test_security.py`。在补上之前，被问到就用 5f 的命令现场展示。

---

## 9. 讲解时可以指向的代码

| 功能 | 位置 |
|---|---|
| A1 提案 `propose()` | `backend/hotstuff.py:184` |
| A2 投票 `vote()`、提案校验 `_valid_proposal()` | `backend/hotstuff.py:280`、`593` |
| A2 `extends()`、`can_vote()` | `backend/node.py:31`、`52` |
| A3 `form_qc()` | `backend/hotstuff.py:320` |
| A4 `receive_qc()`（锁、三链提交） | `backend/node.py:82` |
| A5 `next_view()`、`enter_view()` | `backend/hotstuff.py:391`、`backend/node.py:19` |
| A6 `timeout()`、`recover()` | `backend/hotstuff.py:367`、`418` |
| B1 `submit()` | `backend/hotstuff.py:57` |
| B2 `select_transactions()` | `backend/hotstuff.py:501` |
| B3 `execute_committed()` | `backend/node.py:137` |
| B3/B4 `apply()`、`_apply_transfer()` | `backend/blockchain.py:55`、`18` |
| B4 `finalize_transactions()` | `backend/hotstuff.py:525` |
| B5 `configure_batch()` | `backend/hotstuff.py:551` |
| B6 `transaction_id()`、`verify_transaction()` | `backend/security.py:43`、`47` |
| 共识 → 执行的接线 `dispatch_qc()`（课程提供） | `backend/hotstuff.py:573` |
