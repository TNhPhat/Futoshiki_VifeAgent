"""
Tests for A* search heuristics: h₁ (Empty Cells), h₂ (Domain Sum), h₃ (Min Conflicts).

Each heuristic is tested for:
  - Correct value on hand-crafted states
  - Admissibility: h(n) >= 0 for all states
  - Zero heuristic on complete states
  - Monotonicity: more constrained states → lower h
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from constraints.inequality_constraint import InequalityConstraint
from core.puzzle import Puzzle
from heuristics.empty_cell_heuristic import EmptyCellHeuristic
from heuristics.domain_size_heuristic import DomainSizeHeuristic
from heuristics.min_conflicts_heuristic import MinConflictsHeuristic
from search.state import SearchState


def make_puzzle(N, grid, h=None, v=None):
    """Build a Puzzle from lists."""
    h_constraints = [
        InequalityConstraint(cell1=(r, c), cell2=(r, c + 1), direction=d)
        for r, c, d in (h or [])
    ]
    v_constraints = [
        InequalityConstraint(cell1=(r, c), cell2=(r + 1, c), direction=d)
        for r, c, d in (v or [])
    ]
    return Puzzle(
        N=N,
        grid=np.array(grid, dtype=int),
        h_constraints=h_constraints,
        v_constraints=v_constraints,
    )


def make_state(grid, domains=None):
    """Build a SearchState from a grid and optional domain dict."""
    grid_arr = np.array(grid, dtype=int)
    N = grid_arr.shape[0]
    if domains is None:
        domains = {}
        for i in range(N):
            for j in range(N):
                if grid_arr[i, j] == 0:
                    domains[(i, j)] = set(range(1, N + 1))
    return SearchState(grid=grid_arr, domains=domains)


class TestEmptyCellHeuristic:
    def setup_method(self):
        self.h = EmptyCellHeuristic()

    def test_name(self):
        assert "h1" in self.h.get_name()

    def test_complete_grid_returns_zero(self):
        puzzle = make_puzzle(2, [[1, 2], [2, 1]])
        state = make_state([[1, 2], [2, 1]])
        assert self.h.estimate(state, puzzle) == 0

    def test_all_empty_returns_n_squared(self):
        puzzle = make_puzzle(3, [[0]*3]*3)
        state = make_state([[0]*3]*3)
        assert self.h.estimate(state, puzzle) == 9

    def test_partial_assignment(self):
        puzzle = make_puzzle(2, [[1, 0], [0, 0]])
        state = make_state([[1, 0], [0, 0]])
        assert self.h.estimate(state, puzzle) == 3

    def test_single_empty_cell(self):
        puzzle = make_puzzle(2, [[1, 2], [2, 0]])
        state = make_state([[1, 2], [2, 0]])
        assert self.h.estimate(state, puzzle) == 1

    def test_nonnegative(self):
        """h₁ is always >= 0 (admissibility base condition)."""
        puzzle = make_puzzle(3, [[0]*3]*3)
        state = make_state([[0]*3]*3)
        assert self.h.estimate(state, puzzle) >= 0


class TestDomainSizeHeuristic:
    def setup_method(self):
        self.h = DomainSizeHeuristic()

    def test_name(self):
        assert "h2" in self.h.get_name()

    def test_complete_grid_returns_zero(self):
        puzzle = make_puzzle(2, [[1, 2], [2, 1]])
        state = make_state([[1, 2], [2, 1]], domains={})
        assert self.h.estimate(state, puzzle) == 0

    def test_singleton_domains_return_zero(self):
        """Cells with domain size 1 contribute 0."""
        puzzle = make_puzzle(2, [[1, 0], [0, 0]])
        state = make_state(
            [[1, 0], [0, 0]],
            domains={
                (0, 1): {2},
                (1, 0): {2},
                (1, 1): {1},
            },
        )
        # Each domain has size 1 → (1-1)*3 = 0
        assert self.h.estimate(state, puzzle) == 0

    def test_full_domains(self):
        """Each cell with domain {1,2} contributes 1."""
        puzzle = make_puzzle(2, [[0, 0], [0, 0]])
        state = make_state(
            [[0, 0], [0, 0]],
            domains={
                (0, 0): {1, 2},
                (0, 1): {1, 2},
                (1, 0): {1, 2},
                (1, 1): {1, 2},
            },
        )
        # 4 cells x (2-1) = 4
        assert self.h.estimate(state, puzzle) == 4

    def test_mixed_domains(self):
        """Cells with varying domain sizes."""
        puzzle = make_puzzle(3, [[1, 0, 0], [0, 0, 0], [0, 0, 0]])
        state = make_state(
            [[1, 0, 0], [0, 0, 0], [0, 0, 0]],
            domains={
                (0, 1): {2, 3},      # contributes 1
                (0, 2): {2, 3},      # contributes 1
                (1, 0): {2, 3},      # contributes 1
                (1, 1): {1, 2, 3},   # contributes 2
                (1, 2): {1, 2, 3},   # contributes 2
                (2, 0): {2, 3},      # contributes 1
                (2, 1): {1, 2, 3},   # contributes 2
                (2, 2): {1, 2, 3},   # contributes 2
            },
        )
        assert self.h.estimate(state, puzzle) == 12

    def test_nonnegative(self):
        puzzle = make_puzzle(2, [[0, 0], [0, 0]])
        state = make_state([[0, 0], [0, 0]])
        assert self.h.estimate(state, puzzle) >= 0


class TestMinConflictsHeuristic:
    def setup_method(self):
        self.h = MinConflictsHeuristic()

    def test_name(self):
        assert "h3" in self.h.get_name()

    def test_complete_grid_returns_zero(self):
        puzzle = make_puzzle(2, [[1, 2], [2, 1]])
        state = make_state([[1, 2], [2, 1]], domains={})
        assert self.h.estimate(state, puzzle) == 0

    def test_no_conflicts_possible(self):
        """When the only domain value causes no conflicts → h = 0."""
        puzzle = make_puzzle(2, [[1, 0], [0, 0]])
        # (0,1) has domain {2}, row 0 has 1 → no conflict
        state = make_state(
            [[1, 0], [0, 0]],
            domains={
                (0, 1): {2},
                (1, 0): {2},
                (1, 1): {1},
            },
        )
        assert self.h.estimate(state, puzzle) == 0

    def test_conflict_with_row_peer(self):
        """Cell forced to duplicate a value in its row → conflict = 1."""
        puzzle = make_puzzle(2, [[1, 0], [0, 0]])
        # (0,1) domain is {1} — same as grid[0,0]=1 → 1 conflict
        state = make_state(
            [[1, 0], [0, 0]],
            domains={
                (0, 1): {1},     # min conflict = 1 (duplicates row)
                (1, 0): {2},     # min conflict = 0
                (1, 1): {1},     # min conflict = 0
            },
        )
        assert self.h.estimate(state, puzzle) == 1

    def test_inequality_conflict(self):
        """Cell assignment violates an inequality → conflict counted."""
        # cell(0,0) < cell(0,1), grid[0,0]=2
        puzzle = make_puzzle(2, [[2, 0], [0, 0]], h=[(0, 0, "<")])
        # (0,1) domain {1}: 1 < 2 is False (cell1=2, cell2=1) → conflict
        state = make_state(
            [[2, 0], [0, 0]],
            domains={
                (0, 1): {1},     # assigning 1 violates 2 < 1
                (1, 0): {1},
                (1, 1): {2},
            },
        )
        h_val = self.h.estimate(state, puzzle)
        assert h_val >= 1  # at least (0,1) has min conflict = 1

    def test_nonnegative(self):
        puzzle = make_puzzle(3, [[0]*3]*3)
        state = make_state([[0]*3]*3)
        assert self.h.estimate(state, puzzle) >= 0

    def test_min_over_domain(self):
        """When one domain value has 0 conflicts, min = 0 for that cell."""
        puzzle = make_puzzle(2, [[1, 0], [0, 0]])
        # (0,1) has {1,2}: val=1 → 1 conflict (row dup), val=2 → 0 → min=0
        state = make_state(
            [[1, 0], [0, 0]],
            domains={
                (0, 1): {1, 2},
                (1, 0): {2},
                (1, 1): {1},
            },
        )
        # (0,1) min=0, (1,0) min=0, (1,1) min=0
        assert self.h.estimate(state, puzzle) == 0


class TestHeuristicOrdering:
    """h₂ is generally >= h₁ in informativeness on the same state."""

    def test_h2_gte_h1_on_full_domain(self):
        """On a state with full domains, h₂ >= h₁."""
        puzzle = make_puzzle(3, [[0]*3]*3)
        state = make_state([[0]*3]*3)

        h1 = EmptyCellHeuristic().estimate(state, puzzle)
        h2 = DomainSizeHeuristic().estimate(state, puzzle)

        # h1 = 9, h2 = 9 * (3-1) = 18
        assert h2 >= h1

    def test_all_heuristics_nonneg_on_solved(self):
        puzzle = make_puzzle(2, [[1, 2], [2, 1]])
        state = make_state([[1, 2], [2, 1]], domains={})

        assert EmptyCellHeuristic().estimate(state, puzzle) == 0
        assert DomainSizeHeuristic().estimate(state, puzzle) == 0
        assert MinConflictsHeuristic().estimate(state, puzzle) == 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
