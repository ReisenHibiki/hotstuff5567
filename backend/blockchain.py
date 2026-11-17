from .models import Transaction


INITIAL_BALANCES = {"Alice": 100, "Bob": 100, "Charlie": 100}


class StateMachine:
    def __init__(self):
        self.accounts = INITIAL_BALANCES.copy()
        # Receipts also make execution idempotent across catch-up and retries.
        self.receipts: dict[str, dict] = {}

    def apply(self, tx: Transaction) -> dict:
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

