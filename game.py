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
state = "CONFIG"  # "CONFIG" (size prompt) or "PLAYING"
input_text = "45"

# Board geometry
rows = 45
cell_size = 10
board_size = 0
center_x = scrn_w // 2
center_y = scrn_h // 2
start_x = 0
start_y = 0

fps = 60

# Palette
background_color = "#0d1b2a"
traversable_color = "#1b263b"
untraversable_color = "#415a77"
start_color = traversable_color
end_color = traversable_color

trail_start_rgb = (0, 240, 255)
trail_end_rgb = (10, 45, 90)
player_cube_color = (255, 230, 0)
game_over_cube_color = (220, 20, 60)

# -------------------------------------------------------------
# Screen Shake & Particle System State
# -------------------------------------------------------------
shake_intensity = 0.0
shake_decay = 0.88
shake_offset_x = 0
shake_offset_y = 0

particles = []


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


def update_particles_and_shake(dt_ms):
    global shake_intensity, shake_offset_x, shake_offset_y

    if shake_intensity > 0.4:
        shake_offset_x = random.uniform(-shake_intensity, shake_intensity)
        shake_offset_y = random.uniform(-shake_intensity, shake_intensity)
        shake_intensity *= shake_decay
    else:
        shake_intensity = 0.0
        shake_offset_x = 0
        shake_offset_y = 0

    for p in particles[:]:
        p[0] += p[2]
        p[1] += p[3]
        p[4] -= dt_ms
        if p[4] <= 0:
            particles.remove(p)

# -------------------------------------------------------------
# Procedural Audio & Dynamic Pitch System
# -------------------------------------------------------------


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
    sound_deadend = make_tone(110, 120, "square", volume=0.28)
    sound_undo = make_tone(350, 40, "sine", volume=0.2)
    sound_hint = make_tone(880, 180, "sine", volume=0.22)
    audio_enabled = True
except Exception:
    audio_enabled = False

glide_streak = 0
BASE_CORRIDOR_FREQ = 420.0
MAX_CORRIDOR_FREQ = 1450.0
FREQ_STEP = 38.0


def play_corridor_glide_sfx():
    if not audio_enabled:
        return
    freq = min(MAX_CORRIDOR_FREQ, BASE_CORRIDOR_FREQ +
               (glide_streak * FREQ_STEP))
    dur_ms = max(10, int(22 - min(12, glide_streak * 0.8)))
    tone = make_tone(freq, dur_ms, wave_type="sine", volume=0.18)
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


# -------------------------------------------------------------
# Player, Movement, History & Hint State
# -------------------------------------------------------------
player_grid = [1, 0]
pixel_x = 0.0
pixel_y = 0.0
target_pixel_x = 0.0
target_pixel_y = 0.0
is_moving = False

# Tuned high-speed dual lerp system
BASE_LERP_SPEED = 0.55
AUTO_LERP_SPEED = 0.85
current_lerp_speed = BASE_LERP_SPEED

is_game_over = False
is_won = False

moves_count = 0
optimal_steps = 1
start_time_ms = 0
final_elapsed_seconds = 0.0

# 3-Second Flash Hint System
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
    maze_start = (1, 1)
    board["value"][maze_start] = 0
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

    board["value"][start_point] = 0

    dist = {start_point: 0}
    queue = deque([start_point])
    farthest_cell = start_point
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

    fh, fw = farthest_cell
    edge_candidates = [
        (fh, rows - 1, fh, rows - 2),
        (rows - 1, fw, rows - 2, fw),
        (0, fw, 1, fw),
        (fh, 0, fh, 1)
    ]
    edge_candidates.sort(key=lambda item: abs(
        item[0] - fh) + abs(item[1] - fw))
    exit_tile, inner_tile = edge_candidates[0][:2], edge_candidates[0][2:]

    board["value"][inner_tile] = 0
    board["value"][exit_tile] = 0
    end_point = exit_tile
    optimal_steps = dist.get(inner_tile, max_dist) + 1


