"""Windows cleanup shim for gltest's temporary stdin message file.

gltest duplicates the file descriptor into stdin before unlinking the path.
Windows keeps that path locked until the direct_vm fixture restores stdin, so
cleanup is deferred until fixture teardown. Other platforms are untouched.
"""
import os
import pytest


_pending = []
_real_unlink = os.unlink


if os.name == "nt":
    def _deferred_unlink(path, *args, **kwargs):
        try:
            return _real_unlink(path, *args, **kwargs)
        except PermissionError:
            _pending.append((path, args, kwargs))
            return None

    os.unlink = _deferred_unlink


@pytest.fixture(autouse=True)
def _cleanup_gltest_stdin_files():
    yield
    for item in list(_pending):
        path, args, kwargs = item
        try:
            _real_unlink(path, *args, **kwargs)
            _pending.remove(item)
        except (FileNotFoundError, PermissionError):
            pass
