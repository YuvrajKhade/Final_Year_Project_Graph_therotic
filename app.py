# """
# DISTRIBUTED SCHEDULING ANALYSIS WEB APPLICATION
# Complete Flask Backend with D3.js Animation
# """

# from flask import Flask, request, jsonify, send_file, render_template
# from flask_cors import CORS
# import pandas as pd
# import numpy as np
# import matplotlib
# matplotlib.use('Agg')
# import matplotlib.pyplot as plt
# import networkx as nx
# import os
# import json
# from datetime import datetime
# import traceback
# from werkzeug.utils import secure_filename

# app = Flask(__name__)
# CORS(app)

# # Configuration
# UPLOAD_FOLDER = 'uploads'
# OUTPUT_FOLDER = 'outputs'
# ALLOWED_EXTENSIONS = {'csv'}

# os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
# app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# # Store animation data in memory
# animation_sessions = {}

# # ============================================================================
# # RUNTIME MODELS
# # ============================================================================

# class DistributedParameters:
#     COLOCATED_LATENCY = 1.0
#     COLOCATED_COORDINATOR_QUEUE = 0.05
#     COLOCATED_DATA_COLLECT = 0.1
#     CLOUD_LATENCY = 20.0
#     CLOUD_COORDINATOR_QUEUE = 0.5
#     CLOUD_DATA_COLLECT = 1.0
#     GEO_LATENCY = 100.0
#     GEO_COORDINATOR_QUEUE = 2.0
#     GEO_DATA_COLLECT = 5.0
#     LUBY_PARALLEL_COMPUTE = 2.5
#     LUBY_PARALLEL_SETUP = 1.0
#     LUBY_MESSAGE_LATENCY_FACTOR = 0.5
#     GREEDY_SEQUENTIAL_COMPUTE = 0.5
#     GREEDY_SYNC_OVERHEAD = 0.3
#     GENETIC_GENERATION_TIME = 5.0
#     GENETIC_POPULATION_EVAL = 0.05
#     FIRSTFIT_NODE_TIME = 0.2

# class CompleteRuntimeModel:
#     @staticmethod
#     def luby_distributed(n_nodes, n_rounds, max_degree, latency, queue_time, data_collect):
#         parallel_time = n_rounds * (DistributedParameters.LUBY_PARALLEL_COMPUTE + DistributedParameters.LUBY_PARALLEL_SETUP)
#         message_time = max_degree * np.log2(max(n_nodes, 2)) * latency * DistributedParameters.LUBY_MESSAGE_LATENCY_FACTOR
#         overhead = n_nodes * 0.05
#         return {
#             'total': parallel_time + message_time + overhead,
#             'parallel_time': parallel_time,
#             'message_time': message_time,
#             'overhead': overhead,
#             'coordinator_bottleneck': 0
#         }
    
#     @staticmethod
#     def greedy_centralized(n_nodes, latency, queue_time, data_collect):
#         data_collection_time = n_nodes * data_collect + n_nodes * latency
#         sequential_time = n_nodes * (DistributedParameters.GREEDY_SEQUENTIAL_COMPUTE + DistributedParameters.GREEDY_SYNC_OVERHEAD)
#         coordinator_bottleneck = n_nodes * queue_time * (n_nodes / 10)
#         result_distribution = n_nodes * latency * 0.5
#         return {
#             'total': data_collection_time + sequential_time + coordinator_bottleneck + result_distribution,
#             'coordinator_bottleneck': coordinator_bottleneck
#         }
    
#     @staticmethod
#     def genetic_centralized(n_nodes, generations, population, latency, queue_time, data_collect):
#         data_collection_time = n_nodes * data_collect + n_nodes * latency
#         evolution_time = generations * population * DistributedParameters.GENETIC_POPULATION_EVAL
#         generation_overhead = generations * DistributedParameters.GENETIC_GENERATION_TIME
#         coordinator_bottleneck = (evolution_time + generation_overhead) * 0.3
#         result_distribution = n_nodes * latency * 0.5
#         return {
#             'total': data_collection_time + evolution_time + generation_overhead + coordinator_bottleneck + result_distribution,
#             'coordinator_bottleneck': coordinator_bottleneck
#         }
    
#     @staticmethod
#     def firstfit_centralized(n_nodes, latency, queue_time, data_collect):
#         data_collection_time = n_nodes * data_collect + n_nodes * latency
#         sequential_time = n_nodes * DistributedParameters.FIRSTFIT_NODE_TIME
#         coordinator_bottleneck = n_nodes * queue_time * (n_nodes / 15)
#         result_distribution = n_nodes * latency * 0.5
#         return {
#             'total': data_collection_time + sequential_time + coordinator_bottleneck + result_distribution,
#             'coordinator_bottleneck': coordinator_bottleneck
#         }

# # ============================================================================
# # GRAPH COLORING ALGORITHMS
# # ============================================================================

# def luby_mis_coloring(G):
#     """Luby-MIS algorithm with GUARANTEED complete coloring of all nodes"""
#     n_nodes = G.number_of_nodes()
#     if n_nodes == 0:
#         return {'colors': 0, 'rounds': 0, 'coloring': {}, 'history': []}
    
#     active = set(G.nodes())
#     coloring = {}
#     color = 0
#     total_rounds = 0
#     history = []
    
#     print("=" * 60)
#     print(f"Luby-MIS: {n_nodes} nodes, {G.number_of_edges()} edges")
#     print("=" * 60)
    
#     history.append({
#         'description': f'Initial State: All {n_nodes} tasks as nodes',
#         'active': list(active),
#         'colored': {},
#         'selected': [],
#         'removed': [],
#         'random_values': {}
#     })
    
#     # Main loop: continue until ALL nodes are colored
#     while active:
#         color += 1
#         print(f"COLOR {color}: {len(active)} nodes remaining")
        
#         current_active = active.copy()
#         nodes_colored_in_this_color = set()
#         sub_round = 0
        
#         # For this color, keep finding MIS until current_active is empty
#         while current_active:
#             total_rounds += 1
#             sub_round += 1
            
#             # Assign random priorities
#             random_values = {node: np.random.random() for node in current_active}
            
#             history.append({
#                 'description': f'Time Slot {color}, Round {total_rounds}: Assign random priorities to {len(current_active)} active tasks',
#                 'active': list(current_active),
#                 'colored': {int(k): int(v) for k, v in coloring.items()},
#                 'selected': [],
#                 'removed': [],
#                 'random_values': {int(k): float(v) for k, v in random_values.items()}
#             })
            
#             # Find MIS: nodes with highest priority among their active neighbors
#             mis = set()
#             for node in current_active:
#                 active_neighbors = set(G.neighbors(node)) & current_active
#                 if not active_neighbors:
#                     # Isolated node (no active neighbors) - always select
#                     mis.add(node)
#                 elif all(random_values[node] > random_values[n] for n in active_neighbors):
#                     # Has strictly highest priority among all active neighbors
#                     mis.add(node)
            
#             # Safety: if no MIS found (should be impossible), force select a node
#             if not mis and current_active:
#                 # Pick node with fewest active neighbors
#                 node_degrees = {n: len(set(G.neighbors(n)) & current_active) for n in current_active}
#                 selected = min(node_degrees, key=node_degrees.get)
#                 mis.add(selected)
#                 print(f"WARNING: No MIS at round {sub_round}, forced node {selected}")
            
#             print(f"Sub-round {sub_round}: Selected {len(mis)} nodes")
            
#             history.append({
#                 'description': f'Time Slot {color}, Round {total_rounds}: Select {len(mis)} independent tasks with highest priority',
#                 'active': list(current_active),
#                 'colored': {int(k): int(v) for k, v in coloring.items()},
#                 'selected': list(mis),
#                 'removed': [],
#                 'random_values': {int(k): float(v) for k, v in random_values.items()}
#             })
            
#             # Color all selected nodes with current color
#             for node in mis:
#                 coloring[node] = color
#                 nodes_colored_in_this_color.add(node)
            
#             history.append({
#                 'description': f'Time Slot {color}, Round {total_rounds}: Assign color {color} to {len(mis)} selected tasks',
#                 'active': list(current_active),
#                 'colored': {int(k): int(v) for k, v in coloring.items()},
#                 'selected': list(mis),
#                 'removed': [],
#                 'random_values': {int(k): float(v) for k, v in random_values.items()}
#             })
            
#             # Remove MIS nodes AND their active neighbors
#             to_remove = set(mis)
#             for node in mis:
#                 active_neighbors = set(G.neighbors(node)) & current_active
#                 to_remove.update(active_neighbors)
            
#             history.append({
#                 'description': f'Time Slot {color}, Round {total_rounds}: Remove {len(to_remove)} tasks (colored + conflicts)',
#                 'active': list(current_active),
#                 'colored': {int(k): int(v) for k, v in coloring.items()},
#                 'selected': list(mis),
#                 'removed': list(to_remove),
#                 'random_values': {}
#             })
            
#             current_active -= to_remove
            
#             # Safety: prevent infinite loops
#             if sub_round > n_nodes * 3:
#                 print(f"ERROR: Too many sub-rounds for color {color}, force-coloring remaining")
#                 for node in current_active:
#                     coloring[node] = color
#                     nodes_colored_in_this_color.add(node)
#                 break
        
