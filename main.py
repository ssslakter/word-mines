import uuid
from fasthtml.common import *
from domain import *

lobby = Lobby(1)
users: dict[str, User] = lobby.users
hdrs = [
    Link(rel="stylesheet", href="/static/style.css", type="text/css"),
]
app, rt = fast_app(exts='ws', hdrs=hdrs, bodykw={'hx-boost': 'true'})
app: FastHTML


async def guess_handler(ws, data: dict):
    guess = data['guess'] == 'true'
    lobby.end_round(guess)
    # time.sleep(10)
    # await start_handler(ws, data)  # Сделать отдельную кнопку


@rt('/')
def get(): return Redirect('/lobby')


def see_mines(round: Round, user: User):
    return not user is round.explainer and not user is round.guesser


# def LobbyState(lobby: Lobby, user: User):
#     round = lobby.round
#     is_started = H2("Game started!" if lobby.started else "Game not started", id='started')
#     round_status = H3(f"STATUS: {round.state if round else 'NULL'}", id='round_status')
#     guesser = P(f"Guesser: {round.guesser.name if round else 'No one'}", id='guesser')
#     explainer = P(f"Explainer: {round.explainer.name if round else 'No one'}", id='explainer')
#     game = Game(round, user, id='game') if round and user else Div(id='game')
#     # return is_started, guesser, explainer, usr_list, round_status, mines, game


def MineCard(mine: Mine, curr_user: User):
    btn = Button("EXplOdE", hx_put="/mine", hx_vals={"mine-id": mine.id})
    return Card(*(mine.word, btn) if lobby.round.state == State.ENDED or see_mines(lobby.round, curr_user) else '',
                header=f"{mine.user.name}'s Mine")


def Mines(round: Round, user: User):
    mines = round.mines
    return Div(*[MineCard(m, user) for m in mines.values()], id='mines')


def MineForm(round: Round, curr_user: User):
    if not see_mines(round, curr_user): return None
    return Div(
        Form(
            Input(type="text", name="word", style='flex: 4; '),
            Button("Send", type="submit", style='flex: 1;'),
            hx_post="/mine",
            style='display: flex; align-items: center;'
        ),
        P("Напишите 'слово-мину'!"),
        id='mine-form')


def MiningState(curr_user: User, round: Round):
    mine_form = MineForm(round, curr_user) if round.state == State.MINING else None
    mines = Mines(round, curr_user)
    return mine_form, mines


def GuessingBlock(curr_user: User, round: Round):
    gs, ex = UserCard(round.guesser), UserCard(round.explainer)
    word_block = H2(f"Word: {round.word if curr_user != gs else 'XXX'}", style='text-align: center;')
    btns = Div(
        Button("Guessed correctly", hx_post="/guess", hx_vals={"guess": "true"}),
        Button("Guessed incorrectly", hx_post="/guess", hx_vals={"guess": "false"}),
    ) if round.state == State.GUESSING and curr_user == round.explainer else None
    block = Div(Div('Explainer', ex), word_block, Div("Guesser", gs), style='display: flex; align-items: center;')
    return Div(block, btns, id='guess')


def Game(curr_user: User):
    round = lobby.round
    start = Button("Start Game", hx_post="/start") if not round or round.state == State.ENDED else None
    if not round: return Div(start, id="game")
    mines = MiningState(curr_user, round)
    return Div(GuessingBlock(curr_user, round), start, mines, id="game", style='padding-top: 25px;')


def UserCard(user: User, editable=False):
    name = Input(type="text", name="name", value=user.name, cls='text-like-input',
                 hx_post="/rename", hx_swap='none', hx_vals={'id': lobby.id}) if editable else user.name
    return Div(
        Div(Img(src=user.img), cls='circle'),
        Div(name, cls="user-name"),
        Div(user.points, cls="user-score"),
        cls='user-info'
    )


def Users(curr_user: User = None):
    print(users.keys(), curr_user.name)
    return Div(
        P("Users: "),
        Ul(*[Li(UserCard(u, u == curr_user)) for u in users.values() if u.ws_send],),
        style="display: flex; align-items: center; justify-content: center;", id='users'
    )


def Home(curr_user=None):
    t = 'Word Mines 💣'
    users_list = Users(curr_user)
    hdr = Header(H3(t))
    main = Container(users_list, Game(curr_user), style='flex:1;', hx_ext='ws', ws_connect='/game')
    ftr = Footer(P('© 2024. Made by ssslakter'), style='align-self: center;')
    body = Body(hdr, main, ftr, style='display: flex; flex-direction: column; min-height: 100vh;')
    return Title(t), body


def get_uid(sess=None, scope=None):
    sess: dict = scope.get('session', {}) if sess is None else sess
    return sess.setdefault('uid', str(uuid.uuid4()))


@rt('/lobby')
def get(sess):
    uid = get_uid(sess)
    u = users.setdefault(uid, User())
    return Home(u)


@rt('/rename')
async def post(sess, id: str, name: str = 'null'):
    uid = get_uid(sess)
    if u := users.get(uid): u.name = name
    else: return Redirect(f'/lobby')
    fn = lambda u: (Users(u), (GuessingBlock(u, lobby.round), Mines(lobby.round, u)) if lobby.round else None)
    await update_users(fn)


@rt('/start')
async def post():
    lobby.restart_game()
    await update_users(Game)


@rt('/mine')
async def post(sess, word: str):
    uid = get_uid(sess)
    if u := users.get(uid): lobby.round.add_mine(Mine(u, word))
    else: return Redirect(f'/lobby')
    fn = lambda u: (Mines(lobby.round, u))
    await update_users(fn)


@rt('/mine')
async def put(mine_id: str):
    mine = lobby.round.mines.get(mine_id)
    if mine: mine.click()
    fn = lambda u: (Mines(lobby.round, u))
    await update_users(fn)


@rt('/guess')
async def post(sess, guess: str):
    pass  # TODO


async def update_users(components_fn=None):
    for u in users.values():
        if u.ws_send: await u.ws_send(components_fn(u))


async def on_ws_change(scope, send, disconn=False):
    uid = get_uid(scope=scope)
    if u := users.get(uid): u.ws_send = None if disconn else send
    await update_users(Users)


@app.ws('/game', conn=on_ws_change, disconn=partial(on_ws_change, disconn=True))
async def ws(send): pass


serve(host="0.0.0.0")
