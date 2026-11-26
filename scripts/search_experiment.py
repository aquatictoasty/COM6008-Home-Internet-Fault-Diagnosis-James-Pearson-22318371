"""reproducible 8 puzzle comparison of uninformed and informed search.

50 start states are sampled from exact reverse-BFS depths 16-20, ten per
depth. Peak frontier size is a memory proxy and not the measured ram usage.
"""
from __future__ import annotations

import heapq
import json
import random
import statistics
import time
from collections import deque
from pathlib import Path

GOAL = (1, 2, 3, 4, 5, 6, 7, 8, 0)

def neighbours(state: tuple[int, ...]) -> list[tuple[int, ...]]:
    """return states reachable by one legal blank tile move."""
    blank = state.index(0)
    row, column = divmod(blank, 3)
    result = []
    for row_change, column_change in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        new_row = row + row_change
        new_column = column + column_change
        if 0 <= new_row < 3 and 0 <= new_column < 3:
            other = new_row * 3 + new_column
            updated = list(state)
            updated[blank], updated[other] = updated[other], updated[blank]
            result.append(tuple(updated))
    return result

def misplaced(state: tuple[int, ...]) -> int:
    """Count nonblank tiles outside their goal positions."""
    return sum(
        1 for index, tile in enumerate(state)
        if tile and tile != index + 1
    )

def manhattan(state: tuple[int, ...]) -> int:
    """Sum each non-blank tile's row and column distance from its goal."""
    total = 0
    for index, tile in enumerate(state):
        if tile == 0:
            continue
        goal_row, goal_column = divmod(tile - 1, 3)
        row, column = divmod(index, 3)
        total += abs(row - goal_row) + abs(column - goal_column)
    return total

def path_length(parents: dict, state: tuple[int, ...]) -> int:
    """Count edges from the start state using a parent map."""
    length = 0
    while parents[state] is not None:
        state = parents[state]
        length += 1
    return length

def reverse_depth_buckets(max_depth: int = 20) -> dict[int, list[tuple[int, ...]]]:
    """Enumerate the states from the goal and group them by exact BFS depth."""
    distances = {GOAL: 0}
    queue = deque([GOAL])
    buckets = {depth: [] for depth in range(1, max_depth + 1)}

    while queue:
        state = queue.popleft()
        depth = distances[state]
        if depth == max_depth:
            continue
        for next_state in neighbours(state):
            if next_state in distances:
                continue
            next_depth = depth + 1
            distances[next_state] = next_depth
            queue.append(next_state)
            if next_depth in buckets:
                buckets[next_depth].append(next_state)
    return buckets

def breadth_first(start: tuple[int, ...]) -> tuple[int | None, int, int]:
    """Run BFS and return path length, expanded nodes and peak frontier."""
    queue = deque([start])
    parents = {start: None}
    expanded = 0
    peak_frontier = 1

    while queue:
        state = queue.popleft()
        expanded += 1
        if state == GOAL:
            return path_length(parents, state), expanded, peak_frontier
        for next_state in neighbours(state):
            if next_state not in parents:
                parents[next_state] = state
                queue.append(next_state)
        peak_frontier = max(peak_frontier, len(queue))
    return None, expanded, peak_frontier

def uniform_cost(start: tuple[int, ...]) -> tuple[int | None, int, int]:
    """Run UCS with unit edge costs and stale-entry checking."""
    sequence = 0
    frontier = [(0, sequence, start)]
    parents = {start: None}
    costs = {start: 0}
    expanded = 0
    peak_frontier = 1

    while frontier:
        cost, _, state = heapq.heappop(frontier)
        if cost != costs[state]:
            continue
        expanded += 1
        if state == GOAL:
            return path_length(parents, state), expanded, peak_frontier
        for next_state in neighbours(state):
            new_cost = cost + 1
            if new_cost < costs.get(next_state, 10**9):
                costs[next_state] = new_cost
                parents[next_state] = state
                sequence += 1
                heapq.heappush(frontier, (new_cost, sequence, next_state))
        peak_frontier = max(peak_frontier, len(frontier))
    return None, expanded, peak_frontier

