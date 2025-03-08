# Power System Load Placement Analysis with PYPOWER

This project provides a simple framework for testing the impact of adding new loads to a power system using PYPOWER.

## Overview

The framework allows you to:
- Test the impact of adding a new load at different buses in the system
- Run both AC and DC power flow analysis
- Check for line thermal limit violations and generator capacity violations
- Receive recommendations for the best bus to place a new load

## Installation

### Prerequisites

- Python 3.6+
- PYPOWER package

### Install Dependencies

```bash
pip install pypower numpy
```

## File Structure

- `grid_data_pypower.py`: Contains functions to get the IEEE 9-bus test system and add loads
- `power_flow_pypower.py`: Implements AC/DC power flow and violation checking functions
- `load_testing_pypower.py`: Implements load placement testing and recommendation logic
- `main_pypower.py`: Main script to run the analysis

## Usage

### Basic Usage

Run the main script with default parameters:

```bash
python main_pypower.py
```

This will test placing a 50 MW, 20 MVAr load on buses 5, 7, and 9, using AC power flow by default.

### Command Line Arguments

```bash
python main_pypower.py --load 75 --reactive 30 --buses 5,6,7,8,9 --dc
```

Arguments:
- `--load`: Size of new load in MW (default: 50)
- `--reactive`: Size of reactive component in MVAr (default: 20)
- `--buses`: Comma-separated list of buses to test (default: 5,7,9)
- `--dc`: Use DC power flow instead of AC (flag, default is AC)

## How It Works

1. **Load the Base Case**:
   - Get the IEEE 9-bus system data from PYPOWER

2. **Run Base Case Analysis**:
   - Perform power flow on the base system
   - Check for any existing violations

3. **Test Each Bus**:
   - For each specified bus, add the new load
   - Run power flow with the modified system
   - Check for line and generator violations
   - Calculate changes in line loadings

4. **Generate Recommendations**:
   - Calculate a score for each bus based on violations and line loadings
   - Rank buses from best to worst
   - Provide a recommendation for the optimal placement

## Example Output

```
Testing 50.0 MW load placement on buses: [5, 7, 9]
Using AC power flow
Tests completed in 0.15 seconds

===== LOAD PLACEMENT RECOMMENDATIONS =====
Bus 5 is recommended for the new load placement.
Found 2 feasible placement options.

Ranked buses (lower score is better):
1. Bus 5: Score 80.5 - ✅ FEASIBLE
   Reason: Feasible location
   Max line loading: 65.2%
   Most impacted line: 4 to 5, change: 7.6%
2. Bus 9: Score 102.3 - ✅ FEASIBLE
   Reason: Feasible location
   Max line loading: 76.9%
   Most impacted line: 9 to 4, change: 12.7%
3. Bus 7: Score 1000.0 - ❌ INFEASIBLE
   Reason: Line violations
   Max line loading: 110.8%
   Most impacted line: 7 to 8, change: 25.1%

===== DETAILED TEST RESULTS =====
...
```

## Extending the Framework

You can extend this framework by:
- Adding different power system test cases
- Implementing visualization functions
- Adding more sophisticated economic analysis
- Implementing AC optimal power flow
- Adding contingency analysis (N-1 reliability)

## Limitations

- Currently uses the IEEE 9-bus test system only
- Doesn't integrate economic dispatch or unit commitment
- Limited to steady-state analysis
- No visualization capabilities