import pygame
import random
from collections import deque

pygame.display.init()

board = {"rect": {}, "value": {}}

scrn = pygame.display.Info()
scrn_w = scrn.current_w
scrn_h = scrn.current_h


def ux(percentage): return int(scrn_w * percentage / 1000)
def uy(percentage): return int(scrn_h * percentage / 1000)


center_x = scrn_w // 2
center_y = scrn_h // 2

running = True

# Increase row density for tighter, more confusing corridors
rows = 45

board_size = ux(300)
cell_size = board_size // rows

start_x = center_x - (rows * cell_size) // 2
start_y = center_y - (rows * cell_size) // 2

fps = 240

background_color = "#0d1b2a"
traversable_color = "#1b263b"
untraversable_color = '#415a77'
start_color = traversable_color
end_color = traversable_color

start_point = (1, 0)
end_point = None

directions = [
    (-2, 0),  # Up
    (0, 2),   # Right
    (2, 0),   # Down
    (0, -2)   # Left
]


def initialize():
    board["rect"].clear()
    board["value"].clear()

    for h in range(rows):
        for w in range(rows):
            key = (h, w)
            rect_x = start_x + (w * cell_size)
            rect_y = start_y + (h * cell_size)

            board["rect"][key] = pygame.Rect(
                rect_x, rect_y, cell_size, cell_size)
            board["value"][key] = 1


def generate():
    global end_point

    maze_start = (1, 1)
    board["value"][maze_start] = 0

    # Track (h, w, last_direction_taken)
    stack = [(1, 1, None)]

    while stack:
        h, w, last_dir = stack[-1]
        unvisited = []

        for dh, dw in directions:
            nh, nw = h + dh, w + dw
            if 0 < nh < rows - 1 and 0 < nw < rows - 1:
                if board["value"][(nh, nw)] == 1:
                    unvisited.append((nh, nw, dh, dw))

        if unvisited:
            # Maximally erratic corridors: heavily penalize moving in the same direction
            if len(unvisited) > 1 and last_dir is not None:
                weights = [
                    0.15 if (dh, dw) == last_dir else 1.0 for _, _, dh, dw in unvisited]
                chosen = random.choices(unvisited, weights=weights, k=1)[0]
            else:
                chosen = random.choice(unvisited)

            nh, nw, dh, dw = chosen

            board["value"][(h + dh // 2, w + dw // 2)] = 0
            board["value"][(nh, nw)] = 0

            stack.append((nh, nw, (dh, dw)))
        else:
            stack.pop()

    # Open outer start point
    board["value"][start_point] = 0

    # BFS to calculate the mathematically longest path from start
    dist = {maze_start: 0}
    queue = deque([maze_start])
    farthest_cell = maze_start
    max_dist = 0

    while queue:
        curr = queue.popleft()
        ch, cw = curr

        for dh, dw in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nh, nw = ch + dh, cw + dw
            if (nh, nw) not in dist and board["value"].get((nh, nw)) == 0:
                d = dist[curr] + 1
                dist[(nh, nw)] = d
                if d > max_dist:
                    max_dist = d
                    farthest_cell = (nh, nw)
                queue.append((nh, nw))

    # Carve an exit out to the nearest perimeter edge from that farthest dead-end
    fh, fw = farthest_cell
    edge_candidates = [
        (fh, rows - 1, fh, rows - 2),  # Right
        (rows - 1, fw, rows - 2, fw),  # Bottom
        (0, fw, 1, fw),                # Top
        (fh, 0, fh, 1)                 # Left
    ]

    # Pick the nearest outer perimeter tile
    edge_candidates.sort(key=lambda item: abs(
        item[0] - fh) + abs(item[1] - fw))
    exit_tile, inner_tile = edge_candidates[0][:2], edge_candidates[0][2:]

    board["value"][inner_tile] = 0
    board["value"][exit_tile] = 0
    end_point = exit_tile


def load():
    initialize()
    generate()


def draw(screen):
    for key, rect in board["rect"].items():
        if key == start_point:
            pygame.draw.rect(screen, start_color, rect)
        elif key == end_point:
            pygame.draw.rect(screen, end_color, rect)
        elif board["value"][key] == 1:
            pygame.draw.rect(screen, untraversable_color, rect)
        else:
            pygame.draw.rect(screen, traversable_color, rect)