def depth_first(
    start: tuple[int, ...], node_limit: int = 50_000
) -> tuple[int | None, int, int]:
    """Run graph-search DFS with a fixed expansion limit."""
    stack = [start]
    parents = {start: None}
    seen = {start}
    expanded = 0
    peak_frontier = 1

    while stack and expanded < node_limit:
        state = stack.pop()
        expanded += 1
        if state == GOAL:
            return path_length(parents, state), expanded, peak_frontier
        for next_state in neighbours(state):
            if next_state not in seen:
                seen.add(next_state)
                parents[next_state] = state
                stack.append(next_state)
        peak_frontier = max(peak_frontier, len(stack))
    return None, expanded, peak_frontier

def informed(
    start: tuple[int, ...], heuristic, mode: str, node_limit: int = 500_000
) -> tuple[int | None, int, int]:
    """Run A* or greedy best-first with the supplied heuristic."""
    sequence = 0
    frontier = [(heuristic(start), 0, sequence, start)]
    parents = {start: None}
    best_cost = {start: 0}
    closed = set()
    expanded = 0
    peak_frontier = 1

    while frontier and expanded < node_limit:
        score, cost, _, state = heapq.heappop(frontier)
        if cost != best_cost[state] or state in closed:
            continue
        closed.add(state)
        expanded += 1
        if state == GOAL:
            return path_length(parents, state), expanded, peak_frontier

        for next_state in neighbours(state):
            new_cost = cost + 1
            if next_state in closed:
                continue
            if mode == "astar":
                if new_cost >= best_cost.get(next_state, 10**9):
                    continue
                best_cost[next_state] = new_cost
                parents[next_state] = state
                sequence += 1
                priority = new_cost + heuristic(next_state)
                heapq.heappush(
                    frontier, (priority, new_cost, sequence, next_state)
                )
            else:
                if next_state in best_cost:
                    continue
                best_cost[next_state] = new_cost
                parents[next_state] = state
                sequence += 1
                heapq.heappush(
                    frontier, (heuristic(next_state), new_cost, sequence, next_state)
                )
        peak_frontier = max(peak_frontier, len(frontier))
    return None, expanded, peak_frontier

def sample_states(seed: int = 7) -> list[tuple[tuple[int, ...], int]]:
    """Select ten states at each exact depth from 16 through 20."""
    buckets = reverse_depth_buckets(20)
    generator = random.Random(seed)
    states = []
    for depth in range(16, 21):
        states.extend((state, depth) for state in generator.sample(buckets[depth], 10))
    generator.shuffle(states)
    return states

def distribution(values: list[float | int]) -> dict:
    """return descriptive spread measures using inclusive quartiles."""
    q1, _, q3 = statistics.quantiles(values, n=4, method="inclusive")
    return {
        "min": min(values),
        "max": max(values),
        "sample_sd": round(statistics.stdev(values), 2) if len(values) > 1 else 0.0,
        "q1": round(q1, 2),
        "q3": round(q3, 2),
        "iqr": round(q3 - q1, 2),
    }

