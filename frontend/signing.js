// [AI-assisted] B6 browser signing client. The dashboard form signs transfers
// here, the same way sign_client.py does, so the server still holds only
// public keys. Keys are the deterministic classroom test keys of
// client_keys.py, seed = SHA-256("COMP5567 classroom test key/<account>"):
// public test fixtures, not real secrets.
(function (global) {
  const DOMAIN = 'COMP5567-HotStuff-2026/transfer/v1'; // must equal DOMAIN in backend/security.py
  // RFC 8410 PKCS#8 header that wraps a raw 32-byte Ed25519 seed.
  const PKCS8_PREFIX = [0x30, 0x2e, 0x02, 0x01, 0x00, 0x30, 0x05, 0x06, 0x03, 0x2b, 0x65, 0x70, 0x04, 0x22, 0x04, 0x20];
  const encoder = new TextEncoder();

  // Same bytes as json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).
  function canonicalPayload(sender, receiver, amount, nonce) {
    return JSON.stringify({amount, domain: DOMAIN, nonce, receiver, sender})
      .replace(/[\u007f-￿]/g, c => `\\u${c.charCodeAt(0).toString(16).padStart(4, '0')}`);
  }

  async function classroomKey(account) {
    const seed = await global.crypto.subtle.digest('SHA-256', encoder.encode(`COMP5567 classroom test key/${account}`));
    const pkcs8 = new Uint8Array([...PKCS8_PREFIX, ...new Uint8Array(seed)]);
    return global.crypto.subtle.importKey('pkcs8', pkcs8, {name: 'Ed25519'}, false, ['sign']);
  }

  async function signTransaction(sender, receiver, amount, nonce) {
    if (!global.crypto || !global.crypto.subtle) {
      throw new Error('Signing needs a secure page: open http://127.0.0.1:8000, or use sign_client.py');
    }
    let signature;
    try {
      const key = await classroomKey(sender);
      const payload = encoder.encode(canonicalPayload(sender, receiver, amount, nonce));
      signature = await global.crypto.subtle.sign({name: 'Ed25519'}, key, payload);
    } catch (error) {
      throw new Error(`This browser cannot create Ed25519 signatures (${error.message}); update it or use sign_client.py`);
    }
    const hex = Array.from(new Uint8Array(signature), byte => byte.toString(16).padStart(2, '0')).join('');
    return {sender, receiver, amount, nonce, signature: hex};
  }

  global.HotStuffSigning = {DOMAIN, canonicalPayload, signTransaction};
})(globalThis);
