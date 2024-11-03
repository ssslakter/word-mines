import asyncio
import time
import uuid
from fasthtml.common import *
from domain import *

lobby = Lobby(1)
users: dict[str, User] = lobby.users


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


def MineCard(mine: Mine, curr_user: User):
    btn = Button("Change", hx_post="/trigger",
                 hx_vals={"mine_id": mine.user.uid}) if lobby.round.state == State.GUESSING else None
    triggered = "💥" if mine.triggered else ""
    return Div(H3(f"{mine.user.name}'s Mine"),
               Div(H3(mine.word), P(triggered, style='font-size: xxx-large;'),
                   cls='flex-hor', style='justify-content: space-between;')
               if lobby.round.state == State.ENDED or sees_mines(lobby.round, curr_user) else '',
               btn if sees_mines(lobby.round, curr_user) else None, cls='card flex-vert')


def Mines(round: Round, user: User):
    mines = round.mines
    return Div(*[MineCard(m, user) for m in mines.values()], id='mines', cls='mines-container')


def MineForm(round: Round, curr_user: User):
    if not sees_mines(round, curr_user): return None
    if any(map(lambda m: m.user == curr_user, round.mines.values())): return None
    return Div(
        Form(Group(Input(type="text", name="word"), Button("Send", type="submit")),
             hx_post="/mine", hx_target="#mine-form", hx_swap="outerHTML"),
        P("Напишите 'слово-мину'!"),
        id='mine-form', cls='flex-vert', style='margin-top: 25px;')


def MiningState(curr_user: User, round: Round):
    mine_form = MineForm(round, curr_user) if round.state == State.MINING else None
    mines = Mines(round, curr_user)
    return mines, mine_form


def TimerFT(time: int = 10, _: User=None):
    return Div(H3(f"Time left: {time}"), id='timer', style='padding: 10px;')

def GuessingState(curr_user: User, round: Round):
    gs, ex = UserCard(round.guesser, w_score=False), UserCard(round.explainer, w_score=False)
    word_block = Div(H2(f"Word: {round.word if curr_user != gs else 'XXX'}", style='text-align: center;'))
    timer = TimerFT(round.timer.time)
    btns = Div(
        Button("Guessed correctly", hx_post="/guess", hx_vals={"guess": "true"}),
        Button("Guessed incorrectly", hx_post="/guess", hx_vals={"guess": "false"}),
        cls='row', style='justify-content: center; align-items: center; gap: 30px; margin-top: 20px'
    ) if round.state == State.GUESSING and curr_user == round.explainer else None
    players = Div(Div(H4('Explainer'), ex, cls='flex-vert'), timer, Div(H4("Guesser"), gs, cls='flex-vert'),
                  cls='row', style='justify-content: center; align-items: center;')
    block = Div(word_block, players)
    return Div(block, btns, id='guess')


def Game(curr_user: User):
    round = lobby.round
    btn_text = "Start Game" if not round else "Next Round"
    start = Button(btn_text, hx_post="/start", hx_swap='none') if not round or round.state == State.ENDED else None
    if not round: return Div(start, id="game")
    game_state = H3(f"GAME STATE: {round.state}")
    mines = MiningState(curr_user, round)
    return Div(game_state, GuessingState(curr_user, round), start, mines, id="game", style='padding-top: 25px;', cls='container')


def UserCard(user: User, editable=False, w_score=True):
    name = Input(type="text", name="name", value=user.name, cls='text-like-input',
                 hx_post="/rename", hx_swap='none', hx_vals={'id': lobby.id}, style='margin: 5px 0;') if editable else user.name
    image = Div(Img(src=user.img) if user.img else H3(user.name[0], style='margin: 0;'),
                cls='circle', style=f'background-color: {str2soft_hex(user.name)};')
    return Div(image,
               Div(name, cls="user-name"),
               Div(user.points, cls="user-score") if w_score else None,
               cls='user-info'
               )


