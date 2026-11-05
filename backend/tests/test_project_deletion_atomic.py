from pathlib import Path
from contextlib import contextmanager
import pytest
from fastapi.testclient import TestClient
from backend import main,store,guest

@pytest.fixture
def project(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'DATA',tmp_path)
    with TestClient(main.app,raise_server_exceptions=False) as client:
        client.get('/api/session')
        pid='atomic-delete';folder=tmp_path/pid;folder.mkdir()
        (folder/'source').write_bytes(b'preserved source')
        (folder/'asset.png').write_bytes(b'preserved asset')
        store.save({'id':pid,'owner_id':guest.owner_for_token(client.cookies.get(guest.COOKIE)),'status':'uploaded','clips':[]})
        yield client,pid,folder


def test_locked_project_is_not_partially_deleted(project,monkeypatch):
    client,pid,folder=project;rename=Path.rename
    def locked(path,target):
        if path==folder:raise PermissionError('locked source')
        return rename(path,target)
    monkeypatch.setattr(Path,'rename',locked)
    r=client.delete('/api/projects/'+pid)
    assert r.status_code==409 and 'still available' in r.json()['detail']
    assert store.get(pid) and (folder/'source').read_bytes()==b'preserved source'
    assert (folder/'asset.png').exists()


def test_database_failure_restores_staged_source(project,monkeypatch):
    client,pid,folder=project;connect=store.connect
    class FailingDB:
        def __init__(self,db):self.db=db
        def execute(self,query,*args):
            if query.startswith('DELETE FROM projects'):raise OSError('test database failure')
            return self.db.execute(query,*args)
    @contextmanager
    def failing_connect():
        with connect() as db:yield FailingDB(db)
    monkeypatch.setattr(store,'connect',failing_connect)
    assert client.delete('/api/projects/'+pid).status_code==500
    assert store.get(pid) and (folder/'source').exists() and (folder/'asset.png').exists()
    assert not list(store.DATA.glob('.deleted-*'))


def test_locked_cleanup_is_private_and_retried_after_commit(project,monkeypatch):
    client,pid,folder=project;queued=[]
    class Queue:
        def submit(self,fn,path):queued.append((fn,path))
    monkeypatch.setattr(main,'cleanup_pool',Queue())
    def locked(path):raise PermissionError('open response handle')
    monkeypatch.setattr(main.shutil,'rmtree',locked)
    assert client.delete('/api/projects/'+pid).status_code==204
    assert store.get(pid) is None and not folder.exists()
    assert len(queued)==1 and queued[0][0]==main.cleanup_deleted
    assert (queued[0][1]/'source').exists()
    assert client.get('/api/projects/'+pid).status_code==404


def test_crash_before_commit_restores_owned_project(project,monkeypatch):
    client,pid,folder=project;staged=store.DATA/('.deleted-'+pid+'-'+'a'*32)
    folder.rename(staged)
    main.recover_deletions()
    assert folder.exists() and (folder/'source').exists() and not staged.exists()
    assert store.get(pid)
