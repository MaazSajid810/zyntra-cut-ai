import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DATA = Path(os.environ.get('CLIPFORGE_DATA', Path(__file__).resolve().parents[1] / 'data')).resolve()
DATA.mkdir(parents=True, exist_ok=True)

@contextmanager
def connect():
    db = sqlite3.connect(DATA / 'clipforge.db', timeout=30)
    try:
        db.execute('CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS imports (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS guest_sessions (token_hash TEXT PRIMARY KEY, owner_id TEXT NOT NULL, expires_at INTEGER NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        with db:
            yield db
    finally:
        db.close()

def all_projects():
    with connect() as db:
        return [json.loads(row[0]) for row in db.execute('SELECT payload FROM projects ORDER BY rowid DESC')]

def get(project_id):
    with connect() as db:
        row = db.execute('SELECT payload FROM projects WHERE id=?', (project_id,)).fetchone()
        return json.loads(row[0]) if row else None

def save(project):
    with connect() as db:
        db.execute('INSERT INTO projects VALUES (?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload', (project['id'], json.dumps(project)))

def mutate(project_id, fn):
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT payload FROM projects WHERE id=?', (project_id,)).fetchone()
        if not row:
            return
        project = json.loads(row[0])
        fn(project)
        db.execute('UPDATE projects SET payload=? WHERE id=?', (json.dumps(project), project_id))
        return project

def import_get(job_id):
    with connect() as db:
        row=db.execute('SELECT payload FROM imports WHERE id=?',(job_id,)).fetchone()
        return json.loads(row[0]) if row else None

def import_save(job):
    with connect() as db:
        db.execute('INSERT INTO imports VALUES (?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload',(job['id'],json.dumps(job)))

def import_update(job_id, **changes):
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT payload FROM imports WHERE id=?',(job_id,)).fetchone()
        if not row:
            return
        job=json.loads(row[0])
        job.update(changes)
        db.execute('UPDATE imports SET payload=? WHERE id=?',(json.dumps(job),job_id))
        return job

def all_imports():
    with connect() as db:
        return [json.loads(row[0]) for row in db.execute('SELECT payload FROM imports ORDER BY rowid DESC')]
