"""Menu and configuration screens for Sapphire Dash."""

import pygame


def draw_menu(surface, game):
    surface.fill(game.bg_center_rgb)
    title_font = pygame.font.SysFont("Segoe UI", 40, bold=True)
    subtitle_font = pygame.font.SysFont("Segoe UI", 15)
    card_title = pygame.font.SysFont("Segoe UI", 19, bold=True)
    card_body = pygame.font.SysFont("Segoe UI", 13)
    pill_font = pygame.font.SysFont("Segoe UI", 11, bold=True)

    window = pygame.Rect(game.center_x - 370, game.center_y - 240, 740, 480)
    game.draw_frosted_card(surface, window, border_radius=20, glow=True)
    avatar = pygame.Rect(window.x + 36, window.y + 36, 42, 42)
    pygame.draw.rect(surface, game.accent_purple, avatar, border_radius=12)
    pygame.draw.circle(surface, (255, 255, 255), avatar.center, 8)
    _blit(surface, title_font, "Sapphire Dash", game.text_primary, avatar.right + 16, window.y + 32)
    _blit(surface, subtitle_font, "Kinetic Vector Labyrinth  •  Arcade Engine", game.text_secondary, avatar.right + 18, window.y + 76)

    _draw_mode_card(surface, game, pygame.Rect(window.x + 36, window.y + 128, 668, 110), "SELECT [1]", "Custom Grid Arena", "Dial any matrix dimension from 11 to 999. Follow-cam engages automatically.", False, card_title, card_body, pill_font)
    _draw_mode_card(surface, game, pygame.Rect(window.x + 36, window.y + 254, 668, 110), "SELECT [2]", "Endless Gauntlet Run", "Non-stop scaling: 15x15 -> 995x995 (+10/lvl). Single-run permadeath rules.", True, card_title, card_body, pill_font)
    footer = subtitle_font.render("[ESC] Exit System  •  [F] Toggle Fullscreen", True, game.text_muted)
    surface.blit(footer, (window.centerx - footer.get_width() // 2, window.bottom - 42))


def draw_config(surface, game):
    surface.fill(game.bg_center_rgb)
    title_font = pygame.font.SysFont("Segoe UI", 30, bold=True)
    sub_font = pygame.font.SysFont("Segoe UI", 14)
    input_font = pygame.font.SysFont("Consolas", 42, bold=True)
    window = pygame.Rect(game.center_x - 300, game.center_y - 180, 600, 360)
    game.draw_frosted_card(surface, window, border_radius=18, glow=True)
    _center(surface, title_font, "Matrix Dimensions", game.text_primary, window.centerx, window.y + 36)
    _center(surface, sub_font, f"Display: {game.scrn_w}x{game.scrn_h}  •  Static Ceiling: {game.MAX_STATIC_SIZE}x{game.MAX_STATIC_SIZE}", game.text_secondary, window.centerx, window.y + 80)
    box = pygame.Rect(window.centerx - 120, window.y + 130, 240, 72)
    game.draw_frosted_card(surface, box, border_radius=12)
    pygame.draw.rect(surface, game.accent_purple, box, width=1, border_radius=12)
    _center(surface, input_font, game.input_text or "_", game.accent_bright, box.centerx, box.centery - input_font.get_height() // 2)
    _center(surface, sub_font, "[ENTER] Deploy  •  [ESC] Menu  •  [F] Fullscreen", game.text_muted, window.centerx, window.bottom - 45)


def _draw_mode_card(surface, game, rect, action, title, description, selected, title_font, body_font, pill_font):
    game.draw_frosted_card(surface, rect, border_radius=14)
    pill = pygame.Rect(rect.right - 120, rect.y + 18, 100, 24)
    pygame.draw.rect(surface, game.accent_purple if selected else (53, 43, 87), pill, border_radius=12)
    _center(surface, pill_font, action, (255, 255, 255) if selected else game.accent_bright, pill.centerx, pill.centery - pill_font.get_height() // 2)
    _blit(surface, title_font, title, game.text_primary, rect.x + 22, rect.y + 24)
    _blit(surface, body_font, description, game.text_secondary, rect.x + 22, rect.y + 60)


def _blit(surface, font, text, color, x, y):
    surface.blit(font.render(text, True, color), (x, y))


def _center(surface, font, text, color, x, y):
    rendered = font.render(text, True, color)
    surface.blit(rendered, (x - rendered.get_width() // 2, y))
