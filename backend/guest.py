"""Opaque, HttpOnly guest credentials; ownership is enforced on every API route."""
import hashlib
import json
import os
import re
import secrets
import time
import uuid

from fastapi import HTTPException, Request
from . import store

COOKIE = 'clipforge_guest'
TTL = 180 * 24 * 60 * 60


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def owner_for_token(token):
    if not token or not re.fullmatch(r'[A-Za-z0-9_-]{43}', token):
        return None
    with store.connect() as db:
        row = db.execute('SELECT owner_id FROM guest_sessions WHERE token_hash=? AND expires_at>?',
                         (digest(token), int(time.time()))).fetchone()
    return row[0] if row else None


def bootstrap(request, response):
    token = request.cookies.get(COOKIE)
    owner = owner_for_token(token)
    if not owner:
        token = secrets.token_urlsafe(32)
        owner = uuid.uuid4().hex
    with store.connect() as db:
        db.execute('DELETE FROM guest_sessions WHERE expires_at<=?', (int(time.time()),))
        db.execute('INSERT INTO guest_sessions VALUES (?,?,?) ON CONFLICT(token_hash) DO UPDATE SET expires_at=excluded.expires_at',
                   (digest(token), owner, int(time.time()) + TTL))
    secure = os.environ.get('CLIPFORGE_COOKIE_SECURE', '').lower() == 'true' or request.url.scheme == 'https'
    response.set_cookie(COOKIE, token, max_age=TTL, httponly=True, secure=secure, samesite='strict', path='/')
    return {'mode':'private_guest', 'expires_in_days':180}


def authorize(request: Request):
    if request.url.path in ('/api/session', '/api/health'):
        return
    owner = owner_for_token(request.cookies.get(COOKIE))
    if not owner:
        raise HTTPException(401, 'Your guest session is missing or expired. Refresh the page to start a new private workspace.')
    request.state.owner_id = owner
    project_id = request.path_params.get('project_id')
    if project_id:
        project = store.get(project_id)
        if not project or project.get('owner_id') != owner:
            raise HTTPException(404, 'Project not found')
    job_id = request.path_params.get('job_id')
    if job_id:
        job = store.import_get(job_id)
        if not job or job.get('owner_id') != owner:
            raise HTTPException(404, 'Link import not found')


def prepare_legacy():
    """Never assign old shared data to the first anonymous visitor."""
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        legacy = any(not json.loads(row[0]).get('owner_id')
                     for table in ('projects','imports') for row in db.execute(f'SELECT payload FROM {table}'))
        if not legacy or db.execute("SELECT 1 FROM settings WHERE key='legacy_claim_hash'").fetchone():
            return
        key = secrets.token_urlsafe(32)
        (store.DATA/'legacy-workspace-key.txt').write_text(key, encoding='utf-8')
        db.execute('INSERT INTO settings VALUES (?,?)', ('legacy_claim_hash', digest(key)))


def claim_legacy(key, owner):
    with store.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute("SELECT value FROM settings WHERE key='legacy_claim_hash'").fetchone()
        if not row or not secrets.compare_digest(row[0], digest(key)):
            raise HTTPException(400, 'Invalid or already-used local restore key.')
        counts = {}
        for table in ('projects','imports'):
            items = list(db.execute(f'SELECT id,payload FROM {table}'))
            counts[table] = 0
            for item_id, payload in items:
                item = json.loads(payload)
                if not item.get('owner_id'):
                    item['owner_id'] = owner
                    db.execute(f'UPDATE {table} SET payload=? WHERE id=?', (json.dumps(item), item_id))
                    counts[table] += 1
        db.execute("DELETE FROM settings WHERE key='legacy_claim_hash'")
    # Possession of this one-time file is required; it is never served by the API.
    (store.DATA/'legacy-workspace-key.txt').unlink(missing_ok=True)
    return counts
