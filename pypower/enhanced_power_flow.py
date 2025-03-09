"""
Enhanced script to test load impact on the 9-bus system using both AC and DC power flow
with generator violation checking
"""

import sys
import numpy as np
from pypower.api import case9, runpf, rundcpf, ppoption, case118

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
        
        # Get power flow - handling both AC and DC results
        if 'PF' in ppc_results:  # For DC power flow
            pf = float(ppc_results['branch'][i, ppc_results['PF']])  # Real power flow
            qf = 0  # DC power flow doesn't have reactive power
        else:  # For AC power flow
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

def check_generator_violations(ppc_results, tolerance_mw=1.0):
    """Check if any generators exceed their limits"""
    violations = []
    
    for i in range(ppc_results['gen'].shape[0]):
        bus_id = int(ppc_results['gen'][i, 0]) + 1  # 1-indexed bus number
        output = float(ppc_results['gen'][i, 1])  # PG - active power output
        pmin = float(ppc_results['gen'][i, 9])  # PMIN - minimum output
        pmax = float(ppc_results['gen'][i, 8])  # PMAX - maximum output
        
        # Check for violations
        if output > pmax + tolerance_mw:
            violations.append({
                'bus': bus_id,
                'output': output,
                'limit': pmax,
                'type': 'maximum',
                'excess': output - pmax
            })
        elif output < pmin - tolerance_mw:
            violations.append({
                'bus': bus_id,
                'output': output,
                'limit': pmin,
                'type': 'minimum',
                'deficit': pmin - output
            })
    
    return violations