#         # Update global active set
#         active -= nodes_colored_in_this_color
#         print(f"Color {color} complete: Colored {len(nodes_colored_in_this_color)} nodes, {len(active)} remaining")
        
#         # Safety: prevent infinite colors
#         if color > n_nodes:
#             print(f"ERROR: Used more colors than nodes!")
#             break
    
#     # Final verification
#     uncolored = set(G.nodes()) - set(coloring.keys())
#     if uncolored:
#         print(f"WARNING: {len(uncolored)} nodes uncolored, force-coloring them")
#         for node in uncolored:
#             color += 1
#             coloring[node] = color
    
#     print("=" * 60)
#     print(f"COMPLETE: {len(coloring)}/{n_nodes} nodes in {color} colors, {total_rounds} rounds")
#     print("=" * 60)
    
#     history.append({
#         'description': f'Complete! All {len(coloring)} tasks scheduled in {color} time slots',
#         'active': [],
#         'colored': {int(k): int(v) for k, v in coloring.items()},
#         'selected': [],
#         'removed': [],
#         'random_values': {}
#     })
    
#     return {'colors': color, 'rounds': total_rounds, 'coloring': coloring, 'history': history}

# def greedy_sequential_coloring(G):
#     coloring = {}
#     color_count = 0
#     for node in G.nodes():
#         neighbor_colors = {coloring[n] for n in G.neighbors(node) if n in coloring}
#         color = 1
#         while color in neighbor_colors:
#             color += 1
#         coloring[node] = color
#         color_count = max(color_count, color)
#     return {'colors': color_count, 'rounds': len(G.nodes()), 'coloring': coloring}

# def genetic_algorithm_coloring(G, population_size=30, generations=50):
#     n_nodes = len(G.nodes())
#     max_colors = max(dict(G.degree()).values()) + 1 if n_nodes > 0 else 1
#     population = [{node: np.random.randint(1, max_colors + 1) for node in G.nodes()} for _ in range(population_size)]
    
#     def fitness(coloring):
#         conflicts = sum(1 for edge in G.edges() if coloring[edge[0]] == coloring[edge[1]])
#         return (max(coloring.values()), conflicts)
    
#     def crossover(parent1, parent2):
#         nodes = list(G.nodes())
#         split = len(nodes) // 2
#         return {node: parent1[node] if i < split else parent2[node] for i, node in enumerate(nodes)}
    
#     def mutate(coloring, rate=0.1):
#         for node in G.nodes():
#             if np.random.random() < rate:
#                 coloring[node] = np.random.randint(1, max_colors + 1)
#         return coloring
    
#     for gen in range(generations):
#         fitness_scores = [(fitness(ind), i, ind) for i, ind in enumerate(population)]
#         fitness_scores.sort(key=lambda x: x[0])
#         population = [ind for _, _, ind in fitness_scores[:population_size//2]]
#         while len(population) < population_size:
#             parent1, parent2 = np.random.choice(population, 2, replace=False)
#             child = mutate(crossover(parent1, parent2))
#             population.append(child)
    
#     best_coloring = min(population, key=fitness)
#     return {'colors': max(best_coloring.values()), 'rounds': generations, 'coloring': best_coloring}

# def firstfit_coloring(G):
#     coloring = {}
#     for node in G.nodes():
#         neighbor_colors = {coloring[n] for n in G.neighbors(node) if n in coloring}
#         color = 1
#         while color in neighbor_colors:
#             color += 1
#         coloring[node] = color
#     return {'colors': max(coloring.values()) if coloring else 0, 'rounds': len(G.nodes()), 'coloring': coloring}

# # ============================================================================
# # CONFLICT GRAPH BUILDER
# # ============================================================================

# def build_generic_conflict_graph(df, conflict_rules):
#     """Build conflict graph based on user-defined rules"""
#     G = nx.Graph()
    
#     # Add all nodes
#     for i in range(len(df)):
#         G.add_node(i)
    
#     # Check conflicts between all pairs of tasks
#     for i in range(len(df)):
#         for j in range(i+1, len(df)):
#             has_conflict = False
            
#             # Check each conflict rule
#             for rule in conflict_rules:
#                 rule_type = rule.get('type', '')
                
#                 # Rule 1: Same Value (e.g., same professor, same room)
#                 if rule_type == 'same_value':
#                     col = rule.get('column', '')
#                     if col and col in df.columns:
#                         if pd.notna(df.iloc[i][col]) and pd.notna(df.iloc[j][col]):
#                             if df.iloc[i][col] == df.iloc[j][col]:
#                                 has_conflict = True
#                                 break
                
#                 # Rule 2: Time Overlap (e.g., overlapping time slots)
#                 elif rule_type == 'time_overlap':
#                     # User provides column names like: "time_start,time_end"
#                     col_str = rule.get('column', '')
#                     if ',' in col_str:
#                         cols = [c.strip() for c in col_str.split(',')]
#                         if len(cols) >= 2:
#                             start_col, end_col = cols[0], cols[1]
#                             if start_col in df.columns and end_col in df.columns:
#                                 try:
#                                     # Try to parse as time or numeric
#                                     start_i = df.iloc[i][start_col]
#                                     end_i = df.iloc[i][end_col]
#                                     start_j = df.iloc[j][start_col]
#                                     end_j = df.iloc[j][end_col]
                                    
#                                     # Convert to comparable format
#                                     if isinstance(start_i, str):
#                                         # Try parsing time strings like "9:00" or "09:00:00"
#                                         from datetime import datetime
#                                         try:
#                                             start_i = datetime.strptime(start_i, "%H:%M").time()
#                                             end_i = datetime.strptime(end_i, "%H:%M").time()
#                                             start_j = datetime.strptime(start_j, "%H:%M").time()
#                                             end_j = datetime.strptime(end_j, "%H:%M").time()
#                                         except:
#                                             try:
#                                                 start_i = datetime.strptime(start_i, "%H:%M:%S").time()
#                                                 end_i = datetime.strptime(end_i, "%H:%M:%S").time()
#                                                 start_j = datetime.strptime(start_j, "%H:%M:%S").time()
#                                                 end_j = datetime.strptime(end_j, "%H:%M:%S").time()
#                                             except:
#                                                 # Try as float
#                                                 start_i = float(start_i)
#                                                 end_i = float(end_i)
#                                                 start_j = float(start_j)
#                                                 end_j = float(end_j)
                                    
#                                     # Check overlap: NOT (end_i <= start_j OR end_j <= start_i)
#                                     if not (end_i <= start_j or end_j <= start_i):
#                                         has_conflict = True
#                                         break
#                                 except:
#                                     pass  # Skip if conversion fails
                
#                 # Rule 3: Resource Exceed (e.g., total CPU/memory exceeds limit)
#                 elif rule_type == 'resource_exceed':
#                     # User provides columns like: "cpu,memory" and optional threshold
#                     col_str = rule.get('column', '')
#                     threshold = rule.get('threshold', 100)  # Default threshold
                    
#                     if col_str:
#                         # Parse threshold from column string if provided like "cpu,memory:150"
#                         if ':' in col_str:
#                             parts = col_str.split(':')
#                             col_str = parts[0]
#                             try:
#                                 threshold = float(parts[1])
#                             except:
#                                 pass
                        
#                         cols = [c.strip() for c in col_str.split(',')]
#                         try:
#                             total = 0
#                             for col in cols:
#                                 if col in df.columns:
#                                     val_i = df.iloc[i][col]
#                                     val_j = df.iloc[j][col]
#                                     if pd.notna(val_i) and pd.notna(val_j):
#                                         total += float(val_i) + float(val_j)
                            
#                             if total > threshold:
#                                 has_conflict = True
#                                 break
#                         except:
#                             pass  # Skip if conversion fails
            
#             # Add edge if any rule detected a conflict
#             if has_conflict:
#                 G.add_edge(i, j)
    
#     return G

# def allowed_file(filename):
#     return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# # ============================================================================
# # VISUALIZATION GENERATION
# # ============================================================================

# def generate_visualizations(df, G, session_id):
#     viz_files = []
#     colors_map = {'Luby-MIS': '#2ecc71', 'Greedy Sequential': '#3498db', 
#                   'Genetic Algorithm': '#e74c3c', 'First-Fit': '#f39c12'}
    
#     # VIZ 1: Three Scenarios Comparison
#     fig, axes = plt.subplots(1, 3, figsize=(20, 7))
#     scenarios = df['scenario'].unique()
    
#     scenario_descriptions = {
#         'Co-located Datacenter': 'Same building, low latency (1ms)',
#         'Distributed Cloud': 'Multi-region, medium latency (20ms)',
#         'Geo-distributed Edge': 'Cross-continent, high latency (100ms)'
#     }
    
