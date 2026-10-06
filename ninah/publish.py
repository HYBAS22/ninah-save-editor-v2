"""Multi-target publish: one edited save -> file + registry + Steam Cloud.

Proven layout (2026-10-05, experiment "Quantum Beer Hall"):
- registry (PlayerPrefs) wins when cloud is unreachable;
- cloud wins when it reads;
- the plain file is Steam's sync cache, never read directly by the game.
Writing all three with identical bytes makes the read path irrelevant.
"""
import os

from . import reg as reg_mod
from .crypto import CryptoError

TARGETS = ("registry", "file", "cloud")


def default_backup_dir(save_path):
    return os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(save_path)), "..", "backups"))


def publish(savefile, targets=TARGETS, backup_dir=None,
            cloud_factory=None, filename=None, reg_base=None):
    """Returns {target: {"ok": bool, "detail": str, "backup": path|None}}."""
    targets = [t for t in targets if t in TARGETS]
    if not targets:
        raise ValueError("no targets")
    backup_dir = backup_dir or default_backup_dir(savefile.path)
    os.makedirs(backup_dir, exist_ok=True)
    if reg_base is not None:
        real_base, reg_mod.REG_BASE = reg_mod.REG_BASE, reg_base
    else:
        real_base = None
    blob = savefile.to_blob(keep_iv=False)
    filename = filename or reg_mod.FILENAMES.get(savefile.kind, "GameSaveData.sav")
    rep = {}

    if "file" in targets:
        try:
            bak = savefile.save(backup=True)  # re-reads + compares JSON itself
            rep["file"] = {"ok": True, "detail": savefile.path, "backup": bak}
        except (CryptoError, OSError) as e:
            rep["file"] = {"ok": False, "detail": str(e), "backup": None}

    if "registry" in targets:
        try:
            old_raw = reg_mod.write_blob(savefile.kind, blob)
            if old_raw is None:
                bak = None
            else:
                bak = reg_mod.backup_path(savefile.kind, backup_dir)
                with open(bak, "wb") as f:
                    f.write(old_raw)
            check_text, _ = reg_mod.read_blob(savefile.kind)
            if check_text != blob:
                raise CryptoError("registry re-read differs")
            rep["registry"] = {"ok": True, "detail": "HKCU\\...\\%s" %
                               reg_mod.value_name(savefile.kind), "backup": bak}
        except (CryptoError, OSError) as e:
            rep["registry"] = {"ok": False, "detail": str(e), "backup": None}

    if "cloud" in targets:
        try:
            from .cloudapi import Cloud
            fac = cloud_factory or Cloud
            with fac() as c:
                old = None
                try:
                    old = c.read(filename)
                    with open(os.path.join(backup_dir, "%s.cloud-prev" % filename), "wb") as f:
                        f.write(old)
                except Exception:
                    pass
                c.write(filename, blob)
                back = c.read(filename)
                if back.decode("ascii") != blob:
                    raise CryptoError("cloud re-read differs")
                rep["cloud"] = {"ok": True, "detail": "%d bytes, re-read matches" % len(back),
                                "backup": os.path.join(backup_dir, "%s.cloud-prev" % filename)
                                if old is not None else None}
        except Exception as e:
            rep["cloud"] = {"ok": False, "detail": "%s: %s" % (type(e).__name__, e),
                            "backup": None}
    if real_base is not None:
        reg_mod.REG_BASE = real_base
    savefile.dirty.clear()
    return rep
