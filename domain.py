import asyncio
import hashlib
import uuid
from fasthtml.common import *
from dataclasses import dataclass, field
from random import choice
from copy import copy
from wordpack import WordPack


class State(Enum):
    MINING = ("MINING", 65)
    GUESSING = ("GUESSING", 60)
    ENDED = ("ENDED", 65)

    def __str__(self): return self.value[0]
    def __int__(self): return self.value[1]

class Timer:
    def __init__(self, total_time: int = 10, state: State = State.MINING): 
        self.tot, self.time, self.state, self.task, self.finished = total_time, total_time, state, None, None

    def run(self, coro=None, cb=None):
        self.task = asyncio.create_task(self._run(coro, cb))
        return self

    async def _run(self, coro=None, cb=None):
        self.finished = False
        try:
            while self.time > 0:
                self.time -= 1
                await asyncio.sleep(1)
                if coro: await coro(self.time)
            self.finished = True
        except asyncio.CancelledError: self.reset()
        finally: 
            if cb: await cb(self.finished)

    def reset(self):
        if self.task: self.task.cancel()
        self.time = self.tot


@dataclass
class User:
    name: str = 'null'
    points: int = 0
    ws_send: Optional[FunctionType] = None
    img = None
    uid: str = str(uuid.uuid4())

    def add_points(self, value): self.points += value
    def clear_points(self): self.points = 0


@dataclass
class Mine:
    user: User
    word: str = ''
    triggered: bool = False

    def click(self): self.triggered = not self.triggered




@dataclass
class Round:
    word: str
    guesser: User
    explainer: User
    total_players: int
    states: Iterator = field(default_factory=lambda: cycle([State.MINING, State.GUESSING, State.ENDED]))
    state: State = None
    mines: dict[Mine] = field(default_factory=dict)
    timer: Timer = None

    def __post_init__(self):
        self.timer = Timer(10)
        self.state = next(self.states)

    def add_mine(self, mine: Mine, coro=None, cb=None):
        if self.state != State.MINING: return
        self.mines[mine.user.uid] = mine
        if len(self.mines) >= self.total_players:
            self.timer.reset()
            self.next_state(coro, cb)
            print(f'Total mines: {len(self.mines)}, changing state to {self.state}')

    def next_state(self, coro=None, cb=None): 
        self.state = next(self.states)
        self.set_timer(coro, cb)

    def set_timer(self, coro=None, cb=None):
        self.timer.reset()
        self.timer = Timer(int(self.state), self.state)
        self.timer.run(coro, cb)

    def end_round(self, guessed: bool, coro=None, cb=None):
        self.next_state(coro, cb)
        if not guessed: return
        trig = bool([mine.user.add_points(3) for mine in self.mines.values() if mine.triggered])
        fine = 7 if trig else 0
        self.guesser.add_points(5 - fine)
        self.explainer.add_points(5 - fine)


class Lobby:
    def __init__(self, id: int, wp_name: str = 'default'):
        self.id, self.started, self.round, self.users = id, False, None, {}
        self.select_wordpack(wp_name)
        self.update_users()

    def select_wordpack(self, name: str):
        self.wordpack = WordPack.get_from_dict(name)
        return self.wordpack

    def update_users(self):
        self.user_cycle = cycle(self.users.items())
        for user in self.users.values(): user.clear_points()

    def restart_game(self, coro=None, cb=None) -> Round:
        """Start a new game and return the first round"""
        self.started = True
        self.update_users()
        self.wordpack.reset()
        return self.next_round(coro, cb)

    def join(self, uid: str, user: User):
        if self.started: raise HTTPException(403, "Game already started")
        self.users[uid] = user

    def leave(self, uid: str):
        if self.started: raise HTTPException(401, "Game is started")
        del self.users[uid]

    def end_round(self, resolved: bool): self.round.end_round(resolved)

    def next_round(self, coro=None, cb=None) -> Round:
        curr_id, curr_explainer = next(self.user_cycle)
        guessers = copy(self.users)
        del guessers[curr_id]
        curr_guesser = guessers[choice(list(guessers.keys()))]
        if self.round: self.round.timer.reset() # TODO this is a hack
        self.round = Round(next(self.wordpack), curr_guesser, curr_explainer, len(guessers) - 1)
        self.round.set_timer(coro, cb)
        return self.round


def sees_mines(round: Round, user: User):
    return not user is round.explainer and not user is round.guesser


def str2soft_hex(s: str, factor: float = 0.5) -> str:
    hex_color = hashlib.sha256(s.encode()).hexdigest()[:6]
    rgb = [int(hex_color[i:i + 2], 16) for i in (0, 2, 4)]
    soft_rgb = [int(c + (255 - c) * factor) for c in rgb]
    return '#' + ''.join(f'{c:02x}' for c in soft_rgb)
