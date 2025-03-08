from pypower.api import runpf, rundcpf, ppoption
import numpy as np

def run_ac_power_flow(ppc):
    """
    Run AC power flow on a PYPOWER case.
    
    Args:
        ppc (dict): PYPOWER case dictionary
        
    Returns:
        tuple: (result, success flag)
    """
    # Set power flow options
    ppopt = ppoption(VERBOSE=0, OUT_ALL=0)
    
    # Run AC power flow
    results, success = runpf(ppc, ppopt)
    
    return results, success

def run_dc_power_flow(ppc):
    """
    Run DC power flow on a PYPOWER case.
    
    Args:
        ppc (dict): PYPOWER case dictionary
        
    Returns:
        tuple: (result, success flag)
    """
    # Set power flow options
    ppopt = ppoption(VERBOSE=0, OUT_ALL=0)
    
    # Run DC power flow
    results, success = rundcpf(ppc, ppopt)
    
    return results, success

def check_line_violations(ppc_results, tolerance_percent=100):
    """
    Check for transmission line violations in power flow results.
    
    Args:
        ppc_results (dict): PYPOWER results dictionary
        tolerance_percent (float): Maximum allowed loading percentage
        
    Returns:
        list: List of violated lines
    """
    violations = []
    
    # Get branch flows and limits
    branch_flows = np.array(ppc_results['branch'][:, 13]).flatten()  # PF
    branch_rates = np.array(ppc_results['branch'][:, 5]).flatten()   # RATE_A
    
    # Check each branch
    for i in range(len(branch_flows)):
        # Only check branches with non-zero limits
        if branch_rates[i] > 0:
            flow = float(branch_flows[i])
            rate = float(branch_rates[i])
            loading_percent = abs(flow) / rate * 100
            
            if loading_percent > tolerance_percent:
                from_bus = int(ppc_results['branch'][i, 0]) + 1  # Convert to 1-indexed
                to_bus = int(ppc_results['branch'][i, 1]) + 1    # Convert to 1-indexed
                
                violations.append({
                    'from_bus': from_bus,
                    'to_bus': to_bus,
                    'flow_mw': flow,
                    'limit_mw': rate,
                    'loading_percent': loading_percent
                })
    
    return violations

def check_generation_limits(ppc_results, tolerance_mw=1.0):
    """
    Check for generator limit violations in power flow results.
    
    Args:
        ppc_results (dict): PYPOWER results dictionary
        tolerance_mw (float): Tolerance for limit violations in MW
        
    Returns:
        list: List of generators exceeding limits
    """
    violations = []
    
    # Get generator outputs and limits
    gen_outputs = np.array(ppc_results['gen'][:, 1]).flatten()  # PG
    gen_pmins = np.array(ppc_results['gen'][:, 9]).flatten()    # PMIN
    gen_pmaxs = np.array(ppc_results['gen'][:, 8]).flatten()    # PMAX
    
    # Check each generator
    for i in range(len(gen_outputs)):
        # Get bus number (1-indexed)
        bus_id = int(ppc_results['gen'][i, 0]) + 1
        
        output = float(gen_outputs[i])
        pmin = float(gen_pmins[i])
        pmax = float(gen_pmaxs[i])
        
        # Check if exceeding maximum
        if output > pmax + tolerance_mw:
            violations.append({
                'bus': bus_id,
                'output_mw': output,
                'limit_mw': pmax,
                'type': 'maximum',
                'excess_mw': output - pmax
            })
        
        # Check if below minimum
        if output < pmin - tolerance_mw:
            violations.append({
                'bus': bus_id,
                'output_mw': output,
                'limit_mw': pmin,
                'type': 'minimum',
                'deficit_mw': pmin - output
            })
    
    return violations

def get_branch_loading(ppc_results):
    """
    Get loading percentages for all branches.
    
    Args:
        ppc_results (dict): PYPOWER results dictionary
        
    Returns:
        list: List of branch loading information
    """
    branch_loading = []
    
    # Get branch flows and limits
    branch_flows = np.array(ppc_results['branch'][:, 13]).flatten()  # PF
    branch_rates = np.array(ppc_results['branch'][:, 5]).flatten()   # RATE_A
    from_buses = np.array(ppc_results['branch'][:, 0]).flatten()     # F_BUS
    to_buses = np.array(ppc_results['branch'][:, 1]).flatten()       # T_BUS
    
    # Process each branch
    for i in range(len(branch_flows)):
        from_bus = int(from_buses[i]) + 1  # Convert to 1-indexed
        to_bus = int(to_buses[i]) + 1      # Convert to 1-indexed
        
        flow = float(branch_flows[i])
        rate = float(branch_rates[i])
        
        # Calculate loading percentage
        loading_percent = 0
        if rate > 0:
            loading_percent = abs(flow) / rate * 100
        
        branch_loading.append({
            'from_bus': from_bus,
            'to_bus': to_bus,
            'flow_mw': flow,
            'limit_mw': rate,
            'loading_percent': loading_percent
        })
    
    return branch_loading