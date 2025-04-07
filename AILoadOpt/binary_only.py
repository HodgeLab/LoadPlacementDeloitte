import numpy as np
import pandas as pd
import pandapower as pp
import pandapower.networks as pn
import copy
from scipy.optimize import minimize

class LoadPlacementOptimizer:
    def __init__(self, net, new_load_mva, power_factor=0.9):
        """
        Initialize the optimizer for load placement.
        
        Parameters:
        -----------
        net : pandapower.network
            PANDAPOWER network
        new_load_mva : float
            Size of new load in MVA
        power_factor : float, optional
            Power factor of the new load, default is 0.9
        """
        self.original_net = copy.deepcopy(net)
        self.new_load_mva = new_load_mva
        self.power_factor = power_factor
        
        # Convert MVA to MW and MVAr based on power factor
        self.new_load_mw = new_load_mva * power_factor
        self.new_load_mvar = new_load_mva * np.sin(np.arccos(power_factor))
        
        # Get all buses except the slack bus (ext_grid connection point)
        slack_buses = self.original_net.ext_grid.bus.values
        self.candidate_buses = [bus for bus in self.original_net.bus.index if bus not in slack_buses]
        
        # Map to store bus indices for optimization
        self.bus_map = {i: bus for i, bus in enumerate(self.candidate_buses)}
        self.reverse_bus_map = {bus: i for i, bus in enumerate(self.candidate_buses)}
    
    def evaluate_placement(self, x):
        """
        Evaluate a specific load placement configuration.
        
        Parameters:
        -----------
        x : numpy array
            Binary vector representing bus selection.
            
        Returns:
        --------
        dict
            Results with objective value and constraint violations
        """
        # Create a copy of the original network
        test_net = copy.deepcopy(self.original_net)
        
        # Find the selected bus (index with highest value in x)
        if len(x) > 1:
            selected_idx = np.argmax(x)
            selected_bus = self.bus_map[selected_idx]
        else:
            selected_bus = self.candidate_buses[0]
        
        # Add the new load to the selected bus
        pp.create_load(
            test_net, 
            bus=selected_bus, 
            p_mw=self.new_load_mw, 
            q_mvar=self.new_load_mvar,
            name=f"Optimization Test Load"
        )
        
        # Run power flow
        try:
            pp.runpp(test_net, algorithm='nr', max_iteration=100)
            converged = True
        except pp.powerflow.LoadflowNotConverged:
            converged = False
        
        if converged:
            # Get line loading percentages
            if test_net.res_line.empty:
                return {
                    'objective': float('inf'),
                    'converged': True,
                    'max_loading': 0,
                    'violations': 0,
                    'selected_bus': selected_bus
                }
            
            loading = test_net.res_line['loading_percent']
            max_loading = loading.max() if not loading.empty else 0
            
            # Count violations
            violations = sum(1 for l in loading if l > 100)
            
            # Calculate objective: maximize margin to line limits (minimize maximum loading)
            objective = max_loading
            
            return {
                'objective': objective,
                'converged': True,
                'max_loading': max_loading,
                'violations': violations,
                'selected_bus': selected_bus
            }
        else:
            # Power flow did not converge - highly penalize this solution
            return {
                'objective': float('inf'),
                'converged': False,
                'max_loading': float('inf'),
                'violations': float('inf'),
                'selected_bus': selected_bus
            }
    
    def optimize_binary(self):
        """
        Use a binary optimization approach.
        Tests all buses and selects the best one.
        
        Returns:
        --------
        dict
            Optimization results
        """
        print("Running binary optimization to test all buses...")
        n_buses = len(self.candidate_buses)
        results = []
        
        # Try placing load at each candidate bus
        for i, bus in enumerate(self.candidate_buses):
            # Create a binary vector with 1 at position i
            x = np.zeros(n_buses)
            x[i] = 1.0
            
            # Evaluate this placement
            eval_result = self.evaluate_placement(x)
            bus_name = self.get_bus_name(bus)
            
            results.append({
                'bus': bus,
                'bus_name': bus_name,
                'objective': eval_result['objective'],
                'converged': eval_result['converged'],
                'max_loading': eval_result['max_loading'],
                'violations': eval_result['violations']
            })
            
            # Print progress
            print(f"  Bus {bus} ({bus_name}): ", end="")
            if eval_result['converged']:
                print(f"Max loading: {eval_result['max_loading']:.2f}%, Violations: {eval_result['violations']}")
            else:
                print("Power flow did not converge")
        
        # Filter valid results (converged solutions)
        valid_results = [r for r in results if r['converged']]
        
        if not valid_results:
            print("No valid solutions found!")
            return None
        
        # Filter solutions with no violations
        no_violations = [r for r in valid_results if r['violations'] == 0]
        
        if no_violations:
            # Sort by objective (max line loading)
            best_result = min(no_violations, key=lambda r: r['max_loading'])
        else:
            # If all solutions have violations, take the one with least violations
            best_result = min(valid_results, key=lambda r: (r['violations'], r['max_loading']))
        
        return best_result
    
    def get_bus_name(self, bus):
        """Get the name of a bus if available, otherwise return its number."""
        if 'name' in self.original_net.bus.columns and self.original_net.bus.at[bus, 'name']:
            return self.original_net.bus.at[bus, 'name']
        else:
            return f"Bus {bus}"

# Example usage
if __name__ == "__main__":
    # Load the 9-bus test case
    net = pn.case9()
    
    # Define the new load size in MVA
    new_load_mva = 50.0  # Example: 50 MVA
    
    # Create the optimizer
    optimizer = LoadPlacementOptimizer(net, new_load_mva)
    
    # Run binary optimization (try all buses)
    print("\nRunning Binary Optimization Only:")
    print("=" * 50)
    binary_result = optimizer.optimize_binary()
    
    if binary_result:
        print("\nBinary Optimization Results:")
        print("=" * 50)
        
        # Convert bus name to string to ensure it's subscriptable
        bus_name_str = str(binary_result['bus_name'])
        
        print(f"Best bus for load placement: {binary_result['bus']} ({bus_name_str})")
        print(f"Maximum line loading: {binary_result['max_loading']:.2f}%")
        print(f"Line violations: {binary_result['violations']}")
    else:
        print("No valid solution found!")