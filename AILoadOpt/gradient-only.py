import numpy as np
import pandas as pd
import pandapower as pp
import pandapower.networks as pn
import copy
from scipy.optimize import minimize

class GradientOptimizer:
    def __init__(self, net, new_load_mva, power_factor=0.9):
        """
        Initialize the gradient-based optimizer for load placement.
        
        Parameters:
        -----------
        net : pandapower.network
            PANDAPOWER network
        new_load_mva : float
            Size of new load in MVA
        power_factor : float, optional
            Power factor of the new load, default is 0.9
        """
        self.original_net = copy.deepcopy(net)
        self.new_load_mva = new_load_mva
        self.power_factor = power_factor
        
        # Convert MVA to MW and MVAr based on power factor
        self.new_load_mw = new_load_mva * power_factor
        self.new_load_mvar = new_load_mva * np.sin(np.arccos(power_factor))
        
        # Get all buses except the slack bus (ext_grid connection point)
        slack_buses = self.original_net.ext_grid.bus.values
        self.candidate_buses = [bus for bus in self.original_net.bus.index if bus not in slack_buses]
        
        # Map to store bus indices for optimization
        self.bus_map = {i: bus for i, bus in enumerate(self.candidate_buses)}
        self.reverse_bus_map = {bus: i for i, bus in enumerate(self.candidate_buses)}
        
        # Store initial evaluations for debugging
        self.evaluations = []
    
    def evaluate_placement(self, x):
        """
        Evaluate a load placement configuration with weights.
        
        Parameters:
        -----------
        x : numpy array
            Vector representing weights for each bus (sums to 1)
            
        Returns:
        --------
        dict
            Results with objective value and constraint violations
        """
        # Create a copy of the original network
        test_net = copy.deepcopy(self.original_net)
        
        # For gradient optimization, we'll use the weights directly
        # This allows the optimizer to explore distributing the load
        total_mw = 0
        total_mvar = 0
        selected_buses = []
        
        # Place loads according to weights
        # If no weights exceed threshold, use the maximum weight regardless
        threshold = 0.01  # Threshold for normal operation
        max_weight_idx = np.argmax(x)
        max_weight = x[max_weight_idx]
        
        # Check if any weights exceed threshold
        if np.max(x) <= threshold:
            # No weights exceed threshold, so just use the maximum weight
            bus = self.bus_map[max_weight_idx]
            pp.create_load(
                test_net,
                bus=bus,
                p_mw=self.new_load_mw,  # Full load
                q_mvar=self.new_load_mvar,
                name=f"Opt Load (max)"
            )
            total_mw = self.new_load_mw
            total_mvar = self.new_load_mvar
            selected_buses.append((bus, 1.0))
        else:
            # Normal operation - place according to weights
            for i, weight in enumerate(x):
                if weight > threshold:
                    bus = self.bus_map[i]
                    bus_mw = self.new_load_mw * weight
                    bus_mvar = self.new_load_mvar * weight
                    
                    pp.create_load(
                        test_net, 
                        bus=bus, 
                        p_mw=bus_mw, 
                        q_mvar=bus_mvar,
                        name=f"Opt Load {i}"
                    )
                    
                    total_mw += bus_mw
                    total_mvar += bus_mvar
                    selected_buses.append((bus, weight))
        
        # Ensure we've placed the full load
        if abs(total_mw - self.new_load_mw) > 0.01 or abs(total_mvar - self.new_load_mvar) > 0.01:
            print(f"Warning: Load placed ({total_mw:.2f} MW, {total_mvar:.2f} MVAr) " 
                  f"differs from target ({self.new_load_mw:.2f} MW, {self.new_load_mvar:.2f} MVAr)")
        
        # Run power flow
        try:
            pp.runpp(test_net, algorithm='nr', max_iteration=100)
            converged = True
        except pp.powerflow.LoadflowNotConverged:
            converged = False
        
        if converged:
            # Get line loading percentages
            if test_net.res_line.empty:
                return {
                    'objective': float('inf'),
                    'converged': True,
                    'max_loading': 0,
                    'violations': 0,
                    'selected_buses': selected_buses
                }
            
            loading = test_net.res_line['loading_percent']
            max_loading = loading.max() if not loading.empty else 0
            
            # Count violations
            violations = sum(1 for l in loading if l > 100)
            
            # Calculate objective: maximize margin to line limits (minimize maximum loading)
            objective = max_loading
            
            # If there are violations, add a penalty
            if violations > 0:
                violation_penalty = 1000 * violations
                objective += violation_penalty
            
            result = {
                'objective': objective,
                'converged': True,
                'max_loading': max_loading,
                'violations': violations,
                'selected_buses': selected_buses
            }
            
            # Store this evaluation for analysis
            self.evaluations.append({
                'weights': x.copy(),
                'objective': objective,
                'max_loading': max_loading,
                'violations': violations
            })
            
            return result
        else:
            # Power flow did not converge - highly penalize this solution
            result = {
                'objective': float('inf'),
                'converged': False,
                'max_loading': float('inf'),
                'violations': float('inf'),
                'selected_buses': selected_buses
            }
            
            # Store this failed evaluation
            self.evaluations.append({
                'weights': x.copy(),
                'objective': float('inf'),
                'max_loading': float('inf'),
                'violations': float('inf'),
                'non_convergence': True
            })
            
            return result
    
    def objective_function(self, x):
        """
        Objective function for optimization.
        
        Parameters:
        -----------
        x : numpy array
            Vector of weights for each bus
            
        Returns:
        --------
        float
            Objective value
        """
        # Print progress periodically
        if len(self.evaluations) % 10 == 0:
            print(f"Evaluation {len(self.evaluations)}: Testing configuration...")
        
        result = self.evaluate_placement(x)
        
        if not result['converged']:
            return 1e6  # Large penalty for non-convergence
        
        return result['objective']
    
    def optimize(self):
        """
        Run gradient-based optimization.
        
        Returns:
        --------
        dict
            Optimization results
        """
        print("\nRunning gradient-based optimization...")
        n_buses = len(self.candidate_buses)
        
        # Initial point - equal distribution across all buses
        x0 = np.ones(n_buses) / n_buses
        
        # Bounds (each element of x between 0 and 1)
        bounds = [(0, 1) for _ in range(n_buses)]
        
        # Constraint: sum of x equals 1
        constraint = {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}
        
        # Run the optimization
        result = minimize(
            self.objective_function,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=constraint,
            options={'maxiter': 100, 'disp': True}
        )
        
        # Get the optimal solution
        x_opt = result.x
        
        # Find the bus with the highest weight
        max_weight_idx = np.argmax(x_opt)
        max_weight = x_opt[max_weight_idx]
        best_bus = self.bus_map[max_weight_idx]
        
        # Print the weight distribution
        print("\nWeight distribution:")
        for i, weight in enumerate(x_opt):
            if weight > 0.01:  # Only show significant weights
                bus = self.bus_map[i]
                bus_name = self.get_bus_name(bus)
                print(f"  Bus {bus} ({bus_name}): {weight:.4f}")
        
        # Final evaluation
        best_x = np.zeros(n_buses)
        best_x[max_weight_idx] = 1.0
        final_eval = self.evaluate_placement(best_x)
        
        # Get bus name
        bus_name = self.get_bus_name(best_bus)
        
        # Prepare results
        optimization_result = {
            'bus': best_bus,
            'bus_name': bus_name,
            'weight': max_weight,
            'objective': final_eval['objective'],
            'max_loading': final_eval['max_loading'],
            'violations': final_eval['violations'],
            'optimization_success': result.success,
            'optimization_message': result.message,
            'evaluations': len(self.evaluations),
            'weights': x_opt,
            'solution_vector': best_x
        }
        
        # Analyze convergence
        if len(self.evaluations) > 1:
            objectives = [e['objective'] for e in self.evaluations if e['objective'] < float('inf')]
            if objectives:
                optimization_result['min_objective'] = min(objectives)
                optimization_result['max_objective'] = max(objectives)
                optimization_result['avg_objective'] = sum(objectives) / len(objectives)
        
        return optimization_result
    
    def get_bus_name(self, bus):
        """Get the name of a bus if available, otherwise return its number."""
        if 'name' in self.original_net.bus.columns and self.original_net.bus.at[bus, 'name']:
            return self.original_net.bus.at[bus, 'name']
        else:
            return f"Bus {bus}"

