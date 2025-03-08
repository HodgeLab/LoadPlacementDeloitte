"""
grid_data.py - Contains the power system network data
"""

def get_9bus_system():
    """
    Returns the IEEE 9-bus test system data
    
    Returns:
        dict: Dictionary containing buses, branches, generators data
    """
    # Bus data: [bus_id, type, Pd, Qd, Gs, Bs, area, Vm, Va, baseKV, zone, Vmax, Vmin]
    # Type: 1=PQ, 2=PV, 3=Slack
    buses = [
        [1, 3, 0.0, 0.0, 0.0, 0.0, 1, 1.0, 0.0, 345.0, 1, 1.1, 0.9],
        [2, 2, 0.0, 0.0, 0.0, 0.0, 1, 1.0, 0.0, 345.0, 1, 1.1, 0.9],
        [3, 2, 0.0, 0.0, 0.0, 0.0, 1, 1.0, 0.0, 345.0, 1, 1.1, 0.9],
        [4, 1, 0.0, 0.0, 0.0, 0.0, 1, 1.0, 0.0, 345.0, 1, 1.1, 0.9],
        [5, 1, 90.0, 30.0, 0.0, 0.0, 1, 1.0, 0.0, 345.0, 1, 1.1, 0.9],
        [6, 1, 0.0, 0.0, 0.0, 0.0, 1, 1.0, 0.0, 345.0, 1, 1.1, 0.9],
        [7, 1, 100.0, 35.0, 0.0, 0.0, 1, 1.0, 0.0, 345.0, 1, 1.1, 0.9],
        [8, 1, 0.0, 0.0, 0.0, 0.0, 1, 1.0, 0.0, 345.0, 1, 1.1, 0.9],
        [9, 1, 125.0, 50.0, 0.0, 0.0, 1, 1.0, 0.0, 345.0, 1, 1.1, 0.9]
    ]
    
    # Branch data: [from_bus, to_bus, r, x, b, rate_A, rate_B, rate_C, ratio, angle, status, min_angle, max_angle]
    branches = [
        [1, 4, 0.0, 0.0576, 0.0, 250, 250, 250, 0.0, 0.0, 1, -360, 360],
        [4, 5, 0.017, 0.092, 0.158, 250, 250, 250, 0.0, 0.0, 1, -360, 360],
        [5, 6, 0.039, 0.17, 0.358, 150, 150, 150, 0.0, 0.0, 1, -360, 360],
        [3, 6, 0.0, 0.0586, 0.0, 300, 300, 300, 0.0, 0.0, 1, -360, 360],
        [6, 7, 0.0119, 0.1008, 0.209, 150, 150, 150, 0.0, 0.0, 1, -360, 360],
        [7, 8, 0.0085, 0.072, 0.149, 250, 250, 250, 0.0, 0.0, 1, -360, 360],
        [8, 2, 0.0, 0.0625, 0.0, 250, 250, 250, 0.0, 0.0, 1, -360, 360],
        [8, 9, 0.032, 0.161, 0.306, 250, 250, 250, 0.0, 0.0, 1, -360, 360],
        [9, 4, 0.01, 0.085, 0.176, 250, 250, 250, 0.0, 0.0, 1, -360, 360]
    ]
    
    # Generator data: [bus, Pg, Qg, Qmax, Qmin, Vg, mBase, status, Pmax, Pmin, cost_a, cost_b, cost_c]
    generators = [
        [1, 0.0, 0.0, 300, -300, 1.0, 100, 1, 250, 10, 0.11, 5.0, 150],
        [2, 163.0, 0.0, 300, -300, 1.0, 100, 1, 300, 10, 0.085, 1.2, 600],
        [3, 85.0, 0.0, 300, -300, 1.0, 100, 1, 270, 10, 0.1225, 1.0, 335]
    ]
    
    return {
        'buses': buses,
        'branches': branches,
        'generators': generators,
        'base_mva': 100.0
    }

def add_new_load(bus_data, bus_id, new_load_mw, new_load_mvar=0.0):
    """
    Adds a new load to a specific bus
    
    Args:
        bus_data (list): List of bus data
        bus_id (int): Bus ID to add the load to
        new_load_mw (float): Additional active power load (MW)
        new_load_mvar (float): Additional reactive power load (MVAr)
        
    Returns:
        list: Updated bus data with new load
    """
    updated_bus_data = [bus.copy() for bus in bus_data]
    
    for bus in updated_bus_data:
        if bus[0] == bus_id:  # If this is the target bus
            bus[2] += new_load_mw  # Add to active power load (Pd)
            bus[3] += new_load_mvar  # Add to reactive power load (Qd)
            break
            
    return updated_bus_data