def Users(curr_user: User = None):
    return Div(H3("Users: "),
               *(Div(UserCard(u, u == curr_user), cls='row') for u in users.values() if u.ws_send),
               style='gap: 1.5rem; display: flex; flex-direction: column;', id='users')


def Home(curr_user=None):
    t = 'Word Mines 💣'
    hdr = Header(H3(t), CheckboxX(label="Dark theme", role='switch',
                 onchange='changeTheme(event.target.checked)', id='theme'), cls='flex-hor')
    main = Main(Users(curr_user), Game(curr_user), Div(), style='flex:1;', hx_ext='ws', ws_connect='/game')
    ftr = Footer(P('© 2024. Made by ssslakter'), style='align-self: center;')
    body = Body(hdr, main, ftr, style='display: flex; flex-direction: column; min-height: 100vh;')
    return Title(t), body


def get_uid(sess=None, scope=None):
    sess: dict = scope.get('session', {}) if sess is None else sess
    return sess.setdefault('uid', str(uuid.uuid4()))


@rt('/')
def get(): return Redirect('/lobby')


@rt('/lobby')
def get(sess):
    uid = get_uid(sess)
    u = users.setdefault(uid, User(uid=uid))
    return Home(u)


@rt('/rename')
async def post(sess, id: str, name: str = 'null'):
    uid = get_uid(sess)
    if u := users.get(uid): u.name = name
    else: return Redirect(f'/lobby')
    fn = lambda u: (Users(u), (GuessingState(u, lobby.round), Mines(lobby.round, u)) if lobby.round else None)
    await update_users(fn)


@rt('/start')
async def post(sess):
    if len(users) < 3:
        add_toast(sess, "Not enough players", 'error')
        return Div()
    if not lobby.round: lobby.restart_game()
    elif lobby.round.state == State.ENDED: lobby.next_round()
    else: return
    lobby.round.set_timer(timer_coro, timer_cb)
    await update_users(Game)


@rt('/mine')
async def post(sess, word: str):
    uid = get_uid(sess)
    if (u := users.get(uid)) and uid not in lobby.round.mines: lobby.round.add_mine(Mine(u, word), timer_coro, timer_cb)
    else: return Redirect(f'/lobby')
    await update_users(Game)


@rt('/mine')
async def put(sess, mine_id: str, word: str):
    uid = get_uid(sess)
    u = users.get(uid)
    mine = lobby.round.mines.get(mine_id)
    if not (u and mine) or u != mine.user: return
    mine.word = word
    fn = lambda u: Mines(lobby.round, u)
    await update_users(fn)


@rt('/trigger')
async def post(mine_id: str):
    mine = lobby.round.mines.get(mine_id)
    if mine: mine.click()
    fn = lambda u: Mines(lobby.round, u)
    await update_users(fn)


@rt('/guess')
async def post(sess, guess: str):
    uid = get_uid(sess)
    u = users.get(uid)
    if not u or u != lobby.round.guesser: RedirectResponse(f'/lobby')
    lobby.round.end_round(guess == 'true', timer_coro, timer_cb)
    fn = lambda u: (Users(u), Game(u))
    await update_users(fn)


async def timer_coro(time: int):
    fn = lambda u: TimerFT(time)
    await update_users(fn)
    
async def timer_cb(finished: bool):
    if finished: lobby.round.next_state(timer_coro, timer_cb)
    await update_users(Game)


async def update_users(components_fn=None):
    for u in users.values():
        if u.ws_send:
            try: await u.ws_send(components_fn(u))
            except WebSocketDisconnect: u.ws_send = None


async def on_ws_change(scope, send, disconn=False):
    uid = get_uid(scope=scope)
    if u := users.get(uid): u.ws_send = None if disconn else send
    await update_users(Users)


async def on_disconn(scope, send): await on_ws_change(scope, send, disconn=True)


@app.ws('/game', conn=on_ws_change, disconn=on_disconn)
async def ws(send): pass


serve(host="0.0.0.0")
