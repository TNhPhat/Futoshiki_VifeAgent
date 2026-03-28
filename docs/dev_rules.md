# General formatting

Reference: https://peps.python.org/pep-0008/

- Line length: limit to 88 characters.
- Indentation: Tabs(4 spaces).
- Import: group into theses following groups:
    - Standard library(os, sys, math).
    - Third-party library(numpy).
    - Local imports.

# Naming conventions

| **Type** | **Convention** | **Example** |
| --- | --- | --- |
| **Classes** | PascalCase | Algorithm, Problem |
| **Functions** | snake_case | calc, from |
| **Variables** | snake_case | current_best, population_size |
| **Constants** | UPPER_CASE | MAX_ITERATIONS, PI, SEED |
| Private member | _snake_case | _initialize_population(internal helper) |

When naming make sure to express the characteristic through it name, making meaningful name. With the sole exception being mathematical variable, its is acceptable to use standard mathematical notation(single letters) **if and only if** they match the algorithm paper definition, but remember to add a comment to explain it.

```python
w = 0.9 # Inertia weight # Good
c1 = 2.0 # Cognitive coefficient # Good
a = 3 # Bad since there are no comment explaining what a is.
```

# Documentation

Required to use docstrings to explain the code. Use the **Numpy Docstring Standard**.

**Every Class and Public Method must have a docstring.**

```python
def optimize(self, objective_func, bounds):
    """
    Runs the Particle Swarm Optimization.

    Parameters
    ----------
    objective_func : callable
        The objective function to minimize. Must accept a 1D or 2D numpy array.
    bounds : tuple or list
        The bounds of the search space (min, max).

    Returns
    -------
    best_solution : np.ndarray
        The coordinates of the best solution found.
    best_fitness : float
        The objective value of the best solution.
    history : list
        List of fitness values over iterations (for convergence plotting).
    """
```

# Additional practices

## Vectorization over Loops

Do not use Python for loops to iterate over population members. Use Numpy broadcasting.

- **Bad**

```python
fitnesses = []
for particle in population:
    fitnesses.append(objective_func(particle))
```

- **Good**

```python
# Apply function along axis 1 (rows)
fitnesses = np.apply_along_axis(objective_func, 1, population)
```

## Explicit Shapes in Comments

Always comment the shape of your arrays.

```python
# X shape: (population_size, dimensions) e.g., (50, 10)
X = np.random.uniform(lb, ub, (pop_size, dim))

# fitness shape: (population_size, ) e.g., (50,)
fitness = self.evaluate(X)
```

## **Architectural Interface**

Every algorithm class must inherit from a base class.

Use Python type hints to clarify inputs, especially distinguishing between scalars and arrays(typing library).

## **Visualization & Reporting Ready**

Every algorithm must log their progress:

- Do not just print() the result.
- Store the "Best Fitness" of every iteration in a list (e.g., self.convergence_curve).
- Return this history at the end of the execution so the Visualization module can plot it.

## **Git / Version Control Strategy**

- **Branching**: Do not push to main directly.
    - Create branches for features: feature/genetic-algorithm, fix/simulated-annealing-bug.
- **Commit Messages:** Use imperative mood.
    - Start with the main reason of the commit(best to be one verb).
    - *Good:* "feat: Add crossover function to GA".
    - *BAD:* “Fix stuff”.
- **Jupyter Notebooks**: Do not commit large Jupyter Notebooks with output cells.
    - Clear output before committing, or better yet, keep the logic in .py files and only import them into Notebooks for testing.