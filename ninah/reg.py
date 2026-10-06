"""Windows Registry backend: the game's live local store (Unity PlayerPrefs).

HKCU\\<REG_BASE>\\<value> as REG_BINARY: ASCII Base64 blob + trailing NUL.
Only game + meta values are managed; SettingsPrefsData is plain JSON and
is never touched.
"""
import os
import winreg

REG_BASE = os.environ.get("NINAH_REG_BASE", r"Software\Trioskaz\NoImNotAHuman")
VALUES = {
    "game": "GameSaveData_h303956378",
    "meta": "MetaPrefsData_h3531280890",
}

FILENAMES = {
    "game": "GameSaveData.sav",
    "meta": "MetaPrefsData.sav",
}


class RegistryError(OSError):
    pass


def value_name(kind):
    try:
        return VALUES[kind]
    except KeyError:
        raise RegistryError("no registry value for kind %r" % kind)


def read_blob(kind, base=None):
    """Returns (blob_text_without_nul, raw_bytes)."""
    base = base or REG_BASE
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, base) as k:
            raw, typ = winreg.QueryValueEx(k, value_name(kind))
    except OSError as e:
        raise RegistryError("cannot read %s: %s" % (value_name(kind), e))
    raw = bytes(raw)
    return raw.decode("ascii").rstrip("\x00"), raw


def write_blob(kind, blob_text, base=None):
    """Writes blob (+ trailing NUL) as REG_BINARY. Returns old raw bytes
    (None when the value did not exist yet)."""
    base = base or REG_BASE
    try:
        _, old_raw = read_blob(kind, base)
    except RegistryError:
        old_raw = None
    data = (blob_text + "\x00").encode("ascii")
    try:
        winreg.CreateKey(winreg.HKEY_CURRENT_USER, base)
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, base, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, value_name(kind), 0, winreg.REG_BINARY, data)
    except OSError as e:
        raise RegistryError("cannot write %s: %s" % (value_name(kind), e))
    return old_raw


def backup_path(kind, backup_dir):
    import datetime
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    return os.path.join(backup_dir, "%s.reg-%s.bin" % (FILENAMES[kind], stamp))
