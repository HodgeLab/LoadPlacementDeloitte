"""
Simple script to debug PYPOWER issues with rundcpf
"""

import sys
import numpy as np
from pypower.api import case9, rundcpf, runpf, ppoption

def debug_dc_power_flow():
    """Debug the DC power flow issue"""
    print("Loading case9...")
    ppc = case9()
    
    # Print system info
    print(f"System has {ppc['bus'].shape[0]} buses and {ppc['branch'].shape[0]} branches")
    
    # Set options to suppress output
    ppopt = ppoption(VERBOSE=0, OUT_ALL=0)
    
    # Try running AC power flow first (usually more robust)
    print("\nTrying AC power flow...")
    try:
        ac_results, ac_success = runpf(ppc, ppopt)
        print(f"AC power flow {'converged' if ac_success else 'did not converge'}")
    except Exception as e:
        print(f"AC power flow error: {e}")
    
    # Try DC power flow with extra error handling
    print("\nTrying DC power flow...")
    try:
        # Use a different approach for DC power flow to avoid the shape mismatch
        # Some versions of PYPOWER have issues with the branch flow indexing in rundcpf
        
        # Method 1: Direct call with extra error checks
        print("Method 1: Direct call to rundcpf")
        results, success = rundcpf(ppc, ppopt)
        print(f"DC power flow {'converged' if success else 'did not converge'}")
        
        # Print shape of key results to diagnose the issue
        print(f"Branch matrix shape: {results['branch'].shape}")
        print(f"Branch flow column (PF) shape: {np.shape(results['branch'][:, 13])}")
        
    except Exception as e:
        print(f"DC power flow error: {e}")
        print("Exception type:", type(e).__name__)
        
        # Try an alternative approach
        print("\nMethod 2: Using modified indexing")
        try:
            # Create a copy with modified structure
            ppc_mod = case9()
            results, success = rundcpf(ppc_mod, ppopt)
            
            # Extract values more carefully
            branch_flows = np.zeros(results['branch'].shape[0])
            for i in range(results['branch'].shape[0]):
                branch_flows[i] = float(results['branch'][i, 13].item())
                
            print("Successfully extracted flows with manual indexing")
            print(f"First few flows: {branch_flows[:3]}")
            
        except Exception as e2:
            print(f"Alternative approach error: {e2}")
    
    print("\nDebug complete")

if __name__ == "__main__":
    debug_dc_power_flow()