"""
load_testing.py - Test impact of adding new loads at different buses
"""

from grid_data import get_9bus_system, add_new_load
from dc_power_flow import run_dc_power_flow, check_line_violations
from unit_commitment import solve_unit_commitment

def run_load_placement_test(test_buses, new_load_mw=50.0, new_load_mvar=20.0):
    """
    Test the impact of placing a new load at each specified bus
    
    Args:
        test_buses (list): List of bus IDs to test load placement
        new_load_mw (float): Size of new load to add (MW)
        new_load_mvar (float): Reactive component of new load (MVAr)
        
    Returns:
        dict: Test results for each bus
    """
    # Get original system data
    system_data = get_9bus_system()
    base_mva = system_data['base_mva']
    original_buses = system_data['buses']
    branches = system_data['branches']
    generators = system_data['generators']
    
    # Run base case
    base_case_results = run_dc_power_flow(
        original_buses, branches, generators, base_mva
    )
    
    base_violations = check_line_violations(base_case_results['flows'])
    
    # Test each bus
    test_results = {}
    for bus_id in test_buses:
        # Create a copy with new load added to this bus
        modified_buses = add_new_load(
            original_buses, bus_id, new_load_mw, new_load_mvar
        )

        total_load = sum(bus[2] for bus in modified_buses)
        total_gen_capacity = sum(gen[7] for gen in generators if gen[8] == 1)  # Sum of Pmax for in-service generators
        
        gen_capacity_exceeded = total_load > total_gen_capacity

        # Run power flow with modified load
        pf_results = run_dc_power_flow(
            modified_buses, branches, generators, base_mva
        )
        
        
        # Check for violations
        violations = check_line_violations(pf_results['flows'])
        
        # Calculate change in line loadings
        loading_changes = []
        for i, new_flow in enumerate(pf_results['flows']):
            base_flow = base_case_results['flows'][i]
            loading_change = new_flow['loading_percent'] - base_flow['loading_percent']
            
            loading_changes.append({
                'from_bus': new_flow['from_bus'],
                'to_bus': new_flow['to_bus'],
                'base_loading': base_flow['loading_percent'],
                'new_loading': new_flow['loading_percent'],
                'change': loading_change
            })
        
        # Store results
        test_results[bus_id] = {
            'violations': violations,
            'loading_changes': loading_changes,
            'max_loading_change': max([c['change'] for c in loading_changes]),
            'most_affected_line': sorted(loading_changes, key=lambda x: abs(x['change']), reverse=True)[0],
            'gen_capacity_exceeded': gen_capacity_exceeded

        }
    
    return {
        'base_case': {
            'violations': base_violations
        },
        'test_cases': test_results
    }

def recommend_load_placement(test_results, max_loading_threshold=80.0):
    """
    Recommend the best bus for load placement based on test results
    
    Args:
        test_results (dict): Results from load placement tests
        max_loading_threshold (float): Maximum acceptable line loading percentage
        
    Returns:
        dict: Recommendation results with ranked buses
    """
    test_cases = test_results['test_cases']
    
    # Evaluate each bus
    evaluations = []
    for bus_id, results in test_cases.items():
        # Check for violations
        has_violations = len(results['violations']) > 0
        has_gen_capacity_issues = results['gen_capacity_exceeded']

        # Get maximum line loading
        max_loading = max([c['new_loading'] for c in results['loading_changes']])
        
        # Calculate a score (lower is better)
        if has_violations or has_gen_capacity_issues:
            score = 1000  # Penalize heavily for violations
        else:
            # Score based on maximum loading and maximum change
            score = max_loading + abs(results['max_loading_change']) * 2
        
        evaluations.append({
            'bus_id': bus_id,
            'has_violations': has_violations,
            'has_gen_capacity_issues': has_gen_capacity_issues,

            'max_line_loading': max_loading,
            'max_loading_change': results['max_loading_change'],
            'most_affected_line': f"{results['most_affected_line']['from_bus']} to {results['most_affected_line']['to_bus']}",
            'score': score
        })
    
    # Sort by score (lower is better)
    ranked_buses = sorted(evaluations, key=lambda x: x['score'])
    
    # Make recommendation
    if ranked_buses[0]['has_violations']:
        recommendation = "No bus is recommended due to line violations. Consider a smaller load or system upgrades."
    else:
        best_bus = ranked_buses[0]['bus_id']
        recommendation = f"Bus {best_bus} is recommended for the new load placement."
    
    return {
        'ranked_buses': ranked_buses,
        'recommendation': recommendation
    }