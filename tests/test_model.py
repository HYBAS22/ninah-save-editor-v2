"""Unit + round-trip tests. Needs only pycryptodome. No real saves touched.

Integration against real save copies:
  NINAH_TEST_SAVE=<path-to-GameSaveData-copy> NINAH_TEST_META=<path-to-MetaPrefs-copy>
  python -m unittest
"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ninah.crypto import decrypt_text, encrypt_bytes, CryptoError, DEFAULT_KEY
from ninah.model import SaveFile, parse_path, strip_types
from ninah import simple as simple_mod
from ninah.model import get_path


class TestCrypto(unittest.TestCase):
    def test_roundtrip(self):
        pt = b'{"a": 1, "b": [true, "x"]}'
        blob = encrypt_bytes(pt)
        back, iv, ki = decrypt_text(blob)
        self.assertEqual(back, pt)
        self.assertEqual(ki, 0)

    def test_same_iv_byte_identical(self):
        pt = b'{"a": 1}'
        blob1 = encrypt_bytes(pt, iv=b"0123456789abcdef")
        blob2 = encrypt_bytes(pt, iv=b"0123456789abcdef")
        self.assertEqual(blob1, blob2)

    def test_bad_base64(self):
        with self.assertRaises(CryptoError):
            decrypt_text("!!! not base64 !!!")

    def test_wrong_key(self):
        blob = encrypt_bytes(b'{"a": 1}')
        with self.assertRaises(CryptoError):
            decrypt_text(blob, keys=[b"0" * 32])


class TestModel(unittest.TestCase):
    def test_paths(self):
        self.assertEqual(parse_path("Storage.Bobeer"), ["Storage", "Bobeer"])
        self.assertEqual(parse_path("CharactersInside[0]"), ["CharactersInside", 0])
        self.assertEqual(parse_path("A[0].B"), ["A", 0, "B"])

    def test_strip(self):
        src = {"$type": "T", "a": 1, "n": [{"$type": "U", "b": 2}]}
        self.assertEqual(strip_types(src), {"a": 1, "n": [{"b": 2}]})


class TestIntegration(unittest.TestCase):
    SRC = os.environ.get("NINAH_TEST_SAVE")
    META = os.environ.get("NINAH_TEST_META")

    def test_simple_spec_resolves(self):
        """Every Simple-mode field must resolve against the real save shape."""
        if not self.SRC or not os.path.isfile(self.SRC):
            self.skipTest("set NINAH_TEST_SAVE to a save COPY to run")
        tmp = tempfile.mkdtemp()
        p = self._copy(tmp)
        sf = SaveFile.load(p)
        secs = simple_mod.sections_for(sf.kind)
        n = 0
        for sec in secs:
            for f in sec["fields"]:
                base = sf.doc if f["ctl"] == "_meta" else sf.get(f["ctl"], None)
                get_path(base, parse_path(f["path"]))
                n += 1
        self.assertGreater(n, 30, "spec looks empty")
        if self.META and os.path.isfile(self.META):
            dst = os.path.join(tmp, "M.sav")
            with open(self.META, encoding="utf-8") as fh:
                data = fh.read()
            with open(dst, "w", encoding="utf-8") as fh:
                fh.write(data)
            sm = SaveFile.load(dst)
            self.assertEqual(sm.kind, "meta")
            for sec in simple_mod.sections_for("meta"):
                for f in sec["fields"]:
                    get_path(sm.doc, parse_path(f["path"]))
                    n += 1
        print("spec fields resolved:", n)

    def _copy(self, tmp):
        dst = os.path.join(tmp, "T.sav")
        with open(self.SRC, encoding="utf-8") as f:
            data = f.read()
        with open(dst, "w", encoding="utf-8") as f:
            f.write(data)
        return dst

    def test_live_files(self):
        if not self.SRC or not os.path.isfile(self.SRC):
            self.skipTest("set NINAH_TEST_SAVE to a save COPY to run")
        tmp = tempfile.mkdtemp()
        p = self._copy(tmp)
        with open(p, encoding="utf-8") as f:
            original = f.read()

        sf = SaveFile.load(p)
        # byte-exact re-encrypt with original IV
        self.assertEqual(sf.to_blob(keep_iv=True), original)

        if sf.kind == "game":
            short = sf.short_name("ConsumablesController")
            before = sf.get("ConsumablesController", "Storage.Bobeer")
            sf.set("ConsumablesController", "Storage.Bobeer", 12345)
            rep = sf.verify()
            self.assertFalse(any("BUG" in n for n in rep["notes"]), rep)
            bak = sf.save(backup=True)
            self.assertTrue(bak and os.path.isfile(bak))
            sf2 = SaveFile.load(p)
            self.assertEqual(sf2.get("ConsumablesController", "Storage.Bobeer"), 12345)
            self.assertEqual(
                sf2._inners[short]["Storage"]["Bobeer"], 12345)
            self.assertEqual(
                sf2._reserve[short]["Storage"]["Bobeer"], 12345)
        else:
            self.assertEqual(sf.kind, "meta")


class TestRegistry(unittest.TestCase):
    BASE = r"Software\NINAHToolTest"
    BLOB = "aGVsbG8td29ybGQ="  # base64, content irrelevant here

    def _scratch(self):
        import winreg
        try:
            winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.BASE)
        except OSError as e:
            self.skipTest("no registry access: %s" % e)

    def _clean(self):
        import winreg
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, self.BASE)
        except OSError:
            pass

    def test_roundtrip_scratch_key(self):
        from ninah import reg as reg_mod
        self._scratch()
        try:
            reg_mod.write_blob("game", self.BLOB, base=self.BASE)
            text, raw = reg_mod.read_blob("game", base=self.BASE)
            self.assertEqual(text, self.BLOB)
            self.assertTrue(raw.endswith(b"\x00"))
            with self.assertRaises(reg_mod.RegistryError):
                reg_mod.read_blob("nope", base=self.BASE)
        finally:
            self._clean()

    def test_publish_file_and_registry(self):
        if not os.environ.get("NINAH_TEST_SAVE"):
            self.skipTest("set NINAH_TEST_SAVE to a save COPY to run")
        import winreg
        from ninah import reg as reg_mod
        from ninah.publish import publish
        self._scratch()
        try:
            tmp = tempfile.mkdtemp()
            dst = os.path.join(tmp, "T.sav")
            with open(os.environ["NINAH_TEST_SAVE"], encoding="utf-8") as f:
                data = f.read()
            with open(dst, "w", encoding="utf-8") as f:
                f.write(data)
            sf = SaveFile.load(dst)
            sf.set("ConsumablesController", "Storage.Coffee", 11)
            real_base = reg_mod.REG_BASE
            reg_mod.REG_BASE = self.BASE
            try:
                rep = publish(sf, targets=("file", "registry"),
                              backup_dir=os.path.join(tmp, "backups"))
            finally:
                reg_mod.REG_BASE = real_base
            self.assertTrue(rep["file"]["ok"], rep)
            self.assertTrue(rep["registry"]["ok"], rep)
            text, _ = reg_mod.read_blob("game", base=self.BASE)
            back = SaveFile.load(dst)
            self.assertEqual(
                back.get("ConsumablesController", "Storage.Coffee"), 11)
            self.assertIn("11", text)
        finally:
            self._clean()


class TestCloudChild(unittest.TestCase):
    def test_cloud_list(self):
        if not os.environ.get("NINAH_TEST_CLOUD"):
            self.skipTest("set NINAH_TEST_CLOUD=1 to run (needs live Steam)")
        from ninah.cloudapi import cloud_call
        out = cloud_call("list")
        names = [f["name"] for f in out["files"]]
        self.assertIn("GameSaveData.sav", names)


if __name__ == "__main__":
    unittest.main()
