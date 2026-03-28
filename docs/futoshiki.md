## FOL Axiom System

### Predicates

| Predicate | Arity | Meaning |
|---|---|---|
| `Val(i, j, v)` | 3 | Cell (i,j) holds value v |
| `Given(i, j, v)` | 3 | Cell (i,j) is pre-filled with clue v |
| `LessH(i, j)` | 2 | Horizontal `<` : cell(i,j) < cell(i,j+1) |
| `GreaterH(i, j)` | 2 | Horizontal `>` : cell(i,j) > cell(i,j+1) |
| `LessV(i, j)` | 2 | Vertical `<` : cell(i,j) < cell(i+1,j) |
| `GreaterV(i, j)` | 2 | Vertical `>` : cell(i,j) > cell(i+1,j) |
| `Less(v₁, v₂)` | 2 | Numerical relation v₁ < v₂ |

> All variables range over `{1, …, N}`.


### Complete Axiom Table (A1–A16)

#### Cell Constraints

| ID | Name | FOL | Meaning | CNF Ground Form |
|---|---|---|---|---|
| **A1** | Cell Existence | ∀i ∀j ∃v Val(i,j,v) | Every cell must be filled with some value | `Val(i,j,1) ∨ Val(i,j,2) ∨ … ∨ Val(i,j,N)` |
| **A2** | Cell Uniqueness | ∀i ∀j ∀v₁ ∀v₂ (Val(i,j,v₁) ∧ Val(i,j,v₂)) ⇒ v₁=v₂ | A cell cannot hold two different values at once | `¬Val(i,j,v₁) ∨ ¬Val(i,j,v₂)` for all v₁ < v₂ |

#### Permutation Constraints

| ID | Name | FOL | Meaning | CNF Ground Form |
|---|---|---|---|---|
| **A3** | Row Uniqueness | ∀i ∀j₁ ∀j₂ ∀v (j₁≠j₂ ∧ Val(i,j₁,v) ∧ Val(i,j₂,v)) ⇒ ⊥ | No value repeats in the same row | `¬Val(i,j₁,v) ∨ ¬Val(i,j₂,v)` for all j₁ < j₂ |
| **A4** | Column Uniqueness | ∀i₁ ∀i₂ ∀j ∀v (i₁≠i₂ ∧ Val(i₁,j,v) ∧ Val(i₂,j,v)) ⇒ ⊥ | No value repeats in the same column | `¬Val(i₁,j,v) ∨ ¬Val(i₂,j,v)` for all i₁ < i₂ |
| **A12** | Row Surjection (NEW) | ∀i ∀v ∃j Val(i,j,v) | Every value 1..N must appear in each row | `Val(i,1,v) ∨ Val(i,2,v) ∨ … ∨ Val(i,N,v)` |
| **A13** | Column Surjection (NEW) | ∀j ∀v ∃i Val(i,j,v) | Every value 1..N must appear in each column | `Val(1,j,v) ∨ Val(2,j,v) ∨ … ∨ Val(N,j,v)` |

#### Inequality Constraints