#     for idx, scenario in enumerate(scenarios):
#         ax = axes[idx]
#         scenario_data = df[df['scenario'] == scenario]
#         avg_data = scenario_data.groupby('algorithm')['runtime_ms'].mean().sort_values(ascending=False)
#         bars = ax.barh(avg_data.index, avg_data.values,
#                       color=[colors_map[a] for a in avg_data.index],
#                       edgecolor='black', linewidth=2)
#         ax.set_xlabel('Average Runtime (ms)', fontweight='bold', fontsize=11)
#         ax.set_title(f'{scenario}\n{scenario_descriptions[scenario]}', 
#                     fontweight='bold', fontsize=12, pad=15)
#         ax.set_xscale('log')
#         ax.grid(axis='x', alpha=0.3, linestyle='--')
#         for bar, val in zip(bars, avg_data.values):
#             ax.text(val * 1.15, bar.get_y() + bar.get_height()/2, 
#                    f'{val:.0f}ms', ha='left', va='center', fontweight='bold', fontsize=10)
    
#     plt.suptitle('Runtime Comparison Across 3 Deployment Scenarios', 
#                 fontsize=18, fontweight='bold', y=0.98)
#     plt.tight_layout()
    
#     filename = f'{session_id}_viz1_scenarios.png'
#     filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
#     plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
#     plt.close()
#     viz_files.append('viz1_scenarios.png')
    
#     # VIZ 2: Scalability
#     fig, axes = plt.subplots(1, 3, figsize=(20, 7))
#     for idx, scenario in enumerate(scenarios):
#         ax = axes[idx]
#         scenario_data = df[df['scenario'] == scenario]
#         for algo in scenario_data['algorithm'].unique():
#             algo_data = scenario_data[scenario_data['algorithm'] == algo]
#             ax.scatter(algo_data['nodes'], algo_data['runtime_ms'],
#                       label=algo, s=150, alpha=0.7, color=colors_map[algo],
#                       edgecolors='black', linewidth=2)
#         ax.set_xlabel('Number of Nodes', fontweight='bold', fontsize=12)
#         ax.set_ylabel('Runtime (ms)', fontweight='bold', fontsize=12)
#         ax.set_title(f'{scenario}\nScalability', fontweight='bold', fontsize=13)
#         ax.legend(fontsize=9, loc='upper left')
#         ax.grid(True, alpha=0.3)
#         ax.set_yscale('log')
    
#     plt.suptitle('Scalability Analysis', fontsize=18, fontweight='bold', y=0.98)
#     plt.tight_layout()
    
#     filename = f'{session_id}_viz2_scalability.png'
#     filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
#     plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
#     plt.close()
#     viz_files.append('viz2_scalability.png')
    
#     # ── VIZ 3: Coordinator Bottleneck ────────────────────────────
#     fig, axes = plt.subplots(1, 3, figsize=(20, 7))
#     for idx, scenario in enumerate(scenarios):
#         ax = axes[idx]
#         scenario_data = df[df['scenario'] == scenario]
#         bottleneck_data = scenario_data.groupby('algorithm')['coordinator_bottleneck'].mean().sort_values(ascending=False)
#         bar_colors = [colors_map[a] for a in bottleneck_data.index]
#         bars = ax.bar(range(len(bottleneck_data)), bottleneck_data.values,
#                       color=bar_colors, edgecolor='white', linewidth=1.5, width=0.6)
#         ax.set_xticks(range(len(bottleneck_data)))
#         ax.set_xticklabels([a.replace(' ', '\n') for a in bottleneck_data.index], fontsize=10)
#         ax.set_ylabel('Bottleneck Delay (ms)', fontweight='bold', fontsize=11)
#         ax.set_title(f'{scenario}', fontweight='bold', fontsize=13)
#         ax.grid(axis='y', alpha=0.3, linestyle='--')
#         for bar, val in zip(bars, bottleneck_data.values):
#             ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(bottleneck_data.values)*0.02,
#                    f'{val:.0f}ms', ha='center', va='bottom', fontweight='bold', fontsize=9)
#         ax.spines['top'].set_visible(False)
#         ax.spines['right'].set_visible(False)
#     plt.suptitle('Coordinator Bottleneck Delay by Scenario\n(Luby-MIS = 0 — No Coordinator Needed)',
#                 fontsize=16, fontweight='bold', y=1.01)
#     plt.tight_layout()
#     filepath = os.path.join(app.config['OUTPUT_FOLDER'], f'{session_id}_viz3_bottleneck.png')
#     plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
#     plt.close()
#     viz_files.append('viz3_bottleneck.png')

#     # ── VIZ 4: Network Latency Impact ────────────────────────────
#     fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))
#     latencies = [1, 20, 100]
#     scenarios_order = ['Co-located Datacenter', 'Distributed Cloud', 'Geo-distributed Edge']
#     for algo in df['algorithm'].unique():
#         rts = [df[(df['scenario']==s) & (df['algorithm']==algo)]['runtime_ms'].mean() for s in scenarios_order]
#         ax1.plot(latencies, rts, 'o-', label=algo, linewidth=2.5, markersize=9,
#                 color=colors_map[algo], markeredgecolor='white', markeredgewidth=1.5)
#     ax1.set_xlabel('Network Latency (ms)', fontweight='bold', fontsize=12)
#     ax1.set_ylabel('Average Runtime (ms)', fontweight='bold', fontsize=12)
#     ax1.set_title('Runtime vs. Network Latency', fontweight='bold', fontsize=13)
#     ax1.legend(fontsize=10); ax1.grid(True, alpha=0.3)
#     ax1.set_xscale('log'); ax1.set_yscale('log')
#     ax1.set_xticks(latencies); ax1.set_xticklabels(['1ms\n(Co-located)', '20ms\n(Cloud)', '100ms\n(Geo)'])
#     ax1.spines['top'].set_visible(False); ax1.spines['right'].set_visible(False)

#     luby_rts = [df[(df['scenario']==s) & (df['algorithm']=='Luby-MIS')]['runtime_ms'].mean() for s in scenarios_order]
#     x = np.arange(len(scenarios_order)); width = 0.25
#     for i, algo in enumerate(['Greedy Sequential', 'Genetic Algorithm', 'First-Fit']):
#         algo_rts = [df[(df['scenario']==s) & (df['algorithm']==algo)]['runtime_ms'].mean() for s in scenarios_order]
#         speedups = [a/l if l > 0 else 1 for a, l in zip(algo_rts, luby_rts)]
#         bars = ax2.bar(x + width*(i-1), speedups, width, label=algo, color=colors_map[algo],
#                       edgecolor='white', linewidth=1)
#         for bar, val in zip(bars, speedups):
#             ax2.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.05, f'{val:.1f}x',
#                     ha='center', va='bottom', fontsize=8, fontweight='bold')
#     ax2.axhline(1, color='#2ecc71', linestyle='--', linewidth=2, alpha=0.8, label='Luby-MIS baseline')
#     ax2.set_xticks(x); ax2.set_xticklabels([s.replace(' ','\n') for s in scenarios_order])
#     ax2.set_ylabel('Slowdown vs Luby-MIS (×)', fontweight='bold', fontsize=12)
#     ax2.set_title('Other Algorithms vs Luby-MIS', fontweight='bold', fontsize=13)
#     ax2.legend(fontsize=9); ax2.grid(axis='y', alpha=0.3)
#     ax2.spines['top'].set_visible(False); ax2.spines['right'].set_visible(False)
#     plt.suptitle('Network Latency Impact Analysis', fontsize=16, fontweight='bold', y=1.01)
#     plt.tight_layout()
#     filepath = os.path.join(app.config['OUTPUT_FOLDER'], f'{session_id}_viz4_latency.png')
#     plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
#     plt.close()
#     viz_files.append('viz4_latency.png')

#     # ── VIZ 5: Architecture Summary Table ───────────────────────
#     fig, ax = plt.subplots(figsize=(14, 7))
#     ax.axis('off')
#     summary = []
#     for algo in df['algorithm'].unique():
#         adata = df[df['algorithm'] == algo]
#         summary.append([
#             algo,
#             adata['architecture'].iloc[0],
#             f"{adata['colors'].mean():.1f}",
#             f"{adata['runtime_ms'].mean():.0f} ms",
#             f"{adata['coordinator_bottleneck'].mean():.0f} ms"
#         ])
#     cols = ['Algorithm', 'Architecture', 'Avg Colors\n(Time Slots)', 'Avg Runtime', 'Coordinator\nBottleneck']
#     table = ax.table(cellText=summary, colLabels=cols, cellLoc='center', loc='center')
#     table.auto_set_font_size(False); table.set_fontsize(12); table.scale(1.2, 2.5)
#     header_color = '#2c3e50'
#     for j in range(len(cols)):
#         table[0, j].set_facecolor(header_color)
#         table[0, j].set_text_props(color='white', fontweight='bold')
#     row_colors = {'Luby-MIS': '#eafaf1', 'Greedy Sequential': '#ebf5fb',
#                   'Genetic Algorithm': '#fdedec', 'First-Fit': '#fef9e7'}
#     for i, row in enumerate(summary):
#         c = row_colors.get(row[0], 'white')
#         for j in range(len(cols)):
#             table[i+1, j].set_facecolor(c)
#     ax.set_title('Algorithm Architecture Summary', fontweight='bold', fontsize=16, pad=20)
#     filepath = os.path.join(app.config['OUTPUT_FOLDER'], f'{session_id}_viz5_architecture.png')
#     plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
#     plt.close()
#     viz_files.append('viz5_architecture.png')

