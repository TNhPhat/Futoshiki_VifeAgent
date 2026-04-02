from dataclasses import dataclass
from typing import List, Optional, Dict, Generator
from fol import Literal

@dataclass
class HornClause:
    head: Literal # conclution
    body: List[Literal]

    def is_fact(self) -> bool | None:
        return len(self.body) == 0
    def __repr__(self) -> str:
        if self.is_fact():
            return f"{self.head}"
        else:
            body_str = ", ".join(str(b) for b in self.body)
            return f"{self.body}:- {body_str}"
