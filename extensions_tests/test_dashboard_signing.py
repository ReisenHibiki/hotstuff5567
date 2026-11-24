"""B6 dashboard signing: frontend/signing.js must produce exactly the request
sign_client.py produces, and the snapshot must expose the nonces the form uses."""
# [AI-assisted] Tests for the browser signing client and snapshot nonces.
import json
import shutil
import subprocess
import unittest
from pathlib import Path

from backend.hotstuff import HotStuffDemo
from backend.security import sign_transaction, verify_transaction
from client_keys import classroom_private_key

SIGNING_JS = Path(__file__).resolve().parent.parent / "frontend" / "signing.js"


def signed(sender, receiver, amount, nonce):
    return sign_transaction(sender, receiver, amount, nonce, private_key=classroom_private_key(sender))


class DashboardSigningTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node.js is needed to run frontend/signing.js")
    def test_browser_signature_matches_python_client(self):
        cases = [("Alice", "Bob", 10, 0), ("Bob", "Charlie", 1_000_000, 7), ("Charlie", "Alice", 1, 42)]
        script = (
            f"require({json.dumps(str(SIGNING_JS))});"
            f"Promise.all({json.dumps(cases)}.map(c => HotStuffSigning.signTransaction(...c)))"
            ".then(r => console.log(JSON.stringify(r)));"
        )
        result = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        browser_requests = json.loads(result.stdout)
        # Ed25519 is deterministic: same key and canonical payload give the same signature.
        self.assertEqual(browser_requests, [signed(*case) for case in cases])
        for request in browser_requests:
            self.assertTrue(verify_transaction(**request))

    def test_snapshot_reports_committed_and_next_nonces(self):
        demo = HotStuffDemo(require_signatures=True)
        state = demo.snapshot()
        self.assertEqual(state["nonces"], {"Alice": 0, "Bob": 0, "Charlie": 0})
        self.assertEqual(state["next_nonces"], {"Alice": 0, "Bob": 0, "Charlie": 0})

        demo.submit(**signed("Alice", "Bob", 10, 0))
        state = demo.snapshot()
        self.assertEqual(state["nonces"]["Alice"], 0)       # admission consumes nothing
        self.assertEqual(state["next_nonces"]["Alice"], 1)  # the pending transfer holds nonce 0
        self.assertEqual(state["next_nonces"]["Bob"], 0)    # accounts are independent

        for _ in range(200):
            if not demo.mempool:
                break
            demo.step()
        state = demo.snapshot()
        self.assertEqual(state["mempool"], [])
        self.assertEqual(state["nonces"], {"Alice": 1, "Bob": 0, "Charlie": 0})
        self.assertEqual(state["next_nonces"], {"Alice": 1, "Bob": 0, "Charlie": 0})

        # The form's auto-filled nonce is accepted, and the stale one is not.
        demo.submit(**signed("Alice", "Charlie", 5, state["next_nonces"]["Alice"]))
        with self.assertRaises(ValueError):
            demo.submit(**signed("Alice", "Charlie", 6, 0))

    def test_next_nonce_is_none_without_live_replicas(self):
        demo = HotStuffDemo(require_signatures=True)
        for node in demo.nodes:
            node.crashed = True
        self.assertEqual(demo.snapshot()["next_nonces"], {"Alice": None, "Bob": None, "Charlie": None})


if __name__ == "__main__":
    unittest.main()
