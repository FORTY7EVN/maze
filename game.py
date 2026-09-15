import pygame
import random

pygame.display.init()

# Primary board data structure
# "rect": (h, w) -> pygame.Rect
# "value": (h, w) -> [Top, Right, Bottom, Left] (True = untraversable wall, False = traversable path)
# "visited": (h, w) -> bool (tracks visited state during DFS)
board = {"rect": {}, "value": {}, "visited": {}}

scrn = pygame.display.Info()
scrn_w = scrn.current_w
scrn_h = scrn.current_h


def ux(percentage):
    return int(scrn_w * percentage / 1000)


def uy(percentage):
    return int(scrn_h * percentage / 1000)


center_x = scrn_w // 2
center_y = scrn_h // 2

running = True
rows = 16

board_size = ux(200)
cell_size = board_size // rows

# Calculate top-left corner offset so the board renders centered on screen
start_x = center_x - (rows * cell_size) // 2
start_y = center_y - (rows * cell_size) // 2

fps = 240

traversable_color = 'gray'
untraversable_color = 'white'

# Wall direction mapping: [Top, Right, Bottom, Left]
# (delta_h, delta_w, current_wall_index, neighbor_wall_index)
directions = [
    (-1, 0, 0, 2),  # Up
    (0, 1, 1, 3),   # Right
    (1, 0, 2, 0),   # Down
    (0, -1, 3, 1)   # Left
]


def initialize():
    board["rect"].clear()
    board["value"].clear()
    board["visited"].clear()

    for h in range(rows):
        for w in range(rows):
            key = (h, w)
            # Position rects starting from the centered top-left coordinate
            rect_x = start_x + (w * cell_size)
            rect_y = start_y + (h * cell_size)

            board["rect"][key] = pygame.Rect(
                rect_x, rect_y, cell_size, cell_size)
            # All 4 walls closed by default: [Top, Right, Bottom, Left]
            board["value"][key] = [True, True, True, True]
            board["visited"][key] = False


def generate():
    start = (0, 0)
    board["visited"][start] = True
    stack = [start]

    while stack:
        current = stack[-1]
        h, w = current
        unvisited = []

        for dh, dw, curr_wall, next_wall in directions:
            nh, nw = h + dh, w + dw
            neighbor = (nh, nw)

            if 0 <= nh < rows and 0 <= nw < rows:
                if not board["visited"][neighbor]:
                    unvisited.append((neighbor, curr_wall, next_wall))

        if unvisited:
            next_cell, curr_wall, next_wall = random.choice(unvisited)

            # Knock down dividing walls (set from untraversable to traversable)
            board["value"][current][curr_wall] = False
            board["value"][next_cell][next_wall] = False

            board["visited"][next_cell] = True
            stack.append(next_cell)
        else:
            stack.pop()


def load():
    initialize()
    generate()


def draw(screen):
    for key, rect in board["rect"].items():
        # Fill cell body with traversable floor color
        pygame.draw.rect(screen, traversable_color, rect)

        # Draw standing walls (untraversable)
        top, right, bottom, left = board["value"][key]

        if top:
            pygame.draw.line(screen, untraversable_color,
                             rect.topleft, rect.topright, 2)
        if right:
            pygame.draw.line(screen, untraversable_color,
                             rect.topright, rect.bottomright, 2)
        if bottom:
            pygame.draw.line(screen, untraversable_color,
                             rect.bottomleft, rect.bottomright, 2)
        if left:
            pygame.draw.line(screen, untraversable_color,
                             rect.topleft, rect.bottomleft, 2)
