"""AES save crypto. Format (see NINAH_SAVE_FORMAT_2026-10-05.md):

file = Base64( IV[16] + AES-256-CBC-PKCS7(plaintext, key) )
key  = ASCII bytes of "e38c9861b43264e37c1eef64d7925dde" (NOT hex-decoded!)
"""
import base64
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad

IV_SIZE = 16
DEFAULT_KEY = "e38c9861b43264e37c1eef64d7925dde".encode("utf-8")

assert len(DEFAULT_KEY) == 32, "AES-256 needs 32 key bytes"


class CryptoError(ValueError):
    pass


def decrypt_text(blob_b64, keys=(DEFAULT_KEY,)):
    """Base64 blob -> (plaintext bytes, iv, key_index). Tries each key in order."""
    try:
        raw = base64.b64decode(blob_b64.strip())
    except Exception as e:
        raise CryptoError("not valid Base64: %s" % e)
    if len(raw) < IV_SIZE + 16 or len(raw) % 16 != 0:
        raise CryptoError("bad blob size %d (need 16-byte IV + >=1 block)" % len(raw))
    iv, ct = raw[:IV_SIZE], raw[IV_SIZE:]
    last = None
    for i, key in enumerate(keys):
        try:
            pt = unpad(AES.new(key, AES.MODE_CBC, iv).decrypt(ct), AES.block_size)
            return pt, iv, i
        except Exception as e:
            last = e
    raise CryptoError("no key matched (tried %d): %s. "
                      "Game key may have rotated — add it to keys.json" % (len(keys), last))


def encrypt_bytes(plaintext, key=DEFAULT_KEY, iv=None):
    """Plaintext bytes -> Base64 blob. Fresh random IV unless one is given."""
    if iv is None:
        iv = get_random_bytes(IV_SIZE)
    ct = AES.new(key, AES.MODE_CBC, iv).encrypt(pad(plaintext, AES.block_size))
    return base64.b64encode(iv + ct).decode("ascii")
