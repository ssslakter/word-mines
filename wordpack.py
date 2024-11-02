from fasthtml.common import *
from pathlib import Path
from dataclasses import dataclass
from random import shuffle
from itertools import cycle


wordpacks = {
    'default': 'data.txt'
}


@dataclass
class WordPack:
    name: str
    words: list[str]
    cycle: Iterator[str] = None

    @classmethod
    def get_from_dict(cls, name='default'):
        fname = Path(wordpacks[name])
        try:
            with open(fname, encoding="utf-8") as f: return cls(name, f.readlines())
        except FileNotFoundError: raise HTTPException(404, f"Wordpack {name} not found")

    def __post_init__(self): self.reset()

    def reset(self):
        shuffle(self.words)
        self.cycle = cycle(self.words)

    def __iter__(self): return self
    def __next__(self) -> str: return next(self.cycle)
