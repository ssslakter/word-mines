from fasthtml.common import *
from dataclasses import dataclass
from itertools import cycle
from random import choice, shuffle
from copy import copy


@dataclass
class User:
    name: str
    points: int
    send: FunctionType

    def add_points(self, value):
        self.points += value

    def clear_points(self):
        self.points = 0

@dataclass
class Mine:
    word: str
    triggered: bool
    user: User

    def trigger(self):
        self.triggered = True

@dataclass
class WordPack:
    name: str
    words: list[str]

    def __post_init__(self):
        self.init()

    def init(self):
        shuffle(self.words)
        self.word_cycle = cycle(self.words)
        
    def __iter__(self): return self
    
    def __next__(self) -> str:
        return next(self.word_cycle)

@dataclass
class Round:
    state: str
    resolved: bool
    word: str
    mines: list[Mine]
    guesser: User
    explainer: User
    mines_count: int

    def add_mine(self, mine: Mine):
        self.mines.append(mine)

        if len(self.mines) >= self.mines_count:
            self.state = "GUESSING"

    def end_round(self, resolved: bool):
        if self.state == "MINING":
            raise Exception("Cannot end round while mining")

        mine_trig = False
        self.resolved = resolved
        ## TODO dont give points
        self.state = "ENDED"

        for mine in self.mines:
            if not mine.triggered:
                continue

            mine.user.add_points(3)
            mine_trig = True

        if mine_trig:
            self.guesser.add_points(-2)
            return
        
        self.guesser.add_points(5)
        self.explainer.add_points(5)
    

@dataclass
class Lobby:
    id: int
    started: bool
    users: dict[User]
    round: Round
    word_pack: WordPack

    def update_users(self):
        self.user_cycle = cycle(self.users.items())

        for user in self.users.values():
            user.clear_points()

    def start_game(self) -> Round:
        if self.started: return self.next_round()
        self.started = True
        self.update_users()
        self.word_pack.init()
        return self.next_round()

    def join(self, id: str, user: User):
        if self.started:
            raise Exception("Game is started")

        if user in self.users.values():
            raise Exception("User already exist")

        self.users[id] = user

    def leave(self, id: str):
        if self.started:
            raise Exception("Game is started")

        del self.users[id]

    def end_round(self, resolved: bool):
        self.round.end_round(resolved)

    def next_round(self) -> Round:
        curr_id, curr_explainer = next(self.user_cycle)
        guessers = copy(self.users)
        del guessers[curr_id]
        curr_guesser = guessers[choice(list(guessers.keys()))]

        self.round = Round(
            "MINING",
            False,
            next(self.word_pack),
            [],
            curr_explainer,
            curr_guesser,
            len(guessers) - 1
        )

        return self.round
