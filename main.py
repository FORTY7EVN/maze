import pygame
import game

pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
clock = pygame.time.Clock()

while game.running:
    dt = clock.tick(game.fps)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            game.running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
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
