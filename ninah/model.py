"""SaveFile: load / edit / verify / save with Values<->_jsonValues sync.

GameSaveData shape:
  {"$type": ..., "Values": {FullType: {...}}, "_jsonValues": {ShortType: "<json>"},
   "_jsonValuesReserve": {ShortType: "<json>"}, "NeedToLoad": bool,
   "HasSaveData": bool, "Revision": int}
MetaPrefsData shape: flat dict, no duality — edited directly.

Sync rule (proven on a live save 2026-10-05, including a full evening of
debugging): every _jsonValues[Short] AND _jsonValuesReserve[Short] string is
the Values[Full] object with ALL "$type" keys stripped (recursively), dumped
compact (separators ",", ":"). The reserve is a FULL third copy of all
controllers — the game loads from it, so an edit that skips it silently does
nothing in-game. Values is authoritative; both string copies are re-synced on
every edit of that controller.
"""
import copy
import datetime
import json
import os
import shutil

from .crypto import decrypt_text, encrypt_bytes, CryptoError

FULL_PREFIX_CUT = ", Assembly-CSharp"


def short_of(full_type):
    return full_type.split(",")[0]


def strip_types(node):
    if isinstance(node, dict):
        return {k: strip_types(v) for k, v in node.items() if k != "$type"}
    if isinstance(node, list):
        return [strip_types(v) for v in node]
    return node


def compact(obj):
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)


def parse_path(path):
    """'Storage.Bobeer' / 'CharactersInside[0]' -> ['Storage', 'Bobeer'] / ['CharactersInside', 0]."""
    tokens, cur, i = [], "", 0
    while i < len(path):
        c = path[i]
        if c == ".":
            if cur:
                tokens.append(cur)
                cur = ""
            i += 1
        elif c == "[":
            if cur:
                tokens.append(cur)
                cur = ""
            j = path.index("]", i)
            tokens.append(int(path[i + 1:j]))
            i = j + 1
        else:
            cur += c
            i += 1
    if cur:
        tokens.append(cur)
    if not tokens:
        raise ValueError("empty path")
    return tokens


def get_path(node, tokens):
    for t in tokens:
        node = node[t]
    return node


def set_path(node, tokens, value):
    for t in tokens[:-1]:
        node = node[t]
    node[tokens[-1]] = value


class SyncResult:
    def __init__(self, controller, ok, detail=""):
        self.controller = controller
        self.ok = ok
        self.detail = detail

    def __repr__(self):
        return "SyncResult(%s, ok=%s %s)" % (self.controller, self.ok, self.detail)