#     # ── VIZ 6: Winners Matrix ────────────────────────────────────
#     fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
#     algorithms_list = list(df['algorithm'].unique())
#     scenarios_list  = list(df['scenario'].unique())

#     quality_mat = np.zeros((len(algorithms_list), len(scenarios_list)))
#     speed_mat   = np.zeros((len(algorithms_list), len(scenarios_list)))

#     for j, scenario in enumerate(scenarios_list):
#         sd = df[df['scenario'] == scenario]
#         best_q = sd.groupby('algorithm')['colors'].mean().min()
#         best_s = sd.groupby('algorithm')['runtime_ms'].mean().min()
#         for i, algo in enumerate(algorithms_list):
#             ad = sd[sd['algorithm'] == algo]
#             if not ad.empty:
#                 if abs(ad['colors'].mean() - best_q) < 0.5:
#                     quality_mat[i, j] = 1
#                 if ad['runtime_ms'].mean() <= best_s * 1.1:
#                     speed_mat[i, j] = 1

#     for ax, mat, title in [(ax1, quality_mat, 'Solution Quality Winners'),
#                             (ax2, speed_mat,   'Runtime Speed Winners')]:
#         ax.imshow(mat, cmap='YlGn', aspect='auto', vmin=0, vmax=1)
#         ax.set_xticks(range(len(scenarios_list)))
#         ax.set_xticklabels([s.replace(' ','\n') for s in scenarios_list], fontsize=10)
#         ax.set_yticks(range(len(algorithms_list)))
#         ax.set_yticklabels(algorithms_list, fontsize=10)
#         ax.set_title(title, fontweight='bold', fontsize=13)
#         for i in range(len(algorithms_list)):
#             for j in range(len(scenarios_list)):
#                 ax.text(j, i, '✓' if mat[i,j] else '✗', ha='center', va='center',
#                        fontsize=20, color='#27ae60' if mat[i,j] else '#e74c3c', fontweight='bold')

#     plt.suptitle('Algorithm Winners Across Deployment Scenarios', fontsize=16, fontweight='bold')
#     plt.tight_layout()
#     filepath = os.path.join(app.config['OUTPUT_FOLDER'], f'{session_id}_viz6_winners.png')
#     plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
#     plt.close()
#     viz_files.append('viz6_winners.png')

#     return viz_files

# # ============================================================================
# # API ROUTES
# # ============================================================================

# @app.route('/')
# def index():
#     return render_template('index.html')

# @app.route('/animation/<session_id>')
# def animation_page(session_id):
#     """Serve animation page - data loaded via API"""
#     return render_template('animation.html')

# @app.route('/api/analyze', methods=['POST'])
# def analyze():
#     try:
#         if 'file' not in request.files:
#             return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        
#         file = request.files['file']
#         if file.filename == '' or not allowed_file(file.filename):
#             return jsonify({'success': False, 'error': 'Invalid file'}), 400
        
#         filename = secure_filename(file.filename)
#         filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#         file.save(filepath)
        
#         df = pd.read_csv(filepath)
#         conflict_rules_json = request.form.get('conflict_rules', '[]')
#         conflict_rules = json.loads(conflict_rules_json)
        
#         G = build_generic_conflict_graph(df, conflict_rules)
#         if G.number_of_nodes() == 0:
#             return jsonify({'success': False, 'error': 'No valid data in dataset'}), 400
        
#         max_degree = max(dict(G.degree()).values()) if G.number_of_nodes() > 0 else 0
        
#         # Run algorithms
#         luby_result = luby_mis_coloring(G)
#         algorithms = {
#             'Luby-MIS': luby_result,
#             'Greedy Sequential': greedy_sequential_coloring(G),
#             'Genetic Algorithm': genetic_algorithm_coloring(G),
#             'First-Fit': firstfit_coloring(G)
#         }
        
#         # Calculate runtimes
#         scenarios = [
#             {'name': 'Co-located Datacenter', 'latency': 1.0, 'queue': 0.05, 'collect': 0.1},
#             {'name': 'Distributed Cloud', 'latency': 20.0, 'queue': 0.5, 'collect': 1.0},
#             {'name': 'Geo-distributed Edge', 'latency': 100.0, 'queue': 2.0, 'collect': 5.0}
#         ]
        
#         results = []
#         for scenario in scenarios:
#             for algo_name, algo_result in algorithms.items():
#                 n_nodes = G.number_of_nodes()
#                 rounds = algo_result['rounds']
#                 colors = algo_result['colors']
                
#                 if algo_name == 'Luby-MIS':
#                     runtime_result = CompleteRuntimeModel.luby_distributed(
#                         n_nodes, rounds, max_degree, scenario['latency'], scenario['queue'], scenario['collect'])
#                     architecture = 'DISTRIBUTED'
#                 elif algo_name == 'Greedy Sequential':
#                     runtime_result = CompleteRuntimeModel.greedy_centralized(
#                         n_nodes, scenario['latency'], scenario['queue'], scenario['collect'])
#                     architecture = 'CENTRALIZED'
#                 elif algo_name == 'Genetic Algorithm':
#                     runtime_result = CompleteRuntimeModel.genetic_centralized(
#                         n_nodes, 50, 30, scenario['latency'], scenario['queue'], scenario['collect'])
#                     architecture = 'CENTRALIZED'
#                 else:
#                     runtime_result = CompleteRuntimeModel.firstfit_centralized(
#                         n_nodes, scenario['latency'], scenario['queue'], scenario['collect'])
#                     architecture = 'CENTRALIZED'
                
#                 results.append({
#                     'scenario': scenario['name'],
#                     'algorithm': algo_name,
#                     'architecture': architecture,
#                     'nodes': n_nodes,
#                     'edges': G.number_of_edges(),
#                     'max_degree': max_degree,
#                     'colors': colors,
#                     'rounds': rounds,
#                     'runtime_ms': runtime_result['total'],
#                     'coordinator_bottleneck': runtime_result.get('coordinator_bottleneck', 0)
#                 })
        
#         session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
#         results_df = pd.DataFrame(results)
#         results_file = os.path.join(app.config['OUTPUT_FOLDER'], f'{session_id}_results.csv')
#         results_df.to_csv(results_file, index=False)
        
#         # Generate visualizations
#         viz_files = generate_visualizations(results_df, G, session_id)
        
#         # Prepare animation data
#         nodes = [{'id': int(node)} for node in G.nodes()]
#         edges = [{'source': int(u), 'target': int(v)} for u, v in G.edges()]
#         animation_data = {
#             'graph': {'nodes': nodes, 'edges': edges},
#             'history': luby_result['history']
#         }
#         animation_sessions[session_id] = animation_data
        
#         return jsonify({
#             'success': True,
#             'session_id': session_id,
#             'summary': {
#                 'nodes': G.number_of_nodes(),
#                 'edges': G.number_of_edges(),
#                 'max_degree': max_degree
#             },
#             'results': results,
#             'visualizations': viz_files
#         })
        
#     except Exception as e:
#         traceback.print_exc()
#         return jsonify({'success': False, 'error': str(e)}), 500

# @app.route('/api/download/<session_id>/<filename>')
# def download_file(session_id, filename):
#     try:
#         filepath = os.path.join(app.config['OUTPUT_FOLDER'], f'{session_id}_{filename}')
#         return send_file(filepath, as_attachment=True)
#     except Exception as e:
#         return jsonify({'error': str(e)}), 404

# @app.route('/api/image/<session_id>/<filename>')
# def get_image(session_id, filename):
#     try:
#         filepath = os.path.join(app.config['OUTPUT_FOLDER'], f'{session_id}_{filename}')
#         return send_file(filepath, mimetype='image/png')
#     except Exception as e:
#         return jsonify({'error': str(e)}), 404

# @app.route('/api/animation/<session_id>')
# def get_animation_data(session_id):
#     """API endpoint to fetch animation data"""
#     try:
#         if session_id in animation_sessions:
#             return jsonify(animation_sessions[session_id])
#         else:
#             return jsonify({'error': 'Animation session not found'}), 404
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

# if __name__ == '__main__':
#     print("🚀 Starting Distributed Scheduling Analysis Server...")
#     print("📊 Open your browser to: http://localhost:5000")
#     app.run(debug=True, host='0.0.0.0', port=5000)

"""
DISTRIBUTED SCHEDULING ANALYSIS WEB APPLICATION
Complete Flask Backend with D3.js Animation
"""

