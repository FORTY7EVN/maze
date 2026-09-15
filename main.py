import pygame
import game
pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
clock = pygame.time.Clock()

game.load()
while game.running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            game.running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                game.running = False
    screen.fill(game.background_color)
    game.draw(screen)
    pygame.display.flip()
    clock.tick(game.fps)

pygame.quit()
