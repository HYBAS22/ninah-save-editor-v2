"""CLI: find / dec / info / get / set / enc / verify."""
import argparse
import json
import os
import sys

from . import __version__
from .crypto import DEFAULT_KEY, CryptoError
from .model import SaveFile
from . import steam as steam_mod


def load_keys(path):
    if path and os.path.isfile(path):
        data = json.load(open(path, encoding="utf-8"))
        return [k.encode("utf-8") for k in data["keys"]]
    return [DEFAULT_KEY]


def parse_value(s):
    try:
        return json.loads(s)
    except Exception:
        return s


def cmd_find(args):
    saves = steam_mod.find_saves()
    if not saves:
        print("no saves found (Steam dir: %s)" % steam_mod.steam_install_dir())
        return 1
    for s in saves:
        print("%s  [%s] %d bytes" % (s["path"], s["kind"], s["size"]))
    return 0


def open_save(args, path=None):
    keys = load_keys(args.keys)
    return SaveFile.load(path or args.save, keys=keys)


def cmd_dec(args):
    sf = open_save(args)
    data = json.dumps(sf.doc, indent=2, ensure_ascii=False)
    if args.out:
        open(args.out, "w", encoding="utf-8").write(data + "\n")
        print("wrote %s (%d chars, kind=%s)" % (args.out, len(data), sf.kind))
    else:
        print(data)
    return 0


def cmd_info(args):
    sf = open_save(args)
    print("kind:", sf.kind, "| key slot:", sf.key_index)
    if sf.kind == "game":
        print("controllers: %d" % len(sf.controllers()))
        for short in sf.controllers():
            full = sf._full_of[short]
            v = sf.doc["Values"][full]
            keys = sorted(v.keys()) if isinstance(v, dict) else [type(v).__name__]
            print("  %-28s %s" % (short.split(".")[-1], keys))
        print("top: NeedToLoad=%s HasSaveData=%s Revision=%s"
              % (sf.doc.get("NeedToLoad"), sf.doc.get("HasSaveData"), sf.doc.get("Revision")))
    else:
        keys = sorted(sf.doc.keys()) if isinstance(sf.doc, dict) else []
        print("fields: %s" % keys)
    return 0


def cmd_get(args):
    sf = open_save(args)
    print(json.dumps(sf.get(args.controller, args.path), ensure_ascii=False))
    return 0


def cmd_set(args):
    sf = open_save(args)
    res = sf.set(args.controller, args.path, parse_value(args.value))
    print("set %s.%s = %s" % (args.controller, args.path, args.value))
    print("sync: %s" % res.detail)
    bak = sf.save(backup=not args.no_backup)
    print("saved%s" % (" (backup: %s)" % bak if bak else ""))
    cloud = steam_mod.cloud_status(sf.path)
    if cloud.get("uploaded") is False:
        print("WARNING: %s" % cloud["note"])
    return 0


def cmd_enc(args):
    text = open(args.json, encoding="utf-8").read()
    doc = json.loads(text)  # validate first
    from .model import compact
    from .crypto import encrypt_bytes
    blob = encrypt_bytes(compact(doc).encode("utf-8"))
    open(args.out, "w", encoding="utf-8").write(blob)
    print("wrote %s (%d chars)" % (args.out, len(blob)))
    return 0


def cmd_publish(args):
    from .publish import publish, TARGETS
    sf = open_save(args)
    only = args.only.split(",") if args.only else list(TARGETS)
    rep = publish(sf, targets=only, reg_base=args.reg_base)
    rc = 0
    for t in TARGETS:
        if t in rep:
            r = rep[t]
            print("%-8s %s %s%s" % (t, "OK " if r["ok"] else "FAIL",
                                    r["detail"],
                                    (" (backup: %s)" % r["backup"]) if r["backup"] else ""))
            if not r["ok"]:
                rc = 2
    if rep.get("cloud", {}).get("ok") is False:
        print("note: local targets are consistent; the game may still load a stale "
              "cloud copy until Steam syncs. Restart Steam if the edit seems ignored.")
    return rc


