"""
Simple script to test load impact on the 9-bus system using only AC power flow
"""

import sys
import numpy as np
from pypower.api import case9, runpf, ppoption

def add_load(ppc, bus_id, load_mw):
    """Add load to a specific bus"""
    # Create a copy of the case
    import copy
    ppc_mod = copy.deepcopy(ppc)
    
    # Add the load to the specified bus (convert from 1-based to 0-based indexing)
    bus_idx = bus_id - 1
    ppc_mod['bus'][bus_idx, 2] += load_mw
    
    return ppc_mod

def calculate_loading(ppc_results):
    """Calculate line loading percentages"""
    loading = []
    
    # Examine branch flows
    for i in range(ppc_results['branch'].shape[0]):
        from_bus = int(ppc_results['branch'][i, 0]) + 1  # Convert to 1-based
        to_bus = int(ppc_results['branch'][i, 1]) + 1    # Convert to 1-based
        
        # Get apparent power flow (MVA)
        pf = float(ppc_results['branch'][i, 13])  # Real power flow
        qf = float(ppc_results['branch'][i, 14])  # Reactive power flow
        apparent_flow = np.sqrt(pf**2 + qf**2)
        
        # Get line rating
        rating = float(ppc_results['branch'][i, 5])  # RATE_A
        
        # Calculate loading percentage
        loading_percent = 0
        if rating > 0:
            loading_percent = 100.0 * apparent_flow / rating
        
        loading.append({
            'from_bus': from_bus,
            'to_bus': to_bus,
            'flow_mva': apparent_flow,
            'rating_mva': rating,
            'loading_percent': loading_percent
        })
    
    return loading

def test_load_impacts(test_buses, load_mw=50.0):
    """Test the impact of adding load to different buses"""
    # Get the case
    ppc = case9()
    
    # Run base case
    ppopt = ppoption(VERBOSE=0, OUT_ALL=0)
    base_results, success = runpf(ppc, ppopt)
    
    if not success:
        print("Base case power flow did not converge!")
        return
    
    # Calculate base case loading
    base_loading = calculate_loading(base_results)
    
    # Print base case information
    print("==== BASE CASE ====")
    print("Bus loads (MW):")
    for i in range(ppc['bus'].shape[0]):
        bus_id = int(ppc['bus'][i, 0]) + 1
        load = float(ppc['bus'][i, 2])
        if load > 0:
            print(f"  Bus {bus_id}: {load:.1f} MW")
    
    print("\nLine loadings:")
    for line in sorted(base_loading, key=lambda x: x['loading_percent'], reverse=True):
        print(f"  Line {line['from_bus']}-{line['to_bus']}: {line['loading_percent']:.1f}% " + 
              f"({line['flow_mva']:.1f} MVA / {line['rating_mva']:.1f} MVA)")
    
    # Test each bus
    print("\n==== TESTING LOAD ADDITIONS ====")
    for bus_id in test_buses:
        print(f"\nTesting {load_mw} MW load addition at Bus {bus_id}:")
        
        # Add load to this bus
        modified_ppc = add_load(ppc, bus_id, load_mw)
        
        # Run power flow
        mod_results, success = runpf(modified_ppc, ppopt)
        
        if not success:
            print("  Power flow did not converge!")
            continue
        
        # Calculate new loading
        new_loading = calculate_loading(mod_results)
        
        # Calculate changes
        changes = []
        for i, new_line in enumerate(new_loading):
            base_line = base_loading[i]
            change = new_line['loading_percent'] - base_line['loading_percent']
            changes.append({
                'from_bus': new_line['from_bus'],
                'to_bus': new_line['to_bus'],
                'old_loading': base_line['loading_percent'],
                'new_loading': new_line['loading_percent'],
                'change': change
            })
        
        # Check if any lines are overloaded
        violations = [line for line in new_loading if line['loading_percent'] > 100]
        
        if violations:
            print("  OVERLOADED LINES:")
            for line in violations:
                print(f"    Line {line['from_bus']}-{line['to_bus']}: {line['loading_percent']:.1f}%")
            print("  NOT RECOMMENDED - Line violations")
        else:
            print("  NO LINE VIOLATIONS")
            
            # Sort by largest change
            biggest_changes = sorted(changes, key=lambda x: abs(x['change']), reverse=True)[:3]
            print("  Most affected lines:")
            for line in biggest_changes:
                print(f"    Line {line['from_bus']}-{line['to_bus']}: " + 
                      f"{line['old_loading']:.1f}% → {line['new_loading']:.1f}% " + 
                      f"(change: {line['change']:+.1f}%)")
            
            # Print recommendation based on maximum loading
            max_loading = max([line['loading_percent'] for line in new_loading])
            if max_loading < 80:
                print("  RECOMMENDED - Good margin")
            elif max_loading < 90:
                print("  ACCEPTABLE - Limited margin")
            else:
                print("  NOT RECOMMENDED - Close to limits")

if __name__ == "__main__":
    # Get buses to test from command line or use defaults
    if len(sys.argv) > 1:
        test_buses = [int(b) for b in sys.argv[1].split(',')]
        load_mw = float(sys.argv[2]) if len(sys.argv) > 2 else 50.0
    else:
        test_buses = [5, 7, 9]  # Default buses to test
        load_mw = 50.0
    
    print(f"Testing {load_mw} MW load addition at buses {test_buses}")
    test_load_impacts(test_buses, load_mw)