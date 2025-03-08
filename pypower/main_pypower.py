"""
main_pypower.py - Test the impact of adding a new load to an IEEE 9-bus system using PYPOWER
"""

import argparse
import sys
import time
from load_testing_pypower import test_new_load_placement, recommend_load_placement

def main():
    """Main function to run load placement tests"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Test the impact of adding a new load to the IEEE 9-bus system.'
    )
    parser.add_argument('--load', type=float, default=50.0,
                        help='Size of new load in MW (default: 50.0)')
    parser.add_argument('--reactive', type=float, default=20.0,
                        help='Size of reactive component in MVAr (default: 20.0)')
    parser.add_argument('--buses', type=str, default='5,7,9',
                        help='Comma-separated list of buses to test (default: 5,7,9)')
    parser.add_argument('--dc', action='store_true',
                        help='Use DC power flow instead of AC')
    args = parser.parse_args()
    
    # Parse bus list
    try:
        test_buses = [int(bus) for bus in args.buses.split(',')]
    except ValueError:
        print("ERROR: Bus list must be comma-separated integers")
        return 1
    
    # Print run information
    print(f"Testing {args.load} MW load placement on buses: {test_buses}")
    print(f"Using {'DC' if args.dc else 'AC'} power flow")
    
    # Run the tests
    start_time = time.time()
    test_results = test_new_load_placement(
        test_buses, 
        new_load_mw=args.load,
        new_load_mvar=args.reactive,
        use_dc=args.dc
    )
    elapsed = time.time() - start_time

    
    # Check base case for violations
    base_violations = test_results['base_case']['line_violations']
    if base_violations:
        print("\nWARNING: Base case has line violations:")
        for v in base_violations:
            print(f"  Line {v['from_bus']} to {v['to_bus']}: {v['loading_percent']:.1f}% loaded")
    
    base_gen_violations = test_results['base_case']['gen_violations']
    if base_gen_violations:
        print("\nWARNING: Base case has generator violations:")
        for v in base_gen_violations:
            print(f"  Generator at bus {v['bus']}: {v['output_mw']:.1f} MW (limit: {v['limit_mw']:.1f} MW)")
    
    # Get recommendations
    recommendations = recommend_load_placement(test_results)
    
    # Print recommendations
    print("\n===== LOAD PLACEMENT RECOMMENDATIONS =====")
    print(recommendations['recommendation'])
    print(f"Found {recommendations['feasible_options']} feasible placement options.")
    
    print("\nRanked buses (lower score is better):")
    for i, bus in enumerate(recommendations['ranked_buses']):
        status = "✅ FEASIBLE" if bus['feasible'] else "❌ INFEASIBLE"
        print(f"{i+1}. Bus {bus['bus_id']}: Score {bus['score']:.1f} - {status}")
        print(f"   Reason: {bus['reason']}")
        print(f"   Max line loading: {bus['max_line_loading']:.1f}%")
        print(f"   Most impacted line: {bus['most_impacted_line']}, change: {bus['max_loading_change']:.1f}%")
    
    # Print detailed results for each bus
    print("\n===== DETAILED TEST RESULTS =====")
    for bus_id in test_buses:
        results = test_results['test_cases'][bus_id]
        
        if not results.get('converged', True):
            print(f"\nBus {bus_id}: ❌ Power flow did not converge!")
            continue
        
        line_violations = results['line_violations']
        gen_violations = results['gen_violations']
        most_impacted = results['most_impacted_line']
        
        status = "✅ FEASIBLE" if not (line_violations or gen_violations) else "❌ INFEASIBLE"
        print(f"\nBus {bus_id}: {status}")
        
        # Line violations
        if line_violations:
            print(f"  Line violations: {len(line_violations)}")
            for v in line_violations:
                print(f"    Line {v['from_bus']} to {v['to_bus']}: {v['loading_percent']:.1f}% (limit: {v['limit_mw']:.1f} MW)")
        else:
            print("  Line violations: None")
        
        # Generator violations
        if gen_violations:
            print(f"  Generator violations: {len(gen_violations)}")
            for v in gen_violations:
                print(f"    Generator at bus {v['bus']}: {v['output_mw']:.1f} MW (limit: {v['limit_mw']:.1f} MW)")
        else:
            print("  Generator violations: None")
        
        # Most impacted line
        print(f"  Most impacted line: {most_impacted['from_bus']} to {most_impacted['to_bus']}")
        print(f"    Base loading: {most_impacted['base_loading']:.1f}% → New loading: {most_impacted['new_loading']:.1f}%")
        print(f"    Change: {most_impacted['change']:.1f}%")
    
    print("\nAnalysis completed successfully.")
    return 0

if __name__ == "__main__":
    sys.exit(main())