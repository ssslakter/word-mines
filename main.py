import random
from fasthtml.common import *

from domain import *

lobby = Lobby(
    1,
    False,
    {},
    None,
    WordPack(
        name="default",
        words=["кринж","кринге","кукож","крипота","флекс","тян","кун","куколд","рейв","ивент","айкос","ашка","подик","снюс","вкид","стафф","Garage","ESSA","сидр","энергос","биполярочка","пограничка","СДВГ","аутизм","РПП","трэш","хайп","хейт","всратый","агриться","буллить","триггерить","сталкерить","гамать","ультануть","форсить","шеймить","байтить","хейтить","чекать","юзать","флеймить","свайпить","няшиться","заскамить","сабить","ливнуть","оффнуть","мурчать","чилить","фолловить","шипперить","стэнить","абьюз","буллинг","газлайтинг","бодишейминг","слатшейминг","виктимблейминг","гостинг","харассмент","селфхарм","зашквар","рили","изи","скам","нюдсы","тикток","фаст","краш","симп","нормис","токсик","днокл","шмот","Thrasher","свитшот","чокер","паль","мерч","дрейнер","«Рёдан»","zxc","рофл","лмао","мем","постирония","челлендж","анбоксинг","ауф","сабж","POV","суетолог","думер","скуф","инцел","хейтер","хикка","хоумстакер","альтушка","дединсайд","анимешник","аутист","соулмейт","хоуми","абьюзер","реселлер","типикал","литералли","хорни","эщкере","сасный","ламповый","чайлдфри","позер","офник","душнила","фембой","личинус","каре","парные аватарки","ЛП","ЧСВ","катка","Fortnite","Roblox","VALORANT","CS:GO","PUBG Mobile","Phasmophobia","Brawl Stars","Genshin Impact","Among Us","Куплинов","Booster","Курсед","Братишкин","Даня Милохин","Дора","дорама","MORGENSTERN","FACE","PHARAOH","«Три дня дождя»","Scally Milano","uglystephan","Пошлая Молли","кис-кис","Дайте Танк (!)","Порнофильмы","Инстасамка","OG Buda","xxxtentacion","BTS","Билли Айлиш","The Weeknd","$uicideBoy$","Måneskin","k-pop","грайм","синтипоп","фонк","slowed + reverb","вайб","свэг","панч","попит","симпл-димпл","френдзона","актуалочка","инфа-сотка","база","мув","муд","тейк","фидбэк","гоу","мьют","инвайт","трабл","факап","фанфик","скилл","пруф","слив","тгк","ку","кек","gg","абобус","сойджек","гигачад","орево","жиза","рил","поч","жёсткий пон","пж","сорян","топ","прив","личка","шкила","семпай","гендер","дрейн","стрейт","альт","reels","Хилми","Юля Финесс","Валя Карнавал","Егор Шип","Аня Покров","Артур Бабич","Юля Гаврилина","Влад А4","MrBeast"]
    ))
users = lobby.users

scr = Script(src="https://unpkg.com/hyperscript.org@0.9.13")
app, rt = fast_app(exts='ws', hdrs=[scr])
app: FastHTML


def UsersList(users):
    if not users: return Div("Empty lobby")
    return Div(
        P("Users: "),
        Ul(*[Li(f"User {u.name} - {u.points}") for u in users.values()]),
        id='usr-list')


def on_conn(ws, scope, send):
    uname = ws.cookies.get('name', None)
    uname =  base64.b64decode(uname[2:-1]).decode('utf-8') if uname else 'NONE'
    users[str(id(ws))] = User(name=uname, points=0, send=send)


async def on_disconn(ws):
    del users[str(id(ws))]
    # for u in users.values(): await u.send(UsersList(users))

async def start_handler(ws, data):
    round = lobby.start_game()
    guesser = round.guesser
    explainer = round.explainer
    for u in users.values():
        await u.send(LobbyState(lobby, u))


