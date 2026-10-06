"""Full snapshots: file(s) + registry + cloud copies + manifest, in one dir.

Snapshots live OUTSIDE Steam sync (3180070/backups/snap-<stamp>/), so Steam
never uploads them and the game never sees them.
"""
import datetime
import json
import os
import shutil

from . import reg as reg_mod
from . import steam as steam_mod

MANIFEST = "manifest.json"


def snapshots_root(remote_dir=None):
    if remote_dir is None:
        saves = steam_mod.find_saves()
        if not saves:
            raise OSError("no saves found")
        remote_dir = os.path.dirname(saves[0]["path"])
    root = os.path.normpath(os.path.join(remote_dir, "..", "backups", "snaps"))
    os.makedirs(root, exist_ok=True)
    return root


def take(label="", kinds=("game", "meta"), cloud=True):
    """Snapshot current state of every store. Returns snapshot dir."""
    saves = {s["kind"]: s["path"] for s in steam_mod.find_saves()}
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    name = "snap-%s%s" % (stamp, ("-" + label) if label else "")
    dest = os.path.join(snapshots_root(), name)
    os.makedirs(dest)
    manifest = {"time": stamp, "label": label, "files": {}}
    for kind in kinds:
        entry = {}
        if kind in saves and os.path.isfile(saves[kind]):
            shutil.copy2(saves[kind], os.path.join(dest, "%s.sav" % kind))
            entry["file"] = True
        try:
            text, _ = reg_mod.read_blob(kind)
            with open(os.path.join(dest, "%s.reg.txt" % kind), "w",
                      encoding="utf-8", newline="") as f:
                f.write(text)
            entry["registry"] = True
        except reg_mod.RegistryError as e:
            entry["registry"] = str(e)
        manifest["files"][kind] = entry
    if cloud:
        try:
            from .cloudapi import cloud_call
            have = dict((f["name"], f["size"]) for f in cloud_call("list")["files"])
            for kind in kinds:
                fn = reg_mod.FILENAMES[kind]
                if fn in have:
                    with open(os.path.join(dest, "%s.cloud" % kind), "wb") as f:
                        f.write(cloud_call("read", fn)["data"].encode("ascii"))
                    manifest["files"][kind]["cloud"] = True
                else:
                    manifest["files"][kind]["cloud"] = "absent in cloud"
        except Exception as e:
            manifest["cloud_error"] = "%s: %s" % (type(e).__name__, e)
    with open(os.path.join(dest, MANIFEST), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    return dest


def list_snaps():
    try:
        root = snapshots_root()
    except OSError:
        return []
    out = []
    for d in sorted(os.listdir(root), reverse=True):
        p = os.path.join(root, d)
        m = os.path.join(p, MANIFEST)
        if os.path.isdir(p) and os.path.isfile(m):
            try:
                out.append((d, json.load(open(m, encoding="utf-8"))))
            except Exception:
                pass
    return out


def restore(snap_dir, targets=("registry", "file", "cloud"), kinds=("game", "meta")):
    """Write a snapshot back to live stores. Returns {target: {ok,...}}."""
    from .publish import publish
    from .model import SaveFile
    live = {s["kind"]: s["path"] for s in steam_mod.find_saves()}
    bdir = os.path.dirname(os.path.normpath(snap_dir))
    rep = {}
    for kind in kinds:
        src = os.path.join(snap_dir, "%s.sav" % kind)
        if not os.path.isfile(src):
            continue
        sf = SaveFile.load(src)
        if "file" in targets:
            if kind not in live:
                rep.setdefault("file", {})[kind] = {
                    "ok": False, "detail": "no live save found", "backup": None}
                continue
            sf.path = live[kind]  # point file target at the LIVE path
        r = publish(sf, targets=[t for t in targets if t in ("registry", "file", "cloud")],
                    backup_dir=bdir)
        for t, v in r.items():
            rep.setdefault(t, {})[kind] = v
    return rep
