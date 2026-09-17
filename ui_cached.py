"""Cached menu and configuration screens for Sapphire Dash."""

import pygame

_menu_cache = _config_cache = None
_menu_cache_size = _config_cache_key = None
_fonts = None


def _get_fonts():
    global _fonts
    if _fonts is None:
        _fonts = {
            "menu_title": pygame.font.SysFont("Segoe UI", 40, bold=True), "menu_subtitle": pygame.font.SysFont("Segoe UI", 15),
            "card_title": pygame.font.SysFont("Segoe UI", 19, bold=True), "card_body": pygame.font.SysFont("Segoe UI", 13),
            "pill": pygame.font.SysFont("Segoe UI", 11, bold=True), "config_title": pygame.font.SysFont("Segoe UI", 30, bold=True),
            "config_sub": pygame.font.SysFont("Segoe UI", 14), "config_input": pygame.font.SysFont("Consolas", 42, bold=True),
        }
    return _fonts


def draw_menu(surface, game):
    global _menu_cache, _menu_cache_size
    if _menu_cache is None or _menu_cache_size != surface.get_size():
        _menu_cache_size = surface.get_size()
        _menu_cache = pygame.Surface(_menu_cache_size).convert()
        _build_menu(_menu_cache, game)
    surface.blit(_menu_cache, (0, 0))


def draw_config(surface, game):
    global _config_cache, _config_cache_key
    cache_key = (surface.get_size(), game.MAX_STATIC_SIZE)
    if _config_cache is None or _config_cache_key != cache_key:
        _config_cache_key = cache_key
        _config_cache = pygame.Surface(surface.get_size()).convert()
        _build_config(_config_cache, game)
    surface.blit(_config_cache, (0, 0))
    fonts = _get_fonts()
    window = pygame.Rect(game.center_x - 300, game.center_y - 180, 600, 360)
    box = pygame.Rect(window.centerx - 120, window.y + 130, 240, 72)
    _center(surface, fonts["config_input"], game.input_text or "_", game.accent_bright, box.centerx, box.centery - fonts["config_input"].get_height() // 2)


def _build_menu(surface, game):
    fonts = _get_fonts()
    surface.fill(game.bg_center_rgb)
    window = pygame.Rect(game.center_x - 370, game.center_y - 240, 740, 480)
    game.draw_frosted_card(surface, window, border_radius=20, glow=True)
    avatar = pygame.Rect(window.x + 36, window.y + 36, 42, 42)
    pygame.draw.rect(surface, game.accent_purple, avatar, border_radius=12)
    pygame.draw.circle(surface, (255, 255, 255), avatar.center, 8)
    _blit(surface, fonts["menu_title"], "Sapphire Dash", game.text_primary, avatar.right + 16, window.y + 32)
    _blit(surface, fonts["menu_subtitle"], "Kinetic Vector Labyrinth  •  Arcade Engine", game.text_secondary, avatar.right + 18, window.y + 76)
    _draw_mode_card(surface, game, pygame.Rect(window.x + 36, window.y + 128, 668, 110), "SELECT [1]", "Custom Grid Arena", "Dial any matrix dimension from 11 to 999. Follow-cam engages automatically.", False, fonts)
    _draw_mode_card(surface, game, pygame.Rect(window.x + 36, window.y + 254, 668, 110), "SELECT [2]", "Endless Gauntlet Run", "Non-stop scaling: 15x15 -> 995x995 (+10/lvl). Single-run permadeath rules.", True, fonts)
    footer = fonts["menu_subtitle"].render("[ESC] Exit System  •  [F] Toggle Fullscreen", True, game.text_muted)
    surface.blit(footer, (window.centerx - footer.get_width() // 2, window.bottom - 42))


def _build_config(surface, game):
    fonts = _get_fonts()
    surface.fill(game.bg_center_rgb)
    window = pygame.Rect(game.center_x - 300, game.center_y - 180, 600, 360)
    game.draw_frosted_card(surface, window, border_radius=18, glow=True)
    _center(surface, fonts["config_title"], "Matrix Dimensions", game.text_primary, window.centerx, window.y + 36)
    _center(surface, fonts["config_sub"], f"Display: {game.scrn_w}x{game.scrn_h}  •  Static Ceiling: {game.MAX_STATIC_SIZE}x{game.MAX_STATIC_SIZE}", game.text_secondary, window.centerx, window.y + 80)
    box = pygame.Rect(window.centerx - 120, window.y + 130, 240, 72)
    game.draw_frosted_card(surface, box, border_radius=12)
    pygame.draw.rect(surface, game.accent_purple, box, width=1, border_radius=12)
    _center(surface, fonts["config_sub"], "[ENTER] Deploy  •  [ESC] Menu  •  [F] Fullscreen", game.text_muted, window.centerx, window.bottom - 45)


def _draw_mode_card(surface, game, rect, action, title, description, selected, fonts):
    game.draw_frosted_card(surface, rect, border_radius=14)
    pill = pygame.Rect(rect.right - 120, rect.y + 18, 100, 24)
    pygame.draw.rect(surface, game.accent_purple if selected else (53, 43, 87), pill, border_radius=12)
    _center(surface, fonts["pill"], action, (255, 255, 255) if selected else game.accent_bright, pill.centerx, pill.centery - fonts["pill"].get_height() // 2)
    _blit(surface, fonts["card_title"], title, game.text_primary, rect.x + 22, rect.y + 24)
    _blit(surface, fonts["card_body"], description, game.text_secondary, rect.x + 22, rect.y + 60)


def _blit(surface, font, text, color, x, y):
    surface.blit(font.render(text, True, color), (x, y))


def _center(surface, font, text, color, x, y):
    rendered = font.render(text, True, color)
    surface.blit(rendered, (x - rendered.get_width() // 2, y))
