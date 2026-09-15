import pygame
import game
pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
clock = pygame.time.Clock()

# load()
# initialize()

while game.running:
    game.game_quit()
    screen.fill("black")
    # draw(screen)
    pygame.display.flip()
    clock.tick(game.fps)

pygame.quit()