# Example usage
if __name__ == "__main__":
    # Load the 9-bus test case
    net = pn.case118()
    
    # Define the new load size in MVA
    new_load_mva = 50.0  # Example: 50 MVA
    
    # Create the optimizer
    optimizer = GradientOptimizer(net, new_load_mva)
    
    # Run gradient-based optimization
    gradient_result = optimizer.optimize()
    
    print("\nGradient-Based Optimization Results:")
    print("=" * 50)
    
    # Convert bus name to string to ensure it's subscriptable
    bus_name_str = str(gradient_result['bus_name'])
    
    print(f"Best bus for load placement: {gradient_result['bus']} ({bus_name_str})")
    print(f"Maximum line loading: {gradient_result['max_loading']:.2f}%")
    print(f"Line violations: {gradient_result['violations']}")
    print(f"Optimization success: {gradient_result['optimization_success']}")
    print(f"Optimization message: {gradient_result['optimization_message']}")
    print(f"Total evaluations: {gradient_result['evaluations']}")
    
    # Performance analysis
    if 'min_objective' in gradient_result:
        print("\nPerformance Analysis:")
        print(f"Minimum objective: {gradient_result['min_objective']:.2f}")
        print(f"Maximum objective: {gradient_result['max_objective']:.2f}")
        print(f"Average objective: {gradient_result['avg_objective']:.2f}")
    
    # Print final weight distribution for top buses
    weights = gradient_result['weights']
    indices = np.argsort(weights)[::-1]  # Sort in descending order
    
    print("\nTop 5 buses by weight:")
    print("-" * 50)
    weights_sorted = sorted([(optimizer.bus_map[i], weights[i]) for i in range(len(weights))], 
                           key=lambda x: x[1], reverse=True)
    
    for i in range(min(5, len(weights_sorted))):
        bus, weight = weights_sorted[i]
        bus_name = optimizer.get_bus_name(bus)
        print(f"  Bus {bus} ({bus_name}): {weight:.4f}")