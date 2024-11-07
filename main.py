import asyncio
import time
from fasthtml.common import *
from domain import *
from utils import *
from components import *


gridlink = Link(rel="stylesheet",
                href="https://cdnjs.cloudflare.com/ajax/libs/flexboxgrid/6.3.1/flexboxgrid.min.css", type="text/css")
hdrs = [
    gridlink,
    Link(rel="stylesheet", href="/static/style.css", type="text/css"),
    Script(src="static/scripts.js"),
]
app, rt = fast_app(exts='ws', hdrs=hdrs, bodykw={'hx-boost': 'true'})
app: FastHTML
setup_toasts(app)


@rt('/')
def get(): return Redirect('/lobby')


@rt('/lobby')
def get(sess):
    uid = get_uid(sess)
    u = users.setdefault(uid, User(len(users) == 0, name=sess.get('name'), uid=uid))
    if u not in lobby.players: lobby.join(u)
    return Home(u)


@rt('/rename')
async def post(sess, name: str = 'null'):
    name = name.strip()
    if len(name) > 100: return add_toast(sess, 'Name is too long', 'error')
    if len(name) < 1: return add_toast(sess, 'Name is too short', 'error')
    if u := get_user(sess):
        sess['name'] = name
        u.name = name
    else: return Redirect(f'/lobby')
    fn = lambda u: (Users(u), (GuessingState(u, lobby.game), Mines(lobby.game, u)) if lobby.game else None)
    await update_users(fn)


@rt('/start')
async def post(sess):
    if len(lobby.players) < 3:
        add_toast(sess, "Not enough players", 'error')
        return Div()
    if not lobby.started: lobby.start_game()
    asyncio.create_task(lobby.game.new_round(lambda: update_users(GameFT)))


@rt('/mine')
async def post(sess, word: str):
    uid = get_uid(sess)
    if (u := users.get(uid)) and uid not in lobby.game.mines and sees_mine_cards(lobby.game, u) and u in lobby.players:
        asyncio.create_task(lobby.game.add_mine(Mine(u, word), lambda: update_users(GameFT)))
    else: return Redirect(f'/lobby')


@rt('/mine')
async def put(sess, mine_id: str, word: str):
    u = get_user(sess)
    mine = lobby.game.mines.get(mine_id)
    if not (u and mine) or u != mine.user: return
    mine.word = word
    fn = lambda u: Mines(lobby.game, u)
    await update_users(fn)


@rt('/trigger')
async def post(sess, mine_id: str):
    mine = lobby.game.mines.get(mine_id)
    u = get_user(sess)
    if not mine or u in [lobby.guesser, lobby.explainer]: return
    mine.click()
    fn = lambda u: Mines(lobby.game, u)
    await update_users(fn)


@rt('/guess')
async def post(sess, guess: str):
    uid = get_uid(sess)
    u = users.get(uid)
    if not u or u != lobby.game.guesser: RedirectResponse(f'/lobby')
    fn = lambda u: (Users(u), GameFT(u))
    asyncio.create_task(lobby.game.guess(guess == 'true', lambda: update_users(fn)))


# TODO maybe bugs
@Timer.add_coro()
async def timer_coro(time: int):
    fn = lambda u: TimerFT(time)
    await update_users(fn)


async def on_ws_change(scope, send, disconn=False):
    if u := get_user(scope): u.ws_send = None if disconn else send
    await update_users(Users)


async def on_disconn(scope, send): await on_ws_change(scope, send, disconn=True)


@app.ws('/game', conn=on_ws_change, disconn=on_disconn)
async def ws(send): pass


serve(host="0.0.0.0")
