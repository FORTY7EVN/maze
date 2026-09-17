"""
main.py – Sapphire Dash
Presentation layer: Pygame draws into a software surface (game.render_surface);
this module uploads that surface to a Direct3D 11 streaming texture every frame
and presents it via SDL2's D3D11 renderer (SDL_CreateWindowAndRenderer with
SDL_RENDER_DRIVER=direct3d11).  No PyOpenGL, no comtypes – just SDL2 ctypes.
"""
import os
import sys
import ctypes
import ctypes.wintypes
import pathlib
import importlib.util

# ── Must be set before any SDL init ─────────────────────────────────────────
os.environ["SDL_RENDER_DRIVER"] = "direct3d11"

if sys.platform == "win32":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    try:
        # Prefer discrete GPU on Optimus / Enduro systems
        ctypes.CDLL(None).NvOptimusEnablement = 0x00000001
    except Exception:
        pass

import pygame
import game

# ── Load SDL2.dll bundled with pygame ────────────────────────────────────────
_pkg_path = pathlib.Path(importlib.util.find_spec("pygame").origin).parent
_sdl_dll   = next(_pkg_path.glob("SDL2.dll"))   # always present on Windows
_sdl        = ctypes.CDLL(str(_sdl_dll))

# ── SDL2 constants ───────────────────────────────────────────────────────────
SDL_WINDOW_SHOWN              = 0x00000004
SDL_WINDOW_RESIZABLE          = 0x00000020
SDL_WINDOW_FULLSCREEN_DESKTOP = 0x00001001
SDL_RENDERER_ACCELERATED      = 0x00000002
SDL_PIXELFORMAT_ARGB8888      = 0x16362004   # == pygame depth-32 BGRA byte order
SDL_TEXTUREACCESS_STREAMING   = 1
SDL_BLENDMODE_NONE            = 0

# ── SDL2 function prototypes ─────────────────────────────────────────────────
_sdl.SDL_CreateWindowAndRenderer.restype  = ctypes.c_int
_sdl.SDL_CreateWindowAndRenderer.argtypes = [
    ctypes.c_int, ctypes.c_int, ctypes.c_uint32,
    ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p),
]
_sdl.SDL_SetWindowTitle.restype  = None
_sdl.SDL_SetWindowTitle.argtypes = [ctypes.c_void_p, ctypes.c_char_p]

_sdl.SDL_GetWindowSize.restype  = None
_sdl.SDL_GetWindowSize.argtypes = [
    ctypes.c_void_p, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int),
]
_sdl.SDL_SetWindowFullscreen.restype  = ctypes.c_int
_sdl.SDL_SetWindowFullscreen.argtypes = [ctypes.c_void_p, ctypes.c_uint32]

_sdl.SDL_CreateTexture.restype  = ctypes.c_void_p
_sdl.SDL_CreateTexture.argtypes = [
    ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_int, ctypes.c_int,
]
_sdl.SDL_DestroyTexture.restype  = None
_sdl.SDL_DestroyTexture.argtypes = [ctypes.c_void_p]

_sdl.SDL_UpdateTexture.restype  = ctypes.c_int
_sdl.SDL_UpdateTexture.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int,
]
_sdl.SDL_SetTextureBlendMode.restype  = ctypes.c_int
_sdl.SDL_SetTextureBlendMode.argtypes = [ctypes.c_void_p, ctypes.c_int]

_sdl.SDL_RenderClear.restype  = ctypes.c_int
_sdl.SDL_RenderClear.argtypes = [ctypes.c_void_p]

_sdl.SDL_RenderCopy.restype  = ctypes.c_int
_sdl.SDL_RenderCopy.argtypes = [
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
]
_sdl.SDL_RenderPresent.restype  = None
_sdl.SDL_RenderPresent.argtypes = [ctypes.c_void_p]

_sdl.SDL_DestroyRenderer.restype  = None
_sdl.SDL_DestroyRenderer.argtypes = [ctypes.c_void_p]

_sdl.SDL_DestroyWindow.restype  = None
_sdl.SDL_DestroyWindow.argtypes = [ctypes.c_void_p]

_sdl.SDL_GetError.restype  = ctypes.c_char_p
_sdl.SDL_GetError.argtypes = []

# SDL_SysWMinfo – used to retrieve the HWND for accurate client-rect sizing
class _SDL_version(ctypes.Structure):
    _fields_ = [("major", ctypes.c_uint8), ("minor", ctypes.c_uint8),
                ("patch", ctypes.c_uint8)]

class _SDL_SysWMinfo(ctypes.Structure):
    _fields_ = [("version",   _SDL_version),
                ("subsystem", ctypes.c_int),
                ("hwnd",      ctypes.c_void_p),
                ("hdc",       ctypes.c_void_p),
                ("hinstance", ctypes.c_void_p),
                ("_pad",      ctypes.c_byte * 512)]   # generous padding

_sdl.SDL_GetWindowWMInfo.restype  = ctypes.c_bool
_sdl.SDL_GetWindowWMInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(_SDL_SysWMinfo)]

# ── Create the D3D11 window & renderer ───────────────────────────────────────
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=1)

windowed_w, windowed_h = 1280, 720
is_fullscreen          = False

# Initialise pygame's display subsystem with a tiny hidden surface.
# This is required so that pygame.Surface.convert() calls inside game.py
# succeed.  The actual visible output goes through our SDL2 D3D11 window below.
os.environ["SDL_VIDEO_WINDOW_POS"] = "-32000,-32000"   # park off-screen
pygame.display.set_mode((1, 1), pygame.NOFRAME)
os.environ.pop("SDL_VIDEO_WINDOW_POS", None)

