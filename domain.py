from enum import auto
import logging as l
import asyncio
import hashlib
import uuid
from itertools import permutations
from fasthtml.common import *
from dataclasses import dataclass
from wordpack import WordPack

log = l.getLogger(__name__)


class State(Enum):
    ENDED = auto()
    MINING = auto()
    GUESSING = auto()

    @classmethod
    def configure(cls, mining_time=35, guessing_time=60, ended_time=40):
        cls.times = {str(cls.MINING): mining_time, str(cls.GUESSING): guessing_time, str(cls.ENDED): ended_time}

    def __str__(self): return self.name
    def time(self): return self.times[self.name]


State.configure()


class Timer:
    coro = None

    def __init__(self, show_coro=None):
        self.coro, self.task = self.coro or show_coro, None
        self.pause_, self.stop_ = asyncio.Event(), asyncio.Event()
        self.pause_.set()

    def reset(self):
        self.unpause()
        self.stop_.clear()
    
    def sleep(self, time: int = 10):
        self.reset()
        self.time = time

        async def _sleep():
            for t in range(time, 0, -1):
                print(f'test {t}')
                self.time = t
                await self.pause_.wait()
                if self.stopped: return False
                await asyncio.sleep(1)
                if self.coro: await self.coro(self.time)
            return True
        self.task = asyncio.create_task(_sleep())
        return self.task

    async def stop(self):
        self.stop_.set()
        if self.task and not self.task.done(): await self.task
    def pause(self): self.pause_.clear()
    def unpause(self): self.pause_.set()
    @property
    def stopped(self): return self.stop_.is_set()

    @classmethod
    def add_coro(cls):
        def f(coro):
            cls.coro = staticmethod(coro)
        return f


@dataclass
class User:
    name: str = None
    points: int = 0
    ws_send: Optional[FunctionType] = None
    img = None
    uid: str = str(uuid.uuid4())

    def __post_init__(self):
        if not self.name: self.name = 'null'

    def add_points(self, value): self.points += value
    def clear_points(self): self.points = 0


@dataclass
class Mine:
    user: User
    word: str = ''
    triggered: bool = False

    def click(self): self.triggered = not self.triggered


class Game:
    def __init__(self, wordpack: WordPack, timer: Timer):
        self.wordpack, self.players, self.timer, self.mines, self.started = wordpack, [], timer, {}, False
        self.states = cycle(State)

    def start(self):
        self.started = True
        self.state = next(self.states)
        self.player_cycle = cycle(permutations(self.players, 2))
        self.reset_points()
        # self.new_round()

    def reset_points(self):
        for p in self.players: p.clear_points()

    async def add_mine(self, mine: Mine, render_coro=None):
        if self.state != State.MINING: return
        self.mines[mine.user.uid] = mine
        if len(self.mines) >= len(self.players) - 2:
            log.info(f'Total mines: {len(self.mines)}, changing state to {self.state}')
            await self.next_state()

    async def guess(self, correct: bool = False, render_coro=None):
        if self.state != State.GUESSING: return
        await self.timer.stop()
        l.info(f'guess value: {correct}')
        if correct:
            trig = bool([mine.user.add_points(3) for mine in self.mines.values() if mine.triggered])
            fine = 7 if trig else 0
            self.guesser.add_points(5 - fine)
            self.explainer.add_points(5 - fine)
        await self.next_state(render_coro)
        l.info(f'guess timer done')

    async def new_round(self, render_coro=None):
        if self.state != State.ENDED: return
        await self.timer.stop()
        l.info(f'new round: {self.state}')
        self.mines = {}
        self.guesser, self.explainer = next(self.player_cycle)
        self.word = next(self.wordpack)
        await self.next_state(render_coro)
        l.info(f'new round timer done')

    async def next_state(self, render_coro=None):
        self.state = next(self.states)
        task = self.timer.sleep(self.state.time())
        if render_coro: await render_coro()
        await task
        fn_auto = {State.ENDED:self.new_round,
                    State.GUESSING:self.guess,
                    State.MINING:self.next_state}
        asyncio.create_task(fn_auto[self.state](render_coro))


def sees_mine_cards(game: Game, user: User):
    '''returns true if user can see the mine cards in the game'''
    return game.state == State.ENDED or user != game.explainer and user != game.guesser


def sees_mine_form(game: Game, user: User):
    '''returns true if user can see the mine form in the game'''
    return game.state == State.MINING and user in game.players and user != game.explainer and user != game.guesser


class Lobby:
    def __init__(self, id: int, wp_name: str = 'default', timer: Timer = None):
        self.id, self.game, self.users = id, None, {}
        self.timer = timer or Timer()
        self.select_wordpack(wp_name)
        self.game = Game(self.wordpack, self.timer)
        # self.start_game()

    def __getattr__(self, name): return getattr(self.game, name)

    def select_wordpack(self, name: str):
        self.wordpack = WordPack.get_from_dict(name)
        return self.wordpack

    def join(self, user: User):
        if user in self.players or self.started: return
        self.game.players.append(user)

    def start_game(self) -> Game:
        """Start a new game and return the game object"""
        if self.started: raise HTTPException(400, "Game already started")
        return self.game.start()


@dataclass
class LobbyConfig:
    state_times: dict[State, int]


def str2soft_hex(s: str, factor: float = 0.5) -> str:
    hex_color = hashlib.sha256(s.encode()).hexdigest()[:6]
    rgb = [int(hex_color[i:i + 2], 16) for i in (0, 2, 4)]
    soft_rgb = [int(c + (255 - c) * factor) for c in rgb]
    return '#' + ''.join(f'{c:02x}' for c in soft_rgb)
