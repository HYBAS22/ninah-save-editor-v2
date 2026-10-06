"""Local web GUI (stdlib only — no tkinter, no pip GUI deps).

Run:  python ninah_gui.py [save-path]
Opens http://127.0.0.1:PORT/ in your browser.
"""
import json
import os
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ninah import __version__
from ninah.crypto import DEFAULT_KEY, CryptoError
from ninah.model import SaveFile
from ninah import steam as steam_mod

ROOT = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    ROOT = sys._MEIPASS  # PyInstaller one-file bundle
WEB = os.path.join(ROOT, "web")
MIME = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8", ".ico": "image/x-icon"}

STATE = {"save": None, "path": None}


def send_json(h, obj, code=200):
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    h.send_response(code)
    h.send_header("Content-Type", "application/json; charset=utf-8")
    h.send_header("Content-Length", str(len(body)))
    h.end_headers()
    h.wfile.write(body)


def state_payload():
    sf = STATE["save"]
    if sf is None:
        return {"open": False, "files": steam_mod.find_saves(), "version": __version__}
    ctrls = []
    if sf.kind == "game":
        for short in sf.controllers():
            full = sf._full_of[short]
            v = sf.doc["Values"][full]
            fields = sorted(k for k in v.keys()) if isinstance(v, dict) else []
            ctrls.append({"short": short, "name": short.split(".")[-1],
                          "fields": fields, "dirty": short in sf.dirty})
    else:
        ctrls.append({"short": "_meta", "name": "MetaPrefsData",
                      "fields": sorted(sf.doc.keys()), "dirty": bool(sf.dirty)})
    return {"open": True, "path": STATE["path"], "kind": sf.kind,
            "controllers": ctrls, "verify": sf.verify(),
            "files": steam_mod.find_saves(), "version": __version__}