def pre_render_maze():
    global maze_surface
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


def handle_size_input(key_event):
    global input_text, state

    if key_event.key == pygame.K_RETURN:
        if input_text.strip():
            raw_val = int(input_text.strip())
            final_val = raw_val if raw_val % 2 != 0 else raw_val + 1
            final_val = max(11, final_val)
            start_game_with_size(final_val)
    elif key_event.key == pygame.K_BACKSPACE:
        input_text = input_text[:-1]
    elif key_event.unicode.isdigit():
        if len(input_text) < 3:
            input_text += key_event.unicode


def start_game_with_size(size):
    global rows, cell_size, board_size, start_x, start_y, state
    rows = size

    min_dim = min(scrn_w, scrn_h)
    target_board_size = int(min_dim * 0.82)
    cell_size = max(4, target_board_size // rows)
    board_size = cell_size * rows

    start_x = center_x - board_size // 2
    start_y = center_y - board_size // 2

    load()
    state = "PLAYING"


def load():
    global player_grid, trail_history, trail_set, pixel_x, pixel_y, target_pixel_x, target_pixel_y
    global is_moving, is_game_over, is_won, moves_count, start_time_ms, final_elapsed_seconds
    global particles, shake_intensity, hint_used, hint_path, hint_timer_ms, glide_streak, current_lerp_speed

    initialize()
    generate()
    pre_render_maze()

    player_grid = list(start_point)
    trail_history = [tuple(player_grid)]
    trail_set = {tuple(player_grid)}

    init_x, init_y = grid_to_pixel(player_grid[0], player_grid[1])
    pixel_x = target_pixel_x = init_x
    pixel_y = target_pixel_y = init_y
    is_moving = False
    is_game_over = False
    is_won = False
    moves_count = 0
    start_time_ms = pygame.time.get_ticks()
    final_elapsed_seconds = 0.0
    particles.clear()
    shake_intensity = 0.0
    input_buffer.clear()

    hint_used = False
    hint_path = []
    hint_timer_ms = 0
    glide_streak = 0
    current_lerp_speed = BASE_LERP_SPEED


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


def try_step(dh, dw, is_auto=False):
    global target_pixel_x, target_pixel_y, is_moving, moves_count, current_lerp_speed

    if is_game_over or is_won:
        return False

    nh = player_grid[0] + dh
    nw = player_grid[1] + dw
    target = (nh, nw)

    if target in board["value"] and board["value"][target] == 0:
        if target not in trail_set:
            player_grid[0] = nh
            player_grid[1] = nw
            trail_history.append(target)
            trail_set.add(target)
            moves_count += 1

            current_lerp_speed = min(
                0.95, AUTO_LERP_SPEED + (glide_streak * 0.01)) if is_auto else BASE_LERP_SPEED

            target_pixel_x, target_pixel_y = grid_to_pixel(nh, nw)
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
    global player_grid, pixel_x, pixel_y, target_pixel_x, target_pixel_y
    global is_moving, is_game_over, is_won, glide_streak, current_lerp_speed

    if is_moving or len(trail_history) <= 1:
        return

    is_game_over = False
    is_won = False
    glide_streak = 0
    current_lerp_speed = BASE_LERP_SPEED
    input_buffer.clear()

    removed = trail_history.pop()
    trail_set.discard(removed)

    while len(trail_history) > 1:
        prev = trail_history[-1]
        player_grid = list(prev)
        if len(get_available_moves(prev)) > 1:
            break
        removed = trail_history.pop()
        trail_set.discard(removed)

    player_grid = list(trail_history[-1])
    init_x, init_y = grid_to_pixel(player_grid[0], player_grid[1])
    pixel_x = target_pixel_x = init_x
    pixel_y = target_pixel_y = init_y
    play_sfx("undo")


def process_buffered_input():
    while input_buffer:
        dh, dw = input_buffer.popleft()
        if try_step(dh, dw):
            return True
    return False


def update_player_animation(dt_ms=16.6):
    global pixel_x, pixel_y, is_moving, is_game_over, is_won, final_elapsed_seconds, glide_streak, current_lerp_speed

    if state != "PLAYING":
        return

    update_particles_and_shake(dt_ms)

    if not is_moving:
        return

    pixel_x += (target_pixel_x - pixel_x) * current_lerp_speed
    pixel_y += (target_pixel_y - pixel_y) * current_lerp_speed

    # Snappier 1.2px threshold eliminates the slow deceleration tail
    if abs(pixel_x - target_pixel_x) < 1.2 and abs(pixel_y - target_pixel_y) < 1.2:
        pixel_x = target_pixel_x
        pixel_y = target_pixel_y
        is_moving = False

        center_p_x = pixel_x + cell_size / 2
        center_p_y = pixel_y + cell_size / 2

        if tuple(player_grid) == end_point:
            glide_streak = 0
            current_lerp_speed = BASE_LERP_SPEED
            is_won = True
            final_elapsed_seconds = (
                pygame.time.get_ticks() - start_time_ms) / 1000.0
            input_buffer.clear()
            trigger_screen_shake(12.0)
            spawn_particles(center_p_x, center_p_y, count=40,
                            color=(255, 215, 0), speed=5.5, max_life=600)
            return

        available = get_available_moves()

        if len(available) == 0:
            glide_streak = 0
            current_lerp_speed = BASE_LERP_SPEED
            is_game_over = True
            final_elapsed_seconds = (
                pygame.time.get_ticks() - start_time_ms) / 1000.0
            input_buffer.clear()
            play_sfx("deadend")
            trigger_screen_shake(9.0)
            spawn_particles(center_p_x, center_p_y, count=25,
                            color=(220, 20, 60), speed=4.0, max_life=450)
            return

        elif len(available) == 1:
            glide_streak += 1
            play_corridor_glide_sfx()
            spawn_particles(center_p_x, center_p_y, count=2,
                            color=(0, 240, 255), speed=1.8, max_life=140)
            dh, dw = available[0]
            try_step(dh, dw, is_auto=True)
            return

        else:
            glide_streak = 0
            current_lerp_speed = BASE_LERP_SPEED
            process_buffered_input()


def draw_hint_line(surface):
    if not hint_path:
        return

    elapsed = pygame.time.get_ticks() - hint_timer_ms
    if elapsed >= HINT_DURATION_MS:
        return

    alpha = max(0, min(255, int(255 * (1.0 - (elapsed / HINT_DURATION_MS)))))
    points = [board["rect"][tile].center for tile in hint_path]

    if len(points) < 2:
        return

    glow_surf = pygame.Surface((scrn_w, scrn_h), pygame.SRCALPHA)
    pygame.draw.lines(glow_surf, (255, 215, 0, int(alpha * 0.45)),
                      False, points, max(4, cell_size // 2))
    pygame.draw.lines(glow_surf, (255, 255, 230, alpha),
                      False, points, max(1, cell_size // 6))
    surface.blit(glow_surf, (0, 0))


def draw_config(screen):
    screen.fill(background_color)
    title_font = pygame.font.SysFont("Consolas", 38, bold=True)
    sub_font = pygame.font.SysFont("Consolas", 22)

    title_surf = title_font.render("ENTER MAZE SIZE", True, (0, 240, 255))
    info_surf = sub_font.render(
        "(Even numbers automatically increment to odd)", True, (160, 180, 200))
    display_val = input_text if input_text else "_"
    input_box_surf = title_font.render(
        f"> {display_val} <", True, (255, 230, 0))
    prompt_surf = sub_font.render(
        "Press [ENTER] to Generate", True, (255, 255, 255))

    screen.blit(
        title_surf, (center_x - title_surf.get_width() // 2, center_y - 120))
    screen.blit(
        info_surf, (center_x - info_surf.get_width() // 2, center_y - 65))
    screen.blit(input_box_surf, (center_x -
                input_box_surf.get_width() // 2, center_y - 10))
    screen.blit(prompt_surf, (center_x -
                prompt_surf.get_width() // 2, center_y + 60))


def draw(screen):
    if state == "CONFIG":
        draw_config(screen)
        return

    render_surface.fill(background_color)

    if maze_surface:
        render_surface.blit(maze_surface, (0, 0))

    # Trail
    total_trail = len(trail_history)
    for idx, key in enumerate(trail_history):
        t = (idx / max(1, total_trail - 1))
        r = int(trail_end_rgb[0] + (trail_start_rgb[0] - trail_end_rgb[0]) * t)
        g = int(trail_end_rgb[1] + (trail_start_rgb[1] - trail_end_rgb[1]) * t)
        b = int(trail_end_rgb[2] + (trail_start_rgb[2] - trail_end_rgb[2]) * t)
        pygame.draw.rect(render_surface, (r, g, b), board["rect"][key])

    # 3-Second Glowing Path Hint
    draw_hint_line(render_surface)

    # Intersection indicators
    if not is_moving and not is_game_over and not is_won:
        available = get_available_moves()
        if len(available) >= 2:
            ch, cw = player_grid
            for dh, dw in available:
                target_rect = board["rect"][(ch + dh, cw + dw)]
                pygame.draw.circle(render_surface, (255, 230, 0),
                                   target_rect.center, max(2, cell_size // 5))

    # Particles
    for p in particles:
        alpha_ratio = max(0.0, p[4] / p[5])
        size = max(1.0, p[7] * alpha_ratio)
        pygame.draw.circle(
            render_surface, p[6], (round(p[0]), round(p[1])), round(size))

    # Player cube (Strict sharp-corner geometry)
    color = game_over_cube_color if is_game_over else player_cube_color
    player_rect = pygame.Rect(
        round(pixel_x), round(pixel_y), cell_size, cell_size)
    pygame.draw.rect(render_surface, color, player_rect)

    # HUD Elements
    hud_font = pygame.font.SysFont(
        "Consolas", max(13, int(board_size * 0.023)))
    current_time = final_elapsed_seconds if (is_won or is_game_over) else (
        pygame.time.get_ticks() - start_time_ms) / 1000.0

    timer_surface = hud_font.render(
        f"Time: {current_time:05.1f}s", True, (255, 255, 255))
    moves_surface = hud_font.render(
        f"Steps: {moves_count} (Opt: {optimal_steps})", True, (255, 255, 255))

    hint_status = "[H] Hint (USED)" if hint_used else "[H] Hint (1x)"
    hint_color = (120, 130, 140) if hint_used else (255, 215, 0)
    center_hud = hud_font.render(
        f"[Z] Undo | {hint_status} | [R] Reset | [N] Size", True, hint_color)

    # Top-Left: Running time
    render_surface.blit(timer_surface, (start_x, start_y - 28))

    # Top-Center: Controls and hint state
    render_surface.blit(
        center_hud, (center_x - center_hud.get_width() // 2, start_y - 28))

    # Bottom-Right: Steps taken & optimal distance
    render_surface.blit(moves_surface, (start_x + board_size -
                        moves_surface.get_width(), start_y + board_size + 14))

    # Bottom-Center: End messages
    banner_font = pygame.font.SysFont(None, max(24, int(board_size * 0.045)))
    if is_won:
        efficiency = round((optimal_steps / max(1, moves_count)) * 100)
        text = banner_font.render(
            f"Escaped in {final_elapsed_seconds:.1f}s! Rating: {efficiency}% | [R] Restart", True, (255, 215, 0))
        render_surface.blit(
            text, (center_x - text.get_width() // 2, start_y + board_size + 40))
    elif is_game_over:
        text = banner_font.render(
            "Trapped! Press [Z] to Undo or [R] to Restart", True, (255, 69, 0))
        render_surface.blit(
            text, (center_x - text.get_width() // 2, start_y + board_size + 40))

    screen.fill(background_color)
    screen.blit(render_surface, (round(shake_offset_x), round(shake_offset_y)))
