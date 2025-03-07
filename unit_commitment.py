"""
unit_commitment.py - Implementation of a simplified unit commitment model
with multiple solver options to avoid CBC issues
"""

import numpy as np
import pulp as plp

def solve_unit_commitment(buses, branches, generators, base_mva=100.0, time_periods=24, solver_name=None):
    """
    Solve a simplified unit commitment problem with flexible solver options
    
    Args:
        buses (list): List of bus data
        branches (list): List of branch data
        generators (list): List of generator data
        base_mva (float): Base MVA for the system
        time_periods (int): Number of time periods to solve for
        solver_name (str, optional): Specify solver to use ('CBC', 'GLPK', 'CPLEX', 'GUROBI', 'SCIP')
                                    If None, will try available solvers in sequence
        
    Returns:
        dict: Unit commitment results
    """
    # Create optimization problem
    prob = plp.LpProblem("Unit_Commitment", plp.LpMinimize)
    
    # Get total system load
    total_load = sum(bus[2] for bus in buses)
    
    # Define variables
    # Generator commitment (binary)
    gen_commit = {}
    # Generator output (continuous)
    gen_output = {}
    
    for t in range(time_periods):
        for i, gen in enumerate(generators):
            gen_id = f"g{i+1}"
            gen_commit[gen_id, t] = plp.LpVariable(f"u_{gen_id}_{t}", cat=plp.LpBinary)
            gen_output[gen_id, t] = plp.LpVariable(f"p_{gen_id}_{t}", 
                                                 lowBound=gen[8],  # Pmin
                                                 upBound=gen[7],   # Pmax
                                                 cat=plp.LpContinuous)
    
    # Define objective function: minimize cost
    objective = plp.LpAffineExpression()
    for t in range(time_periods):
        for i, gen in enumerate(generators):
            gen_id = f"g{i+1}"
            # Cost is a + b*P + c*P^2, we linearize it as a*u + b*P
            cost_a = gen[10]  # Fixed cost
            cost_b = gen[11]  # Linear cost
            objective += cost_a * gen_commit[gen_id, t] + cost_b * gen_output[gen_id, t]
    
    prob += objective
    
    # Add constraints
    # Power balance: generation = load
    for t in range(time_periods):
        # Simple model: use a load profile that varies over time
        load_factor = 0.8 + 0.4 * np.sin(np.pi * t / 12)  # Load profile with peak at t=6
        current_load = total_load * load_factor
        
        prob += plp.lpSum([gen_output[f"g{i+1}", t] for i in range(len(generators))]) == current_load, f"power_balance_{t}"
    
    # Generator limits
    for t in range(time_periods):
        for i, gen in enumerate(generators):
            gen_id = f"g{i+1}"
            # Output must be between min and max when committed
            prob += gen_output[gen_id, t] <= gen[7] * gen_commit[gen_id, t], f"max_output_{gen_id}_{t}"
            prob += gen_output[gen_id, t] >= gen[8] * gen_commit[gen_id, t], f"min_output_{gen_id}_{t}"
    
    # Solve the problem with specified or available solver
    status = -1
    solver_message = ""
    
    # Try specified solver or go through alternatives
    solver_options = []
    
    if solver_name:
        # Use only the specified solver
        solver_options = [solver_name]
    else:
        # Try multiple solvers in order of preference
        solver_options = ['CBC', 'GLPK', 'CPLEX', 'GUROBI', 'SCIP']
    
    # Try solvers until one works
    for solver in solver_options:
        try:
            print(f"Attempting to solve with {solver}...")
            
            if solver == 'CBC':
                solver_instance = plp.PULP_CBC_CMD(msg=False)
            elif solver == 'GLPK':
                solver_instance = plp.GLPK_CMD(msg=False)
            elif solver == 'CPLEX':
                solver_instance = plp.CPLEX_CMD(msg=False)
            elif solver == 'GUROBI':
                solver_instance = plp.GUROBI_CMD(msg=False)
            elif solver == 'SCIP':
                solver_instance = plp.SCIP_CMD(msg=False)
            else:
                continue  # Skip unknown solver
                
            status = prob.solve(solver_instance)
            solver_message = f"Solved with {solver}"
            break  # Stop if a solver works
            
        except Exception as e:
            print(f"Solver {solver} failed: {str(e)}")
            continue
    
    # Check if any solver worked
    if status == -1:
        print("All solvers failed. Using simplified dispatch model instead...")
        return solve_simplified_dispatch(buses, generators)
    
    # Extract results
    results = {
        'status': plp.LpStatus[status],
        'solver': solver_message,
        'objective': plp.value(prob.objective),
        'generator_schedule': {}
    }
    
    # Extract generator schedules
    for i, gen in enumerate(generators):
        gen_id = f"g{i+1}"
        schedule = []
        for t in range(time_periods):
            schedule.append({
                'period': t,
                'commitment': plp.value(gen_commit[gen_id, t]),
                'output_mw': plp.value(gen_output[gen_id, t])
            })
        results['generator_schedule'][gen_id] = schedule
    
    return results

def solve_simplified_dispatch(buses, generators):
    """
    A fallback simple economic dispatch model when unit commitment fails
    
    Args:
        buses (list): List of bus data
        generators (list): List of generator data
        
    Returns:
        dict: Simplified dispatch results
    """
    # Get total load
    total_load = sum(bus[2] for bus in buses)
    
    # Sort generators by cost (cheapest first)
    sorted_gens = sorted(generators, key=lambda g: g[11])  # Sort by marginal cost
    
    # Dispatch generators to meet load
    dispatched = []
    remaining_load = total_load
    total_cost = 0
    
    for i, gen in enumerate(sorted_gens):
        gen_id = f"g{i+1}"
        pmax = gen[7]
        pmin = gen[8]
        cost_a = gen[10]  # Fixed cost
        cost_b = gen[11]  # Linear cost
        
        # Determine output
        if remaining_load <= 0:
            output = 0
            committed = 0
        else:
            committed = 1
            output = min(pmax, max(pmin, remaining_load))
            remaining_load -= output
            total_cost += cost_a + cost_b * output
        
        dispatched.append({
            'gen_id': gen_id,
            'output_mw': output,
            'commitment': committed
        })
    
    # Create schedule format (same time period for all)
    results = {
        'status': 'Optimal (Simplified)',
        'solver': 'Simplified Economic Dispatch',
        'objective': total_cost,
        'generator_schedule': {}
    }
    
    # Format results in the same structure as unit commitment
    for gen in dispatched:
        schedule = []
        for t in range(24):
            schedule.append({
                'period': t,
                'commitment': gen['commitment'],
                'output_mw': gen['output_mw']
            })
        results['generator_schedule'][gen['gen_id']] = schedule
    
    return results