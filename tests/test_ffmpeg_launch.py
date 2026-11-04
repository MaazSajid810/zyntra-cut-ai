from types import SimpleNamespace
import pytest
from backend import media

def test_transient_windows_launch_is_retried_but_bounded(monkeypatch):
    calls=[]
    def launch(*args,**kwargs):
        calls.append(1)
        if len(calls)<3:
            exc=PermissionError('Locked executable');exc.winerror=5;raise exc
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(media.subprocess,'run',launch)
    monkeypatch.setattr(media.time,'sleep',lambda _:None)
    media.run([])
    assert len(calls)==3
    def always_locked(*args,**kwargs):
        calls.append(1);exc=PermissionError('Persistent denial');exc.winerror=5;raise exc
    calls.clear()
    monkeypatch.setattr(media.subprocess,'run',always_locked)
    with pytest.raises(PermissionError):media.run([])
    assert len(calls)==4
