import pygame
import game

pygame.init()

# Initial windowed dimensions
windowed_w, windowed_h = 1280, 720
is_fullscreen = False

screen = pygame.display.set_mode((windowed_w, windowed_h), pygame.RESIZABLE)
clock = pygame.time.Clock()

game.handle_resize(screen.get_width(), screen.get_height())


def toggle_fullscreen():
    global screen, is_fullscreen, windowed_w, windowed_h
    is_fullscreen = not is_fullscreen
    if is_fullscreen:
        # Cache windowed size prior to going fullscreen
        windowed_w, windowed_h = screen.get_width(), screen.get_height()
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        screen = pygame.display.set_mode(
            (windowed_w, windowed_h), pygame.RESIZABLE)
    game.handle_resize(screen.get_width(), screen.get_height())


while game.running:
    dt = clock.tick(game.fps)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            game.running = False

        elif event.type == pygame.VIDEORESIZE:
            if not is_fullscreen:
                screen = pygame.display.set_mode(
                    (event.w, event.h), pygame.RESIZABLE)
                game.handle_resize(event.w, event.h)

        elif event.type == pygame.KEYDOWN:
            # Global Fullscreen Toggle
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

    game.draw(screen)
    pygame.display.flip()

pygame.quit()
