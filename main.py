"""
main_fixed.py - Main script to run the power system analysis with new load testing
Includes improved error handling and solver options
"""

import time
import argparse
import sys
from grid_data import get_9bus_system, add_new_load
from dc_power_flow import run_dc_power_flow, check_line_violations
from unit_commitment import solve_unit_commitment
from load_testing import run_load_placement_test, recommend_load_placement
from visualization import (
    plot_network, 
    plot_loading_changes, 
    plot_recommendation_results,
    plot_generator_dispatch
    )


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Power System Load Analysis')
    parser.add_argument('--load-size', type=float, default=50.0,
                        help='Size of new load to test (MW)')
    parser.add_argument('--reactive-load', type=float, default=20.0,
                        help='Reactive component of new load (MVAr)')
    parser.add_argument('--test-buses', type=str, default='4,5,6,7,8,9',
                        help='Comma-separated list of buses to test load placement')
    parser.add_argument('--solver', type=str, default=None,
                        help='Solver to use for unit commitment (CBC, GLPK, CPLEX, GUROBI, SCIP)')
    parser.add_argument('--skip-uc', action='store_true',
                        help='Skip unit commitment step')
    args = parser.parse_args()
    
    # Parse test buses
    try:
        test_buses = [int(bus) for bus in args.test_buses.split(',')]
    except ValueError:
        print("ERROR: Invalid bus list. Please provide comma-separated integers.")
        return 1
    
    print(f"Running load placement test with {args.load_size} MW load on buses: {test_buses}")
    
    # Get system data
    try:
        system_data = get_9bus_system()
        base_mva = system_data['base_mva']
        buses = system_data['buses']
        branches = system_data['branches']
        generators = system_data['generators']
    except Exception as e:
        print(f"ERROR: Failed to load system data: {str(e)}")
        return 1
    
    # Step 1: Run base case power flow
    try:
        print("\n1. Running base case DC power flow...")
        start_time = time.time()
        base_results = run_dc_power_flow(buses, branches, generators, base_mva)
        print(f"   Completed in {time.time() - start_time:.2f} seconds")
    except Exception as e:
        print(f"ERROR: DC power flow failed: {str(e)}")
        return 1
    
    # Step 2: Run unit commitment for the base case (if not skipped)
    uc_results = None
    if not args.skip_uc:
        try:
            print("\n2. Running unit commitment optimization...")
            start_time = time.time()
            uc_results = solve_unit_commitment(buses, branches, generators, base_mva, solver_name=args.solver)
            print(f"   Completed in {time.time() - start_time:.2f} seconds")
            print(f"   Status: {uc_results['status']}")
            print(f"   Solver: {uc_results.get('solver', 'Unknown')}")
            print(f"   Total cost: {uc_results['objective']:.2f}")
        except Exception as e:
            print(f"WARNING: Unit commitment failed: {str(e)}")
            print("   Continuing analysis without unit commitment results.")
    else:
        print("\n2. Skipping unit commitment optimization (--skip-uc flag used)")
    
    # Step 3: Test load placement at each specified bus
    try:
        print("\n3. Testing load placement at each specified bus...")
        start_time = time.time()
        test_results = run_load_placement_test(
            test_buses, 
            new_load_mw=args.load_size,
            new_load_mvar=args.reactive_load
        )
        print(f"   Completed in {time.time() - start_time:.2f} seconds")
    except Exception as e:
        print(f"ERROR: Load placement test failed: {str(e)}")
        return 1
    
    # Step 4: Analyze results and make recommendations
    try:
        print("\n4. Analyzing results and making recommendations...")
        recommendation = recommend_load_placement(test_results)
        
        # Print recommendation
        print("\n==== RECOMMENDATION ====")
        print(recommendation['recommendation'])
        print("\nRanked buses (lower score is better):")
        for bus in recommendation['ranked_buses']:
            print(f"   Bus {bus['bus_id']}: Score = {bus['score']:.2f}, "
                f"Max Loading = {bus['max_line_loading']:.2f}%, "
                f"Has Violations = {bus['has_violations']}")
        
        # Print detailed results for each bus
        print("\n==== DETAILED RESULTS ====")
        for bus_id in test_buses:
            results = test_results['test_cases'][bus_id]
            violations = results['violations']
            most_affected = results['most_affected_line']
            
            print(f"\nBus {bus_id}:")
            print(f"   Line violations: {len(violations)}")
            print(f"   Max loading change: {results['max_loading_change']:.2f}%")
            print(f"   Most affected line: {most_affected['from_bus']} to {most_affected['to_bus']} "
                f"({most_affected['base_loading']:.2f}% → {most_affected['new_loading']:.2f}%)")
    except Exception as e:
        print(f"ERROR: Result analysis failed: {str(e)}")
        return 1
    
    # Option to display visualizations if available
    show_plots = input("\nDo you want to display visualizations? (y/n): ").lower() == 'y'
    
    if show_plots:
        try:
            # Plot base network
            print("\nPlotting base network...")
            plot_network(buses, branches, base_results['flows'], title="Base Case Network")
            
            # Plot generator dispatch if unit commitment was run
            if uc_results and not args.skip_uc:
                print("Plotting generator dispatch...")
                plot_generator_dispatch(uc_results)
            
            # Plot results for recommended bus
            if not recommendation['ranked_buses'][0]['has_violations']:
                best_bus = recommendation['ranked_buses'][0]['bus_id']
                print(f"Plotting results for recommended bus {best_bus}...")
                plot_loading_changes(base_results, test_results, best_bus)
                
                # Plot network with the new load at the recommended bus
                modified_buses = add_new_load(
                    buses, best_bus, args.load_size, args.reactive_load
                )
                modified_results = run_dc_power_flow(
                    modified_buses, branches, generators, base_mva
                )
                plot_network(
                    modified_buses, 
                    branches, 
                    modified_results['flows'],
                    highlight_buses=[best_bus],
                    title=f"Network with New Load at Bus {best_bus}"
                )
            
            # Plot recommendation results
            print("Plotting recommendation results...")
            plot_recommendation_results(recommendation)
        except Exception as e:
            print(f"WARNING: Visualization failed: {str(e)}")
            print("   Continuing without visualizations.")
    else:
        print("\nVisualizations not available. Install matplotlib, networkx, and pandas to enable.")
    
    print("\nAnalysis completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
