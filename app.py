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
                    mis.add(node)
                elif all(random_values[node] > random_values[n] for n in active_neighbors):
                    mis.add(node)

            # Safety: if no MIS found, force select a node
            if not mis and current_active:
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
        population = [ind for _, _, ind in fitness_scores[:population_size // 2]]
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
# DATE / TIME PARSING UTILITY  (FIXED)
# ============================================================================

def parse_temporal_value(val):
    """
    Parse a time OR date string to a single comparable float.

    Handles:
      • HH:MM  /  HH:MM:SS          → seconds since midnight
      • DD-MM-YYYY, YYYY-MM-DD,
        DD/MM/YYYY, MM/DD/YYYY,
        YYYY/MM/DD, DD-MM-YY …      → ordinal day number (integer)
      • Raw int / float              → returned as-is
      • Excel fractional day (0–1)   → seconds since midnight
    """
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None

    # Already numeric
    if isinstance(val, (int, float)):
        fval = float(val)
        # Excel fractional day
        if 0.0 <= fval <= 1.0:
            return fval * 86400.0
        return fval

    val_str = str(val).strip()

    if not val_str or val_str.lower() in ('nan', 'none', 'nat', ''):
        return None

    # ── Time string: HH:MM or HH:MM:SS ──────────────────────────────────────
    # Must be short enough to be a time (≤ 8 chars) and contain ':'
    if ':' in val_str and len(val_str) <= 8:
        try:
            parts = val_str.split(':')
            hours   = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2]) if len(parts) > 2 else 0
            return float(hours * 3600 + minutes * 60 + seconds)
        except (ValueError, IndexError):
            pass  # fall through to date parsing

    # ── Date strings ─────────────────────────────────────────────────────────
    date_formats = [
        '%d-%m-%Y', '%Y-%m-%d', '%m-%d-%Y',
        '%d/%m/%Y', '%Y/%m/%d', '%m/%d/%Y',
        '%d-%m-%y', '%Y-%d-%m',
        '%d.%m.%Y', '%Y.%m.%d',
        '%d %b %Y', '%d %B %Y',
        '%b %d, %Y', '%B %d, %Y',
    ]
    for fmt in date_formats:
        try:
            dt = datetime.strptime(val_str, fmt)
            return float(dt.toordinal())
        except ValueError:
            continue

    # ── Pandas fallback (handles many ambiguous formats) ─────────────────────
    try:
        dt = pd.to_datetime(val_str, dayfirst=True, errors='raise')
        return float(dt.toordinal())
    except Exception:
        pass

    # ── Last resort: plain numeric string ────────────────────────────────────
    try:
        return float(val_str)
    except ValueError:
        pass

    return None  # completely unparseable


# ============================================================================
# CONFLICT GRAPH BUILDER  (FIXED time_overlap rule)
# ============================================================================