from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import networkx as nx
import os
import json
from datetime import datetime
import traceback
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_EXTENSIONS = {'csv'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Store animation data in memory
animation_sessions = {}

# ============================================================================
# RUNTIME MODELS
# ============================================================================

class DistributedParameters:
    COLOCATED_LATENCY = 1.0
    COLOCATED_COORDINATOR_QUEUE = 0.05
    COLOCATED_DATA_COLLECT = 0.1
    CLOUD_LATENCY = 20.0
    CLOUD_COORDINATOR_QUEUE = 0.5
    CLOUD_DATA_COLLECT = 1.0
    GEO_LATENCY = 100.0
    GEO_COORDINATOR_QUEUE = 2.0
    GEO_DATA_COLLECT = 5.0
    LUBY_PARALLEL_COMPUTE = 2.5
    LUBY_PARALLEL_SETUP = 1.0
    LUBY_MESSAGE_LATENCY_FACTOR = 0.5
    GREEDY_SEQUENTIAL_COMPUTE = 0.5
    GREEDY_SYNC_OVERHEAD = 0.3
    GENETIC_GENERATION_TIME = 5.0
    GENETIC_POPULATION_EVAL = 0.05
    FIRSTFIT_NODE_TIME = 0.2

class CompleteRuntimeModel:
    @staticmethod
    def luby_distributed(n_nodes, n_rounds, max_degree, latency, queue_time, data_collect):
        parallel_time = n_rounds * (DistributedParameters.LUBY_PARALLEL_COMPUTE + DistributedParameters.LUBY_PARALLEL_SETUP)
        message_time = max_degree * np.log2(max(n_nodes, 2)) * latency * DistributedParameters.LUBY_MESSAGE_LATENCY_FACTOR
        overhead = n_nodes * 0.05
        return {
            'total': parallel_time + message_time + overhead,
            'parallel_time': parallel_time,
            'message_time': message_time,
            'overhead': overhead,
            'coordinator_bottleneck': 0
        }
    
    @staticmethod
    def greedy_centralized(n_nodes, latency, queue_time, data_collect):
        data_collection_time = n_nodes * data_collect + n_nodes * latency
        sequential_time = n_nodes * (DistributedParameters.GREEDY_SEQUENTIAL_COMPUTE + DistributedParameters.GREEDY_SYNC_OVERHEAD)
        coordinator_bottleneck = n_nodes * queue_time * (n_nodes / 10)
        result_distribution = n_nodes * latency * 0.5
        return {
            'total': data_collection_time + sequential_time + coordinator_bottleneck + result_distribution,
            'coordinator_bottleneck': coordinator_bottleneck
        }
    
    @staticmethod
    def genetic_centralized(n_nodes, generations, population, latency, queue_time, data_collect):
        data_collection_time = n_nodes * data_collect + n_nodes * latency
        evolution_time = generations * population * DistributedParameters.GENETIC_POPULATION_EVAL
        generation_overhead = generations * DistributedParameters.GENETIC_GENERATION_TIME
        coordinator_bottleneck = (evolution_time + generation_overhead) * 0.3
        result_distribution = n_nodes * latency * 0.5
        return {
            'total': data_collection_time + evolution_time + generation_overhead + coordinator_bottleneck + result_distribution,
            'coordinator_bottleneck': coordinator_bottleneck
        }
    
    @staticmethod
    def firstfit_centralized(n_nodes, latency, queue_time, data_collect):
        data_collection_time = n_nodes * data_collect + n_nodes * latency
        sequential_time = n_nodes * DistributedParameters.FIRSTFIT_NODE_TIME
        coordinator_bottleneck = n_nodes * queue_time * (n_nodes / 15)
        result_distribution = n_nodes * latency * 0.5
        return {
            'total': data_collection_time + sequential_time + coordinator_bottleneck + result_distribution,
            'coordinator_bottleneck': coordinator_bottleneck
        }

# ============================================================================
# GRAPH COLORING ALGORITHMS
# ============================================================================

def luby_mis_coloring(G):
    """Luby-MIS algorithm with GUARANTEED complete coloring of all nodes"""
    n_nodes = G.number_of_nodes()
    if n_nodes == 0:
        return {'colors': 0, 'rounds': 0, 'coloring': {}, 'history': []}
    
    active = set(G.nodes())
    coloring = {}
    color = 0
    total_rounds = 0
    history = []
    
    print("=" * 60)
    print(f"Luby-MIS: {n_nodes} nodes, {G.number_of_edges()} edges")
    print("=" * 60)
    
    history.append({
        'description': f'Initial State: All {n_nodes} tasks as nodes',
        'active': list(active),
        'colored': {},
        'selected': [],
        'removed': [],
        'random_values': {}
    })
    
    # Main loop: continue until ALL nodes are colored
    while active:
        color += 1
        print(f"COLOR {color}: {len(active)} nodes remaining")
        
        current_active = active.copy()
        nodes_colored_in_this_color = set()
        sub_round = 0
        
        # For this color, keep finding MIS until current_active is empty
        while current_active:
            total_rounds += 1
            sub_round += 1
            
            # Assign random priorities
            random_values = {node: np.random.random() for node in current_active}
            
            history.append({
                'description': f'Time Slot {color}, Round {total_rounds}: Assign random priorities to {len(current_active)} active tasks',
                'active': list(current_active),
                'colored': {int(k): int(v) for k, v in coloring.items()},
                'selected': [],
                'removed': [],
                'random_values': {int(k): float(v) for k, v in random_values.items()}
            })
            
            # Find MIS: nodes with highest priority among their active neighbors
            mis = set()
            for node in current_active:
                active_neighbors = set(G.neighbors(node)) & current_active
                if not active_neighbors:
                    # Isolated node (no active neighbors) - always select
                    mis.add(node)
                elif all(random_values[node] > random_values[n] for n in active_neighbors):
                    # Has strictly highest priority among all active neighbors
                    mis.add(node)
            
            # Safety: if no MIS found (should be impossible), force select a node
            if not mis and current_active:
                # Pick node with fewest active neighbors
                node_degrees = {n: len(set(G.neighbors(n)) & current_active) for n in current_active}
                selected = min(node_degrees, key=node_degrees.get)
                mis.add(selected)
                print(f"WARNING: No MIS at round {sub_round}, forced node {selected}")
            
            print(f"Sub-round {sub_round}: Selected {len(mis)} nodes")
            
            history.append({
                'description': f'Time Slot {color}, Round {total_rounds}: Select {len(mis)} independent tasks with highest priority',
                'active': list(current_active),
                'colored': {int(k): int(v) for k, v in coloring.items()},
                'selected': list(mis),
                'removed': [],
                'random_values': {int(k): float(v) for k, v in random_values.items()}
            })
            
            # Color all selected nodes with current color
            for node in mis:
                coloring[node] = color
                nodes_colored_in_this_color.add(node)
            
            history.append({
                'description': f'Time Slot {color}, Round {total_rounds}: Assign color {color} to {len(mis)} selected tasks',
                'active': list(current_active),
                'colored': {int(k): int(v) for k, v in coloring.items()},
                'selected': list(mis),
                'removed': [],
                'random_values': {int(k): float(v) for k, v in random_values.items()}
            })
            
            # Remove MIS nodes AND their active neighbors
            to_remove = set(mis)
            for node in mis:
                active_neighbors = set(G.neighbors(node)) & current_active
                to_remove.update(active_neighbors)
            
            history.append({
                'description': f'Time Slot {color}, Round {total_rounds}: Remove {len(to_remove)} tasks (colored + conflicts)',
                'active': list(current_active),
                'colored': {int(k): int(v) for k, v in coloring.items()},
                'selected': list(mis),
                'removed': list(to_remove),
                'random_values': {}
            })
            
            current_active -= to_remove
            
            # Safety: prevent infinite loops
            if sub_round > n_nodes * 3:
                print(f"ERROR: Too many sub-rounds for color {color}, force-coloring remaining")
                for node in current_active:
                    coloring[node] = color
                    nodes_colored_in_this_color.add(node)
                break
        
        # Update global active set
        active -= nodes_colored_in_this_color
        print(f"Color {color} complete: Colored {len(nodes_colored_in_this_color)} nodes, {len(active)} remaining")
        
        # Safety: prevent infinite colors
        if color > n_nodes:
            print(f"ERROR: Used more colors than nodes!")
            break
    
    # Final verification
    uncolored = set(G.nodes()) - set(coloring.keys())
    if uncolored:
        print(f"WARNING: {len(uncolored)} nodes uncolored, force-coloring them")
        for node in uncolored:
            color += 1
            coloring[node] = color
    
    print("=" * 60)
    print(f"COMPLETE: {len(coloring)}/{n_nodes} nodes in {color} colors, {total_rounds} rounds")
    print("=" * 60)
    
    history.append({
        'description': f'Complete! All {len(coloring)} tasks scheduled in {color} time slots',
        'active': [],
        'colored': {int(k): int(v) for k, v in coloring.items()},
        'selected': [],
        'removed': [],
        'random_values': {}
    })
    
    return {'colors': color, 'rounds': total_rounds, 'coloring': coloring, 'history': history}

def greedy_sequential_coloring(G):
    coloring = {}
    color_count = 0
    for node in G.nodes():
        neighbor_colors = {coloring[n] for n in G.neighbors(node) if n in coloring}
        color = 1
        while color in neighbor_colors:
            color += 1
        coloring[node] = color
        color_count = max(color_count, color)
    return {'colors': color_count, 'rounds': len(G.nodes()), 'coloring': coloring}

def genetic_algorithm_coloring(G, population_size=30, generations=50):
    n_nodes = len(G.nodes())
    max_colors = max(dict(G.degree()).values()) + 1 if n_nodes > 0 else 1
    population = [{node: np.random.randint(1, max_colors + 1) for node in G.nodes()} for _ in range(population_size)]
    
    def fitness(coloring):
        conflicts = sum(1 for edge in G.edges() if coloring[edge[0]] == coloring[edge[1]])
        return (max(coloring.values()), conflicts)
    
    def crossover(parent1, parent2):
        nodes = list(G.nodes())
        split = len(nodes) // 2
        return {node: parent1[node] if i < split else parent2[node] for i, node in enumerate(nodes)}
    
    def mutate(coloring, rate=0.1):
        for node in G.nodes():
            if np.random.random() < rate:
                coloring[node] = np.random.randint(1, max_colors + 1)
        return coloring
    
    for gen in range(generations):
        fitness_scores = [(fitness(ind), i, ind) for i, ind in enumerate(population)]
        fitness_scores.sort(key=lambda x: x[0])
        population = [ind for _, _, ind in fitness_scores[:population_size//2]]
        while len(population) < population_size:
            parent1, parent2 = np.random.choice(population, 2, replace=False)
            child = mutate(crossover(parent1, parent2))
            population.append(child)
    
    best_coloring = min(population, key=fitness)
    return {'colors': max(best_coloring.values()), 'rounds': generations, 'coloring': best_coloring}

def firstfit_coloring(G):
    coloring = {}
    for node in G.nodes():
        neighbor_colors = {coloring[n] for n in G.neighbors(node) if n in coloring}
        color = 1
        while color in neighbor_colors:
            color += 1
        coloring[node] = color
    return {'colors': max(coloring.values()) if coloring else 0, 'rounds': len(G.nodes()), 'coloring': coloring}

# ============================================================================
# CONFLICT GRAPH BUILDER
# ============================================================================

def build_generic_conflict_graph(df, conflict_rules):
    """Build conflict graph based on user-defined rules"""
    G = nx.Graph()
    
    # Add all nodes
    for i in range(len(df)):
        G.add_node(i)
    
    # Check conflicts between all pairs of tasks
    for i in range(len(df)):
        for j in range(i+1, len(df)):
            has_conflict = False
            
            # Check each conflict rule
            for rule in conflict_rules:
                rule_type = rule.get('type', '')
                
                # Rule 1: Same Value (e.g., same professor, same room)
                if rule_type == 'same_value':
                    col = rule.get('column', '')
                    if col and col in df.columns:
                        if pd.notna(df.iloc[i][col]) and pd.notna(df.iloc[j][col]):
                            if df.iloc[i][col] == df.iloc[j][col]:
                                has_conflict = True
                                break
                
                # Rule 2: Time Overlap (e.g., overlapping time slots)
                elif rule_type == 'time_overlap':
                    # User provides column names like: "time_start,time_end"
                    col_str = rule.get('column', '')
                    if ',' in col_str:
                        cols = [c.strip() for c in col_str.split(',')]
                        if len(cols) >= 2:
                            start_col, end_col = cols[0], cols[1]
                            if start_col in df.columns and end_col in df.columns:
                                try:
                                    start_i = df.iloc[i][start_col]
                                    end_i = df.iloc[i][end_col]
                                    start_j = df.iloc[j][start_col]
                                    end_j = df.iloc[j][end_col]
                                    
                                    # Skip if any value is NaN
                                    if pd.isna(start_i) or pd.isna(end_i) or pd.isna(start_j) or pd.isna(end_j):
                                        continue
                                    
                                    # Convert to comparable format
                                    def parse_time(val):
                                        """Parse time string to seconds since midnight"""
                                        if isinstance(val, (int, float)):
                                            return float(val)
                                        
                                        val_str = str(val).strip()
                                        
                                        # Handle HH:MM:SS or HH:MM format
                                        if ':' in val_str:
                                            parts = val_str.split(':')
                                            hours = int(parts[0])
                                            minutes = int(parts[1])
                                            seconds = int(parts[2]) if len(parts) > 2 else 0
                                            return hours * 3600 + minutes * 60 + seconds
                                        
                                        # Handle numeric
                                        return float(val_str)
                                    
                                    # Convert all to seconds
                                    start_i_sec = parse_time(start_i)
                                    end_i_sec = parse_time(end_i)
                                    start_j_sec = parse_time(start_j)
                                    end_j_sec = parse_time(end_j)
                                    
                                    # Check overlap: NOT (end_i <= start_j OR end_j <= start_i)
                                    if not (end_i_sec <= start_j_sec or end_j_sec <= start_i_sec):
                                        has_conflict = True
                                        break
                                except Exception as e:
                                    print(f"    Warning: Time overlap check failed for tasks {i},{j}: {e}")
                                    pass
                
                # Rule 3: Resource Exceed (e.g., total CPU/memory exceeds limit)
                elif rule_type == 'resource_exceed':
                    # User provides columns like: "cpu,memory" and optional threshold
                    col_str = rule.get('column', '')
                    threshold = rule.get('threshold', 100)  # Default threshold
                    
                    if col_str:
                        # Parse threshold from column string if provided like "cpu,memory:150"
                        if ':' in col_str:
                            parts = col_str.split(':')
                            col_str = parts[0]
                            try:
                                threshold = float(parts[1])
                            except:
                                pass
                        
                        cols = [c.strip() for c in col_str.split(',')]
                        try:
                            total = 0
                            for col in cols:
                                if col in df.columns:
                                    val_i = df.iloc[i][col]
                                    val_j = df.iloc[j][col]
                                    if pd.notna(val_i) and pd.notna(val_j):
                                        total += float(val_i) + float(val_j)
                            
                            if total > threshold:
                                has_conflict = True
                                break
                        except:
                            pass  # Skip if conversion fails
            
            # Add edge if any rule detected a conflict
            if has_conflict:
                G.add_edge(i, j)
    
    return G

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ============================================================================
# VISUALIZATION GENERATION
# ============================================================================

def generate_visualizations(df, G, session_id):
    viz_files = []
    colors_map = {'Luby-MIS': '#2ecc71', 'Greedy Sequential': '#3498db', 
                  'Genetic Algorithm': '#e74c3c', 'First-Fit': '#f39c12'}
    
    # VIZ 1: Three Scenarios Comparison
    fig, axes = plt.subplots(1, 3, figsize=(20, 7))
    scenarios = df['scenario'].unique()
    
    scenario_descriptions = {
        'Co-located Datacenter': 'Same building, low latency (1ms)',
        'Distributed Cloud': 'Multi-region, medium latency (20ms)',
        'Geo-distributed Edge': 'Cross-continent, high latency (100ms)'
    }
    
    for idx, scenario in enumerate(scenarios):
        ax = axes[idx]
        scenario_data = df[df['scenario'] == scenario]
        avg_data = scenario_data.groupby('algorithm')['runtime_ms'].mean().sort_values(ascending=False)
        bars = ax.barh(avg_data.index, avg_data.values,
                      color=[colors_map[a] for a in avg_data.index],
                      edgecolor='black', linewidth=2)
        ax.set_xlabel('Average Runtime (ms)', fontweight='bold', fontsize=11)
        ax.set_title(f'{scenario}\n{scenario_descriptions[scenario]}', 
                    fontweight='bold', fontsize=12, pad=15)
        ax.set_xscale('log')
        ax.grid(axis='x', alpha=0.3, linestyle='--')
        for bar, val in zip(bars, avg_data.values):
            ax.text(val * 1.15, bar.get_y() + bar.get_height()/2, 
                   f'{val:.0f}ms', ha='left', va='center', fontweight='bold', fontsize=10)
    
    plt.suptitle('Runtime Comparison Across 3 Deployment Scenarios', 
                fontsize=18, fontweight='bold', y=0.98)
    plt.tight_layout()
    
    filename = f'{session_id}_viz1_scenarios.png'
    filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    viz_files.append('viz1_scenarios.png')
    
    # VIZ 2: Scalability
    fig, axes = plt.subplots(1, 3, figsize=(20, 7))
    for idx, scenario in enumerate(scenarios):
        ax = axes[idx]
        scenario_data = df[df['scenario'] == scenario]
        for algo in scenario_data['algorithm'].unique():
            algo_data = scenario_data[scenario_data['algorithm'] == algo]
            ax.scatter(algo_data['nodes'], algo_data['runtime_ms'],
                      label=algo, s=150, alpha=0.7, color=colors_map[algo],
                      edgecolors='black', linewidth=2)
        ax.set_xlabel('Number of Nodes', fontweight='bold', fontsize=12)
        ax.set_ylabel('Runtime (ms)', fontweight='bold', fontsize=12)
        ax.set_title(f'{scenario}\nScalability', fontweight='bold', fontsize=13)
        ax.legend(fontsize=9, loc='upper left')
        ax.grid(True, alpha=0.3)
        ax.set_yscale('log')
    
    plt.suptitle('Scalability Analysis', fontsize=18, fontweight='bold', y=0.98)
    plt.tight_layout()
    
    filename = f'{session_id}_viz2_scalability.png'
    filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    viz_files.append('viz2_scalability.png')
    
    # ── VIZ 3: Coordinator Bottleneck ────────────────────────────
    fig, axes = plt.subplots(1, 3, figsize=(20, 7))
    for idx, scenario in enumerate(scenarios):
        ax = axes[idx]
        scenario_data = df[df['scenario'] == scenario]
        bottleneck_data = scenario_data.groupby('algorithm')['coordinator_bottleneck'].mean().sort_values(ascending=False)
        bar_colors = [colors_map[a] for a in bottleneck_data.index]
        bars = ax.bar(range(len(bottleneck_data)), bottleneck_data.values,
                      color=bar_colors, edgecolor='white', linewidth=1.5, width=0.6)
        ax.set_xticks(range(len(bottleneck_data)))
        ax.set_xticklabels([a.replace(' ', '\n') for a in bottleneck_data.index], fontsize=10)
        ax.set_ylabel('Bottleneck Delay (ms)', fontweight='bold', fontsize=11)
        ax.set_title(f'{scenario}', fontweight='bold', fontsize=13)
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        for bar, val in zip(bars, bottleneck_data.values):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(bottleneck_data.values)*0.02,
                   f'{val:.0f}ms', ha='center', va='bottom', fontweight='bold', fontsize=9)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
    plt.suptitle('Coordinator Bottleneck Delay by Scenario\n(Luby-MIS = 0 — No Coordinator Needed)',
                fontsize=16, fontweight='bold', y=1.01)
    plt.tight_layout()
    filepath = os.path.join(app.config['OUTPUT_FOLDER'], f'{session_id}_viz3_bottleneck.png')
    plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    viz_files.append('viz3_bottleneck.png')

    # ── VIZ 4: Network Latency Impact ────────────────────────────
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))
    latencies = [1, 20, 100]
    scenarios_order = ['Co-located Datacenter', 'Distributed Cloud', 'Geo-distributed Edge']
    for algo in df['algorithm'].unique():
        rts = [df[(df['scenario']==s) & (df['algorithm']==algo)]['runtime_ms'].mean() for s in scenarios_order]
        ax1.plot(latencies, rts, 'o-', label=algo, linewidth=2.5, markersize=9,
                color=colors_map[algo], markeredgecolor='white', markeredgewidth=1.5)
    ax1.set_xlabel('Network Latency (ms)', fontweight='bold', fontsize=12)
    ax1.set_ylabel('Average Runtime (ms)', fontweight='bold', fontsize=12)
    ax1.set_title('Runtime vs. Network Latency', fontweight='bold', fontsize=13)
    ax1.legend(fontsize=10); ax1.grid(True, alpha=0.3)
    ax1.set_xscale('log'); ax1.set_yscale('log')
    ax1.set_xticks(latencies); ax1.set_xticklabels(['1ms\n(Co-located)', '20ms\n(Cloud)', '100ms\n(Geo)'])
    ax1.spines['top'].set_visible(False); ax1.spines['right'].set_visible(False)

    luby_rts = [df[(df['scenario']==s) & (df['algorithm']=='Luby-MIS')]['runtime_ms'].mean() for s in scenarios_order]
    x = np.arange(len(scenarios_order)); width = 0.25
    for i, algo in enumerate(['Greedy Sequential', 'Genetic Algorithm', 'First-Fit']):
        algo_rts = [df[(df['scenario']==s) & (df['algorithm']==algo)]['runtime_ms'].mean() for s in scenarios_order]
        speedups = [a/l if l > 0 else 1 for a, l in zip(algo_rts, luby_rts)]
        bars = ax2.bar(x + width*(i-1), speedups, width, label=algo, color=colors_map[algo],
                      edgecolor='white', linewidth=1)
        for bar, val in zip(bars, speedups):
            ax2.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.05, f'{val:.1f}x',
                    ha='center', va='bottom', fontsize=8, fontweight='bold')
    ax2.axhline(1, color='#2ecc71', linestyle='--', linewidth=2, alpha=0.8, label='Luby-MIS baseline')
    ax2.set_xticks(x); ax2.set_xticklabels([s.replace(' ','\n') for s in scenarios_order])
    ax2.set_ylabel('Slowdown vs Luby-MIS (×)', fontweight='bold', fontsize=12)
    ax2.set_title('Other Algorithms vs Luby-MIS', fontweight='bold', fontsize=13)
    ax2.legend(fontsize=9); ax2.grid(axis='y', alpha=0.3)
    ax2.spines['top'].set_visible(False); ax2.spines['right'].set_visible(False)
    plt.suptitle('Network Latency Impact Analysis', fontsize=16, fontweight='bold', y=1.01)
    plt.tight_layout()
    filepath = os.path.join(app.config['OUTPUT_FOLDER'], f'{session_id}_viz4_latency.png')
    plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    viz_files.append('viz4_latency.png')

    # ── VIZ 5: Architecture Summary Table ───────────────────────
    fig, ax = plt.subplots(figsize=(14, 7))
    ax.axis('off')
    summary = []
    for algo in df['algorithm'].unique():
        adata = df[df['algorithm'] == algo]
        summary.append([
            algo,
            adata['architecture'].iloc[0],
            f"{adata['colors'].mean():.1f}",
            f"{adata['runtime_ms'].mean():.0f} ms",
            f"{adata['coordinator_bottleneck'].mean():.0f} ms"
        ])
    cols = ['Algorithm', 'Architecture', 'Avg Colors\n(Time Slots)', 'Avg Runtime', 'Coordinator\nBottleneck']
    table = ax.table(cellText=summary, colLabels=cols, cellLoc='center', loc='center')
    table.auto_set_font_size(False); table.set_fontsize(12); table.scale(1.2, 2.5)
    header_color = '#2c3e50'
    for j in range(len(cols)):
        table[0, j].set_facecolor(header_color)
        table[0, j].set_text_props(color='white', fontweight='bold')
    row_colors = {'Luby-MIS': '#eafaf1', 'Greedy Sequential': '#ebf5fb',
                  'Genetic Algorithm': '#fdedec', 'First-Fit': '#fef9e7'}
    for i, row in enumerate(summary):
        c = row_colors.get(row[0], 'white')
        for j in range(len(cols)):
            table[i+1, j].set_facecolor(c)
    ax.set_title('Algorithm Architecture Summary', fontweight='bold', fontsize=16, pad=20)
    filepath = os.path.join(app.config['OUTPUT_FOLDER'], f'{session_id}_viz5_architecture.png')
    plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    viz_files.append('viz5_architecture.png')

    # ── VIZ 6: Winners Matrix ────────────────────────────────────
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    algorithms_list = list(df['algorithm'].unique())
    scenarios_list  = list(df['scenario'].unique())

    quality_mat = np.zeros((len(algorithms_list), len(scenarios_list)))
    speed_mat   = np.zeros((len(algorithms_list), len(scenarios_list)))

    for j, scenario in enumerate(scenarios_list):
        sd = df[df['scenario'] == scenario]
        best_q = sd.groupby('algorithm')['colors'].mean().min()
        best_s = sd.groupby('algorithm')['runtime_ms'].mean().min()
        for i, algo in enumerate(algorithms_list):
            ad = sd[sd['algorithm'] == algo]
            if not ad.empty:
                if abs(ad['colors'].mean() - best_q) < 0.5:
                    quality_mat[i, j] = 1
                if ad['runtime_ms'].mean() <= best_s * 1.1:
                    speed_mat[i, j] = 1

    for ax, mat, title in [(ax1, quality_mat, 'Solution Quality Winners'),
                            (ax2, speed_mat,   'Runtime Speed Winners')]:
        ax.imshow(mat, cmap='YlGn', aspect='auto', vmin=0, vmax=1)
        ax.set_xticks(range(len(scenarios_list)))
        ax.set_xticklabels([s.replace(' ','\n') for s in scenarios_list], fontsize=10)
        ax.set_yticks(range(len(algorithms_list)))
        ax.set_yticklabels(algorithms_list, fontsize=10)
        ax.set_title(title, fontweight='bold', fontsize=13)
        for i in range(len(algorithms_list)):
            for j in range(len(scenarios_list)):
                ax.text(j, i, '✓' if mat[i,j] else '✗', ha='center', va='center',
                       fontsize=20, color='#27ae60' if mat[i,j] else '#e74c3c', fontweight='bold')

    plt.suptitle('Algorithm Winners Across Deployment Scenarios', fontsize=16, fontweight='bold')
    plt.tight_layout()
    filepath = os.path.join(app.config['OUTPUT_FOLDER'], f'{session_id}_viz6_winners.png')
    plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    viz_files.append('viz6_winners.png')

    return viz_files

