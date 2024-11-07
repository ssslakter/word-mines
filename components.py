from domain import *


def MineCard(mine: Mine, curr_user: User):
    kwargs = dict(hx_post="/trigger", hx_vals={"mine_id": mine.user.uid}, style='cursor: pointer;')
    triggered = "💥" if mine.triggered else ""
    return Div(H3(f"{mine.user.name}'s Mine"),
               Div(H3(mine.word), P(triggered, style='font-size: xxx-large;'),
                   cls='flex-hor', style='justify-content: space-between;')
               if sees_mine_cards(lobby.game, curr_user) else '',
               **kwargs if lobby.game.state == State.GUESSING and sees_mine_cards(lobby.game, curr_user) and curr_user in lobby.players else {}, cls='card flex-vert')


def Mines(game: Game, user: User):
    mines = game.mines
    return Div(*[MineCard(m, user) for m in mines.values()], id='mines', cls='mines-container')


def MineForm(game: Game, curr_user: User):
    if not sees_mine_form(game, curr_user) or any(map(lambda m: m.user == curr_user, game.mines.values())): return None
    return Div(
        Form(Group(Input(type="text", name="word"), Button("Send", type="submit")),
             hx_post="/mine", hx_target="#mine-form", hx_swap="outerHTML"),
        P("Write a 'word-mine'!"),
        id='mine-form', cls='flex-vert', style='margin-top: 25px;')


def MiningState(curr_user: User, round: Game):
    mine_form = MineForm(round, curr_user) if round.state == State.MINING else None
    mines = Mines(round, curr_user)
    return mines, mine_form


def TimerFT(time: int = 10, _: User = None):
    return Div(H3(f"Time left: {time}"), id='timer', style='padding: 10px;')


def GuessingState(curr_user: User, game: Game):
    gs, ex = UserCard(game.guesser, w_score=False), UserCard(game.explainer, w_score=False)
    word_block = Div(H2(f"Word: {game.word if game.state == State.ENDED or curr_user !=game.guesser else 'XXX'}", style='text-align: center;'))
    timer = TimerFT(game.timer.time)
    btns = Div(
        Button("Guessed correctly", hx_post="/guess", hx_vals={"guess": "true"}),
        Button("Guessed incorrectly", hx_post="/guess", hx_vals={"guess": "false"}),
        cls='row', style='justify-content: center; align-items: center; gap: 30px; margin-top: 20px'
    ) if game.state == State.GUESSING and curr_user == game.explainer else None
    players = Div(Div(H4('Explainer'), ex, cls='flex-vert'), timer, Div(H4("Guesser"), gs, cls='flex-vert'),
                  cls='row', style='justify-content: center; align-items: center;')
    block = Div(word_block, players)
    return Div(block, btns, id='guess')


def GameFT(curr_user: User):
    round = lobby.game
    btn_text = "Start Game" if not round.started else "Next Round"
    start = Button(btn_text, hx_post="/start",
                   hx_swap='none') if not round.started or round.state == State.ENDED else None
    if not round.started: return Div(start, id="game")
    game_state = H3(f"GAME STATE: {round.state}")
    mines = MiningState(curr_user, round)
    return Div(game_state, GuessingState(curr_user, round), start, mines, id="game", style='padding-top: 25px;', cls='container')


def UserCard(user: User, editable=False, w_score=True):
    name = Input(type="text", name="name", value=user.name, cls='text-like-input',
                 hx_post="/rename", hx_swap='none', hx_vals={'id': lobby.id}, style='margin: 5px 0;') if editable else user.name
    image = Div(Img(src=user.img) if user.img else H3(user.name[0] if user.name else 'n', style='margin: 0;'),
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
    main = Main(Users(curr_user), GameFT(curr_user), Div(), style='flex:1;', hx_ext='ws', ws_connect='/game')
    ftr = Footer(P('© 2024. Made by ssslakter & cortuzz'), style='align-self: center;')
    body = Body(hdr, main, ftr, style='display: flex; flex-direction: column; min-height: 100vh;')
    return Title(t), body
