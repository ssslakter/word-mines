import uuid, logging as l
from datetime import date
from fasthtml.common import *
from domain import lobby, users


def get_uid(sess=None, scope=None):
    sess: dict = scope.get('session', {}) if sess is None else sess
    return sess.setdefault('uid', str(uuid.uuid4()))


def get_user(sess=None, scope=None):
    uid = get_uid(sess, scope)
    return users.get(uid)


async def update_users(components_fn=None):
    for u in users.values():
        if u.ws_send:
            try: await u.ws_send(components_fn(u))
            except WebSocketDisconnect: u.ws_send = None



DEF_FMT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

def init_logger(name: str = None, level=l.INFO, format: str = None, handlers: list = None, logs_dir='./logs'):
    '''Initializes a logger, adds handlers and sets the format. If logs_dir is provided, a file handler is added to the logger.'''
    if handlers is None: handlers = []
    handlers.append(l.StreamHandler())
    if logs_dir:
        p = Path(logs_dir) / f'{date.today()}.log'
        p.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(l.FileHandler(p))
    if format is None: format = DEF_FMT
    log_fmt = l.Formatter(format, datefmt='%Y-%m-%d %H:%M:%S')
    log = l.getLogger(name)
    log.setLevel(level)
    log.handlers.clear()
    for h in handlers: h.setFormatter(log_fmt); log.addHandler(h)