_win_ptr = ctypes.c_void_p()
_ren_ptr = ctypes.c_void_p()

_ret = _sdl.SDL_CreateWindowAndRenderer(
    windowed_w, windowed_h,
    SDL_WINDOW_SHOWN | SDL_WINDOW_RESIZABLE,
    ctypes.byref(_win_ptr), ctypes.byref(_ren_ptr),
)
if _ret != 0 or not _win_ptr or not _ren_ptr:
    raise RuntimeError(
        f"SDL_CreateWindowAndRenderer failed: {_sdl.SDL_GetError().decode()}"
    )

_sdl.SDL_SetWindowTitle(_win_ptr, b"Sapphire Dash")
clock = pygame.time.Clock()

active_w = windowed_w
active_h = windowed_h


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_hwnd() -> int | None:
    """Return the Win32 HWND for our SDL window (for accurate client-rect queries)."""
    info = _SDL_SysWMinfo()
    # Fill in the SDL version we linked against
    info.version.major = 2
    info.version.minor = 28
    info.version.patch = 4
    if _sdl.SDL_GetWindowWMInfo(_win_ptr, ctypes.byref(info)):
        return info.hwnd
    return None


_hwnd = _get_hwnd()


def get_actual_window_size() -> tuple[int, int]:
    """Query true physical client size (accounts for DPI scaling)."""
    if sys.platform == "win32" and _hwnd:
        rect = ctypes.wintypes.RECT()
        ctypes.windll.user32.GetClientRect(_hwnd, ctypes.byref(rect))
        w = rect.right  - rect.left
        h = rect.bottom - rect.top
        if w > 0 and h > 0:
            return w, h
    # Fallback: ask SDL
    w, h = ctypes.c_int(), ctypes.c_int()
    _sdl.SDL_GetWindowSize(_win_ptr, ctypes.byref(w), ctypes.byref(h))
    return w.value, h.value


def _make_texture(w: int, h: int) -> ctypes.c_void_p:
    """Allocate a streaming ARGB8888 D3D11 texture at (w, h)."""
    tex = _sdl.SDL_CreateTexture(
        _ren_ptr, SDL_PIXELFORMAT_ARGB8888, SDL_TEXTUREACCESS_STREAMING, w, h,
    )
    if tex:
        _sdl.SDL_SetTextureBlendMode(tex, SDL_BLENDMODE_NONE)
    return tex


_d3d_tex = _make_texture(active_w, active_h)


def sync_viewport(w: int, h: int) -> None:
    """Recreate the streaming texture for a new window size and notify game."""
    global active_w, active_h, _d3d_tex

    if w <= 0 or h <= 0:
        return
    active_w, active_h = w, h

    if _d3d_tex:
        _sdl.SDL_DestroyTexture(_d3d_tex)
    _d3d_tex = _make_texture(w, h)

    game.handle_resize(w, h)


def render_surface_to_d3d(surf: pygame.Surface) -> None:
    """
    Upload the pygame render_surface into the D3D11 streaming texture and
    call SDL_RenderPresent (maps to IDXGISwapChain::Present internally).
    """
    pitch = surf.get_width() * 4          # ARGB8888 → 4 bytes per pixel
    raw   = surf.get_buffer()             # zero-copy buffer view
    _sdl.SDL_UpdateTexture(_d3d_tex, None, ctypes.c_char_p(bytes(raw)), pitch)
    _sdl.SDL_RenderClear(_ren_ptr)
    _sdl.SDL_RenderCopy(_ren_ptr, _d3d_tex, None, None)   # fullscreen quad
    _sdl.SDL_RenderPresent(_ren_ptr)                       # Present(0, 0)


def toggle_fullscreen() -> None:
    global is_fullscreen, windowed_w, windowed_h

    is_fullscreen = not is_fullscreen
    if is_fullscreen:
        windowed_w, windowed_h = get_actual_window_size()
        _sdl.SDL_SetWindowFullscreen(_win_ptr, SDL_WINDOW_FULLSCREEN_DESKTOP)
    else:
        _sdl.SDL_SetWindowFullscreen(_win_ptr, 0)

    w, h = get_actual_window_size()
    sync_viewport(w, h)


# ── Initialise game viewport ──────────────────────────────────────────────────
_iw, _ih = get_actual_window_size()
sync_viewport(_iw, _ih)

# ── Main loop ─────────────────────────────────────────────────────────────────
frame_counter = 0

while game.running:
    dt = clock.tick(0)

    frame_counter += 1
    if frame_counter % 30 == 0:
        title = f"Sapphire Dash — {clock.get_fps():.0f} FPS".encode()
        _sdl.SDL_SetWindowTitle(_win_ptr, title)

    real_w, real_h = get_actual_window_size()
    if real_w != active_w or real_h != active_h:
        sync_viewport(real_w, real_h)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            game.running = False

        elif event.type in (pygame.WINDOWSIZECHANGED, pygame.WINDOWRESIZED,
                            pygame.VIDEORESIZE):
            w, h = get_actual_window_size()
            sync_viewport(w, h)

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_f:
                toggle_fullscreen()
            elif event.key == pygame.K_ESCAPE:
                if game.state in ("PLAYING", "CONFIG"):
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

    render_surface_to_d3d(game.render_surface)

# ── Cleanup ───────────────────────────────────────────────────────────────────
if _d3d_tex:
    _sdl.SDL_DestroyTexture(_d3d_tex)
_sdl.SDL_DestroyRenderer(_ren_ptr)
_sdl.SDL_DestroyWindow(_win_ptr)
pygame.quit()