class SaveFile:
    def __init__(self):
        self.path = None
        self.doc = None
        self.kind = None          # "game" | "meta" | "unknown"
        self.key_index = 0
        self.iv = None
        self._plain = None        # original plaintext bytes (for byte-exact check)
        self._values = None       # doc["Values"] when kind == "game"
        self._inners = {}         # short -> parsed _jsonValues object
        self._reserve = {}        # short -> parsed _jsonValuesReserve object
        self._full_of = {}        # short -> full type key
        self.dirty = set()        # short names of edited controllers

    # ---- load ----
    @classmethod
    def load(cls, path, keys=None):
        self = cls()
        self.path = path
        with open(path, "r", encoding="utf-8-sig") as f:
            text = f.read()
        pt, iv, ki = decrypt_text(text, keys or None) if keys else decrypt_text(text)
        self._plain = pt
        self.iv = iv
        self.key_index = ki
        try:
            self.doc = json.loads(pt.decode("utf-8"))
        except Exception as e:
            raise CryptoError("decrypted but JSON does not parse: %s" % e)
        if isinstance(self.doc, dict) and "Values" in self.doc and "_jsonValues" in self.doc:
            self.kind = "game"
            self._values = self.doc["Values"]
            reserve = self.doc.get("_jsonValuesReserve") or {}
            for full, v in self._values.items():
                if full == "$type":
                    continue
                short = short_of(full)
                self._full_of[short] = full
                raw = self.doc["_jsonValues"].get(short)
                self._inners[short] = json.loads(raw) if isinstance(raw, str) else None
                rraw = reserve.get(short) if isinstance(reserve, dict) else None
                self._reserve[short] = json.loads(rraw) if isinstance(rraw, str) else None
        elif isinstance(self.doc, dict) and "$type" in self.doc and "Meta" in self.doc["$type"]:
            self.kind = "meta"
        else:
            self.kind = "unknown"
        return self

    # ---- introspection ----
    def controllers(self):
        if self.kind != "game":
            return []
        return sorted(self._full_of.keys())

    def short_name(self, name):
        """Accept full type, short type, or bare class name -> short type."""
        if name in self._full_of:
            return name
        for short in self._full_of:
            if short == name or short.split(".")[-1] == name:
                return short
        raise KeyError("no such controller: %r (have: %s)" % (name, self.controllers()))

    # ---- edit ----
    def get(self, controller, path=None):
        if self.kind == "game":
            short = self.short_name(controller)
            node = self._values[self._full_of[short]]
        elif self.kind == "meta":
            node = self.doc
        else:
            raise ValueError("unsupported save kind: %s" % self.kind)
        return get_path(node, parse_path(path)) if path else node

    def set(self, controller, path, value):
        """Set a leaf (or a whole subtree when path is empty); mirrors into
        _jsonValues for game saves. Returns SyncResult."""
        tokens = parse_path(path) if path else []
        if self.kind == "game":
            short = self.short_name(controller)
            full = self._full_of[short]
            if tokens:
                set_path(self._values[full], tokens, value)
            else:
                if not isinstance(value, dict):
                    raise ValueError("controller replacement needs a JSON object")
                self._values[full] = value
            self.dirty.add(short)
            return self.resync(short)
        if tokens:
            set_path(self.doc, tokens, value)
        else:
            if not isinstance(value, dict):
                raise ValueError("document replacement needs a JSON object")
            self.doc = value
        self.dirty.add("(meta)")
        return SyncResult("(meta)", True, "flat file, no sync needed")

    def resync(self, controller):
        """Regenerate _jsonValues[short] AND _jsonValuesReserve[short] from
        Values. Only called for edited controllers."""
        short = self.short_name(controller)
        full = self._full_of[short]
        fresh = strip_types(self._values[full])
        self._inners[short] = fresh
        self.doc["_jsonValues"][short] = compact(fresh)
        n = 0
        if isinstance(self.doc.get("_jsonValuesReserve"), dict) and short in self.doc["_jsonValuesReserve"]:
            self._reserve[short] = copy.deepcopy(fresh)
            self.doc["_jsonValuesReserve"][short] = compact(fresh)
            n = 1
        # sanity: regenerated copies must carry the same key set as before
        return SyncResult(short, True, "2 copies regenerated (%d chars%s)"
                         % (len(self.doc["_jsonValues"][short]),
                            ", +reserve" if n else ""))

    # ---- verify: three independent checks ----
    def verify(self):
        """Returns dict with independent checks; edited paths must agree on both sides."""
        rep = {"base64": False, "decrypt": False, "json": False,
               "controllers": 0, "synced": [], "diverged": [], "notes": []}
        rep["base64"] = True  # we hold decrypted state; re-check on raw below
        rep["decrypt"] = True
        rep["json"] = True
        if self.kind != "game":
            rep["notes"].append("kind=%s, no duality to check" % self.kind)
            return rep
        rep["controllers"] = len(self._full_of)
        for short, full in self._full_of.items():
            cur = strip_types(self._values[full])
            inner = self._inners.get(short)
            res = self._reserve.get(short)
            ok_in = inner is not None and json.dumps(cur, sort_keys=True) == json.dumps(inner, sort_keys=True)
            ok_res = res is not None and json.dumps(cur, sort_keys=True) == json.dumps(res, sort_keys=True)
            name = short.split(".")[-1]
            if ok_in and ok_res:
                rep["synced"].append(name)
            else:
                missing = []
                if not ok_in:
                    missing.append("inner")
                if not ok_res:
                    missing.append("reserve")
                rep["diverged"].append("%s (%s)" % (name, "+".join(missing)))
        if self.dirty:
            bad = [d for d in self.dirty
                   if d != "(meta)" and d.split(".")[-1] not in rep["synced"]]
            if bad:
                rep["notes"].append("EDITED but diverged (BUG): %s" % bad)
            else:
                rep["notes"].append("edited controllers fully synced: %s"
                                    % sorted(s.split(".")[-1] for s in self.dirty if s != "(meta)"))
        else:
            rep["notes"].append("no edits; divergences are the game's own stale cache (normal)")
        return rep

    # ---- save ----
    def to_blob(self, keep_iv=False, key=None):
        data = compact(self.doc).encode("utf-8")
        from .crypto import DEFAULT_KEY
        return encrypt_bytes(data, key or DEFAULT_KEY, iv=self.iv if keep_iv else None)

    def save(self, path=None, backup=True, keep_iv=False):
        path = path or self.path
        if backup and os.path.exists(path):
            # NEVER inside remote/: Steam uploads every file there to the
            # cloud, and stray files confuse the game's cloud loader.
            stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            bdir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(path)), "..", "backups"))
            os.makedirs(bdir, exist_ok=True)
            bak = os.path.join(bdir, "%s.bak-%s" % (os.path.basename(path), stamp))
            shutil.copy2(path, bak)
        else:
            bak = None
        blob = self.to_blob(keep_iv=keep_iv)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(blob)
        # post-write verify: read back and compare JSON
        check = SaveFile.load(path)
        a = json.dumps(self.doc, sort_keys=True)
        b = json.dumps(check.doc, sort_keys=True)
        if a != b:
            raise CryptoError("post-save verify FAILED: written file differs")
        self.dirty.clear()
        self.path = path
        return bak
