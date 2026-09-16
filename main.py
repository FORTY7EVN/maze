import os
import sys
import ctypes

if sys.platform == "win32":
    import ctypes.wintypes

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    try:
        ctypes.CDLL(None).NvOptimusEnablement = 0x00000001
    except Exception:
        pass
    os.environ["SDL_RENDER_DRIVER"] = "opengl"

import pygame
from OpenGL.GL import *
import game

pygame.init()
pygame.display.gl_set_attribute(pygame.GL_SWAP_CONTROL, 0)

windowed_w, windowed_h = 1280, 720
is_fullscreen = False

gl_flags = pygame.OPENGL | pygame.DOUBLEBUF | pygame.RESIZABLE
screen = pygame.display.set_mode((windowed_w, windowed_h), gl_flags, vsync=0)
pygame.display.set_caption("Sapphire Dash")
clock = pygame.time.Clock()


def disable_driver_vsync():
    if sys.platform == "win32":
        try:
            opengl32 = ctypes.windll.opengl32
            wglGetProcAddress = opengl32.wglGetProcAddress
            wglGetProcAddress.restype = ctypes.c_void_p
            wglGetProcAddress.argtypes = [ctypes.c_char_p]

            proc_addr = wglGetProcAddress(b"wglSwapIntervalEXT")
            if proc_addr:
                proto = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int)
                wgl_swap = proto(proc_addr)
                wgl_swap(0)
        except Exception:
            pass


disable_driver_vsync()

glEnable(GL_TEXTURE_2D)
tex_id = glGenTextures(1)
glBindTexture(GL_TEXTURE_2D, tex_id)
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
glPixelStorei(GL_UNPACK_ALIGNMENT, 4)

active_w = windowed_w
active_h = windowed_h
tex_allocated_w = 0
tex_allocated_h = 0


def get_actual_window_size():
    if sys.platform == "win32":
        hwnd = pygame.display.get_wm_info().get("window")
        if hwnd:
            rect = ctypes.wintypes.RECT()
            ctypes.windll.user32.GetClientRect(hwnd, ctypes.byref(rect))
            w = rect.right - rect.left
            h = rect.bottom - rect.top
            if w > 0 and h > 0:
                return w, h
    return screen.get_width(), screen.get_height()


def sync_viewport(w, h):
    global active_w, active_h, tex_allocated_w, tex_allocated_h
    if w <= 0 or h <= 0:
        return

    active_w = w
    active_h = h

    glViewport(0, 0, w, h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(0, w, h, 0, -1, 1)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    glBindTexture(GL_TEXTURE_2D, tex_id)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, w, h,
                 0, GL_BGRA, GL_UNSIGNED_BYTE, None)
    tex_allocated_w = w
    tex_allocated_h = h

    game.handle_resize(w, h)


init_w, init_h = get_actual_window_size()
sync_viewport(init_w, init_h)


def render_surface_to_opengl(surf, win_w, win_h):
    global tex_allocated_w, tex_allocated_h

    if tex_allocated_w != win_w or tex_allocated_h != win_h:
        sync_viewport(win_w, win_h)

    buffer_data = memoryview(surf.get_view('1'))

    glBindTexture(GL_TEXTURE_2D, tex_id)
    glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, win_w, win_h,
                    GL_BGRA, GL_UNSIGNED_BYTE, buffer_data)

    glClear(GL_COLOR_BUFFER_BIT)

    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 0.0)
    glVertex2f(0, 0)
    glTexCoord2f(1.0, 0.0)
    glVertex2f(win_w, 0)
    glTexCoord2f(1.0, 1.0)
    glVertex2f(win_w, win_h)
    glTexCoord2f(0.0, 1.0)
    glVertex2f(0, win_h)
    glEnd()


def toggle_fullscreen():
    global screen, is_fullscreen, windowed_w, windowed_h
    is_fullscreen = not is_fullscreen
    if is_fullscreen:
        windowed_w, windowed_h = get_actual_window_size()
        screen = pygame.display.set_mode(
            (0, 0), pygame.OPENGL | pygame.DOUBLEBUF | pygame.FULLSCREEN, vsync=0)
    else:
        screen = pygame.display.set_mode(
            (windowed_w, windowed_h), gl_flags, vsync=0)

    disable_driver_vsync()
    w, h = get_actual_window_size()
    sync_viewport(w, h)


frame_counter = 0

while game.running:
    dt = clock.tick(0)

    frame_counter += 1
    if frame_counter % 30 == 0:
        pygame.display.set_caption(
            f"Sapphire Dash — {clock.get_fps():.0f} FPS")

    real_w, real_h = get_actual_window_size()
    if real_w != active_w or real_h != active_h:
        sync_viewport(real_w, real_h)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            game.running = False

        elif event.type == pygame.VIDEORESIZE:
            sync_viewport(event.w, event.h)

        elif event.type == pygame.WINDOWSIZECHANGED or event.type == pygame.WINDOWRESIZED:
            w, h = get_actual_window_size()
            sync_viewport(w, h)

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_f:
                toggle_fullscreen()
            elif event.key == pygame.K_ESCAPE:
                if game.state == "PLAYING" or game.state == "CONFIG":
                    game.state = "MENU"
                else:
                    game.running = False
            elif game.state == "MENU":
                game.handle_menu_input(event)
            elif game.state == "CONFIG":
                game.handle_size_input(event)
            elif game.state == "PLAYING":
                if event.key == pygame.K_w:
                    game.queue_input(-1, 0)
                elif event.key == pygame.K_s:
                    game.queue_input(1, 0)
                elif event.key == pygame.K_a:
                    game.queue_input(0, -1)
                elif event.key == pygame.K_d:
                    game.queue_input(0, 1)
                elif event.key == pygame.K_z:
                    game.undo()
                elif event.key == pygame.K_h:
                    game.trigger_hint()
                elif event.key == pygame.K_r:
                    game.reset_game()
                elif event.key == pygame.K_m:
                    game.state = "MENU"

    game.update_player_animation(dt)
    game.draw()

    render_surface_to_opengl(game.render_surface, active_w, active_h)
    pygame.display.flip()

pygame.quit()