class Handler(BaseHTTPRequestHandler):
    server_version = "NINAHGui/%s" % __version__

    def log_message(self, *a):
        pass

    def _body(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        raw = self.rfile.read(n) if n else b""
        try:
            return json.loads(raw.decode("utf-8")) if raw else {}
        except Exception:
            return {}

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/api/state":
            return send_json(self, state_payload())
        if u.path == "/api/restores":
            from ninah.snap import list_snaps as _ls
            return send_json(self, {"snaps": [
                {"name": n, "label": m.get("label", "")} for n, m in _ls()]})
        if u.path == "/api/simple":
            sf = STATE["save"]
            if sf is None:
                return send_json(self, {"error": "no file open"}, 400)
            try:
                from ninah import simple as simple_mod
                from ninah.model import get_path, parse_path
                import copy as _copy
                secs = _copy.deepcopy(simple_mod.sections_for(sf.kind))
                for sec in secs:
                    for f in sec["fields"]:
                        ctl = f["ctl"]
                        base = sf.doc if ctl == "_meta" else sf.get(ctl, None)
                        v = get_path(base, parse_path(f["path"]))
                        if isinstance(v, dict):
                            v = {k: x for k, x in v.items() if k != "$type"}
                        f["value"] = v
                return send_json(self, {"sections": secs})
            except (KeyError, ValueError) as e:
                return send_json(self, {"error": str(e)}, 400)
        if u.path == "/api/node":
            q = parse_qs(u.query)
            sf = STATE["save"]
            if sf is None:
                return send_json(self, {"error": "no file open"}, 400)
            try:
                ctl, path = q.get("controller", [""])[0], q.get("path", [""])[0] or None
                node = sf.doc if (sf.kind == "meta" and ctl in ("_meta", "")) else sf.get(ctl, path)
                return send_json(self, {"value": node})
            except (KeyError, ValueError) as e:
                return send_json(self, {"error": str(e)}, 400)
        # static
        name = "index.html" if u.path in ("/", "/index.html") else u.path.lstrip("/").replace("\\", "/")
        if ".." in name or "/" in name:
            return send_json(self, {"error": "forbidden"}, 403)
        disk = os.path.join(WEB, name)
        if os.path.isfile(disk):
            ext = os.path.splitext(disk)[1]
            data = open(disk, "rb").read()
            self.send_response(200)
            self.send_header("Content-Type", MIME.get(ext, "application/octet-stream"))
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            send_json(self, {"error": "not found: %s" % name}, 404)

    def do_POST(self):
        u = urlparse(self.path)
        body = self._body()
        if u.path == "/api/open":
            try:
                STATE["save"] = SaveFile.load(body.get("path"), keys=[DEFAULT_KEY])
                STATE["path"] = body.get("path")
                return send_json(self, state_payload())
            except (CryptoError, OSError, ValueError) as e:
                return send_json(self, {"error": str(e)}, 400)
        if u.path == "/api/reload":
            try:
                STATE["save"] = SaveFile.load(STATE["path"], keys=[DEFAULT_KEY])
                return send_json(self, state_payload())
            except (CryptoError, OSError, ValueError) as e:
                return send_json(self, {"error": str(e)}, 400)
        if u.path == "/api/backup":
            from ninah.snap import take
            try:
                d = take(label=(body.get("label") or ""))
                return send_json(self, {"ok": True, "dir": d})
            except OSError as e:
                return send_json(self, {"error": str(e)}, 400)
        if u.path == "/api/restore":
            from ninah.snap import restore, list_snaps, snapshots_root
            import os as _os
            name = body.get("name") or ""
            if not _os.path.isdir(name):
                for n, _ in list_snaps():
                    if n == name or n.endswith(name):
                        name = _os.path.join(snapshots_root(), n)
                        break
            if not _os.path.isdir(name):
                return send_json(self, {"error": "unknown snapshot: %r" % body.get("name")}, 400)
            try:
                rep = restore(name)
                try:
                    STATE["save"] = SaveFile.load(STATE["path"], keys=[DEFAULT_KEY])
                    vv = STATE["save"].verify()
                except (CryptoError, OSError, ValueError):
                    vv = None
                return send_json(self, {"ok": True, "rep": rep, "verify": vv})
            except (OSError, ValueError, KeyError) as e:
                return send_json(self, {"error": str(e)}, 400)
        if u.path == "/api/set":
            sf = STATE["save"]
            if sf is None:
                return send_json(self, {"error": "no file open"}, 400)
            try:
                ctl = body.get("controller") or ""
                if sf.kind == "meta":
                    ctl = "_meta"
                res = sf.set(ctl if ctl != "_meta" else None, body.get("path") or None,
                             body.get("value"))
                # meta set with controller=None would fail; handle: meta uses doc directly
                return send_json(self, {"ok": True, "sync": res.detail,
                                         "verify": sf.verify()})
            except (KeyError, ValueError, TypeError) as e:
                return send_json(self, {"error": str(e)}, 400)
        if u.path == "/api/save":
            sf = STATE["save"]
            if sf is None:
                return send_json(self, {"error": "no file open"}, 400)
            try:
                from ninah.publish import publish
                rep = publish(sf)
                return send_json(self, {"ok": all(r["ok"] for r in rep.values()),
                                         "targets": rep, "verify": sf.verify(),
                                         "cloud": steam_mod.cloud_status(STATE["path"])})
            except (CryptoError, OSError) as e:
                return send_json(self, {"error": str(e)}, 400)
        return send_json(self, {"error": "unknown endpoint"}, 404)


def main():
    if "_cloud" in sys.argv:
        from ninah.cli import main as cli_main
        return cli_main()
    args = sys.argv[1:]
    port = 0
    no_browser = False
    save = None
    i = 0
    while i < len(args):
        if args[i] in ("-h", "--help"):
            print("usage: python ninah_gui.py [--port N] [--no-browser] [save-path]")
            return 0
        if args[i] == "--port":
            port = int(args[i + 1]); i += 2
        elif args[i] == "--no-browser":
            no_browser = True; i += 1
        else:
            save = args[i]; i += 1
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    port = srv.server_address[1]
    if save:
        try:
            STATE["save"] = SaveFile.load(save, keys=[DEFAULT_KEY])
            STATE["path"] = save
            print("opened:", save, flush=True)
        except (CryptoError, OSError, ValueError) as e:
            print("could not open %s: %s (pick a file in the UI)" % (save, e), flush=True)
    print("NINAH save editor v%s  ->  http://127.0.0.1:%d/" % (__version__, port), flush=True)
    print("Close this window to stop the editor.", flush=True)
    if not no_browser:
        threading.Timer(0.6, lambda: webbrowser.open("http://127.0.0.1:%d/" % port)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