async def join_handler(ws, data: dict):
    name: str = data['name']
    users[str(id(ws))].name = name
    for u in users.values(): await u.send(UsersList(users))
    u = users[str(id(ws))]
    await u.send(Script(f'document.cookie = "name={base64.b64encode(name.encode('utf-8'))}; path=/;";', id="name_script"))


async def guess_handler(ws, data: dict):
    guess = data['guess'] == 'true'
    lobby.end_round(guess)
    # time.sleep(10)
    await start_handler(ws, data) # Сделать отдельную кнопку

async def submit_mine_handler(ws, data: dict):
    word = data['name']
    round = lobby.round
    round.add_mine(Mine(word, False, users[str(id(ws))]))
    for u in users.values():
        await u.send(LobbyState(lobby, u)) # потом)

handlers = {
    'start': start_handler,
    'join': join_handler,
    'guess': guess_handler,
    'submit mine': submit_mine_handler
}


@app.ws("/ws", conn=on_conn, disconn=on_disconn)
async def ws(ws, data, send):
    await handlers[data['action']](ws, data)


@rt('/')
def get():
    return Redirect('/lobby')


def WsButton(key, value, *args, name='', **kwargs):
    return Form(
        *args,
        Input(type="hidden", value=value, name=key),
        Input(type="submit", value=name),
        ws_send=True, **kwargs)

def can_see_mines(round: Round, user: User):
    return not user is round.explainer and not user is round.guesser

def Mines(round: Round, user: User):
    mines = round.mines
    return Div(
        *[Card(
            Div(
                mine.word,
                P("💥" if mine.triggered else "✅"),
                
                ) if round.state == "ENDED" or can_see_mines(round, user) else 'XXX',
            header=f"{mine.user.name}'s Mine", id=f"mine-{i}") 
          for i, mine in enumerate(mines)], 
        id='mines')

def CreateMineForm(round: Round, user: User):
    if not can_see_mines(round, user): return Container(id='mine-form')

    for mine in round.mines:
        if mine.user == user: return Container(id='mine-form')
    
    return Container(
        P("Enter wordmine:"),
            WsButton("action", "submit mine", 
                     Input(type="text", name="name"),
                     name="Submit mine"), 
            id='mine-form'
    )
    

def Game(round, user: User = False, id="game"):
    is_explainer = round.explainer == user
    is_guesser = round.guesser == user
    word = round.word if not is_guesser else 'XXX'

    if round.state == "GUESSING":
        controls = Div(
            WsButton("action", "guess",
                Input(type="hidden", value='true', name='guess'),
                name="Word is correct"),
            WsButton(
                "action", "guess", 
                Input(type="hidden", value='false', name='guess'),
                name="Word is incorrect"),
        ) if is_explainer else None
    elif round.state == "MINING":
        controls = CreateMineForm(round, user)
    return Container(H2(f"Word: {word}"), controls, id=id)

def LobbyState(lobby: Lobby, user: User):
    round = lobby.round
    is_started = H2("Game started!" if lobby.started else "Game not started", id='started')
    round_status = H3(f"STATUS: {round.state  if round else 'NULL'}", id='round_status')
    guesser = P(f"Guesser: {round.guesser.name if round else 'No one'}", id='guesser')
    explainer = P(f"Explainer: {round.explainer.name  if round else 'No one'}", id='explainer')
    game = Game(round, user, id='game') if round and user else Div(id='game')
    usr_list = UsersList(lobby.users)
    mines = Mines(round, user) if round and user else Div(id='mines')
    return is_started, guesser, explainer, usr_list, round_status, mines, game


@rt('/lobby')
def get(sess, id: int = None):
    if not id:
        # lobby = Lobby(id, list())
        return Redirect(f'/lobby?id={1}')
    # Get all users in the lobby
    *before, after = LobbyState(lobby, None)
    return Container(
        Script(id="name_script"),
        H1(f"Lobby {id}"),
        *before,
        P("Enter your name:"),
        Form(
            Input(type="text", name="name"),
            WsButton("action", "join", name="Join"), ws_send=True
        ),
        WsButton("action", "start", name="Start game"),
        after,
        hx_ext='ws', ws_connect="/ws"
    )


serve(host="0.0.0.0")
