import hashlib
import json
import re
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

DOMAIN = "COMP5567-HotStuff-2026/transfer/v1"

# assisted by aiL Public keys for deterministic classroom test accounts.
# Only public keys are loaded by the backend.
# The public key is derived from a private key seed found in `client_keys.py`
# these are test keys used for class purposes, 
# and anyone can re-derive the private key.
# SHA256("COMP5567 classroom test key/Alice")
# SHA256("COMP5567 classroom test key/Bob")
# SHA256("COMP5567 classroom test key/Charlie")
PUBLIC_KEY_HEX = {
    "Alice": "a3a60ce33f9b0307eb6eb87a441dd4197cd3f689f3e8b99d9e00211dcee87ab6",
    "Bob": "b9dbffcd14ecd8b20fe8ae2c5683350e031cb7dc26e3857f826b3ecbd228d677",
    "Charlie": "e3079cb237625c8c87384502fa6fd8d5c35a0704836126edb7dc204a65b0e500",
}

PUBLIC_KEYS = {
    account: Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_hex))
    for account, public_hex in PUBLIC_KEY_HEX.items()
}

def canonical_payload(sender, receiver, amount, nonce) -> bytes:
    body = {
        "domain": DOMAIN,
        "sender": sender,
        "receiver": receiver,
        "amount": amount,
        "nonce": nonce,
    }
    return json.dumps(
        body,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")

def transaction_id(sender, receiver, amount, nonce) -> str:
    payload = canonical_payload(sender, receiver, amount, nonce)
    return "tx-" + hashlib.sha256(payload).hexdigest()

def verify_transaction(sender, receiver, amount, nonce, signature) -> bool:

    if type(sender) is not str or type(receiver) is not str:
        return False

    if type(amount) is not int:
        return False

    if type(nonce) is not int or nonce < 0:
        return False

    if type(signature) is not str:
        return False

    if re.fullmatch(r"[0-9a-f]{128}", signature) is None:
        return False

    public_key = PUBLIC_KEYS.get(sender)
    if public_key is None:
        return False

    try:
        payload = canonical_payload(sender, receiver, amount, nonce)
        public_key.verify(bytes.fromhex(signature), payload)
    except (InvalidSignature, ValueError, TypeError):
        return False

    return True

def sign_transaction(sender, receiver, amount, nonce, *, private_key) -> dict:
    payload = canonical_payload(sender, receiver, amount, nonce)
    return {
        "sender": sender,
        "receiver": receiver,
        "amount": amount,
        "nonce": nonce,
        "signature": private_key.sign(payload).hex(),
    }

    