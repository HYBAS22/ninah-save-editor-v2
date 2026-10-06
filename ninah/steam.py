"""Locate game saves across all Steam libraries (registry + libraryfolders.vdf)."""
import os
import re
import winreg

APP_ID = "3180070"
FILE_NAMES = ("GameSaveData.sav", "MetaPrefsData.sav")


def steam_install_dir():
    for root, sub in ((winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam"),
                      (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam"),
                      (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Valve\Steam")):
        try:
            with winreg.OpenKey(root, sub) as k:
                v, _ = winreg.QueryValueEx(k, "InstallPath")
                if v and os.path.isdir(v):
                    return v
        except OSError:
            pass
    for cand in (r"C:\Program Files (x86)\Steam", r"C:\Program Files\Steam"):
        if os.path.isdir(cand):
            return cand
    return None


def library_folders(steam_dir):
    folders = [steam_dir]
    vdf = os.path.join(steam_dir, "steamapps", "libraryfolders.vdf")
    try:
        with open(vdf, encoding="utf-8", errors="replace") as f:
            for m in re.finditer(r'"path"\s*"([^"]+)"', f.read()):
                p = m.group(1).replace("\\\\", "\\")
                if os.path.isdir(p) and p not in folders:
                    folders.append(p)
    except OSError:
        pass
    return folders


def find_saves():
    """Returns list of dicts: {path, kind, size, mtime}. kind = game|meta."""
    steam = steam_install_dir()
    if not steam:
        return []
    out = []
    users = os.path.join(steam, "userdata")
    try:
        uids = [d for d in os.listdir(users) if os.path.isdir(os.path.join(users, d))]
    except OSError:
        uids = []
    for uid in uids:
        remote = os.path.join(users, uid, APP_ID, "remote")
        for fn in FILE_NAMES:
            p = os.path.join(remote, fn)
            if os.path.isfile(p):
                st = os.stat(p)
                out.append({"path": p,
                            "kind": "game" if fn.startswith("Game") else "meta",
                            "size": st.st_size, "mtime": st.st_mtime})
    return sorted(out, key=lambda d: d["mtime"], reverse=True)


def cloud_status(save_path):
    """Compare local file vs Steam's remotecache.vdf.

    The game loads from Steam Cloud, so a local edit is invisible until Steam
    uploads it (remotetime catches up). Returns dict with uploaded: bool.
    """
    remote = os.path.dirname(save_path)
    cache = os.path.join(os.path.dirname(remote), "remotecache.vdf")
    fn = os.path.basename(save_path)
    res = {"cache": os.path.isfile(cache), "uploaded": None, "note": ""}
    if not res["cache"]:
        res["note"] = "no remotecache.vdf (Steam Cloud unused?)"
        return res
    try:
        text = open(cache, encoding="utf-8", errors="replace").read()
    except OSError as e:
        res["note"] = "cannot read remotecache.vdf: %s" % e
        return res
    m = re.search(r'"%s"\s*\{(.*?)\n\t\}' % re.escape(fn), text, re.S)
    if not m:
        res["note"] = "file not tracked in remotecache.vdf"
        return res
    block = m.group(1)
    vals = dict(re.findall(r'"(\w+)"\s*"([^"]*)"', block))
    try:
        res["remotetime"] = int(vals.get("remotetime", 0))
    except ValueError:
        pass
    local_mtime = None
    try:
        local_mtime = int(os.stat(save_path).st_mtime)
    except OSError:
        pass
    res["localtime"] = local_mtime
    if "remotetime" in res and local_mtime is not None:
        res["uploaded"] = res["remotetime"] >= local_mtime - 60
        if res["uploaded"]:
            res["note"] = "Steam Cloud has this version"
        else:
            res["note"] = ("Steam Cloud is STALE (cloud %d < local %d): the game "
                           "will load the old copy. Restart Steam to force an "
                           "upload, then re-launch the game."
                           % (res["remotetime"], local_mtime))
    return res