# ============================================================================
# CSV PREPROCESSING
# ============================================================================

def preprocess_csv(df):
    """Clean and preprocess CSV data to handle invalid formats"""
    import re
    from datetime import datetime, time
    
    print("\nPreprocessing CSV...")
    
    # Make a copy to avoid modifying original
    df = df.copy()
    
    # 1. Replace #### with empty values
    df = df.replace('####', np.nan)
    df = df.replace('#####', np.nan)
    df = df.replace('######', np.nan)
    df = df.replace('#VALUE!', np.nan)
    df = df.replace('#REF!', np.nan)
    df = df.replace('#DIV/0!', np.nan)
    
    # 2. Clean each column
    for col in df.columns:
        print(f"  Cleaning column: {col}")
        
        # Skip if all NaN
        if df[col].isna().all():
            print(f"    → All NaN, skipping")
            continue
        
        # Get sample of non-null values
        sample = df[col].dropna().astype(str).head(20)
        if len(sample) == 0:
            continue
        
        # Check if column looks like time (HH:MM or HH:MM:SS)
        time_pattern = r'^\d{1,2}:\d{2}(:\d{2})?$'
        if sample.str.match(time_pattern).sum() > len(sample) * 0.5:  # More than 50% match
            print(f"    → Detected as TIME column")
            df[col] = df[col].apply(clean_time_value)
            continue
        
        # Check if column looks like date
        date_indicators = sample.str.contains(r'\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{4}/\d{2}/\d{2}', na=False)
        if date_indicators.sum() > len(sample) * 0.3:  # More than 30% match
            print(f"    → Detected as DATE column")
            df[col] = df[col].apply(clean_date_value)
            # Keep as string, don't try to convert to numeric
            continue
        
        # Check if column is numeric (but not dates that look like numbers)
        # Try to convert to numeric - if it fails for most values, it's probably text
        try:
            numeric_conversion = pd.to_numeric(df[col], errors='coerce')
            non_null_count = df[col].notna().sum()
            converted_count = numeric_conversion.notna().sum()
            
            # If more than 70% successfully converted, treat as numeric
            if converted_count > non_null_count * 0.7:
                print(f"    → Numeric column ({converted_count}/{non_null_count} converted)")
                df[col] = numeric_conversion
                continue
        except:
            pass
        
        # Otherwise keep as string, but clean it
        print(f"    → Text column")
        df[col] = df[col].astype(str)
        df[col] = df[col].str.strip()
        df[col] = df[col].replace('nan', np.nan)
        df[col] = df[col].replace('None', np.nan)
        df[col] = df[col].replace('', np.nan)
        df[col] = df[col].replace('NaT', np.nan)
    
    print(f"Preprocessing complete. Shape: {df.shape}\n")
    return df

