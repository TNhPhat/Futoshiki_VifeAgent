from typing import List, Optional, Dict, Generator
from .predicates import Literal
from dataclasses import dataclass

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

class HornClauseKnowledgeBase:
    """
    Knowledge base of Horn clauses for SLD resolution
    Indexed by head predicate name for fast clause lookup.
    """
    def __init__(self) -> None:
        self._clause: List[HornClause] = []
        self._index: Dict[str,List[HornClause]] = {}

    def add_clause(self,clause: HornClause) -> None:
        self._clause.append(clause)
        name = clause.head.name
        if name not in self._index:
            self._index[name] = []
        self._index[name].append(clause)
    
    def add_fact(self, fact: Literal) -> None:
        self.add_clause(HornClause(head = fact,body = []))
    
    def add_rule(self,rule: HornClause) -> None:
        self.add_clause(rule)
    
    def get_clause_for(self,predicate_name: str) -> List[HornClause]:
        return self._index.get(predicate_name, [])

    @property
    def clause_count(self) -> int:
        return len(self._clause)