def run_experiment() -> dict:
    """run all algorithms and write reproducible case-level and summary data."""
    starts = sample_states()
    algorithms = {
        "BFS": lambda state: breadth_first(state),
        "UCS": lambda state: uniform_cost(state),
        "DFS": lambda state: depth_first(state),
        "A* Manhattan": lambda state: informed(state, manhattan, "astar"),
        "A* misplaced": lambda state: informed(state, misplaced, "astar"),
        "Greedy Manhattan": lambda state: informed(state, manhattan, "greedy"),
        "Greedy misplaced": lambda state: informed(state, misplaced, "greedy"),
    }

    cases = []
    for case_number, (state, exact_depth) in enumerate(starts, 1):
        case = {
            "case": case_number,
            "state": state,
            "optimal_depth": exact_depth,
            "heuristics": {
                "misplaced": misplaced(state),
                "manhattan": manhattan(state),
            },
            "methods": {},
        }
        for name, algorithm in algorithms.items():
            started = time.perf_counter()
            path, expanded, peak = algorithm(state)
            elapsed = time.perf_counter() - started
            case["methods"][name] = {
                "path_length": path,
                "nodes_expanded": expanded,
                "peak_frontier_size": peak,
                "elapsed_seconds": round(elapsed, 6),
                "optimal": path == exact_depth,
            }
        cases.append(case)

    summary = {}
    for name in algorithms:
        expanded = [case["methods"][name]["nodes_expanded"] for case in cases]
        frontier = [case["methods"][name]["peak_frontier_size"] for case in cases]
        paths = [
            case["methods"][name]["path_length"]
            for case in cases
            if case["methods"][name]["path_length"] is not None
        ]
        runtimes = [case["methods"][name]["elapsed_seconds"] for case in cases]
        summary[name] = {
            "mean_nodes": round(statistics.mean(expanded), 1),
            "median_nodes": statistics.median(expanded),
            "nodes_distribution": distribution(expanded),
            "mean_peak_frontier": round(statistics.mean(frontier), 1),
            "median_peak_frontier": statistics.median(frontier),
            "frontier_distribution": distribution(frontier),
            "mean_runtime_seconds": round(statistics.mean(runtimes), 6),
            "median_runtime_seconds": round(statistics.median(runtimes), 6),
            "solved": len(paths),
            "optimal": sum(case["methods"][name]["optimal"] for case in cases),
            "optimal_rate": round(sum(case["methods"][name]["optimal"] for case in cases) / len(cases), 3),
            "mean_path_when_solved": round(statistics.mean(paths), 2) if paths else None,
        }

    pair_wins = {}
    comparisons = (
        ("A* Manhattan", "A* misplaced"),
        ("Greedy Manhattan", "Greedy misplaced"),
        ("A* Manhattan", "Greedy Manhattan"),
        ("A* misplaced", "Greedy misplaced"),
    )
    for first, second in comparisons:
        first_wins = second_wins = ties = 0
        for case in cases:
            first_count = case["methods"][first]["nodes_expanded"]
            second_count = case["methods"][second]["nodes_expanded"]
            if first_count < second_count:
                first_wins += 1
            elif second_count < first_count:
                second_wins += 1
            else:
                ties += 1
        pair_wins[f"{first} vs {second}"] = {
            first: first_wins,
            second: second_wins,
            "ties": ties,
        }

    depth_distribution = {
        str(depth): sum(case["optimal_depth"] == depth for case in cases)
        for depth in range(16, 21)
    }
    output = {
        "method": (
            "50 solvable 8-puzzle states sampled from reverse-BFS exact depths "
            "16-20; ten per depth; seed=7"
        ),
        "heuristics": {
            "misplaced": "nnumber of misplaced nonblank tiles",
            "manhattan": "sum of row/column distances of non blank tiles from goal positions",
        },
        "dfs_node_limit": 50_000,
        "optimal_depth_distribution": depth_distribution,
        "summary": summary,
        "pairwise_expansion_wins": pair_wins,
        "cases": cases,
        "": [
         
        ],
    }

    results_path = Path(__file__).resolve().parents[1] / "results" / "search_results.json"
    results_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print("8-puzzle experiment: 50 states; 10 at each exact reverse-BFS depth 16-20; seed 7")
    print("Algorithm | mean expanded | median | range | SD | mean peak frontier | optimal/50 | mean path | mean runtime (ms)")
    for name, values in summary.items():
        print(
            f"{name:18} | {values['mean_nodes']:13} | "
            f"{values['median_nodes']:7} | "
            f"{values['nodes_distribution']['min']}-{values['nodes_distribution']['max']} | "
            f"{values['nodes_distribution']['sample_sd']:7} | {values['mean_peak_frontier']:12} | "
            f"{values['optimal']:10} | {values['mean_path_when_solved']} | "
            f"{values['mean_runtime_seconds'] * 1000:.1f}"
        )
    print("Pairwise expansion comparisons:", json.dumps(pair_wins, indent=2))
    return output

if __name__ == "__main__":
    run_experiment()