def clean_time_value(val):
    """Clean and standardize time values"""
    if pd.isna(val):
        return np.nan
    
    val_str = str(val).strip()
    
    # Remove #### symbols
    if '####' in val_str or '#' in val_str:
        return np.nan
    
    # Try to parse as time
    try:
        # Handle HH:MM format
        if ':' in val_str:
            parts = val_str.split(':')
            if len(parts) >= 2:
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = int(parts[2]) if len(parts) > 2 else 0
                return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        # Handle numeric (e.g., 900 = 9:00)
        elif val_str.isdigit():
            num = int(val_str)
            if num < 2400:  # Valid time
                hours = num // 100
                minutes = num % 100
                return f"{hours:02d}:{minutes:02d}:00"
        
        # Handle Excel time (fraction of day)
        else:
            fval = float(val_str)
            if 0 <= fval <= 1:
                total_seconds = int(fval * 24 * 60 * 60)
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    except:
        pass
    
    return np.nan

def clean_date_value(val):
    """Clean and standardize date values"""
    if pd.isna(val):
        return np.nan
    
    val_str = str(val).strip()
    
    # Remove #### symbols
    if '####' in val_str or '#' in val_str:
        return np.nan
    
    # If it's already a valid date string, keep it
    if val_str.lower() in ['nan', 'none', '', 'nat']:
        return np.nan
    
    # Try common date formats
    date_formats = [
        '%Y-%m-%d',
        '%m/%d/%Y',
        '%d/%m/%Y',
        '%Y/%m/%d',
        '%d-%m-%Y',
        '%m-%d-%Y',
        '%Y%m%d'
    ]
    
    for fmt in date_formats:
        try:
            dt = datetime.strptime(val_str, fmt)
            return dt.strftime('%Y-%m-%d')  # Standardize to YYYY-MM-DD
        except:
            continue
    
    # Try pandas parsing (handles many formats)
    try:
        dt = pd.to_datetime(val_str, errors='coerce')
        if pd.notna(dt):
            return dt.strftime('%Y-%m-%d')
    except:
        pass
    
    # If we can't parse it, keep as string (don't convert to float)
    return val_str

