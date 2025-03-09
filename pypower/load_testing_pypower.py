from grid_data_pypower import get_case9, add_load_to_bus, get_case118
from power_flow_pypower import (
    run_dc_power_flow,
    check_line_violations,
    check_generation_limits,
    get_branch_loading
)

def test_new_load_placement(test_buses, new_load_mw=50.0, new_load_mvar=20.0, use_dc=True):
    """
    Test adding a new load at different buses and check system impacts.
    
    Args:
        test_buses (list): List of bus IDs to test (1-indexed)
        new_load_mw (float): Size of new load to add (MW)
        new_load_mvar (float): Size of new load reactive component (MVAr)
        use_dc (bool): Use DC power flow (True) or AC power flow (False)
        
    Returns:
        dict: Test results for each bus
    """
    # Get the base case
    ppc = get_case118()
    
    # Run base case power flow
    if use_dc:
        base_results, base_success = run_dc_power_flow(ppc)
    else:
        from power_flow_pypower import run_ac_power_flow
        base_results, base_success = run_ac_power_flow(ppc)
    
    if not base_success:
        raise RuntimeError("Base case power flow did not converge!")
    
    # Check for any violations in base case
    base_line_violations = check_line_violations(base_results)
    base_gen_violations = check_generation_limits(base_results)
    base_branch_loading = get_branch_loading(base_results)
    
    # Test each bus
    test_results = {}
    
    for bus_id in test_buses:
        # Add new load to this bus
        modified_ppc = add_load_to_bus(ppc, bus_id, new_load_mw, new_load_mvar)
        
        # Run power flow with new load
        try:
            if use_dc:
                mod_results, mod_success = run_dc_power_flow(modified_ppc)
            else:
                from power_flow_pypower import run_ac_power_flow
                mod_results, mod_success = run_ac_power_flow(modified_ppc)
                
            # Check if power flow converged
            if not mod_success:
                test_results[bus_id] = {
                    'converged': False,
                    'message': "Power flow did not converge with new load"
                }
                continue
                
            # Check for violations
            line_violations = check_line_violations(mod_results)
            gen_violations = check_generation_limits(mod_results)
            
            # Get branch loading
            branch_loading = get_branch_loading(mod_results)
            
            # Calculate changes in loading
            loading_changes = []
            
            for i, new_load in enumerate(branch_loading):
                base_load = base_branch_loading[i]
                change = new_load['loading_percent'] - base_load['loading_percent']
                
                loading_changes.append({
                    'from_bus': new_load['from_bus'],
                    'to_bus': new_load['to_bus'],
                    'base_loading': base_load['loading_percent'],
                    'new_loading': new_load['loading_percent'],
                    'change': change
                })
            
            # Find most impacted line
            most_impacted = sorted(loading_changes, key=lambda x: abs(x['change']), reverse=True)[0]
            
            # Store results
            test_results[bus_id] = {
                'converged': True,
                'line_violations': line_violations,
                'gen_violations': gen_violations,
                'loading_changes': loading_changes,
                'most_impacted_line': most_impacted,
                'max_loading_change': most_impacted['change'],
                'max_loading': max([line['new_loading'] for line in loading_changes])
            }
        except Exception as e:
            # Handle any unexpected errors during power flow
            test_results[bus_id] = {
                'converged': False,
                'message': f"Error during power flow: {str(e)}"
            }
    
    return {
        'base_case': {
            'line_violations': base_line_violations,
            'gen_violations': base_gen_violations
        },
        'test_cases': test_results
    }

def recommend_load_placement(test_results, max_loading_threshold=80.0):
    """
    Recommend the best bus for new load placement based on test results.
    
    Args:
        test_results (dict): Results from test_new_load_placement
        max_loading_threshold (float): Maximum acceptable line loading percentage
        
    Returns:
        dict: Recommendation with ranked buses
    """
    test_cases = test_results['test_cases']
    
    # Evaluate each bus
    evaluations = []
    
    for bus_id, results in test_cases.items():
        # Skip buses where power flow didn't converge
        if not results.get('converged', True):
            evaluations.append({
                'bus_id': bus_id,
                'feasible': False,
                'reason': results.get('message', "Power flow did not converge"),
                'score': float('inf')
            })
            continue
        
        # Check for violations
        has_line_violations = len(results['line_violations']) > 0
        has_gen_violations = len(results['gen_violations']) > 0
        
        # Get maximum line loading
        max_loading = results['max_loading']
        
        # Calculate score (lower is better)
        if has_line_violations or has_gen_violations:
            score = 1000  # Heavily penalize violations
            feasible = False
            
            if has_line_violations and has_gen_violations:
                reason = "Line and generator violations"
            elif has_line_violations:
                reason = "Line violations"
            else:
                reason = "Generator violations"
        elif max_loading > max_loading_threshold:
            score = 500 + max_loading  # Penalize high loading
            feasible = False
            reason = f"Line loading exceeds threshold of {max_loading_threshold}%"
        else:
            # Score based on maximum loading and change
            score = max_loading + abs(results['max_loading_change']) * 2
            feasible = True
            reason = "Feasible location"
        
        evaluations.append({
            'bus_id': bus_id,
            'feasible': feasible,
            'reason': reason,
            'max_line_loading': max_loading,
            'max_loading_change': results['max_loading_change'],
            'most_impacted_line': f"{results['most_impacted_line']['from_bus']} to {results['most_impacted_line']['to_bus']}",
            'score': score
        })
    
    # Sort by score (lower is better)
    ranked_buses = sorted(evaluations, key=lambda x: x['score'])
    
    # Make recommendation
    feasible_buses = [bus for bus in ranked_buses if bus['feasible']]
    
    if feasible_buses:
        best_bus = feasible_buses[0]['bus_id']
        recommendation = f"Bus {best_bus} is recommended for the new load placement."
    else:
        recommendation = "No bus is recommended for this load size. Consider reducing the load or upgrading the system."
    
    return {
        'ranked_buses': ranked_buses,
        'recommendation': recommendation,
        'feasible_options': len(feasible_buses)
    }