def cmd_backup(args):
    from .snap import take
    d = take(label=args.label or "")
    print("snapshot: %s" % d)
    return 0


def cmd_backups(args):
    from .snap import list_snaps
    snaps = list_snaps()
    if not snaps:
        print("no snapshots")
        return 1
    for name, m in snaps:
        print("%s  %s" % (name, m.get("label") or m.get("time", "")))
    return 0


def cmd_restore(args):
    from .snap import restore, list_snaps
    name = args.name
    if not os.path.isdir(name):
        for n, _ in list_snaps():
            if n == name or n.endswith(name):
                from .snap import snapshots_root
                name = os.path.join(snapshots_root(), n)
                break
    if not os.path.isdir(name):
        print("error: unknown snapshot %r (see `backups`)" % args.name)
        return 1
    rep = restore(name)
    rc = 0
    for t, kinds in rep.items():
        for k, r in kinds.items():
            print("%-8s %-4s %s %s" % (t, k, "OK " if r["ok"] else "FAIL", r["detail"]))
            if not r["ok"]:
                rc = 2
    return rc


def cmd_verify(args):
    if args.save:
        saves = [{"path": args.save}]
    else:
        saves = steam_mod.find_saves()
        if not saves:
            print("no saves found")
            return 1
    rc = 0
    for s in saves:
        try:
            sf = open_save(args, s["path"])
            rep = sf.verify()
            print("== %s (kind=%s)" % (s["path"], sf.kind))
            print("   base64/decrypt/json: OK | controllers: %d" % rep["controllers"])
            print("   synced: %d  diverged(stale cache): %d"
                  % (len(rep["synced"]), len(rep["diverged"])))
            for n in rep["notes"]:
                print("   note: %s" % n)
            if any("BUG" in n for n in rep["notes"]):
                rc = 2
        except CryptoError as e:
            print("== %s FAIL: %s" % (s["path"], e))
            rc = 1
    return rc


def build_parser():
    p = argparse.ArgumentParser(prog="ninah", description="No, I'm not a Human — save tool v%s" % __version__)
    p.add_argument("--keys", default=None, help="keys.json for key rotation")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("find", help="locate saves in all Steam libraries")

    d = sub.add_parser("dec", help="decrypt .sav to JSON")
    d.add_argument("save"); d.add_argument("-o", "--out", default=None)

    i = sub.add_parser("info", help="list controllers and fields")
    i.add_argument("save")

    g = sub.add_parser("get", help="print one value: get SAVE CONTROLLER PATH")
    g.add_argument("save"); g.add_argument("controller"); g.add_argument("path")

    s = sub.add_parser("set", help="edit one value: set SAVE CONTROLLER PATH VALUE")
    s.add_argument("save"); s.add_argument("controller"); s.add_argument("path"); s.add_argument("value")
    s.add_argument("--no-backup", action="store_true")

    e = sub.add_parser("enc", help="encrypt edited JSON back to .sav blob")
    e.add_argument("json"); e.add_argument("out")

    v = sub.add_parser("verify", help="three independent checks")
    v.add_argument("save", nargs="?")

    pb = sub.add_parser("publish", help="write save to file + registry + Steam Cloud")
    pb.add_argument("save")
    pb.add_argument("--only", default=None, help="subset: registry,file,cloud")
    pb.add_argument("--reg-base", default=None, help="registry base override (testing)")

    b = sub.add_parser("backup", help="snapshot file(s) + registry + cloud")
    b.add_argument("--label", default="")

    sub.add_parser("backups", help="list snapshots")

    r = sub.add_parser("restore", help="write a snapshot back to live stores")
    r.add_argument("name", help="snapshot dir or name")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return {"find": cmd_find, "dec": cmd_dec, "info": cmd_info,
                "get": cmd_get, "set": cmd_set, "enc": cmd_enc,
                "verify": cmd_verify, "publish": cmd_publish,
                "backup": cmd_backup, "backups": cmd_backups,
                "restore": cmd_restore}[args.cmd](args)
    except (CryptoError, KeyError, ValueError) as ex:
        print("error: %s" % ex)
        return 1


if __name__ == "__main__":
    sys.exit(main())
