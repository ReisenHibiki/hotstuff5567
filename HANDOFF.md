# Task B 交接文档

更新日期：2026-11-17
课程：COMP5567 HotStuff Project（演示 2026-11-29，提交截止 2026-12-02 23:59）

## 1. 一句话现状

Task B 的 B1–B5 已实现并通过全部公开测试，改动在本地分支 `taskB-eve` 上，**尚未提交、尚未推送**。B6（交易签名与 nonce）未做。

## 2. 代码位置与环境

| 项 | 值 |
| --- | --- |
| 仓库 | https://github.com/ReisenHibiki/hotstuff5567 |
| 基线 | `hengyu` 分支，提交 `a501942 complete A5` |
| 工作分支 | `taskB-eve`（仅本地，从 `a501942` 分出） |
| 状态 | 3 个文件有未提交改动；`hengyu` 与远端未被改动 |
| Python | 需要 3.10+；项目内 `.venv` 为 3.12.16（已被 `.gitignore` 忽略） |

系统自带的 `python3` 是 3.9，跑不了本项目（`str | None` 语法报错）。新机器上的准备步骤：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## 3. 已完成的内容

| 项 | 分值 | 函数 | 文件 |
| --- | ---: | --- | --- |
| B1 准入与交易池 | 5 | `HotStuffDemo.submit` | `backend/hotstuff.py` |
| B2 区块载荷 | 5 | `HotStuffDemo.select_transactions` | `backend/hotstuff.py` |
| B3 状态执行 | 8 | `Node.execute_committed`、`StateMachine.apply` | `backend/node.py`、`backend/blockchain.py` |
| B4 回执与去重 | 7 | `StateMachine.apply`、`HotStuffDemo.finalize_transactions` | `backend/blockchain.py`、`backend/hotstuff.py` |
| B5 批量配置（可选） | 2 | `HotStuffDemo.configure_batch` | `backend/hotstuff.py` |

各函数的行为：

- **`submit`**：校验账户在 `INITIAL_BALANCES` 中、金额是 1 到 1000000 的严格整数（拒绝 `True` 和浮点数），全部通过后才分配 `Tx1, Tx2…` 并写入 `transactions` 和 `mempool`。不检查余额，不改余额。
- **`select_transactions`**：从父块沿父指针走到创世块，收集这条链上已打包的交易 ID；再按 mempool 顺序挑出不在其中的交易，最多 `max_txs_per_block` 笔。只读不删，废弃分支上的交易可被重新打包。
- **`execute_committed`**：崩溃副本直接返回。先检查所有传入的区块 ID 都在本副本的 `committed_blocks` 中，否则在任何状态变更前抛 `ValueError`；再按区块顺序和载荷顺序逐笔调用 `machine.apply()`。
- **`apply`**：已有回执的 ID 直接返回原回执（去重）。否则重新校验账户、金额、余额；通过则扣款入账并记 `committed`，失败则不改余额并记 `rejected` 加错误原因。
- **`finalize_transactions`**：把新提交区块中的交易从 mempool 移除（成功和被拒的都移除）并写日志。已移除的跳过，所以重复调用无副作用。
- **`configure_batch`**：只接受正整数（拒绝 bool、0、负数、非整数），失败时不改状态；成功则更新 `max_txs_per_block` 并返回该值。

## 4. 设计决定（需写进报告）

- **拒绝自转账**：`sender == receiver` 时 `submit` 抛 `ValueError`。规范没有规定，这是我们自己的选择；想允许的话删掉对应两行。
- **准入不查余额**：余额只有在区块提交后才能确定，所以余额不足在执行时判定，产生 `rejected` 回执，而不是在提交时拒绝。
- **执行层重复校验**：`apply` 不信任准入层，自己再查一遍账户和金额，保证各副本结论一致。
- **交易 ID 来源**：`len(self.transactions) + 1`。`transactions` 只增不减，`reset()` 后回到 `Tx1`。做 B6 时这一点要改成由载荷推导。

## 5. 测试结果

2026-11-17 在 `.venv`（Python 3.12.16）下运行：

| 命令 | 结果 |
| --- | --- |
| `python -m unittest discover -s tests -v` | 17 个全部通过（框架 2、Task A、Task B 5、集成 6） |
| `python -m unittest extensions_tests.test_batch -v` | 2 个全部通过（B5） |
| `python -m unittest extensions_tests.test_recovery -v` | 5 个中 4 个报错，原因是 A6 的 `timeout`/`recover` 未实现，与 Task B 无关 |

