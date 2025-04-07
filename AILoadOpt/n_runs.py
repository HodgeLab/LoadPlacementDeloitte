import numpy as np
import pandas as pd
import pandapower as pp
import pandapower.networks as pn
import copy

def test_load_addition(net, new_load_mva, power_factor=0.9):
    """
    Test the addition of a new load at each bus in the system.
    
    Parameters:
    -----------
    net : pandapower.network
        PANDAPOWER network
    new_load_mva : float
        Size of new load in MVA
    power_factor : float, optional
        Power factor of the new load, default is 0.9
    
    Returns:
    --------
    dict
        Results for each bus with line loading information
    """
    # Make a copy of the original network
    original_net = copy.deepcopy(net)
    
    # Convert MVA to MW and MVAr based on power factor
    new_load_mw = new_load_mva * power_factor
    new_load_mvar = new_load_mva * np.sin(np.arccos(power_factor))
    
    # Get all buses except the slack bus (ext_grid connection point)
    slack_buses = net.ext_grid.bus.values
    candidate_buses = [bus for bus in net.bus.index if bus not in slack_buses]
    
    # Dictionary to store results
    results = {}
    
    print(f"Testing addition of {new_load_mva:.2f} MVA load at each bus...")
    
    # Try adding load to each bus
    for bus in candidate_buses:
        # Get bus name or number
        bus_name = f"Bus {bus}"
        if 'name' in net.bus.columns and net.bus.at[bus, 'name']:
            bus_name = net.bus.at[bus, 'name']
        
        print(f"\n{bus_name}: Adding {new_load_mw:.2f} MW, {new_load_mvar:.2f} MVAr")
        
        # Create a copy of the original network for this test
        test_net = copy.deepcopy(original_net)
        
        # Add a new load to the bus
        pp.create_load(
            test_net, 
            bus=bus, 
            p_mw=new_load_mw, 
            q_mvar=new_load_mvar,
            name=f"New Load at {bus_name}"
        )
        
        # Run power flow
        try:
            pp.runpp(test_net, algorithm='nr', max_iteration=100)
            converged = True
            print("  Power flow converged")
        except pp.powerflow.LoadflowNotConverged:
            converged = False
            print("  Power flow did NOT converge!")
        
        if converged:
            # Get line loading information
            loading = test_net.res_line['loading_percent'].sort_values(ascending=False)
            max_loading = loading.max() if not loading.empty else 0
            margin_to_limit = 100 - max_loading
            
            # Check for line limit violations
            violations = test_net.res_line[test_net.res_line['loading_percent'] > 100]
            
            # Store detailed branch loading information
            branch_loading = []
            for idx, row in test_net.res_line.iterrows():
                from_bus = test_net.line.at[idx, 'from_bus']
                to_bus = test_net.line.at[idx, 'to_bus']
                
                # Get bus names if available
                from_bus_name = f"Bus {from_bus}"
                to_bus_name = f"Bus {to_bus}"
                if 'name' in test_net.bus.columns:
                    if test_net.bus.at[from_bus, 'name']:
                        from_bus_name = test_net.bus.at[from_bus, 'name']
                    if test_net.bus.at[to_bus, 'name']:
                        to_bus_name = test_net.bus.at[to_bus, 'name']
                
                loading_percent = row['loading_percent']
                
                branch_info = {
                    'line_idx': idx,
                    'from_bus': from_bus,
                    'to_bus': to_bus,
                    'from_bus_name': from_bus_name,
                    'to_bus_name': to_bus_name,
                    'flow_mw': row['p_from_mw'],
                    'loading_percent': loading_percent
                }
                branch_loading.append(branch_info)
            
            # Sort branch loading by loading percentage (descending)
            branch_loading.sort(key=lambda x: x['loading_percent'], reverse=True)
            
            # Collect violations
            violations_list = []
            if not violations.empty:
                for idx, row in violations.iterrows():
                    line_data = test_net.line.loc[idx]
                    from_bus = line_data['from_bus']
                    to_bus = line_data['to_bus']
                    
                    violation_info = {
                        'line_idx': idx,
                        'from_bus': from_bus,
                        'to_bus': to_bus,
                        'loading_percent': row['loading_percent']
                    }
                    violations_list.append(violation_info)
                
                print(f"  WARNING: {len(violations_list)} line violations detected!")
                for v in violations_list:
                    print(f"    Line {v['from_bus']}-{v['to_bus']}: {v['loading_percent']:.2f}%")
            else:
                print(f"  No violations. Max loading: {max_loading:.2f}%")
            
            # Store results
            results[bus] = {
                'bus_name': bus_name,
                'converged': True,
                'branch_loading': branch_loading,
                'violations': violations_list,
                'max_loading': max_loading,
                'margin_to_limit': margin_to_limit
            }
        else:
            # Store results for non-converged case
            results[bus] = {
                'bus_name': bus_name,
                'converged': False,
                'branch_loading': [],
                'violations': [],
                'max_loading': float('inf'),
                'margin_to_limit': -float('inf')
            }
    
    return results

def find_best_bus(results):
    """
    Find the best bus for load placement based on line loading margins.
    
    Parameters:
    -----------
    results : dict
        Results dictionary from test_load_addition
    
    Returns:
    --------
    int
        Bus number with the highest margin to line limits
    """
    # Filter out buses where power flow didn't converge
    valid_results = {bus: data for bus, data in results.items() if data['converged']}
    
    if not valid_results:
        print("No valid solutions found!")
        return None
    
    # First filter for buses with no violations
    no_violations = {bus: data for bus, data in valid_results.items() if not data['violations']}
    
    if no_violations:
        # Find the bus with the highest margin to limit (lowest line loading)
        best_bus = max(no_violations.items(), key=lambda x: x[1]['margin_to_limit'])[0]
    else:
        # If all buses have violations, find the one with the fewest violations
        best_bus = min(valid_results.items(), key=lambda x: (len(x[1]['violations']), -x[1]['margin_to_limit']))[0]
    
    return best_bus

# Example usage
if __name__ == "__main__":
    # Create a 9-bus test case (IEEE 9-bus system)
    net = pn.case118()
    
    # Define the new load size in MVA
    new_load_mva = 600 # Example: 50 MVA
    
    # Run the testing function
    results = test_load_addition(net, new_load_mva)
    
    # Find the best bus
    best_bus = find_best_bus(results)
    
    if best_bus is not None:
        print("\nResults Summary:")
        print("=" * 50)
        
        # Sort buses by margin to limit (descending)
        sorted_buses = sorted(
            results.items(), 
            key=lambda x: x[1]['margin_to_limit'] if x[1]['converged'] else -float('inf'), 
            reverse=True
        )
        
        print(f"{'Bus':<5} {'Name':<15} {'Converged':<10} {'Max Loading %':<15} {'Margin %':<15} {'Violations':<10}")
        print("-" * 70)
        
        for bus, data in sorted_buses:
            bus_name = data['bus_name']
            bus_name_str = str(bus_name)
            print(f"{bus:<5} {bus_name_str[:15]:<15} {str(data['converged']):<10} "
                  f"{data['max_loading']:<15.2f} {data['margin_to_limit']:<15.2f} "
                  f"{len(data['violations']):<10}")
        
        print("\nBest bus for new load placement:", best_bus)
        print(f"Bus name: {results[best_bus]['bus_name']}")
        print(f"Margin to limit: {results[best_bus]['margin_to_limit']:.2f}%")
        print(f"Maximum line loading: {results[best_bus]['max_loading']:.2f}%")