import numpy as np
from pypower.api import case9

def get_case9():
    """
    Get the IEEE 9-bus test case in PYPOWER format.
    
    Returns:
        dict: PYPOWER case dictionary
    """
    # Get the standard PYPOWER case9
    ppc = case9()
    
    # Return the case
    return ppc

def get_case118():
    """
    Get the IEEE 9-bus test case in PYPOWER format.
    
    Returns:
        dict: PYPOWER case dictionary
    """
    # Get the standard PYPOWER case9
    ppc = case118()
    
    # Return the case
    return ppc


def add_load_to_bus(ppc, bus_id, new_load_mw, new_load_mvar=0.0):
    """
    Add a new load to a specific bus in the PYPOWER case.
    
    Args:
        ppc (dict): PYPOWER case dictionary
        bus_id (int): Bus ID to add the load to (1-indexed)
        new_load_mw (float): Additional active power load (MW)
        new_load_mvar (float): Additional reactive power load (MVAr)
        
    Returns:
        dict: Modified PYPOWER case dictionary
    """
    # Create a deep copy of the case
    import copy
    new_ppc = copy.deepcopy(ppc)
    
    # PYPOWER buses are 0-indexed internally
    bus_idx = bus_id - 1
    
    # Add the new load to the specified bus
    new_ppc['bus'][bus_idx, 2] += new_load_mw
    new_ppc['bus'][bus_idx, 3] += new_load_mvar
    
    return new_ppc