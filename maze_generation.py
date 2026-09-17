"""Pure maze construction routines, independent of rendering and input."""

import random
from collections import deque


CARVE_DIRECTIONS = [(-2, 0), (0, 2), (2, 0), (0, -2)]
CARDINAL_DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]


def generate(rows, start_point=(1, 0), attempts=15):
    """Return a difficulty-selected maze grid, its exit tile, and optimal steps."""
    best_maze = None
    best_difficulty_score = -1.0

    for _ in range(attempts):
        values = {(row, col): 1 for row in range(rows) for col in range(rows)}
        start_cell = (1, 1)
        values[start_cell] = 0
        target_row, target_col = rows - 2, rows - 2
        stack, visited = [(1, 1, None)], {start_cell}

        while stack:
            row, col, last_direction = stack[-1]
            unvisited = []
            for d_row, d_col in CARVE_DIRECTIONS:
                next_row, next_col = row + d_row, col + d_col
                if 0 < next_row < rows - 1 and 0 < next_col < rows - 1 and (next_row, next_col) not in visited:
                    unvisited.append((next_row, next_col, d_row, d_col))
            if not unvisited:
                stack.pop()
                continue

            weights = []
            for next_row, next_col, d_row, d_col in unvisited:
                weight = 1.0 + (6.5 if last_direction == (d_row, d_col) else 0)
                distance = abs(next_row - target_row) + abs(next_col - target_col)
                weight += (distance / max(1, rows)) * 2.0 if len(stack) < rows // 2 else ((rows * 2 - distance) / max(1, rows)) * 1.5
                weights.append(weight)
            next_row, next_col, d_row, d_col = random.choices(unvisited, weights=weights, k=1)[0]
            values[(row + d_row // 2, col + d_col // 2)] = 0
            values[(next_row, next_col)] = 0
            visited.add((next_row, next_col))
            stack.append((next_row, next_col, (d_row, d_col)))

        values[start_point] = 0
        _add_loops(values, rows)
        deepest_cells = _distances(values, start_point)
        candidate = next((item for item in deepest_cells if item[0][0] in (1, rows - 2) or item[0][1] in (1, rows - 2)), deepest_cells[0])
        inner_tile, path_length = candidate
        branch_depths = [depth for _, depth in deepest_cells if depth > 10]
        average_depth = sum(branch_depths) / max(1, len(branch_depths))
        score = (path_length / (rows * 2)) * (average_depth / 10.0)
        if score > best_difficulty_score:
            best_difficulty_score = score
            best_maze = (values, inner_tile, path_length)
        if path_length >= int(rows * 1.45) and average_depth >= 16.0:
            break

    values, inner_tile, optimal_steps = best_maze
    row, col = inner_tile
    exit_tile = min(((row, rows - 1), (rows - 1, col), (0, col), (row, 0)), key=lambda point: abs(point[0] - row) + abs(point[1] - col))
    values[inner_tile] = values[exit_tile] = 0
    return values, exit_tile, optimal_steps


def _add_loops(values, rows):
    dead_ends = []
    for row in range(1, rows - 1):
        for col in range(1, rows - 1):
            if values[(row, col)] == 0 and sum(values.get((row + dr, col + dc), 1) == 1 for dr, dc in CARDINAL_DIRECTIONS) == 3:
                dead_ends.append((row, col))
    random.shuffle(dead_ends)
    for row, col in dead_ends[:max(1, int(len(dead_ends) * 0.045))]:
        candidates = []
        for d_row, d_col in CARDINAL_DIRECTIONS:
            near, far = (row + d_row, col + d_col), (row + 2 * d_row, col + 2 * d_col)
            if 0 < far[0] < rows - 1 and 0 < far[1] < rows - 1 and values[near] == 1 and values[far] == 0:
                candidates.append(near)
        if candidates:
            values[random.choice(candidates)] = 0


def _distances(values, start):
    distances, queue, cells = {start: 0}, deque([start]), []
    while queue:
        row, col = queue.popleft()
        for d_row, d_col in CARDINAL_DIRECTIONS:
            neighbor = row + d_row, col + d_col
            if neighbor not in distances and values.get(neighbor) == 0:
                distances[neighbor] = distances[(row, col)] + 1
                queue.append(neighbor)
                cells.append((neighbor, distances[neighbor]))
    return sorted(cells, key=lambda item: item[1], reverse=True)
