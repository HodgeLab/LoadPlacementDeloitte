# Power System Load Impact Analysis

## Project Structure

The project is broken down into the following modules:

- `grid_data.py`: Contains the power system network data (buses, branches, generators)
- `dc_power_flow.py`: Implements DC power flow calculations
- `unit_commitment.py`: Provides a simplified unit commitment optimization model (optional)
- `load_testing.py`: Tools for testing the impact of new load placement
- `visualization.py`: Visualization utilities for power system results
- `main.py`: Main script that deals with the analysis

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/power-system-analysis.git
cd power-system-analysis
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Run the main script with default parameters:

```bash
python main.py
```

This will test placing a 50 MW load on buses 4 through 9 of the IEEE 9-bus system.

### Advanced Usage

You can customize the analysis with command-line parameters:

```bash
python main.py --load-size 75.0 --reactive-load 30.0 --test-buses 4,5,7
```

Parameters:
- `--load-size`: Size of new load to test in MW (default: 50.0)
- `--reactive-load`: Reactive component of new load in MVAr (default: 20.0)
- `--test-buses`: Comma-separated list of buses to test load placement (default: 4,5,6,7,8,9)

## Example Workflow

The analysis follows these steps:

1. Run a base case DC power flow to establish the initial state of the system
2. Perform unit commitment optimization to determine generator dispatch
3. Test the impact of placing the new load at each specified bus
4. Analyze results and recommend the best bus for load placement
5. Generate visualizations to help understand the results

## Visualization

The program can generate various visualizations:

- Network diagram showing buses, lines, and power flows
- Line loading comparison between base case and load addition scenarios
- Generator dispatch schedule from unit commitment
- Bus ranking for load placement recommendations

## Extending the Project

### Adding a New System

To add a new power system model:

1. Create a new function in `grid_data.py` that returns the system data
2. Follow the same format as `get_9bus_system()`