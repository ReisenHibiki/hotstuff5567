import hashlib

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ACCOUNTS = ("Alice", "Bob", "Charlie")

def classroom_private_key(account: str) -> Ed25519PrivateKey:
    """return a reproducible classroom test key, not a real account secret"""
    #assisted by ai, Deterministic key fixture for the signing client and tests
    if type(account) is not str or account not in ACCOUNTS:
        raise ValueError("unknown classroom account")

    label = f"COMP5567 classroom test key/{account}"
    seed = hashlib.sha256(label.encode("utf-8")).digest()
    return Ed25519PrivateKey.from_private_bytes(seed)