def build_generic_conflict_graph(df, conflict_rules):
    """Build conflict graph based on user-defined rules"""
    G = nx.Graph()

    # Add all nodes
    for i in range(len(df)):
        G.add_node(i)

    # Check conflicts between all pairs of tasks
    for i in range(len(df)):
        for j in range(i + 1, len(df)):
            has_conflict = False

            for rule in conflict_rules:
                rule_type = rule.get('type', '')

                # ── Rule 1: Same Value ────────────────────────────────────────
                if rule_type == 'same_value':
                    col = rule.get('column', '')
                    if col and col in df.columns:
                        vi = df.iloc[i][col]
                        vj = df.iloc[j][col]
                        if pd.notna(vi) and pd.notna(vj) and vi == vj:
                            has_conflict = True
                            break

                # ── Rule 2: Time / Date Overlap (FIXED) ──────────────────────
                elif rule_type == 'time_overlap':
                    col_str = rule.get('column', '')
                    if ',' in col_str:
                        cols = [c.strip() for c in col_str.split(',')]
                        if len(cols) >= 2:
                            start_col, end_col = cols[0], cols[1]
                            if start_col in df.columns and end_col in df.columns:
                                try:
                                    raw_si = df.iloc[i][start_col]
                                    raw_ei = df.iloc[i][end_col]
                                    raw_sj = df.iloc[j][start_col]
                                    raw_ej = df.iloc[j][end_col]

                                    # Skip rows with missing values
                                    if any(
                                        v is None or (isinstance(v, float) and np.isnan(v))
                                        for v in [raw_si, raw_ei, raw_sj, raw_ej]
                                    ):
                                        continue

                                    start_i = parse_temporal_value(raw_si)
                                    end_i   = parse_temporal_value(raw_ei)
                                    start_j = parse_temporal_value(raw_sj)
                                    end_j   = parse_temporal_value(raw_ej)

                                    # If any value couldn't be parsed, skip
                                    if any(v is None for v in [start_i, end_i, start_j, end_j]):
                                        print(
                                            f"    Warning: Could not parse temporal values for "
                                            f"rows {i},{j} — skipping overlap check."
                                        )
                                        continue

                                    # Overlap: NOT (end_i <= start_j  OR  end_j <= start_i)
                                    if not (end_i <= start_j or end_j <= start_i):
                                        has_conflict = True
                                        break

                                except Exception as e:
                                    print(f"    Warning: Time overlap check failed for tasks {i},{j}: {e}")

                # ── Rule 3: Resource Exceed ───────────────────────────────────
                elif rule_type == 'resource_exceed':
                    col_str   = rule.get('column', '')
                    # threshold comes from the rule dict (sent by the frontend)
                    # Support both: rule['threshold'] = 100  OR  "cpu:100" legacy format
                    threshold = rule.get('threshold', 100)

                    if col_str:
                        # Legacy support: "cpu,memory:150" encodes threshold after ':'
                        # Only treat the last ':' as a threshold separator if the part
                        # after it looks like a number (not a column name like "hh:mm")
                        if ':' in col_str:
                            last_colon = col_str.rfind(':')
                            possible_threshold = col_str[last_colon + 1:].strip()
                            try:
                                threshold = float(possible_threshold)
                                col_str   = col_str[:last_colon]
                            except ValueError:
                                pass  # ':' is part of a column name, keep col_str as-is

                        cols = [c.strip() for c in col_str.split(',') if c.strip()]

                        # Validate columns exist
                        missing = [c for c in cols if c not in df.columns]
                        if missing:
                            print(f"    Warning: resource_exceed — columns not found: {missing}")
                            print(f"    Available columns: {list(df.columns)}")
                            continue

                        try:
                            total    = 0.0
                            skipped  = False

                            for col in cols:
                                vi = df.iloc[i][col]
                                vj = df.iloc[j][col]

                                # Skip pair if either value is missing
                                if vi is None or vj is None:
                                    skipped = True
                                    break
                                # pandas NA / NaN check
                                try:
                                    if pd.isna(vi) or pd.isna(vj):
                                        skipped = True
                                        break
                                except (TypeError, ValueError):
                                    pass

                                # Robust numeric conversion: strip currency, %, commas
                                def to_numeric(v):
                                    if isinstance(v, (int, float)):
                                        return float(v)
                                    s = str(v).strip()
                                    # Remove common non-numeric characters
                                    s = s.replace(',', '').replace('%', '')
                                    s = s.replace('$', '').replace('£', '').replace('€', '')
                                    s = s.strip()
                                    return float(s)  # raises ValueError if still non-numeric

                                try:
                                    total += to_numeric(vi) + to_numeric(vj)
                                except (ValueError, TypeError) as e:
                                    print(
                                        f"    Warning: resource_exceed — cannot convert "
                                        f"values '{vi}', '{vj}' in column '{col}' "
                                        f"for rows {i},{j}: {e}"
                                    )
                                    skipped = True
                                    break

                            if not skipped and total > float(threshold):
                                has_conflict = True
                                break

                        except Exception as e:
                            print(f"    Warning: resource_exceed check failed for rows {i},{j}: {e}")

            if has_conflict:
                G.add_edge(i, j)

    print(f"\nConflict graph built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    if G.number_of_edges() == 0:
        print("  WARNING: No conflicts detected — check column names and rule types.")
        print(f"  DataFrame columns available: {list(df.columns)}")
        for idx, rule in enumerate(conflict_rules):
            print(f"  Rule {idx + 1}: {rule}")

    return G


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ============================================================================
# VISUALIZATION GENERATION
# ============================================================================

def generate_visualizations(df, G, session_id):
    viz_files = []
    colors_map = {
        'Luby-MIS':           '#2ecc71',
        'Greedy Sequential':  '#3498db',
        'Genetic Algorithm':  '#e74c3c',
        'First-Fit':          '#f39c12'
    }

    # VIZ 1: Three Scenarios Comparison
    fig, axes = plt.subplots(1, 3, figsize=(20, 7))
    scenarios = df['scenario'].unique()

    scenario_descriptions = {
        'Co-located Datacenter':  'Same building, low latency (1ms)',
        'Distributed Cloud':      'Multi-region, medium latency (20ms)',
        'Geo-distributed Edge':   'Cross-continent, high latency (100ms)'
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
            ax.text(val * 1.15, bar.get_y() + bar.get_height() / 2,
                    f'{val:.0f}ms', ha='left', va='center', fontweight='bold', fontsize=10)

    plt.suptitle('Runtime Comparison Across 3 Deployment Scenarios',
                 fontsize=18, fontweight='bold', y=0.98)
    plt.tight_layout()
    filename = f'{session_id}_viz1_scenarios.png'
    plt.savefig(os.path.join(app.config['OUTPUT_FOLDER'], filename),
                dpi=300, bbox_inches='tight', facecolor='white')
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
    plt.savefig(os.path.join(app.config['OUTPUT_FOLDER'], f'{session_id}_viz2_scalability.png'),
                dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    viz_files.append('viz2_scalability.png')

    # VIZ 3: Coordinator Bottleneck
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
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + max(bottleneck_data.values) * 0.02,
                    f'{val:.0f}ms', ha='center', va='bottom', fontweight='bold', fontsize=9)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    plt.suptitle('Coordinator Bottleneck Delay by Scenario\n(Luby-MIS = 0 — No Coordinator Needed)',
                 fontsize=16, fontweight='bold', y=1.01)
    plt.tight_layout()
    plt.savefig(os.path.join(app.config['OUTPUT_FOLDER'], f'{session_id}_viz3_bottleneck.png'),
                dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    viz_files.append('viz3_bottleneck.png')

    # VIZ 4: Network Latency Impact
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))
    latencies       = [1, 20, 100]
    scenarios_order = ['Co-located Datacenter', 'Distributed Cloud', 'Geo-distributed Edge']

    for algo in df['algorithm'].unique():
        rts = [df[(df['scenario'] == s) & (df['algorithm'] == algo)]['runtime_ms'].mean()
               for s in scenarios_order]
        ax1.plot(latencies, rts, 'o-', label=algo, linewidth=2.5, markersize=9,
                 color=colors_map[algo], markeredgecolor='white', markeredgewidth=1.5)

    ax1.set_xlabel('Network Latency (ms)', fontweight='bold', fontsize=12)
    ax1.set_ylabel('Average Runtime (ms)', fontweight='bold', fontsize=12)
    ax1.set_title('Runtime vs. Network Latency', fontweight='bold', fontsize=13)
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.set_xscale('log')
    ax1.set_yscale('log')
    ax1.set_xticks(latencies)
    ax1.set_xticklabels(['1ms\n(Co-located)', '20ms\n(Cloud)', '100ms\n(Geo)'])
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)

    luby_rts = [df[(df['scenario'] == s) & (df['algorithm'] == 'Luby-MIS')]['runtime_ms'].mean()
                for s in scenarios_order]
    x     = np.arange(len(scenarios_order))
    width = 0.25

    for i, algo in enumerate(['Greedy Sequential', 'Genetic Algorithm', 'First-Fit']):
        algo_rts = [df[(df['scenario'] == s) & (df['algorithm'] == algo)]['runtime_ms'].mean()
                    for s in scenarios_order]
        speedups = [a / l if l > 0 else 1 for a, l in zip(algo_rts, luby_rts)]
        bars = ax2.bar(x + width * (i - 1), speedups, width,
                       label=algo, color=colors_map[algo], edgecolor='white', linewidth=1)
        for bar, val in zip(bars, speedups):
            ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                     f'{val:.1f}x', ha='center', va='bottom', fontsize=8, fontweight='bold')

    ax2.axhline(1, color='#2ecc71', linestyle='--', linewidth=2, alpha=0.8, label='Luby-MIS baseline')
    ax2.set_xticks(x)
    ax2.set_xticklabels([s.replace(' ', '\n') for s in scenarios_order])
    ax2.set_ylabel('Slowdown vs Luby-MIS (×)', fontweight='bold', fontsize=12)
    ax2.set_title('Other Algorithms vs Luby-MIS', fontweight='bold', fontsize=13)
    ax2.legend(fontsize=9)
    ax2.grid(axis='y', alpha=0.3)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)

    plt.suptitle('Network Latency Impact Analysis', fontsize=16, fontweight='bold', y=1.01)
    plt.tight_layout()
    plt.savefig(os.path.join(app.config['OUTPUT_FOLDER'], f'{session_id}_viz4_latency.png'),
                dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    viz_files.append('viz4_latency.png')

    # VIZ 5: Architecture Summary Table
    fig, ax = plt.subplots(figsize=(14, 7))
    ax.axis('off')
    summary = []
    for algo in df['algorithm'].unique():
        adata = df[df['algorithm'] == algo]
        summary.append([
            algo,
            f"{adata['colors'].mean():.1f}",
            f"{adata['runtime_ms'].mean():.0f} ms",
            f"{adata['coordinator_bottleneck'].mean():.0f} ms"
        ])
    cols  = ['Algorithm', 'Avg Colors\n(Time Slots)', 'Avg Runtime', 'Coordinator\nBottleneck']
    table = ax.table(cellText=summary, colLabels=cols, cellLoc='center', loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1.2, 2.5)

    header_color = '#2c3e50'
    for j in range(len(cols)):
        table[0, j].set_facecolor(header_color)
        table[0, j].set_text_props(color='white', fontweight='bold')

    row_colors = {
        'Luby-MIS':          '#eafaf1',
        'Greedy Sequential': '#ebf5fb',
        'Genetic Algorithm': '#fdedec',
        'First-Fit':         '#fef9e7'
    }
    for i, row in enumerate(summary):
        c = row_colors.get(row[0], 'white')
        for j in range(len(cols)):
            table[i + 1, j].set_facecolor(c)

    ax.set_title('Algorithm Architecture Summary', fontweight='bold', fontsize=16, pad=20)
    plt.savefig(os.path.join(app.config['OUTPUT_FOLDER'], f'{session_id}_viz5_architecture.png'),
                dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    viz_files.append('viz5_architecture.png')

    # VIZ 6: Winners Matrix
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    algorithms_list = list(df['algorithm'].unique())
    scenarios_list  = list(df['scenario'].unique())

    quality_mat = np.zeros((len(algorithms_list), len(scenarios_list)))
    speed_mat   = np.zeros((len(algorithms_list), len(scenarios_list)))

    for j, scenario in enumerate(scenarios_list):
        sd      = df[df['scenario'] == scenario]
        best_q  = sd.groupby('algorithm')['colors'].mean().min()
        best_s  = sd.groupby('algorithm')['runtime_ms'].mean().min()
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
        ax.set_xticklabels([s.replace(' ', '\n') for s in scenarios_list], fontsize=10)
        ax.set_yticks(range(len(algorithms_list)))
        ax.set_yticklabels(algorithms_list, fontsize=10)
        ax.set_title(title, fontweight='bold', fontsize=13)
        for i in range(len(algorithms_list)):
            for j in range(len(scenarios_list)):
                ax.text(j, i, '✓' if mat[i, j] else '✗', ha='center', va='center',
                        fontsize=20,
                        color='#27ae60' if mat[i, j] else '#e74c3c',
                        fontweight='bold')

    plt.suptitle('Algorithm Winners Across Deployment Scenarios', fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(app.config['OUTPUT_FOLDER'], f'{session_id}_viz6_winners.png'),
                dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    viz_files.append('viz6_winners.png')

    return viz_files


# ============================================================================
# CSV PREPROCESSING
# ============================================================================

def preprocess_csv(df):
    """Clean and preprocess CSV data to handle invalid formats"""
    print("\nPreprocessing CSV...")

    df = df.copy()

    # Replace Excel error strings with NaN
    error_strings = ['####', '#####', '######', '#VALUE!', '#REF!', '#DIV/0!', '#NAME?', '#N/A', '#NULL!']
    for err in error_strings:
        df = df.replace(err, np.nan)

    for col in df.columns:
        print(f"  Cleaning column: {col}")

        if df[col].isna().all():
            print(f"    → All NaN, skipping")
            continue

        sample = df[col].dropna().astype(str).head(20)
        if len(sample) == 0:
            continue

        # Detect time column (HH:MM or HH:MM:SS)
        time_pattern = r'^\d{1,2}:\d{2}(:\d{2})?$'
        if sample.str.match(time_pattern).sum() > len(sample) * 0.5:
            print(f"    → Detected as TIME column")
            df[col] = df[col].apply(clean_time_value)
            continue

        # Detect date column
        date_indicators = sample.str.contains(
            r'\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{4}/\d{2}/\d{2}|\d{2}-\d{2}-\d{4}',
            na=False
        )
        if date_indicators.sum() > len(sample) * 0.3:
            print(f"    → Detected as DATE column")
            df[col] = df[col].apply(clean_date_value)
            continue

        # Try numeric conversion
        try:
            numeric_conversion = pd.to_numeric(df[col], errors='coerce')
            non_null_count  = df[col].notna().sum()
            converted_count = numeric_conversion.notna().sum()
            if converted_count > non_null_count * 0.7:
                print(f"    → Numeric column ({converted_count}/{non_null_count} converted)")
                df[col] = numeric_conversion
                continue
        except Exception:
            pass

        # Keep as cleaned string
        print(f"    → Text column")
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace({'nan': np.nan, 'None': np.nan, '': np.nan, 'NaT': np.nan})

    print(f"Preprocessing complete. Shape: {df.shape}\n")
    return df


def clean_time_value(val):
    """Clean and standardize time values to HH:MM:SS strings"""
    if pd.isna(val):
        return np.nan

    val_str = str(val).strip()

    if '#' in val_str:
        return np.nan

    try:
        if ':' in val_str:
            parts   = val_str.split(':')
            hours   = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2]) if len(parts) > 2 else 0
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        elif val_str.isdigit():
            num = int(val_str)
            if num < 2400:
                hours   = num // 100
                minutes = num % 100
                return f"{hours:02d}:{minutes:02d}:00"
        else:
            fval = float(val_str)
            if 0 <= fval <= 1:
                total_seconds = int(fval * 86400)
                hours   = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    except Exception:
        pass

    return np.nan


def clean_date_value(val):
    """Clean and standardize date values to YYYY-MM-DD strings"""
    if pd.isna(val):
        return np.nan

    val_str = str(val).strip()

    if '#' in val_str:
        return np.nan

    if val_str.lower() in ('nan', 'none', '', 'nat'):
        return np.nan

    date_formats = [
        '%d-%m-%Y', '%Y-%m-%d', '%m-%d-%Y',
        '%d/%m/%Y', '%Y/%m/%d', '%m/%d/%Y',
        '%d-%m-%y', '%y-%m-%d',
        '%d.%m.%Y', '%Y.%m.%d',
    ]
    for fmt in date_formats:
        try:
            dt = datetime.strptime(val_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue

    try:
        dt = pd.to_datetime(val_str, dayfirst=True, errors='coerce')
        if pd.notna(dt):
            return dt.strftime('%Y-%m-%d')
    except Exception:
        pass

    return val_str  # Return as-is if unparseable


# ============================================================================
# API ROUTES
# ============================================================================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/animation/<session_id>')
def animation_page(session_id):
    """Serve animation page — data loaded via API"""
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

        # Load CSV with encoding fallback
        for enc in ('utf-8', 'latin-1', 'iso-8859-1'):
            try:
                df = pd.read_csv(filepath, encoding=enc)
                break
            except UnicodeDecodeError:
                continue

        print(f"\n{'=' * 60}")
        print(f"Loaded CSV: {len(df)} rows, {len(df.columns)} columns")
        print(f"Columns: {list(df.columns)}")
        print(f"{'=' * 60}\n")

        # Preprocess
        df = preprocess_csv(df)

        # Get conflict rules
        conflict_rules_json = request.form.get('conflict_rules', '[]')
        conflict_rules      = json.loads(conflict_rules_json)

        # Build conflict graph
        G = build_generic_conflict_graph(df, conflict_rules)

        if G.number_of_nodes() == 0:
            return jsonify({'success': False, 'error': 'No valid data in dataset'}), 400

        max_degree = max(dict(G.degree()).values()) if G.number_of_nodes() > 0 else 0

        print(f"Graph created: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
        print(f"Max degree: {max_degree}")

        # Run algorithms
        luby_result = luby_mis_coloring(G)
        algorithms  = {
            'Luby-MIS':          luby_result,
            'Greedy Sequential': greedy_sequential_coloring(G),
            'Genetic Algorithm': genetic_algorithm_coloring(G),
            'First-Fit':         firstfit_coloring(G)
        }

        # Calculate runtimes for 3 scenarios
        scenarios = [
            {'name': 'Co-located Datacenter', 'latency': 1.0,   'queue': 0.05, 'collect': 0.1},
            {'name': 'Distributed Cloud',      'latency': 20.0,  'queue': 0.5,  'collect': 1.0},
            {'name': 'Geo-distributed Edge',   'latency': 100.0, 'queue': 2.0,  'collect': 5.0}
        ]

        results = []
        for scenario in scenarios:
            for algo_name, algo_result in algorithms.items():
                n_nodes = G.number_of_nodes()
                rounds  = algo_result['rounds']
                colors  = algo_result['colors']

                if algo_name == 'Luby-MIS':
                    runtime_result = CompleteRuntimeModel.luby_distributed(
                        n_nodes, rounds, max_degree,
                        scenario['latency'], scenario['queue'], scenario['collect'])
                    architecture = 'DISTRIBUTED'
                elif algo_name == 'Greedy Sequential':
                    runtime_result = CompleteRuntimeModel.greedy_centralized(
                        n_nodes, scenario['latency'], scenario['queue'], scenario['collect'])
                    architecture = 'CENTRALIZED'
                elif algo_name == 'Genetic Algorithm':
                    runtime_result = CompleteRuntimeModel.genetic_centralized(
                        n_nodes, 50, 30,
                        scenario['latency'], scenario['queue'], scenario['collect'])
                    architecture = 'CENTRALIZED'
                else:
                    runtime_result = CompleteRuntimeModel.firstfit_centralized(
                        n_nodes, scenario['latency'], scenario['queue'], scenario['collect'])
                    architecture = 'CENTRALIZED'

                results.append({
                    'scenario':               scenario['name'],
                    'algorithm':              algo_name,
                    'architecture':           architecture,
                    'nodes':                  n_nodes,
                    'edges':                  G.number_of_edges(),
                    'max_degree':             max_degree,
                    'colors':                 colors,
                    'rounds':                 rounds,
                    'runtime_ms':             runtime_result['total'],
                    'coordinator_bottleneck': runtime_result.get('coordinator_bottleneck', 0)
                })

        session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_df = pd.DataFrame(results)
        results_df.to_csv(
            os.path.join(app.config['OUTPUT_FOLDER'], f'{session_id}_results.csv'), index=False)

        # Generate visualizations
        viz_files = generate_visualizations(results_df, G, session_id)

        # Prepare animation data
        nodes = [{'id': int(node)} for node in G.nodes()]
        edges = [{'source': int(u), 'target': int(v)} for u, v in G.edges()]
        animation_sessions[session_id] = {
            'graph':   {'nodes': nodes, 'edges': edges},
            'history': luby_result['history']
        }

        return jsonify({
            'success':        True,
            'session_id':     session_id,
            'summary': {
                'nodes':      G.number_of_nodes(),
                'edges':      G.number_of_edges(),
                'max_degree': max_degree
            },
            'results':        results,
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
        return jsonify({'error': 'Animation session not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("🚀 Starting Distributed Scheduling Analysis Server...")
    print("📊 Open your browser to: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)