def test_load_impacts(test_buses, load_mw=50.0, use_dc=False):
    """Test the impact of adding load to different buses"""
    # Get the case
    ppc = case118()
    
    # Run base case
    ppopt = ppoption(VERBOSE=0, OUT_ALL=0)
    
    if use_dc:
        try:
            # Try DC power flow
            base_results, success = rundcpf(ppc, ppopt)
            if not success:
                print("DC power flow did not converge. Falling back to AC.")
                use_dc = False
                base_results, success = runpf(ppc, ppopt)
        except Exception as e:
            print(f"Error running DC power flow: {e}")
            print("Falling back to AC power flow.")
            use_dc = False
            base_results, success = runpf(ppc, ppopt)
    else:
        # Use AC power flow
        base_results, success = runpf(ppc, ppopt)
    
    if not success:
        print("Base case power flow did not converge!")
        return
    
    # Calculate base case loading
    base_loading = calculate_loading(base_results)
    
    # Check generator violations in base case
    base_gen_violations = check_generator_violations(base_results)
    
    # Print base case information
    print(f"==== BASE CASE ({('DC' if use_dc else 'AC')} POWER FLOW) ====")
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
    
    # Print generator information
    print("\nGenerator outputs:")
    for i in range(ppc['gen'].shape[0]):
        bus_id = int(ppc['gen'][i, 0]) + 1
        output = float(ppc['gen'][i, 1])
        pmin = float(ppc['gen'][i, 9])
        pmax = float(ppc['gen'][i, 8])
        print(f"  Gen at Bus {bus_id}: {output:.1f} MW (Min: {pmin:.1f} MW, Max: {pmax:.1f} MW)")
    
    # Print generator violations if any
    if base_gen_violations:
        print("\nBase case generator violations:")
        for v in base_gen_violations:
            if v['type'] == 'maximum':
                print(f"  Gen at Bus {v['bus']}: Exceeds maximum by {v['excess']:.1f} MW")
            else:
                print(f"  Gen at Bus {v['bus']}: Below minimum by {v['deficit']:.1f} MW")
    
    # Test each bus
    print("\n==== TESTING LOAD ADDITIONS ====")
    
    results = {}
    
    for bus_id in test_buses:
        print(f"\nTesting {load_mw} MW load addition at Bus {bus_id}:")
        
        # Add load to this bus
        modified_ppc = add_load(ppc, bus_id, load_mw)
        
        # Run power flow
        if use_dc:
            try:
                mod_results, success = rundcpf(modified_ppc, ppopt)
            except Exception as e:
                print(f"  Error running DC power flow: {e}")
                success = False
        else:
            mod_results, success = runpf(modified_ppc, ppopt)
        
        if not success:
            print("  Power flow did not converge!")
            results[bus_id] = {
                'converged': False,
                'line_violations': None,
                'gen_violations': None,
                'max_loading': None
            }
            continue
        
        # Calculate new loading
        new_loading = calculate_loading(mod_results)
        
        # Check generator violations
        gen_violations = check_generator_violations(mod_results)
        
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
        line_violations = [line for line in new_loading if line['loading_percent'] > 100]
        
        # Print line violation information
        if line_violations:
            print("  LINE VIOLATIONS:")
            for line in line_violations:
                print(f"    Line {line['from_bus']}-{line['to_bus']}: {line['loading_percent']:.1f}%")
        else:
            print("  No line violations")
        
        # Print generator violation information
        if gen_violations:
            print("  GENERATOR VIOLATIONS:")
            for v in gen_violations:
                if v['type'] == 'maximum':
                    print(f"    Gen at Bus {v['bus']}: Exceeds maximum by {v['excess']:.1f} MW")
                else:
                    print(f"    Gen at Bus {v['bus']}: Below minimum by {v['deficit']:.1f} MW")
        else:
            print("  No generator violations")
            
        # Sort by largest change
        biggest_changes = sorted(changes, key=lambda x: abs(x['change']), reverse=True)[:3]
        print("  Most affected lines:")
        for line in biggest_changes:
            print(f"    Line {line['from_bus']}-{line['to_bus']}: " + 
                  f"{line['old_loading']:.1f}% → {line['new_loading']:.1f}% " + 
                  f"(change: {line['change']:+.1f}%)")
        
        # Print recommendation based on maximum loading and violations
        max_loading = max([line['loading_percent'] for line in new_loading])
        
        if line_violations or gen_violations:
            print("  NOT RECOMMENDED - Violations detected")
            recommendation = "Not recommended - violations"
        elif max_loading < 80:
            print("  RECOMMENDED - Good margin")
            recommendation = "Recommended - good margin"
        elif max_loading < 90:
            print("  ACCEPTABLE - Limited margin")
            recommendation = "Acceptable - limited margin"
        else:
            print("  NOT RECOMMENDED - Close to limits")
            recommendation = "Not recommended - close to limits"
        
        # Store results for this bus
        results[bus_id] = {
            'converged': True,
            'line_violations': line_violations,
            'gen_violations': gen_violations,
            'max_loading': max_loading,
            'changes': changes,
            'recommendation': recommendation
        }
    
    # Summarize results
    print("\n==== SUMMARY OF RESULTS ====")
    print("Bus ID | Max Loading | Line Violations | Gen Violations | Recommendation")
    print("-" * 75)
    
    for bus_id, res in results.items():
        if not res['converged']:
            print(f"{bus_id:6d} | {'N/A':11s} | {'N/A':15s} | {'N/A':14s} | Not recommended - did not converge")
            continue
            
        line_v = len(res['line_violations']) if res['line_violations'] else 0
        gen_v = len(res['gen_violations']) if res['gen_violations'] else 0
        
        print(f"{bus_id:6d} | {res['max_loading']:8.1f}% | {line_v:15d} | {gen_v:14d} | {res['recommendation']}")
    
    # Find best bus if any are recommended
    recommended_buses = [bus_id for bus_id, res in results.items() 
                        if res['converged'] and not res['line_violations'] and not res['gen_violations']]
    
    if recommended_buses:
        best_bus = min(recommended_buses, 
                       key=lambda bus_id: results[bus_id]['max_loading'])
        print(f"\nBEST RECOMMENDATION: Bus {best_bus} with maximum loading of {results[best_bus]['max_loading']:.1f}%")
    else:
        print("\nNo buses recommended for this load size. Consider reducing the load.")

if __name__ == "__main__":
    # Get buses to test from command line or use defaults
    if len(sys.argv) > 1:
        try:
            test_buses = [int(b) for b in sys.argv[1].split(',')]
            load_mw = float(sys.argv[2]) if len(sys.argv) > 2 else 50.0
            use_dc = "--dc" in sys.argv or "-d" in sys.argv
        except ValueError:
            print("Usage: python enhanced_power_flow.py [bus1,bus2,...] [load_mw] [--dc]")
            print("Example: python enhanced_power_flow.py 5,7,9 75 --dc")
            sys.exit(1)
    else:
        test_buses = [5, 7, 9]  # Default buses to test
        load_mw = 50.0
        use_dc = False
    
    print(f"Testing {load_mw} MW load addition at buses {test_buses}")
    print(f"Using {'DC' if use_dc else 'AC'} power flow")
    test_load_impacts(test_buses, load_mw, use_dc)