尚未做的验证：没有启动 `python backend/main.py` 在浏览器面板上手动走一遍转账流程；没有为 Task B 补充公开测试以外的用例。

## 6. 未完成的事项

Task B 范围内：

1. **B6 交易安全（可选，3 分）**：未开始。需要新增 `sign_transaction`、`verify_transaction`、`transaction_id`；给 `Transaction` 和请求模型加 nonce 与签名字段；`submit` 和 `apply` 各验一次签名；按账户维护 nonce（从 0 开始，只有已提交的执行才消耗）；ID 由载荷而非签名推导；并自己补测试（篡改、错误账户、提交前后重放、nonce 递增）。
2. **提交代码**：`taskB-eve` 上的改动还没有 commit。
3. **更新 `changes.md`**：还没有加 Task B 的贡献行和已完成扩展（B5）的说明。
4. **合并**：尚未与 `hengyu` 或 `main` 合并，也没有开 PR。
5. **现场演示准备**：演示要求展示交易提交、提交前后的余额、回执和一个失败用例，需要在面板上实际演练。

Task B 范围外（供全组参考）：

- A6 恢复（`timeout`、`recover`）和 A7 恶意节点（`inject_attack`）仍是 TODO。
- 报告、PPT、贡献表尚未开始。

## 7. AI 使用情况（重要）

B1–B5 的全部 6 个函数都是在 AI（Claude）辅助下写成的，每个函数体开头都有 `[AI-assisted]` 注释。

课程政策规定：AI 只能辅助单个函数的实现或调试；整个组件由 AI 完成的，该组件记 0 分；未声明的 AI 辅助代码扣相应分数；答辩时讲不清 AI 辅助的函数，最多扣完该函数的分数。

目前 Task B 已实现的部分全部来自 AI，存在被认定为“整个组件由 AI 完成”的风险。接手的人需要决定如何处理，至少应当：

- 逐个函数读懂并能独立讲解，必要时按自己的理解重写。
- 在报告中如实列出哪些函数使用了 AI、AI 提供了什么帮助。
- 保留代码中的 `[AI-assisted]` 标注。

## 8. 建议的下一步

1. 启动服务，在面板上走一遍：提交转账 → 逐步推进到提交 → 看余额和回执 → 做一笔余额不足的转账。
2. 读懂并按需重写 B1–B5，然后 commit 到 `taskB-eve`。
3. 更新 `changes.md`。
4. 和组员确认后再推送并合并到 `hengyu`。
5. 时间允许再做 B6。

| 情况 | 是否执行转账 | nonce 是否增加 | 是否保存最终回执 |
|---|---|---|---|
| 字段类型错误、ID 不匹配 | 否 | 否 | 否 |
| 签名错误 | 否 | 否 | 否 |
| 合法交易的 ID 已有回执 | 否 | 否 | 返回已有回执 |
| 签名有效，但 nonce 过旧 | 否 | 否 | 是，rejected |
| 签名有效，但 nonce 超前 | 否 | 否 | 否 |
| 签名有效、nonce 匹配、余额不足 | 否 | 是 | 是，rejected |
| 签名有效、nonce 匹配、转账成功 | 是 | 是 | 是，committed |

| 测试组 | 必须断言的结果 |
|---|---|
| 安全模式与 reset | 未签名、缺 nonce、缺 signature 都被拒；reset 后仍要求签名；新状态的 nonce 为 0 |
| 篡改与错误账户 | 改金额、用 Bob 的密钥签 Alice 的交易均被拒；交易表、池、余额、nonce 不变 |
| 提交前重试 | 两次 `submit(**request)` 返回同一个对象；池中只有一个 ID；余额和执行 nonce 不变 |
| 提交后重试 | 通过真实 `step()` 等待最终回执，再重试；ID 不变、余额只扣一次、nonce 只增加一次 |
| nonce 与余额不足 | 连续 nonce 可以入池；同 nonce 不同载荷、跳号 nonce 被拒；账户之间独立；已认证余额不足产生最终 rejected 并消耗 nonce |
| 执行层再次验证 | 绕过准入给 `apply()` 假签名、伪造 ID、畸形字段；均不扣款、不消耗 nonce、不占用真实交易的最终回执 |

“未来 nonce 的处理”

伪造签名不会污染真实交易的 ID。
原样重放返回原来的回执。
用过的 nonce 会存一条最终的拒绝回执，未来 nonce 则不存。
已认证但余额不足，照样消耗 nonce。
字段类型不对时不会抛异常

TODO:
submit() 的签名路径，包括拒绝未签名的请求
TransferRequest 加 nonce 和 signature 两个字段
最小签名客户端
test_security.py
