# Power System Load Placement Optimization

This repository contains tools to analyze and optimize the placement of new loads in power systems using AC power flow analysis.

## Problem Statement

When adding a new load to a power system, the location (bus) of placement matters significantly as it affects line flows, voltage profiles, and overall system stability. This project addresses:

1. **Individual Testing Approach**: Testing the effect of adding a load of X MVA on each bus in the system one by one, running N separate power flows.
2. **Optimization Approach**: Finding the optimal bus for load placement in a single optimization run rather than N separate tests.

## Components

### 1. Individual Bus Testing Script

`individual-bus-testing.py` performs:
- Sequential testing of load placement at each bus
- AC power flow analysis for each placement
- Evaluation of line loading constraints
- Identification of the best bus based on margin to line limits

### 2. Optimization Approach

`optimization-approach.py` implements a more efficient optimization-based approach that:
- Formulates the load placement as an optimization problem
- Finds the optimal solution in a single run instead of N separate runs
- Supports both binary and gradient-based optimization methods

## Optimization Formulation

The optimization problem is formulated as follows:

### Decision Variables
- Binary vector x of length N (number of buses), where x[i] = 1 if the load is placed at bus i, and 0 otherwise

### Objective Function
- Minimize the maximum line loading percentage across all lines
- Add penalties for power flow non-convergence and line limit violations

### Constraints
- Only one bus can receive the new load (sum of x equals 1)
- Power flow equations must be satisfied (handled implicitly through power flow solutions)
- Line flow limits should not be violated (handled through penalties in the objective function)

### Solution Approaches

#### Binary Approach
Directly compares all possible placements within a single optimization framework.

#### Gradient-Based Approach
Uses SciPy's SLSQP solver to find the optimal solution in a continuous space, then rounds to the best discrete solution.

## How It Works

The key function that enables single-run optimization is `evaluate_placement()`, which:

1. Takes a placement vector (can be binary or continuous weights)
2. Distributes the load according to this vector
3. Runs a single power flow
4. Calculates line loadings and constraint violations
5. Returns a comprehensive result that the optimizer can use

Unlike the N-run approach where each bus is tested individually, the optimization approach:
- Intelligently searches through the solution space
- Uses the optimization algorithm to guide the search toward promising solutions
- Finds the optimal solution without exhaustively testing every bus

## Requirements

- Python 3.6+
- PYPOWER or MATPOWER
- NumPy
- SciPy (for optimization)

## Usage

### Individual Testing

```python
# Example: Test adding a 50 MVA load to each bus
python individual-bus-testing.py
```

### Optimization Approach

```python
# Example: Find optimal placement for a 50 MVA load
python optimization-approach.py
```

## Customization

You can modify these scripts to:

1. Change the test case by replacing `case9()` with other PYPOWER test cases like `case14()`, `case30()`, etc.
2. Adjust the new load size by changing `new_load_mva` value
3. Modify the power factor of the load as needed
4. Add more constraints to the optimization problem
5. Implement more sophisticated objective functions (e.g., including voltage profiles, losses, etc.)

## Advantages of the Optimization Approach

1. **Efficiency**: Finds the optimal solution in a single run instead of N separate runs
2. **Scalability**: Particularly valuable for larger systems where testing all buses individually would be computationally expensive
3. **Flexibility**: Can be extended to consider multiple simultaneous load placements
4. **Extensibility**: Allows for flexible objective functions and constraints
5. **Advanced Scenarios**: Can handle more complex cases like distributed load placement
