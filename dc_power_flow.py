"""
dc_power_flow.py - Implementation of DC power flow calculations
"""

import numpy as np
from scipy.sparse import csr_matrix, lil_matrix
from scipy.sparse.linalg import spsolve

def build_b_matrix(buses, branches, base_mva=100.0):
    """
    Build the B matrix for DC power flow
    
    Args:
        buses (list): List of bus data
        branches (list): List of branch data
        base_mva (float): Base MVA for the system
        
    Returns:
        tuple: (B matrix, bus indices mapping)
    """
    num_buses = len(buses)
    bus_indices = {}
    
    # Create mapping from bus numbers to indices
    for i, bus in enumerate(buses):
        bus_indices[int(bus[0])] = i
    
    # Create B matrix (susceptance matrix)
    B = lil_matrix((num_buses, num_buses))
    
    # Fill the B matrix
    for branch in branches:
        from_bus = int(branch[0])
        to_bus = int(branch[1])
        x = branch[3]  # Reactance
        status = branch[10]
        
        if status == 1 and x != 0:  # Branch is in service and reactance is not zero
            from_idx = bus_indices[from_bus]
            to_idx = bus_indices[to_bus]
            b = 1.0 / x  # Susceptance
            
            # Update diagonal elements
            B[from_idx, from_idx] += b
            B[to_idx, to_idx] += b
            
            # Update off-diagonal elements
            B[from_idx, to_idx] -= b
            B[to_idx, from_idx] -= b
    
    return B.tocsr(), bus_indices

def run_dc_power_flow(buses, branches, generators, base_mva=100.0):
    """
    Run DC power flow
    
    Args:
        buses (list): List of bus data
        branches (list): List of branch data
        generators (list): List of generator data
        base_mva (float): Base MVA for the system
        
    Returns:
        dict: Power flow results including bus angles, line flows, etc.
    """
    # Build B matrix
    B, bus_indices = build_b_matrix(buses, branches, base_mva)
    num_buses = len(buses)
    
    # Create power injection vector
    P = np.zeros(num_buses)
    
    # Add generation
    for gen in generators:
        if gen[7] == 1:  # Generator is in service
            bus_id = int(gen[0])
            if bus_id in bus_indices:
                P[bus_indices[bus_id]] += gen[1]  # Add Pg
    
    # Subtract load
    for i, bus in enumerate(buses):
        P[i] -= bus[2]  # Subtract Pd
    
    # Normalize by base MVA
    P /= base_mva
    
    # Identify slack bus (type 3)
    slack_buses = [i for i, bus in enumerate(buses) if bus[1] == 3]
    if not slack_buses:
        raise ValueError("No slack bus found in the system")
    
    slack_idx = slack_buses[0]
    
    # Remove slack bus row and column from B matrix
    B_reduced = B.copy()
    B_reduced = B_reduced.tolil()
    
    # Remove slack bus row and column
    mask = np.ones(num_buses, dtype=bool)
    mask[slack_idx] = False
    B_reduced = B_reduced[mask, :][:, mask].tocsr()
    
    # Remove slack bus from power vector
    P_reduced = P[mask]
    
    # Solve for voltage angles: B_reduced * theta = P_reduced
    theta_reduced = spsolve(B_reduced, P_reduced)
    
    # Reconstruct full voltage angle vector
    theta = np.zeros(num_buses)
    theta[mask] = theta_reduced
    
    # Calculate branch flows
    flows = []
    for branch in branches:
        if branch[10] == 1:  # Branch is in service
            from_bus = int(branch[0])
            to_bus = int(branch[1])
            x = branch[3]  # Reactance
            
            if x != 0:
                from_idx = bus_indices[from_bus]
                to_idx = bus_indices[to_bus]
                
                # Flow = (theta_from - theta_to) / x * base_mva
                flow = (theta[from_idx] - theta[to_idx]) / x * base_mva
                
                # Store flow information
                flows.append({
                    'from_bus': from_bus,
                    'to_bus': to_bus,
                    'flow_mw': flow,
                    'limit_mw': branch[5],
                    'loading_percent': abs(flow) / branch[5] * 100 if branch[5] > 0 else 0
                })
    
    # Return results
    return {
        'theta': theta,
        'flows': flows,
        'bus_indices': bus_indices
    }

def check_line_violations(flows, tolerance_percent=100):
    """
    Check for line flow violations
    
    Args:
        flows (list): List of branch flow results
        tolerance_percent (float): Maximum allowed loading percentage
        
    Returns:
        list: List of violated lines
    """
    violations = []
    
    for flow in flows:
        if flow['loading_percent'] > tolerance_percent:
            violations.append({
                'from_bus': flow['from_bus'],
                'to_bus': flow['to_bus'],
                'flow_mw': flow['flow_mw'],
                'limit_mw': flow['limit_mw'],
                'loading_percent': flow['loading_percent']
            })
    
    return violations