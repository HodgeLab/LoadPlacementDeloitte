"""
visualization.py - Visualize power system results
"""

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

def plot_network(buses, branches, flow_results=None, highlight_buses=None, title="Power System Network"):
    """
    Plot the power system network with optional flow visualization
    
    Args:
        buses (list): List of bus data
        branches (list): List of branch data
        flow_results (dict, optional): Power flow results
        highlight_buses (list, optional): List of bus IDs to highlight
        title (str): Plot title
    """
    # Create graph
    G = nx.Graph()
    
    # Add nodes (buses)
    bus_types = {1: 'PQ', 2: 'PV', 3: 'Slack'}
    bus_colors = {1: 'lightblue', 2: 'lightgreen', 3: 'orange'}
    
    node_colors = []
    node_sizes = []
    labels = {}
    
    for bus in buses:
        bus_id = int(bus[0])
        bus_type = int(bus[1])
        load = bus[2]  # Active power load
        
        # Set node size based on load
        size = 300 + load * 0.5
        
        # Set color based on bus type, or highlight if specified
        if highlight_buses and bus_id in highlight_buses:
            color = 'red'
        else:
            color = bus_colors[bus_type]
        
        G.add_node(bus_id)
        node_colors.append(color)
        node_sizes.append(size)
        
        # Add label: bus ID and type
        labels[bus_id] = f"{bus_id}\n({bus_types[bus_type]})"
    
    # Add edges (branches)
    edge_widths = []
    edge_colors = []
    
    for branch in branches:
        from_bus = int(branch[0])
        to_bus = int(branch[1])
        limit = branch[5]  # Rate A
        
        G.add_edge(from_bus, to_bus)
        
        # Default edge properties
        width = 1.0
        color = 'black'
        
        # Update based on flow results if provided
        if flow_results:
            for flow in flow_results:
                if (flow['from_bus'] == from_bus and flow['to_bus'] == to_bus) or \
                   (flow['from_bus'] == to_bus and flow['to_bus'] == from_bus):
                    # Set width based on flow magnitude
                    flow_magnitude = abs(flow['flow_mw'])
                    width = 1.0 + 3.0 * flow_magnitude / limit if limit > 0 else 1.0
                    
                    # Set color based on loading percentage
                    loading = flow['loading_percent']
                    if loading < 50:
                        color = 'green'
                    elif loading < 80:
                        color = 'blue'
                    elif loading < 100:
                        color = 'orange'
                    else:
                        color = 'red'
                    
                    break
        
        edge_widths.append(width)
        edge_colors.append(color)
    
    # Create figure
    plt.figure(figsize=(12, 8))
    
    # Draw network
    pos = nx.spring_layout(G, seed=42)  # Position nodes using spring layout
    
    # Draw nodes
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, alpha=0.8)
    
    # Draw edges
    nx.draw_networkx_edges(G, pos, width=edge_widths, edge_color=edge_colors, alpha=0.7)
    
    # Draw labels
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=10)
    
    # Set title and show plot
    plt.title(title)
    plt.axis('off')
    plt.tight_layout()
    plt.show()

def plot_loading_changes(base_results, test_results, bus_id):
    """
    Plot line loading changes after adding load to a specific bus
    
    Args:
        base_results (dict): Base case power flow results
        test_results (dict): Test case power flow results for the specified bus
        bus_id (int): Bus ID where load was added
    """
    # Extract data
    base_flows = base_results['flows']
    test_flows = test_results['test_cases'][bus_id]['loading_changes']
    
    # Create DataFrame for plotting
    data = []
    for change in test_flows:
        line_name = f"{change['from_bus']}-{change['to_bus']}"
        base_loading = change['base_loading']
        new_loading = change['new_loading']
        loading_change = change['change']
        
        data.append({
            'Line': line_name,
            'Base Loading (%)': base_loading,
            'New Loading (%)': new_loading,
            'Change (%)': loading_change
        })
    
    df = pd.DataFrame(data)
    
    # Sort by absolute change
    df = df.sort_values(by='Change (%)', key=abs, ascending=False)
    
    # Create plot
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 8))
    
    # Plot loading comparison
    df.plot(x='Line', y=['Base Loading (%)', 'New Loading (%)'], kind='bar', ax=ax1)
    ax1.set_title(f'Line Loading Comparison (Load Added to Bus {bus_id})')
    ax1.set_ylabel('Loading (%)')
    ax1.set_xlabel('Transmission Line')
    ax1.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Plot changes
    df['Change (%)'].plot(kind='bar', ax=ax2, color=df['Change (%)'].apply(
        lambda x: 'red' if x > 0 else 'green'))
    ax2.set_title(f'Line Loading Changes (Load Added to Bus {bus_id})')
    ax2.set_ylabel('Change in Loading (%)')
    ax2.set_xlabel('Transmission Line')
    ax2.grid(axis='y', linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    plt.show()

def plot_recommendation_results(recommendation_results):
    """
    Plot the results of the bus recommendations
    
    Args:
        recommendation_results (dict): Results from recommend_load_placement function
    """
    ranked_buses = recommendation_results['ranked_buses']
    
    # Create DataFrame
    df = pd.DataFrame(ranked_buses)
    
    # Create figure
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 8))
    
    # Plot scores
    df.plot(x='bus_id', y='score', kind='bar', ax=ax1, color='skyblue')
    ax1.set_title('Bus Scores for Load Placement (Lower is Better)')
    ax1.set_ylabel('Score')
    ax1.set_xlabel('Bus ID')
    ax1.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Plot maximum line loadings
    df.plot(x='bus_id', y='max_line_loading', kind='bar', ax=ax2, color='orange')
    ax2.set_title('Maximum Line Loading for Each Bus Placement')
    ax2.set_ylabel('Maximum Line Loading (%)')
    ax2.set_xlabel('Bus ID')
    ax2.grid(axis='y', linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    plt.show()

def plot_generator_dispatch(unit_commitment_results):
    """
    Plot generator dispatch schedule from unit commitment results
    
    Args:
        unit_commitment_results (dict): Results from unit commitment model
    """
    # Extract data
    gen_schedule = unit_commitment_results['generator_schedule']
    
    # Create a DataFrame for each generator
    dfs = []
    for gen_id, schedule in gen_schedule.items():
        df = pd.DataFrame(schedule)
        df['generator'] = gen_id
        dfs.append(df)
    
    # Combine all generators
    combined_df = pd.concat(dfs)
    
    # Pivot to get generators as columns and time periods as rows
    pivot_df = combined_df.pivot(index='period', columns='generator', values='output_mw')
    
    # Plot
    plt.figure(figsize=(12, 6))
    pivot_df.plot(kind='bar', stacked=True, colormap='viridis')
    plt.title('Generator Dispatch Schedule')
    plt.xlabel('Time Period')
    plt.ylabel('Power Output (MW)')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.legend(title='Generator')
    plt.tight_layout()
    plt.show()