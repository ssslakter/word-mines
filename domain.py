from datetime import timedelta
from enum import auto
import logging as l
import asyncio
import time as t
import hashlib
import uuid
from itertools import permutations
from fasthtml.common import *
from dataclasses import dataclass
from wordpack import WordPack

l.getLogger().setLevel(l.INFO)


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

    def __init__(self):
        self.pause_, self.stop_ = asyncio.Event(), asyncio.Event()
        
    def set(self, time: int = 10): self.rem_t = self.total = time

    def reset(self):
        self.unpause()
        self.stop_.clear()

    async def sleep(self, time: int = None):
        self.rem_t = self.total or time
        self.reset()
        finish_t = t.monotonic() + self.total
        while self.rem_t > 0:
            timer = asyncio.create_task(asyncio.sleep(0.5))  # interval check on pause and stop
            await asyncio.wait([timer, asyncio.create_task(self.stop_.wait())], return_when=asyncio.FIRST_COMPLETED)
            if self.stop_.is_set(): return
            elif self.pause_.is_set():
                paused_t = t.monotonic()
                await self.pause_.wait()
                unpause_t = t.monotonic()
                finish_t += paused_t - unpause_t
            else: self.rem_t = finish_t - t.monotonic()

    @property
    def time(self): 
        return timedelta(seconds=max(0, self.rem_t))
    def unpause(self): self.pause_.clear()
    def pause(self): self.pause_.set()
    def stop(self): 
        l.info("Timer stopped")
        self.stop_.set()


@dataclass
class User:
    is_host: bool = False
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
        self.state = None

    def start(self, render_coro=None):
        self.started = True
        self.player_cycle = cycle(permutations(self.players, 2))
        self.state = next(self.states)
        self.reset_points()
        l.info("Game started")
        asyncio.create_task(self.end_round_ended(render_coro))

    def reset_points(self):
        for p in self.players: p.clear_points()

    def add_mine(self, mine: Mine):
        if self.state != State.MINING: return
        self.mines[mine.user.uid] = mine
        if len(self.mines) >= len(self.players) - 2:
            l.info(f'Total mines: {len(self.mines)}, changing state to {self.state}')
            self.timer.stop()

    async def end_guessing(self, render_coro=None):
        if self.state != State.GUESSING: return
        l.info(f'guess value: {self.guessed}')
        if self.guessed:
            trig = bool([mine.user.add_points(3) for mine in self.mines.values() if mine.triggered])
            fine = 7 if trig else 0
            self.guesser.add_points(5 - fine)
            self.explainer.add_points(5 - fine)
        await self.next_state(render_coro)

    async def end_round_ended(self, render_coro=None):
        if self.state != State.ENDED and self.state: return
        l.info(f'new round, state: {self.state}')
        self.mines = {}
        self.guesser, self.explainer = next(self.player_cycle)
        self.guessed = False
        self.word = next(self.wordpack)
        await self.next_state(render_coro)
        l.info(f'new round timer done')

    async def next_state(self, render_coro=None):
        self.state = next(self.states)
        self.timer.set(self.state.time())
        l.info(f'rendering state: {self.state}')
        if render_coro: await render_coro()
        l.info(f'state {self.state} timer started on {self.state.time()}s')
        await self.timer.sleep()
        l.info(f'state {self.state} timer done')
        fn_auto = {State.ENDED: self.end_round_ended,
                   State.GUESSING: self.end_guessing,
                   State.MINING: self.next_state}
        asyncio.create_task(fn_auto[self.state](render_coro))
        
    def guess(self, correct: bool = False):
        if self.state != State.GUESSING: return
        self.guessed = correct
        self.timer.stop()
    
    def next_round(self):
        if self.state != State.ENDED: return
        self.timer.stop()

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

    def start_game(self, render_coro=None) -> Game:
        """Start a new game and return the game object"""
        if self.started: raise HTTPException(400, "Game already started")
        return self.game.start(render_coro)


def str2soft_hex(s: str, factor: float = 0.5) -> str:
    hex_color = hashlib.sha256(s.encode()).hexdigest()[:6]
    rgb = [int(hex_color[i:i + 2], 16) for i in (0, 2, 4)]
    soft_rgb = [int(c + (255 - c) * factor) for c in rgb]
    return '#' + ''.join(f'{c:02x}' for c in soft_rgb)


lobby = Lobby(1)
users: dict[str, User] = lobby.users