| ID | Name | FOL | Meaning | CNF Ground Form |
|---|---|---|---|---|
| **A5** | Vertical Less | ∀i,j,v₁,v₂ (LessV(i,j) ∧ Val(i,j,v₁) ∧ Val(i+1,j,v₂)) ⇒ Less(v₁,v₂) | If a `<` arrow points down, the top cell's value must be smaller than the bottom cell's | `¬Val(i,j,v₁) ∨ ¬Val(i+1,j,v₂) ∨ Less(v₁,v₂)` |
| **A6** | Vertical Greater | ∀i,j,v₁,v₂ (GreaterV(i,j) ∧ Val(i,j,v₁) ∧ Val(i+1,j,v₂)) ⇒ Less(v₂,v₁) | If a `>` arrow points down, the top cell's value must be larger than the bottom cell's | `¬Val(i,j,v₁) ∨ ¬Val(i+1,j,v₂) ∨ Less(v₂,v₁)` |
| **A7** | Horizontal Less | ∀i,j,v₁,v₂ (LessH(i,j) ∧ Val(i,j,v₁) ∧ Val(i,j+1,v₂)) ⇒ Less(v₁,v₂) | If a `<` arrow points right, the left cell's value must be smaller than the right cell's | `¬Val(i,j,v₁) ∨ ¬Val(i,j+1,v₂) ∨ Less(v₁,v₂)` |
| **A8** | Horizontal Greater | ∀i,j,v₁,v₂ (GreaterH(i,j) ∧ Val(i,j,v₁) ∧ Val(i,j+1,v₂)) ⇒ Less(v₂,v₁) | If a `>` arrow points right, the left cell's value must be larger than the right cell's | `¬Val(i,j,v₁) ∨ ¬Val(i,j+1,v₂) ∨ Less(v₂,v₁)` |
| **A16** | Inequality Contrapositive (NEW) | LessH(i,j) ∧ ¬Less(v₁,v₂) ⇒ ¬Val(i,j,v₁) ∨ ¬Val(i,j+1,v₂) | Directly forbid value pairs that would violate an inequality (e.g. if `<`, ban all v₁ ≥ v₂) | `¬Val(i,j,v₁) ∨ ¬Val(i,j+1,v₂)` for all (v₁,v₂) where v₁ ≥ v₂ |

> [!TIP]
> **A16 is key for propagation.** When `LessH(i,j)` exists, directly emit `¬Val(i,j,v₁) ∨ ¬Val(i,j+1,v₂)` for every pair where v₁ ≥ v₂. This lets unit propagation prune impossible values immediately rather than waiting for multi-step inference.

#### Clues & Domain

| ID | Name | FOL | Meaning | CNF Ground Form |
|---|---|---|---|---|
| **A9** | Given Clues | ∀i,j,v Given(i,j,v) ⇒ Val(i,j,v) | Pre-filled cells must keep their given value | Unit clause: `Val(i,j,v)` |
| **A10** | Domain Bound | ∀i,j,v Val(i,j,v) ⇒ (v ∈ {1…N}) | Cell values can only be integers from 1 to N | Satisfied by only grounding v ∈ {1…N} |

#### Less Relation Definition (NEW)

| ID | Name | FOL | Meaning | CNF Ground Form |
|---|---|---|---|---|
| **A11** | Less Ground Truth (NEW) | Less(a,b) iff a < b | Define which number pairs satisfy "less than" (e.g. 1<2, 1<3, 2<3…) | Unit facts: `Less(1,2)`, `Less(1,3)`, …, `Less(N-1,N)` |
| **A14** | Less Irreflexivity (NEW) | ∀v ¬Less(v,v) | No number is less than itself | Unit clause: `¬Less(v,v)` for each v |
| **A15** | Less Asymmetry (NEW) | ∀v₁,v₂ Less(v₁,v₂) ⇒ ¬Less(v₂,v₁) | If a < b then b cannot be < a | `¬Less(v₁,v₂) ∨ ¬Less(v₂,v₁)` for all v₁ ≠ v₂ |

### Clause Count Estimate (for N×N grid)

| Axiom | # Clauses | Example (N=4) |
|---|---|---|
| A1 (existence) | N² | 16 |
| A2 (cell uniqueness) | N² × C(N,2) | 16 × 6 = 96 |
| A3 (row uniqueness) | N × C(N,2) × N | 4 × 6 × 4 = 96 |
| A4 (col uniqueness) | N × C(N,2) × N | 96 |
| A12 (row surjection) | N × N | 16 |
| A13 (col surjection) | N × N | 16 |
| A11 (Less facts) | C(N,2) | 6 |
| A14 (irreflexivity) | N | 4 |
| A15 (asymmetry) | C(N,2) | 6 |
| A16 (contrapositives) | per constraint × N²/2 | varies |
| **Total** | **≈ O(N⁴)** | **~350 for 4×4** |

---