import pygame
import random
import math
from collections import deque

pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=1)

board = {"rect": {}, "value": {}}

scrn = pygame.display.Info()
scrn_w = scrn.current_w
scrn_h = scrn.current_h

running = True
state = "MENU"  # MENU, CONFIG, PLAYING
game_mode = "CUSTOM"  # "CUSTOM" or "GAUNTLET"
input_text = "45"

# Resolution-based static constraints
MIN_READABLE_CELL_PX = 12
MAX_STATIC_SIZE = int((min(scrn_w, scrn_h) * 0.82) // MIN_READABLE_CELL_PX)
MAX_STATIC_SIZE = MAX_STATIC_SIZE if MAX_STATIC_SIZE % 2 != 0 else MAX_STATIC_SIZE - 1

# Gauntlet mode progress
GAUNTLET_START_SIZE = 15
GAUNTLET_STEP = 10
GAUNTLET_MAX_SIZE = 995
gauntlet_level = 1

# Board geometry
rows = 45
cell_size = 10
board_size = 0
center_x = scrn_w // 2
center_y = scrn_h // 2
start_x = 0
start_y = 0

# Camera state
is_camera_follow = False
cam_x = 0.0
cam_y = 0.0
cam_lead_x = 0.0
cam_lead_y = 0.0

fps = 1000

# Palette
background_color = "#0d1b2a"
traversable_color = "#1b263b"
untraversable_color = "#415a77"
start_color = traversable_color
end_color = traversable_color

player_cube_color = (255, 230, 0)
trail_color = player_cube_color
game_over_cube_color = (220, 20, 60)

# Visual effects
shake_intensity = 0.0
shake_decay = 0.88
shake_offset_x = 0
shake_offset_y = 0

particles = []
shockwaves = []
afterimages = deque(maxlen=6)
current_move_dir = (0, 0)


def trigger_screen_shake(intensity=8.0):
    global shake_intensity
    shake_intensity = max(shake_intensity, intensity)


def spawn_particles(px, py, count=15, color=(0, 240, 255), speed=3.0, max_life=300):
    for _ in range(count):
        angle = random.uniform(0, 2 * math.pi)
        vel = random.uniform(speed * 0.4, speed)
        vx = math.cos(angle) * vel
        vy = math.sin(angle) * vel
        size = random.uniform(2.0, max(3.0, cell_size * 0.35))
        life = random.uniform(max_life * 0.6, max_life)
        particles.append([px, py, vx, vy, life, life, color, size])


def spawn_square_shockwave(cx, cy, max_r=None, color=(0, 240, 255)):
    if max_r is None:
        max_r = max(12, cell_size * 2.8)
    shockwaves.append([cx, cy, 2.0, max_r, 255, color])


def update_visual_effects(dt_ms):
    global shake_intensity, shake_offset_x, shake_offset_y

    dt_s = dt_ms / 1000.0

    if shake_intensity > 0.4:
        shake_offset_x = random.uniform(-shake_intensity, shake_intensity)
        shake_offset_y = random.uniform(-shake_intensity, shake_intensity)
        shake_intensity *= math.exp(-12.0 * dt_s)
    else:
        shake_intensity = 0.0
        shake_offset_x = 0
        shake_offset_y = 0

    for p in particles[:]:
        p[0] += p[2] * (dt_ms / 16.6)
        p[1] += p[3] * (dt_ms / 16.6)
        p[4] -= dt_ms
        if p[4] <= 0:
            particles.remove(p)

    for sw in shockwaves[:]:
        sw[2] += ((sw[3] - sw[2]) * 14.0 * dt_s) + (60.0 * dt_s)
        progress = sw[2] / sw[3]
        sw[4] = max(0, int(255 * (1.0 - progress)))
        if progress >= 1.0 or sw[4] <= 0:
            shockwaves.remove(sw)

# Audio


def make_tone(freq, duration_ms, wave_type="sine", volume=0.25):
    sample_rate = 44100
    n_samples = int(sample_rate * (duration_ms / 1000.0))
    buf = bytearray(n_samples * 2)
    for i in range(n_samples):
        t = float(i) / sample_rate
        if wave_type == "sine":
            val = math.sin(2.0 * math.pi * freq * t)
        elif wave_type == "noise":
            val = random.uniform(-1.0, 1.0)
        else:
            val = 1.0 if (i // (sample_rate // max(1, int(freq)))
                          ) % 2 == 0 else -1.0
        val *= max(0.0, 1.0 - (i / n_samples)) * volume
        sample = int(val * 32767)
        buf[i * 2:i * 2 +
            2] = sample.to_bytes(2, byteorder='little', signed=True)
    return pygame.mixer.Sound(bytes(buf))


try:
    sound_deadend = make_tone(110, 120, "square", volume=0.25)
    sound_undo = make_tone(320, 40, "sine", volume=0.18)
    sound_hint = make_tone(580, 180, "sine", volume=0.20)
    sound_levelup = make_tone(750, 240, "sine", volume=0.25)
    audio_enabled = True
except Exception:
    audio_enabled = False

glide_streak = 0
BASE_CORRIDOR_FREQ = 300.0
MAX_CORRIDOR_FREQ = 620.0
FREQ_STEP = 8.0


def play_corridor_glide_sfx():
    if not audio_enabled:
        return
    freq = min(MAX_CORRIDOR_FREQ, BASE_CORRIDOR_FREQ +
               (glide_streak * FREQ_STEP))
    dur_ms = max(14, int(24 - min(8, glide_streak * 0.3)))
    tone = make_tone(freq, dur_ms, wave_type="sine", volume=0.15)
    tone.play()


def play_sfx(name):
    if not audio_enabled:
        return
    if name == "deadend":
        sound_deadend.play()
    elif name == "undo":
        sound_undo.play()
    elif name == "hint":
        sound_hint.play()
    elif name == "levelup":
        sound_levelup.play()


# Mechanics & Movement
player_grid = [1, 0]
pixel_x = 0.0
pixel_y = 0.0
is_moving = False

BASE_MS_PER_TILE = 35.0
MAX_CORRIDOR_TIME_MS = 1000.0
MANUAL_SINGLE_STEP_MS = 90.0

segment_points = []
segment_start_time = 0
segment_total_duration = 0.0
segment_last_sound_idx = 0

is_game_over = False
is_won = False
is_gauntlet_completed = False

moves_count = 0
optimal_steps = 1
start_time_ms = 0
final_elapsed_seconds = 0.0

HINT_DURATION_MS = 3000
hint_used = False
hint_path = []
hint_timer_ms = 0

input_buffer = deque(maxlen=2)
trail_history = []
trail_set = set()

start_point = (1, 0)
end_point = None

maze_surface = None
scanline_surface = None
render_surface = pygame.Surface((scrn_w, scrn_h))

directions = [
    (-2, 0),
    (0, 2),
    (2, 0),
    (0, -2)
]


def grid_to_pixel(h, w):
    return float(start_x + w * cell_size), float(start_y + h * cell_size)


def initialize():
    board["rect"].clear()
    board["value"].clear()
    for h in range(rows):
        for w in range(rows):
            key = (h, w)
            rx = start_x + (w * cell_size)
            ry = start_y + (h * cell_size)
            board["rect"][key] = pygame.Rect(rx, ry, cell_size, cell_size)
            board["value"][key] = 1


def generate():
    global end_point, optimal_steps

    max_attempts = 15
    best_maze = None
    best_difficulty_score = -1.0

    for attempt in range(max_attempts):
        for key in board["value"]:
            board["value"][key] = 1

        start_cell = (1, 1)
        board["value"][start_cell] = 0

        target_r = rows - 2
        target_c = rows - 2

        stack = [(1, 1, None)]
        visited_nodes = {start_cell}

        while stack:
            h, w, last_dir = stack[-1]
            unvisited = []

            for dh, dw in directions:
                nh, nw = h + dh, w + dw
                if 0 < nh < rows - 1 and 0 < nw < rows - 1:
                    if (nh, nw) not in visited_nodes and board["value"][(nh, nw)] == 1:
                        unvisited.append((nh, nw, dh, dw))

            if unvisited:
                weights = []
                for nh, nw, dh, dw in unvisited:
                    weight = 1.0
                    if last_dir is not None and (dh, dw) == last_dir:
                        weight += 6.5

                    dist_to_exit = abs(nh - target_r) + abs(nw - target_c)
                    if len(stack) < (rows // 2):
                        weight += (dist_to_exit / max(1, rows)) * 2.0
                    else:
                        weight += ((rows * 2 - dist_to_exit) /
                                   max(1, rows)) * 1.5

                    weights.append(weight)

                chosen = random.choices(unvisited, weights=weights, k=1)[0]
                nh, nw, dh, dw = chosen

                board["value"][(h + dh // 2, w + dw // 2)] = 0
                board["value"][(nh, nw)] = 0
                visited_nodes.add((nh, nw))
                stack.append((nh, nw, (dh, dw)))
            else:
                stack.pop()

        board["value"][start_point] = 0

        dead_ends = []
        for r in range(1, rows - 1):
            for c in range(1, rows - 1):
                if board["value"][(r, c)] == 0:
                    wall_count = 0
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        if board["value"].get((r + dr, c + dc), 1) == 1:
                            wall_count += 1
                    if wall_count == 3:
                        dead_ends.append((r, c))

        num_loops = max(1, int(len(dead_ends) * 0.045))
        random.shuffle(dead_ends)
        for dr, dc in dead_ends[:num_loops]:
            neighbors_to_carve = []
            for ddr, ddc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = dr + ddr, dc + ddc
                if 0 < nr < rows - 1 and 0 < nc < rows - 1:
                    if board["value"][(nr, nc)] == 1:
                        far_r, far_c = nr + ddr, nc + ddc
                        if 0 < far_r < rows - 1 and 0 < far_c < rows - 1:
                            if board["value"][(far_r, far_c)] == 0:
                                neighbors_to_carve.append((nr, nc))
            if neighbors_to_carve:
                wall_to_break = random.choice(neighbors_to_carve)
                board["value"][wall_to_break] = 0

        dist = {start_point: 0}
        parents = {start_point: None}
        bfs_q = deque([start_point])
        deepest_cells = []

        while bfs_q:
            curr = bfs_q.popleft()
            cr, cc = curr
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = cr + dr, cc + dc
                if (nr, nc) not in dist and board["value"].get((nr, nc)) == 0:
                    d = dist[curr] + 1
                    dist[(nr, nc)] = d
                    parents[(nr, nc)] = curr
                    bfs_q.append((nr, nc))
                    deepest_cells.append(((nr, nc), d))

        deepest_cells.sort(key=lambda item: item[1], reverse=True)

        chosen_candidate = None
        for (cell, length) in deepest_cells:
            cr, cc = cell
            if cr == 1 or cr == rows - 2 or cc == 1 or cc == rows - 2:
                chosen_candidate = (cell, length)
                break

        if not chosen_candidate:
            chosen_candidate = deepest_cells[0]

        cand_cell, path_length = chosen_candidate

        branch_depths = [d for c, d in deepest_cells if d > 10]
        avg_depth = sum(branch_depths) / max(1, len(branch_depths))
        difficulty_score = (path_length / (rows * 2)) * (avg_depth / 10.0)

        if difficulty_score > best_difficulty_score:
            best_difficulty_score = difficulty_score
            best_maze = {
                "values": dict(board["value"]),
                "exit_inner": cand_cell,
                "opt_steps": path_length
            }

        if path_length >= int(rows * 1.45) and avg_depth >= 16.0:
            break

    if best_maze:
        board["value"] = best_maze["values"]
        inner_tile = best_maze["exit_inner"]
        optimal_steps = best_maze["opt_steps"]
    else:
        inner_tile = (rows - 2, rows - 2)
        optimal_steps = rows * 2

    fh, fw = inner_tile
    edge_candidates = [
        (fh, rows - 1),
        (rows - 1, fw),
        (0, fw),
        (fh, 0)
    ]
    edge_candidates.sort(key=lambda pos: abs(pos[0] - fh) + abs(pos[1] - fw))
    exit_tile = edge_candidates[0]

    board["value"][inner_tile] = 0
    board["value"][exit_tile] = 0
    end_point = exit_tile


def pre_render_maze_and_scanlines():
    global maze_surface, scanline_surface
    if not is_camera_follow:
        maze_surface = pygame.Surface((scrn_w, scrn_h))
        maze_surface.fill(background_color)
        for key, rect in board["rect"].items():
            if key == end_point:
                pygame.draw.rect(maze_surface, end_color, rect)
            elif key == start_point:
                pygame.draw.rect(maze_surface, start_color, rect)
            elif board["value"][key] == 1:
                pygame.draw.rect(maze_surface, untraversable_color, rect)
            else:
                pygame.draw.rect(maze_surface, traversable_color, rect)
    else:
        maze_surface = None

    scanline_surface = pygame.Surface((scrn_w, scrn_h), pygame.SRCALPHA)
    for y in range(0, scrn_h, 3):
        pygame.draw.line(scanline_surface, (0, 0, 0, 22), (0, y), (scrn_w, y))


def handle_menu_input(event):
    global state, game_mode, gauntlet_level
    if event.key == pygame.K_1:
        game_mode = "CUSTOM"
        state = "CONFIG"
    elif event.key == pygame.K_2:
        game_mode = "GAUNTLET"
        gauntlet_level = 1
        start_game_with_size(GAUNTLET_START_SIZE)


def handle_size_input(key_event):
    global input_text
    if key_event.key == pygame.K_RETURN:
        if input_text.strip():
            raw_val = int(input_text.strip())
            raw_val = min(999, max(11, raw_val))
            final_val = raw_val if raw_val % 2 != 0 else raw_val + 1
            start_game_with_size(final_val)
    elif key_event.key == pygame.K_BACKSPACE:
        input_text = input_text[:-1]
    elif key_event.unicode.isdigit():
        if len(input_text) < 3:
            input_text += key_event.unicode


def start_game_with_size(size):
    global rows, cell_size, board_size, start_x, start_y, state, is_camera_follow
    rows = size

    if rows > MAX_STATIC_SIZE:
        is_camera_follow = True
        cell_size = max(20, int(min(scrn_w, scrn_h) * 0.024))
        board_size = cell_size * rows
        start_x = 0
        start_y = 0
    else:
        is_camera_follow = False
        target_board_space = int(min(scrn_w, scrn_h) * 0.82)
        cell_size = target_board_space // rows
        board_size = cell_size * rows
        start_x = center_x - board_size // 2
        start_y = center_y - board_size // 2

    load()
    state = "PLAYING"


def load():
    global player_grid, trail_history, trail_set, pixel_x, pixel_y
    global is_moving, is_game_over, is_won, is_gauntlet_completed, moves_count, start_time_ms, final_elapsed_seconds
    global particles, shockwaves, afterimages, shake_intensity, hint_used, hint_path, hint_timer_ms
    global glide_streak, current_move_dir, cam_x, cam_y, cam_lead_x, cam_lead_y
    global segment_points, segment_last_sound_idx

    initialize()
    generate()
    pre_render_maze_and_scanlines()

    player_grid = list(start_point)
    trail_history = [tuple(player_grid)]
    trail_set = {tuple(player_grid)}

    init_x, init_y = grid_to_pixel(player_grid[0], player_grid[1])
    pixel_x = init_x
    pixel_y = init_y
    cam_x = pixel_x + cell_size / 2 - center_x
    cam_y = pixel_y + cell_size / 2 - center_y
    cam_lead_x = 0.0
    cam_lead_y = 0.0

    is_moving = False
    is_game_over = False
    is_won = False
    is_gauntlet_completed = False
    moves_count = 0
    start_time_ms = pygame.time.get_ticks()
    final_elapsed_seconds = 0.0
    particles.clear()
    shockwaves.clear()
    afterimages.clear()
    shake_intensity = 0.0
    input_buffer.clear()

    segment_points = []
    segment_last_sound_idx = 0

    hint_used = False
    hint_path = []
    hint_timer_ms = 0
    glide_streak = 0
    current_move_dir = (0, 0)


def advance_gauntlet():
    global gauntlet_level, rows, is_gauntlet_completed
    if rows >= GAUNTLET_MAX_SIZE:
        is_gauntlet_completed = True
        return
    gauntlet_level += 1
    play_sfx("levelup")
    next_size = rows + GAUNTLET_STEP
    start_game_with_size(next_size)


def reset_game():
    global gauntlet_level
    if game_mode == "GAUNTLET":
        gauntlet_level = 1
        start_game_with_size(GAUNTLET_START_SIZE)
    else:
        load()


def get_available_moves(pos=None):
    ch, cw = pos if pos else player_grid
    available = []
    for dh, dw in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        target = (ch + dh, cw + dw)
        if target in board["value"] and board["value"][target] == 0:
            if target not in trail_set:
                available.append((dh, dw))
    return available


def trigger_hint():
    global hint_used, hint_path, hint_timer_ms

    if hint_used or is_game_over or is_won or is_moving:
        return

    start_node = tuple(player_grid)
    if start_node == end_point:
        return

    queue = deque([start_node])
    came_from = {start_node: None}

    while queue:
        curr = queue.popleft()
        if curr == end_point:
            break

        ch, cw = curr
        for dh, dw in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            neighbor = (ch + dh, cw + dw)
            if neighbor in board["value"] and board["value"][neighbor] == 0:
                if neighbor not in came_from and (neighbor not in trail_set or neighbor == start_node):
                    came_from[neighbor] = curr
                    queue.append(neighbor)

    if end_point in came_from:
        path = []
        curr = end_point
        while curr is not None:
            path.append(curr)
            curr = came_from[curr]
        path.reverse()
        hint_path = path
        hint_used = True
        hint_timer_ms = pygame.time.get_ticks()
        play_sfx("hint")
    else:
        play_sfx("deadend")


def compute_glide_corridor(start_pos, first_step_dir):
    path = []
    curr = (start_pos[0] + first_step_dir[0], start_pos[1] + first_step_dir[1])
    path.append(curr)

    sim_trail = set(trail_set)
    sim_trail.add(curr)

    while True:
        if curr == end_point:
            break

        ch, cw = curr
        avail = []
        for dh, dw in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nh, nw = ch + dh, cw + dw
            target = (nh, nw)
            if target in board["value"] and board["value"][target] == 0:
                if target not in sim_trail:
                    avail.append((dh, dw))

        if len(avail) != 1:
            break

        dh, dw = avail[0]
        curr = (ch + dh, cw + dw)
        path.append(curr)
        sim_trail.add(curr)

    return path


def try_step(dh, dw):
    global is_moving, segment_points, segment_start_time, segment_total_duration
    global segment_last_sound_idx, moves_count, current_move_dir

    if is_game_over or is_won or is_moving:
        return False

    nh = player_grid[0] + dh
    nw = player_grid[1] + dw
    target = (nh, nw)

    if target in board["value"] and board["value"][target] == 0:
        if target not in trail_set:
            segment_points = compute_glide_corridor(player_grid, (dh, dw))
            segment_start_time = pygame.time.get_ticks()

            count = len(segment_points)
            if count > 1:
                calculated_time = count * BASE_MS_PER_TILE
                segment_total_duration = min(
                    MAX_CORRIDOR_TIME_MS, calculated_time)
            else:
                segment_total_duration = MANUAL_SINGLE_STEP_MS

            segment_last_sound_idx = 0
            current_move_dir = (dh, dw)

            moves_count += count
            is_moving = True
            return True
    return False


def queue_input(dh, dw):
    if is_game_over or is_won:
        return
    if not is_moving:
        try_step(dh, dw)
    else:
        input_buffer.append((dh, dw))


def undo():
    global player_grid, pixel_x, pixel_y
    global is_moving, is_game_over, is_won, glide_streak, afterimages, current_move_dir
    global segment_points, segment_last_sound_idx

    if is_moving or len(trail_history) <= 1:
        return

    is_game_over = False
    is_won = False
    glide_streak = 0
    current_move_dir = (0, 0)
    input_buffer.clear()
    afterimages.clear()
    segment_points = []
    segment_last_sound_idx = 0

    removed_tile = trail_history.pop()
    trail_set.discard(removed_tile)

    while len(trail_history) > 1:
        prev_tile = trail_history[-1]
        player_grid = list(prev_tile)
        if len(get_available_moves(prev_tile)) > 1:
            break
        removed_tile = trail_history.pop()
        trail_set.discard(removed_tile)

    last_tile = trail_history[-1]
    player_grid = list(last_tile)
    init_x, init_y = grid_to_pixel(player_grid[0], player_grid[1])
    pixel_x = init_x
    pixel_y = init_y
    play_sfx("undo")


def process_buffered_input():
    while input_buffer:
        dh, dw = input_buffer.popleft()
        if try_step(dh, dw):
            return True
    return False


def get_squash_and_stretch_geometry():
    if glide_streak < 2 or not is_moving:
        return pixel_x, pixel_y, cell_size, cell_size

    stretch = min(3.5, max(1.0, cell_size * 0.14 *
                  min(1.0, glide_streak / 6.0)))
    dh, dw = current_move_dir

    if dw != 0:
        rx = pixel_x - (stretch if dw > 0 else 0)
        ry = pixel_y + stretch * 0.5
        rw = cell_size + stretch
        rh = max(2.0, cell_size - stretch)
    elif dh != 0:
        rx = pixel_x + stretch * 0.5
        ry = pixel_y - (stretch if dh > 0 else 0)
        rw = max(2.0, cell_size - stretch)
        rh = cell_size + stretch
    else:
        rx, ry, rw, rh = pixel_x, pixel_y, cell_size, cell_size

    return rx, ry, rw, rh


def update_player_animation(dt_ms=16.6):
    global pixel_x, pixel_y, is_moving, is_game_over, is_won, final_elapsed_seconds
    global glide_streak, current_move_dir, cam_x, cam_y, cam_lead_x, cam_lead_y
    global segment_last_sound_idx

    if state != "PLAYING":
        return

    dt_s = min(0.05, max(0.0001, dt_ms / 1000.0))
    update_visual_effects(dt_ms)

    if is_camera_follow:
        dh, dw = current_move_dir
        target_lead_x = dw * (cell_size * 2.8)
        target_lead_y = dh * (cell_size * 2.8)

        lead_decay = 1.0 - math.exp(-6.0 * dt_s)
        cam_lead_x += (target_lead_x - cam_lead_x) * lead_decay
        cam_lead_y += (target_lead_y - cam_lead_y) * lead_decay

        target_cam_x = pixel_x + cell_size / 2 - center_x + cam_lead_x
        target_cam_y = pixel_y + cell_size / 2 - center_y + cam_lead_y

        cam_decay = 1.0 - math.exp(-7.5 * dt_s)
        cam_x += (target_cam_x - cam_x) * cam_decay
        cam_y += (target_cam_y - cam_y) * cam_decay

    if not is_moving or not segment_points:
        afterimages.clear()
        return

    elapsed = pygame.time.get_ticks() - segment_start_time
    progress = min(1.0, elapsed / max(1.0, segment_total_duration))

    num_sub_segments = len(segment_points)
    continuous_index = progress * num_sub_segments

    sub_idx = min(int(continuous_index), num_sub_segments - 1)
    local_t = continuous_index - sub_idx

    p0_grid = player_grid if sub_idx == 0 else segment_points[sub_idx - 1]
    p1_grid = segment_points[sub_idx]

    while segment_last_sound_idx <= sub_idx:
        tile = segment_points[segment_last_sound_idx]
        if tile not in trail_set:
            glide_streak += 1
            play_corridor_glide_sfx()
            trail_history.append(tile)
            trail_set.add(tile)
        segment_last_sound_idx += 1

    x0, y0 = grid_to_pixel(p0_grid[0], p0_grid[1])
    x1, y1 = grid_to_pixel(p1_grid[0], p1_grid[1])

    pixel_x = x0 + (x1 - x0) * local_t
    pixel_y = y0 + (y1 - y0) * local_t

    current_move_dir = (p1_grid[0] - p0_grid[0], p1_grid[1] - p0_grid[1])

    if len(segment_points) > 1:
        rx, ry, rw, rh = get_squash_and_stretch_geometry()
        afterimages.append((rx, ry, rw, rh, player_cube_color))

    if progress >= 1.0:
        final_node = segment_points[-1]
        player_grid[0], player_grid[1] = final_node
        pixel_x, pixel_y = grid_to_pixel(final_node[0], final_node[1])

        is_moving = False
        afterimages.clear()

        center_p_x = pixel_x + cell_size / 2
        center_p_y = pixel_y + cell_size / 2

        if tuple(player_grid) == end_point:
            glide_streak = 0
            current_move_dir = (0, 0)
            is_won = True
            final_elapsed_seconds = (
                pygame.time.get_ticks() - start_time_ms) / 1000.0
            input_buffer.clear()
            trigger_screen_shake(12.0)
            spawn_square_shockwave(
                center_p_x, center_p_y, max_r=cell_size * 5.0, color=(255, 215, 0))
            spawn_particles(center_p_x, center_p_y, count=40,
                            color=(255, 215, 0), speed=5.5, max_life=600)

            # Gauntlet Auto-Progression
            if game_mode == "GAUNTLET":
                if rows < GAUNTLET_MAX_SIZE:
                    advance_gauntlet()
            return

        available = get_available_moves()

        if len(available) == 0:
            glide_streak = 0
            current_move_dir = (0, 0)
            is_game_over = True
            final_elapsed_seconds = (
                pygame.time.get_ticks() - start_time_ms) / 1000.0
            input_buffer.clear()
            play_sfx("deadend")
            trigger_screen_shake(9.0)
            spawn_square_shockwave(
                center_p_x, center_p_y, max_r=cell_size * 3.5, color=(220, 20, 60))
            spawn_particles(center_p_x, center_p_y, count=25,
                            color=(220, 20, 60), speed=4.0, max_life=450)
            return

        else:
            if len(segment_points) > 2:
                spawn_square_shockwave(
                    center_p_x, center_p_y, max_r=cell_size * 2.2, color=(0, 240, 255))
            glide_streak = 0
            current_move_dir = (0, 0)
            process_buffered_input()


def draw_exit_pointer(surface, ox, oy):
    if not end_point or not is_camera_follow:
        return

    ex_world = start_x + end_point[1] * cell_size + cell_size / 2
    ey_world = start_y + end_point[0] * cell_size + cell_size / 2

    ex_scr = ex_world - ox
    ey_scr = ey_world - oy

    margin = 55
    if margin <= ex_scr <= scrn_w - margin and margin <= ey_scr <= scrn_h - margin:
        return

    dx = ex_scr - center_x
    dy = ey_scr - center_y
    angle = math.atan2(dy, dx)

    bound_w = (scrn_w // 2) - 48
    bound_h = (scrn_h // 2) - 48

    cos_a = math.cos(angle)
    sin_a = math.sin(angle)

    if abs(cos_a) * bound_h > abs(sin_a) * bound_w:
        edge_dist = abs(bound_w / max(1e-5, cos_a))
    else:
        edge_dist = abs(bound_h / max(1e-5, sin_a))

    edge_x = center_x + edge_dist * cos_a
    edge_y = center_y + edge_dist * sin_a

    size = 18
    tip = (edge_x + math.cos(angle) * size, edge_y + math.sin(angle) * size)
    left = (edge_x + math.cos(angle + 2.5) * size,
            edge_y + math.sin(angle + 2.5) * size)
    right = (edge_x + math.cos(angle - 2.5) * size,
             edge_y + math.sin(angle - 2.5) * size)
    notch = (edge_x, edge_y)

    poly = [tip, left, notch, right]
    pygame.draw.polygon(surface, (255, 170, 0), poly)
    pygame.draw.polygon(surface, (255, 255, 200), poly, 1)

    dist_tiles = int(math.hypot(
        end_point[0] - player_grid[0], end_point[1] - player_grid[1]))
    font = pygame.font.SysFont("Consolas", 14, bold=True)
    txt = font.render(f"{dist_tiles}m", True, (255, 215, 0))

    txt_x = edge_x - math.cos(angle) * 24 - txt.get_width() // 2
    txt_y = edge_y - math.sin(angle) * 24 - txt.get_height() // 2
    surface.blit(txt, (txt_x, txt_y))


def draw_hint_line(surface, ox, oy):
    if not hint_path:
        return

    elapsed = pygame.time.get_ticks() - hint_timer_ms
    if elapsed >= HINT_DURATION_MS:
        return

    alpha = max(0, min(255, int(255 * (1.0 - (elapsed / HINT_DURATION_MS)))))
    points = [(board["rect"][tile].centerx - ox, board["rect"]
               [tile].centery - oy) for tile in hint_path]

    if len(points) < 2:
        return

    glow_surf = pygame.Surface((scrn_w, scrn_h), pygame.SRCALPHA)
    pygame.draw.lines(glow_surf, (255, 215, 0, int(alpha * 0.45)),
                      False, points, max(4, cell_size // 2))
    pygame.draw.lines(glow_surf, (255, 255, 230, alpha),
                      False, points, max(1, cell_size // 6))
    surface.blit(glow_surf, (0, 0))


def draw_speed_lines(surface):
    if glide_streak < 5:
        return

    dh, dw = current_move_dir
    line_surf = pygame.Surface((scrn_w, scrn_h), pygame.SRCALPHA)
    streak_intensity = min(1.0, (glide_streak - 4) / 8.0)
    alpha = int(140 * streak_intensity)

    if dw != 0:
        for _ in range(7):
            y = random.randint(
                start_y, start_y + board_size) if not is_camera_follow else random.randint(0, scrn_h)
            length = random.randint(35, 120)
            x = random.randint(0, 80) if dw > 0 else random.randint(
                scrn_w - 140, scrn_w)
            pygame.draw.line(line_surf, (0, 240, 255, alpha),
                             (x, y), (x + length, y), 1)
    elif dh != 0:
        for _ in range(7):
            x = random.randint(
                start_x, start_x + board_size) if not is_camera_follow else random.randint(0, scrn_w)
            length = random.randint(35, 120)
            y = random.randint(0, 80) if dh > 0 else random.randint(
                scrn_h - 140, scrn_h)
            pygame.draw.line(line_surf, (0, 240, 255, alpha),
                             (x, y), (x + length, y), 1)

    surface.blit(line_surf, (0, 0))


def draw_menu(screen):
    screen.fill(background_color)
    title_font = pygame.font.SysFont("Consolas", 44, bold=True)
    opt_font = pygame.font.SysFont("Consolas", 24, bold=True)
    sub_font = pygame.font.SysFont("Consolas", 16)

    title_surf = title_font.render("CIRCUIT DASH", True, (0, 240, 255))
    screen.blit(
        title_surf, (center_x - title_surf.get_width() // 2, center_y - 160))

    opt1_surf = opt_font.render("[1] CUSTOM GRID SIZE", True, (255, 230, 0))
    opt1_sub = sub_font.render(
        "Specify custom dimensions (11 to 999)", True, (160, 180, 200))
    screen.blit(
        opt1_surf, (center_x - opt1_surf.get_width() // 2, center_y - 60))
    screen.blit(opt1_sub, (center_x - opt1_sub.get_width() // 2, center_y - 28))

    opt2_surf = opt_font.render("[2] GAUNTLET RUN", True, (255, 230, 0))
    opt2_sub = sub_font.render(
        "Permadeath run: 15x15 -> 995x995 (+10/lvl). Failing resets to Lv 1!", True, (160, 180, 200))
    screen.blit(
        opt2_surf, (center_x - opt2_surf.get_width() // 2, center_y + 35))
    screen.blit(opt2_sub, (center_x - opt2_sub.get_width() // 2, center_y + 67))

    esc_surf = sub_font.render("Press [ESC] to Exit", True, (100, 120, 140))
    screen.blit(esc_surf, (center_x - esc_surf.get_width() // 2, center_y + 160))


def draw_config(screen):
    screen.fill(background_color)
    title_font = pygame.font.SysFont("Consolas", 38, bold=True)
    sub_font = pygame.font.SysFont("Consolas", 18)

    title_surf = title_font.render("ENTER GRID SIZE", True, (0, 240, 255))
    info_surf = sub_font.render(
        f"Resolution: {scrn_w}x{scrn_h} | Static up to {MAX_STATIC_SIZE}x{MAX_STATIC_SIZE} (Max Limit: 999)",
        True,
        (160, 180, 200)
    )
    display_val = input_text if input_text else "_"
    input_box_surf = title_font.render(
        f"> {display_val} <", True, (255, 230, 0))
    prompt_surf = sub_font.render(
        "Press [ENTER] to Generate | [ESC] for Menu", True, (255, 255, 255))

    screen.blit(
        title_surf, (center_x - title_surf.get_width() // 2, center_y - 120))
    screen.blit(
        info_surf, (center_x - info_surf.get_width() // 2, center_y - 65))
    screen.blit(input_box_surf, (center_x -
                input_box_surf.get_width() // 2, center_y - 10))
    screen.blit(prompt_surf, (center_x -
                prompt_surf.get_width() // 2, center_y + 60))


def draw(screen):
    if state == "MENU":
        draw_menu(screen)
        return
    elif state == "CONFIG":
        draw_config(screen)
        return

    render_surface.fill(background_color)

    ox = round(cam_x) if is_camera_follow else 0
    oy = round(cam_y) if is_camera_follow else 0

    if maze_surface and not is_camera_follow:
        render_surface.blit(maze_surface, (0, 0))
    else:
        min_col = max(0, int(ox // cell_size) - 1)
        max_col = min(rows, int((ox + scrn_w) // cell_size) + 2)
        min_row = max(0, int(oy // cell_size) - 1)
        max_row = min(rows, int((oy + scrn_h) // cell_size) + 2)

        for r in range(min_row, max_row):
            for c in range(min_col, max_col):
                key = (r, c)
                val = board["value"].get(key, 1)
                rx = start_x + c * cell_size - ox
                ry = start_y + r * cell_size - oy
                draw_rect = pygame.Rect(rx, ry, cell_size, cell_size)

                if key == end_point:
                    pygame.draw.rect(render_surface, end_color, draw_rect)
                elif key == start_point:
                    pygame.draw.rect(render_surface, start_color, draw_rect)
                elif val == 1:
                    pygame.draw.rect(
                        render_surface, untraversable_color, draw_rect)
                else:
                    pygame.draw.rect(
                        render_surface, traversable_color, draw_rect)

    if end_point:
        ex = start_x + end_point[1] * cell_size - ox
        ey = start_y + end_point[0] * cell_size - oy
        end_rect = pygame.Rect(ex, ey, cell_size, cell_size)

        t = pygame.time.get_ticks() * 0.003
        for ring_idx in range(3):
            phase = (t + ring_idx * (1.0 / 3.0)) % 1.0
            scale = 1.0 - phase
            w = max(2, int(cell_size * scale))
            h = max(2, int(cell_size * scale))
            rx = end_rect.centerx - w // 2
            ry = end_rect.centery - h // 2
            ring_alpha = int(220 * phase)
            ring_surf = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(
                ring_surf, (255, 180, 30, ring_alpha), (0, 0, w, h), 1)
            render_surface.blit(ring_surf, (rx, ry))

    for key in trail_history:
        rx = start_x + key[1] * cell_size - ox
        ry = start_y + key[0] * cell_size - oy
        if -cell_size <= rx <= scrn_w and -cell_size <= ry <= scrn_h:
            pygame.draw.rect(render_surface, trail_color,
                             pygame.Rect(rx, ry, cell_size, cell_size))

    draw_hint_line(render_surface, ox, oy)

    if not is_moving and not is_game_over and not is_won:
        available = get_available_moves()
        if len(available) >= 2:
            ch, cw = player_grid
            marker_dim = max(2, cell_size // 4)
            for dh, dw in available:
                cx = (start_x + (cw + dw) * cell_size + cell_size // 2) - ox
                cy = (start_y + (ch + dh) * cell_size + cell_size // 2) - oy
                reticle_rect = pygame.Rect(
                    cx - marker_dim // 2, cy - marker_dim // 2, marker_dim, marker_dim)
                pygame.draw.rect(render_surface, (255, 230, 0), reticle_rect)

    for idx, (gx, gy, gw, gh, col) in enumerate(afterimages):
        alpha_factor = (idx + 1) / (len(afterimages) + 1)
        ghost_surf = pygame.Surface((round(gw), round(gh)), pygame.SRCALPHA)
        ghost_surf.fill((col[0], col[1], col[2], int(95 * alpha_factor)))
        render_surface.blit(ghost_surf, (round(gx - ox), round(gy - oy)))

    for sw in shockwaves:
        cx, cy, current_r, _, alpha, col = sw
        side = int(current_r * 2)
        if side > 2 and alpha > 0:
            sw_surf = pygame.Surface((side, side), pygame.SRCALPHA)
            pygame.draw.rect(
                sw_surf, (col[0], col[1], col[2], alpha), (0, 0, side, side), 1)
            render_surface.blit(
                sw_surf, (cx - side // 2 - ox, cy - side // 2 - oy))

    for p in particles:
        alpha_ratio = max(0.0, p[4] / p[5])
        size = max(1.0, p[7] * alpha_ratio)
        p_rect = pygame.Rect(round(p[0] - size / 2 - ox), round(
            p[1] - size / 2 - oy), max(1, round(size)), max(1, round(size)))
        pygame.draw.rect(render_surface, p[6], p_rect)

    color = game_over_cube_color if is_game_over else player_cube_color
    px, py, pw, ph = get_squash_and_stretch_geometry()
    player_rect = pygame.Rect(
        round(px - ox), round(py - oy), round(pw), round(ph))

    glow_surf = pygame.Surface((scrn_w, scrn_h), pygame.SRCALPHA)
    pygame.draw.rect(
        glow_surf, (color[0], color[1], color[2], 50), player_rect.inflate(6, 6), 1)
    pygame.draw.rect(
        glow_surf, (color[0], color[1], color[2], 120), player_rect.inflate(2, 2), 1)
    render_surface.blit(glow_surf, (0, 0))

    pygame.draw.rect(render_surface, color, player_rect)

    draw_speed_lines(render_surface)
    draw_exit_pointer(render_surface, ox, oy)

    if scanline_surface:
        render_surface.blit(scanline_surface, (0, 0))

    hud_font = pygame.font.SysFont("Consolas", 15)
    current_time = final_elapsed_seconds if (is_won or is_game_over) else (
        pygame.time.get_ticks() - start_time_ms) / 1000.0

    timer_surface = hud_font.render(
        f"Time: {current_time:05.1f}s", True, (255, 255, 255))
    moves_surface = hud_font.render(
        f"Steps: {moves_count} (Opt: {optimal_steps})", True, (255, 255, 255))

    hint_status = "[H] Hint (USED)" if hint_used else "[H] Hint (1x)"
    hint_color = (120, 130, 140) if hint_used else (255, 215, 0)
    mode_str = f" | GAUNTLET LV.{gauntlet_level} ({rows}x{rows})" if game_mode == "GAUNTLET" else f" | CUSTOM ({rows}x{rows})"
    cam_str = " [CAM]" if is_camera_follow else ""
    center_hud = hud_font.render(
        f"[Z] Undo | {hint_status} | [R] Reset | [M] Menu{mode_str}{cam_str}", True, hint_color)

    render_surface.blit(timer_surface, (24, 20))
    render_surface.blit(
        center_hud, (center_x - center_hud.get_width() // 2, 20))
    render_surface.blit(
        moves_surface, (scrn_w - moves_surface.get_width() - 24, scrn_h - 36))

    banner_font = pygame.font.SysFont(None, 40)
    if is_gauntlet_completed:
        text = banner_font.render(
            "GAUNTLET MASTER! Cleared Level 99 (995x995)! [M] Menu", True, (255, 215, 0))
        render_surface.blit(
            text, (center_x - text.get_width() // 2, scrn_h // 2 + 80))
    elif is_won and game_mode == "CUSTOM":
        efficiency = round((optimal_steps / max(1, moves_count)) * 100)
        text = banner_font.render(
            f"Escaped in {final_elapsed_seconds:.1f}s! Rating: {efficiency}% | [R] Restart", True, (255, 215, 0))
        render_surface.blit(
            text, (center_x - text.get_width() // 2, scrn_h // 2 + 80))
    elif is_game_over:
        if game_mode == "GAUNTLET":
            text = banner_font.render(
                f"Failed at Level {gauntlet_level} ({rows}x{rows})! [R] Reset to Lv 1 | [Z] Undo", True, (255, 69, 0))
        else:
            text = banner_font.render(
                "Trapped! Press [Z] to Undo or [R] to Restart", True, (255, 69, 0))
        render_surface.blit(
            text, (center_x - text.get_width() // 2, scrn_h // 2 + 80))

    screen.fill(background_color)
    screen.blit(render_surface, (round(shake_offset_x), round(shake_offset_y)))
