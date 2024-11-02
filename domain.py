import uuid
from fasthtml.common import *
from dataclasses import dataclass, field
from random import choice
from copy import copy
from wordpack import WordPack


@dataclass
class User:
    name: str = 'null'
    points: int = 0
    ws_send: Optional[FunctionType] = None
    img: str = 'https://randomuser.me/api/portraits/lego/2.jpg'

    def add_points(self, value): self.points += value
    def clear_points(self): self.points = 0


@dataclass
class Mine:
    user: User
    id: str = str(uuid.uuid4())
    word: str = ''
    triggered: bool = False

    def click(self): self.triggered = not self.triggered

class State(Enum):
    MINING = "MINING"
    GUESSING = "GUESSING"
    ENDED = "ENDED"


@dataclass
class Round:
    word: str
    guesser: User
    explainer: User
    mines_count: int 
    states = cycle([State.MINING, State.GUESSING, State.ENDED])
    state: State = State.MINING
    resolved: bool = False
    mines: dict[Mine] = field(default_factory=dict)

    def add_mine(self, mine: Mine):
        self.mines[mine.id] = mine
        if len(self.mines) >= self.mines_count: self.state = next(self.states)
        
    def get_mine(self, mine_id: str): return self.mines[mine_id]

    def end_round(self, resolved: bool):
        if self.state == State.MINING:
            raise Exception("Cannot end round while mining")

        mine_trig = False
        self.resolved = resolved
        # TODO dont give points
        self.state = State.ENDED

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

    def restart_game(self) -> Round:
        """Start a new game and return the first round"""
        self.started = True
        self.update_users()
        self.wordpack.reset()
        return self.next_round()

    def join(self, uid: str, user: User):
        if self.started: raise HTTPException(403, "Game already started")
        self.users[uid] = user

    def leave(self, uid: str):
        if self.started: raise HTTPException(401, "Game is started")
        del self.users[uid]

    def end_round(self, resolved: bool):
        self.round.end_round(resolved)

    def next_round(self) -> Round:
        curr_id, curr_explainer = next(self.user_cycle)
        guessers = copy(self.users)
        del guessers[curr_id]
        curr_guesser = guessers[choice(list(guessers.keys()))]

        self.round = Round(next(self.wordpack),curr_guesser, curr_explainer,len(guessers) - 1)

        return self.round