# ============================================================================
# API ROUTES
# ============================================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/animation/<session_id>')
def animation_page(session_id):
    """Serve animation page - data loaded via API"""
    return render_template('animation.html')

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """Main analysis endpoint with CSV preprocessing"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '' or not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Invalid file'}), 400
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Load and preprocess CSV
        try:
            df = pd.read_csv(filepath, encoding='utf-8')
        except UnicodeDecodeError:
            # Try different encodings
            try:
                df = pd.read_csv(filepath, encoding='latin-1')
            except:
                df = pd.read_csv(filepath, encoding='iso-8859-1')
        
        print(f"\n{'='*60}")
        print(f"Loaded CSV: {len(df)} rows, {len(df.columns)} columns")
        print(f"Columns: {list(df.columns)}")
        print(f"{'='*60}\n")
        
        # Preprocess: Clean invalid values (####, NaN, etc.)
        df = preprocess_csv(df)
        
        # Get conflict rules
        conflict_rules_json = request.form.get('conflict_rules', '[]')
        conflict_rules = json.loads(conflict_rules_json)
        
        # Build conflict graph
        G = build_generic_conflict_graph(df, conflict_rules)
        
        if G.number_of_nodes() == 0:
            return jsonify({'success': False, 'error': 'No valid data in dataset'}), 400
        
        max_degree = max(dict(G.degree()).values()) if G.number_of_nodes() > 0 else 0
        
        print(f"Graph created: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
        print(f"Max degree: {max_degree}")
        
        # Run algorithms
        luby_result = luby_mis_coloring(G)
        algorithms = {
            'Luby-MIS': luby_result,
            'Greedy Sequential': greedy_sequential_coloring(G),
            'Genetic Algorithm': genetic_algorithm_coloring(G),
            'First-Fit': firstfit_coloring(G)
        }
        
        # Calculate runtimes
        scenarios = [
            {'name': 'Co-located Datacenter', 'latency': 1.0, 'queue': 0.05, 'collect': 0.1},
            {'name': 'Distributed Cloud', 'latency': 20.0, 'queue': 0.5, 'collect': 1.0},
            {'name': 'Geo-distributed Edge', 'latency': 100.0, 'queue': 2.0, 'collect': 5.0}
        ]
        
        results = []
        for scenario in scenarios:
            for algo_name, algo_result in algorithms.items():
                n_nodes = G.number_of_nodes()
                rounds = algo_result['rounds']
                colors = algo_result['colors']
                
                if algo_name == 'Luby-MIS':
                    runtime_result = CompleteRuntimeModel.luby_distributed(
                        n_nodes, rounds, max_degree, scenario['latency'], scenario['queue'], scenario['collect'])
                    architecture = 'DISTRIBUTED'
                elif algo_name == 'Greedy Sequential':
                    runtime_result = CompleteRuntimeModel.greedy_centralized(
                        n_nodes, scenario['latency'], scenario['queue'], scenario['collect'])
                    architecture = 'CENTRALIZED'
                elif algo_name == 'Genetic Algorithm':
                    runtime_result = CompleteRuntimeModel.genetic_centralized(
                        n_nodes, 50, 30, scenario['latency'], scenario['queue'], scenario['collect'])
                    architecture = 'CENTRALIZED'
                else:
                    runtime_result = CompleteRuntimeModel.firstfit_centralized(
                        n_nodes, scenario['latency'], scenario['queue'], scenario['collect'])
                    architecture = 'CENTRALIZED'
                
                results.append({
                    'scenario': scenario['name'],
                    'algorithm': algo_name,
                    'architecture': architecture,
                    'nodes': n_nodes,
                    'edges': G.number_of_edges(),
                    'max_degree': max_degree,
                    'colors': colors,
                    'rounds': rounds,
                    'runtime_ms': runtime_result['total'],
                    'coordinator_bottleneck': runtime_result.get('coordinator_bottleneck', 0)
                })
        
        session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_df = pd.DataFrame(results)
        results_file = os.path.join(app.config['OUTPUT_FOLDER'], f'{session_id}_results.csv')
        results_df.to_csv(results_file, index=False)
        
        # Generate visualizations
        viz_files = generate_visualizations(results_df, G, session_id)
        
        # Prepare animation data
        nodes = [{'id': int(node)} for node in G.nodes()]
        edges = [{'source': int(u), 'target': int(v)} for u, v in G.edges()]
        animation_data = {
            'graph': {'nodes': nodes, 'edges': edges},
            'history': luby_result['history']
        }
        animation_sessions[session_id] = animation_data
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'summary': {
                'nodes': G.number_of_nodes(),
                'edges': G.number_of_edges(),
                'max_degree': max_degree
            },
            'results': results,
            'visualizations': viz_files
        })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/download/<session_id>/<filename>')
def download_file(session_id, filename):
    try:
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], f'{session_id}_{filename}')
        return send_file(filepath, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/api/image/<session_id>/<filename>')
def get_image(session_id, filename):
    try:
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], f'{session_id}_{filename}')
        return send_file(filepath, mimetype='image/png')
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/api/animation/<session_id>')
def get_animation_data(session_id):
    """API endpoint to fetch animation data"""
    try:
        if session_id in animation_sessions:
            return jsonify(animation_sessions[session_id])
        else:
            return jsonify({'error': 'Animation session not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting Distributed Scheduling Analysis Server...")
    print("📊 Open your browser to: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)