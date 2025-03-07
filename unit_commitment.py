"""
unit_commitment.py - Implementation of a simplified unit commitment model
"""

import numpy as np
import pulp as plp

def solve_unit_commitment(buses, branches, generators, base_mva=100.0, time_periods=24):
    """
    Solve a simplified unit commitment problem
    
    Args:
        buses (list): List of bus data
        branches (list): List of branch data
        generators (list): List of generator data
        base_mva (float): Base MVA for the system
        time_periods (int): Number of time periods to solve for
        
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
    
    # Solve the problem
    status = prob.solve(plp.PULP_CBC_CMD(msg=False))
    
    # Extract results
    results = {
        'status': plp.LpStatus[status],
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