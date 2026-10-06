"""Steam Cloud backend via the game's own steam_api64.dll (ctypes, flat API).

No Valve binaries are shipped: the DLL is loaded from the installed game
(NoImNotAHuman_Data/Plugins/x86_64/steam_api64.dll). Requires a running
Steam client + ownership of the game.
"""
import ctypes
import os
import tempfile

APP_ID = "3180070"
DLL_REL = os.path.join("NoImNotAHuman_Data", "Plugins", "x86_64", "steam_api64.dll")


class CloudError(OSError):
    pass


def find_api_dll(game_dirs=()):
    from . import steam as steam_mod
    cand = [os.path.join(d, DLL_REL) for d in game_dirs]
    base = steam_mod.steam_install_dir()
    if base:
        for lib in steam_mod.library_folders(base):
            cand.append(os.path.join(lib, "steamapps", "common",
                                     "No, I'm not a Human", DLL_REL))
    for p in cand:
        if os.path.isfile(p):
            return p
    raise CloudError("steam_api64.dll not found (is the game installed via Steam?)")


class Cloud:
    """Context-managed Flat-API client. Usage: with Cloud() as c: c.files() ..."""

    def __init__(self, dll_path=None, app_id=APP_ID):
        self.dll_path = dll_path or find_api_dll()
        self.app_id = str(app_id)
        self._api = None
        self._rs = None
        self._tmp = None
        self._old_cwd = None

    def open(self):
        self._tmp = tempfile.mkdtemp(prefix="ninah-steam-")
        with open(os.path.join(self._tmp, "steam_appid.txt"), "w") as f:
            f.write(self.app_id)
        self._old_cwd = os.getcwd()
        os.chdir(self._tmp)
        try:
            self._api = ctypes.CDLL(self.dll_path)
        except OSError as e:
            os.chdir(self._old_cwd)
            raise CloudError("cannot load %s: %s" % (self.dll_path, e))
        a = self._api
        a.SteamAPI_InitFlat.argtypes = [ctypes.c_char_p]
        a.SteamAPI_InitFlat.restype = ctypes.c_int
        err = ctypes.create_string_buffer(1024)
        if a.SteamAPI_InitFlat(err) != 0:
            msg = err.value.decode("utf-8", "replace")
            os.chdir(self._old_cwd)
            raise CloudError("SteamAPI init failed: %s" % msg)
        a.SteamAPI_SteamRemoteStorage_v016.restype = ctypes.c_void_p
        self._rs = a.SteamAPI_SteamRemoteStorage_v016()
        if not self._rs:
            self.close()
            raise CloudError("no RemoteStorage interface (Steam running? cloud blocked?)")
        a = self._api
        a.SteamAPI_ISteamRemoteStorage_GetFileCount.argtypes = [ctypes.c_void_p]
        a.SteamAPI_ISteamRemoteStorage_GetFileCount.restype = ctypes.c_int32
        a.SteamAPI_ISteamRemoteStorage_GetFileNameAndSize.argtypes = [
            ctypes.c_void_p, ctypes.c_int32, ctypes.POINTER(ctypes.c_int32)]
        a.SteamAPI_ISteamRemoteStorage_GetFileNameAndSize.restype = ctypes.c_char_p
        a.SteamAPI_ISteamRemoteStorage_FileRead.argtypes = [
            ctypes.c_void_p, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_int32]
        a.SteamAPI_ISteamRemoteStorage_FileRead.restype = ctypes.c_int32
        a.SteamAPI_ISteamRemoteStorage_FileWrite.argtypes = [
            ctypes.c_void_p, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_int32]
        a.SteamAPI_ISteamRemoteStorage_FileWrite.restype = ctypes.c_bool
        a.SteamAPI_ISteamRemoteStorage_FileDelete.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        a.SteamAPI_ISteamRemoteStorage_FileDelete.restype = ctypes.c_bool
        return self

    def close(self):
        if self._api is not None:
            try:
                self._api.SteamAPI_Shutdown()
            except OSError:
                pass
            self._api = None
            self._rs = None
        if self._old_cwd is not None:
            os.chdir(self._old_cwd)
            self._old_cwd = None

    def __enter__(self):
        return self.open()

    def __exit__(self, *a):
        self.close()

    def files(self):
        out = []
        n = self._api.SteamAPI_ISteamRemoteStorage_GetFileCount(self._rs)
        for i in range(n):
            sz = ctypes.c_int32(0)
            nm = self._api.SteamAPI_ISteamRemoteStorage_GetFileNameAndSize(
                self._rs, i, ctypes.byref(sz))
            out.append((nm.decode(), sz.value))
        return out

    def read(self, name):
        buf = ctypes.create_string_buffer(8 << 20)
        got = self._api.SteamAPI_ISteamRemoteStorage_FileRead(
            self._rs, name.encode(), buf, len(buf))
        if got < 0:
            raise CloudError("cloud read failed: %s" % name)
        return bytes(buf.raw[:got])

    def write(self, name, data):
        if isinstance(data, str):
            data = data.encode("ascii")
        ok = self._api.SteamAPI_ISteamRemoteStorage_FileWrite(
            self._rs, name.encode(), data, len(data))
        if not ok:
            raise CloudError("cloud write failed: %s" % name)
        return True

    def delete(self, name):
        ok = self._api.SteamAPI_ISteamRemoteStorage_FileDelete(self._rs, name.encode())
        if not ok:
            raise CloudError("cloud delete failed: %s" % name)
        return True
