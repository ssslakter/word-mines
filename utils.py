import uuid
from fasthtml.common import *
from domain import lobby, users


def get_uid(sess=None, scope=None):
    sess: dict = scope.get('session', {}) if sess is None else sess
    return sess.setdefault('uid', str(uuid.uuid4()))


def get_user(sess):
    uid = get_uid(sess)
    return users.get(uid)


async def update_users(components_fn=None):
    for u in users.values():
        if u.ws_send:
            try: await u.ws_send(components_fn(u))
            except WebSocketDisconnect: u.ws_send = None

