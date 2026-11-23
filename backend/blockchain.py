from .models import Transaction
from .security import transaction_id, verify_transaction

INITIAL_BALANCES = {"Alice": 100, "Bob": 100, "Charlie": 100}


class StateMachine:
    def __init__(self, require_signatures: bool = False):
        self.accounts = INITIAL_BALANCES.copy()
        
        # Receipts also make execution idempotent across catch-up and retries.
        self.receipts: dict[str, dict] = {}

        self.nonces = {account: 0 for account in INITIAL_BALANCES}

        self.require_signatures = require_signatures

    def _apply_transfer(self, tx: Transaction) -> dict:
        """B3 B4 validate and deterministically execute one committed transaction.
        Called only through the committed-execution path (or isolated unit tests).
        Check known accounts, a strict positive integer amount and available
        funds. A failed transfer changes no balance. Return/store a receipt with
        status committed or rejected and error None or an explanatory string.
        Reusing a transaction ID returns its prior receipt without another debit.
        B6 extends this with signature verification, nonces and stable identities."""
        # B4 去重：同一个交易 ID 只执行一次。重复投递（重试、追赶）直接返回
        # 第一次的回执，不再扣款。成功和失败的回执都算“最终结果”。
        if tx.id in self.receipts:
            return self.receipts[tx.id]

        # B3 校验：执行层不信任准入层，自己再查一遍，保证每个副本对同一笔
        # 交易得出相同结论（确定性）。任何一项失败都不改余额。
        error = None
        if tx.sender not in self.accounts or tx.receiver not in self.accounts:
            error = "Unknown sender or receiver account"
        elif type(tx.amount) is not int or tx.amount < 1:
            # type(...) is int：排除 bool（True 是 int 的子类）和浮点数。
            error = "Amount must be a positive integer"
        elif self.accounts[tx.sender] < tx.amount:
            error = (f"Insufficient balance: {tx.sender} has "
                     f"{self.accounts[tx.sender]}, needs {tx.amount}")

        if error is None:
            # 所有检查通过后才改状态，扣款和入账一起发生。
            self.accounts[tx.sender] -= tx.amount
            self.accounts[tx.receiver] += tx.amount
            receipt = {"status": "committed", "error": None}
        else:
            # 失败的交易也写回执：它已随区块提交，只是执行被拒绝。
            receipt = {"status": "rejected", "error": error}

        self.receipts[tx.id] = receipt
        return receipt

    def apply(self, tx: Transaction) -> dict:
        """Execure one committed transaction, with optional B6 authentication"""

        # assisted by ai: Authentication, stable identity and nonce checks

        def rejected(message: str) -> dict:
            # 1.不自动写入 self.reciepts, 仅构造返回值
            return {"status": "rejected", "error": message}
    
        if not isinstance(tx, Transaction):
            return rejected("Invalid transaction object")

        if type(tx.id) is not str or not tx.id:
            return rejected("Invalid transaction ID")

        if type(tx.sender) is not str or type(tx.receiver) is not str:
            return rejected("Account names must be str")

            # 2.两个字段都没有，才属于 unsigned/basic 路径
        unsigned = tx.nonce is None and tx.signature is None

        if unsigned:
            if self.require_signatures:
                return rejected("Signature required")
            return self._apply_transfer(tx)

        # 给了其中一个字段，不能退回 basic 路径
        if tx.nonce is None or tx.signature is None:
            return rejected("Nonce and signature must be provided together")

        # 3. 签名载荷的严格类型检查。
        # 此处不检查 amount > 0：非正整数金额属于后面的业务失败
        if type(tx.amount) is not int:
            return rejected("Amount must be an integer")

        if type(tx.nonce) is not int or tx.nonce < 0:
            return rejected("Nonce must be a non-negative integer")

        if type(tx.signature) is not str:
            return rejected("Signature must be a string")

        # 4. 按载荷重算身份。非法输入不得中断整个区块的执行。
        try:
            expected_id = transaction_id(
                tx.sender,
                tx.receiver,
                tx.amount,
                tx.nonce,
            )
        except (TypeError, ValueError):
            return rejected("Invalid canonical payload")

        if tx.id != expected_id:
            return rejected("Transaction ID does not match payload")

        # 5.执行时重新验签。失败不保存最终回执
        if not verify_transaction(
            tx.sender,
            tx.receiver,
            tx.amount,
            tx.nonce,
            tx.signature,
        ):
            return rejected("Invalid signature or unknown signing account")

        if tx.sender not in self.accounts or tx.sender not in self.nonces:
            return rejected("Unknown sender account")

        # 6.合法重复投递必须先返回旧回执，再考虑 nonce
        if tx.id in self.receipts:
            return self.receipts[tx.id]

        expected_nonce = self.nonces[tx.sender]

        # 7. 旧 nonce 已经不可再用，可以记录最终拒绝。
        if tx.nonce < expected_nonce:
            receipt = rejected("Nonce already consumed")
            self.receipts[tx.id] = receipt
            return receipt

        # 未来 nonce 现在不可执行，但之后可能变得可执行
        # 因此不把这次拒绝保存为最终回执。
        if tx.nonce > expected_nonce:
            return rejected("Future nonce")

        # 8. 已认证且 nonce 匹配：执行原有 B3/B4 业务规则
        # _apply_transfer 会保存 committed 或 rejected 的最终回执
        receipt = self._apply_transfer(tx)

        # 成功和已认证的业务失败都消耗一次 nonce
        self.nonces[tx.sender] = expected_nonce + 1
        return receipt

#         | 情况 | 是否执行转账 | nonce 是否增加 | 是否保存最终回执 |
# |---|---|---|---|
# | 字段类型错误、ID 不匹配 | 否 | 否 | 否 |
# | 签名错误 | 否 | 否 | 否 |
# | 合法交易的 ID 已有回执 | 否 | 否 | 返回已有回执 |
# | 签名有效，但 nonce 过旧 | 否 | 否 | 是，rejected |
# | 签名有效，但 nonce 超前 | 否 | 否 | 否 |
# | 签名有效、nonce 匹配、余额不足 | 否 | 是 | 是，rejected |
# | 签名有效、nonce 匹配、转账成功 | 是 | 是 | 是，committed |