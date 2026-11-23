import argparse
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from backend.security import sign_transaction
from client_keys import classroom_private_key


def main():
    # [AI-assisted] Minimal classroom signing client.
    parser = argparse.ArgumentParser()
    parser.add_argument("sender")
    parser.add_argument("receiver")
    parser.add_argument("amount", type=int)
    parser.add_argument("nonce", type=int)
    args = parser.parse_args()

    body = sign_transaction(
        args.sender,
        args.receiver,
        args.amount,
        args.nonce,
        private_key=classroom_private_key(args.sender),
    )

    request = Request(
        "http://127.0.0.1:8000/api/transactions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=10) as response:
            print(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise SystemExit(
            f"HTTP {exc.code}: {exc.read().decode('utf-8')}"
        )


if __name__ == "__main__":
    main()