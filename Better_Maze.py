"""
pygame Maze Game (coin-aware Dijkstra, full integration)
-------------------------------------------------
- English-only interface
- Tracks distance moved instead of score
- Coins reduce total distance by 10 (bonus)
- 2~4 coins per maze
- Dijkstra with bitmask considers coins in pathfinding
- Press H for help (shows shortest path as bright blue line)

Controls:
  Move: Arrow keys or WASD
  Restart: R
  Quit: Q
  Help: H

Written by ChatGPT
"""

import pygame
import random
import sys
import math
import heapq

CELL_SIZE = 36
GRID_W = 21
GRID_H = 15
FPS = 60

CHAR_WALL = '■'
CHAR_PATH = ' '
CHAR_PLAYER = '•'
CHAR_COIN = '©'
CHAR_EXIT = '★'

BG_COLOR = (20, 20, 20)
TEXT_COLOR = (240, 240, 240)
HUD_COLOR = (200, 200, 100)
PATH_COLOR = (80, 200, 255)

# Maze generation (recursive backtracker)
def make_maze(w, h):
    maze = [[1 for _ in range(w)] for _ in range(h)]

    def carve(x, y):
        dirs = [(2,0),(-2,0),(0,2),(0,-2)]
        random.shuffle(dirs)
        for dx, dy in dirs:
            nx, ny = x + dx, y + dy
            if 0 < nx < w - 1 and 0 < ny < h - 1 and maze[ny][nx] == 1:
                maze[ny][nx] = 0
                maze[y + dy//2][x + dx//2] = 0
                carve(nx, ny)

    maze[1][1] = 0
    carve(1,1)
    return maze

def place_coins(maze, n):
    h, w = len(maze), len(maze[0])
    empties = [(x,y) for y in range(h) for x in range(w) if maze[y][x] == 0 and not (x==1 and y==1)]
    random.shuffle(empties)
    return empties[:n]

# Coin-aware Dijkstra with bitmask
def dijkstra_with_coins(maze, start, end, coins):
    h, w = len(maze), len(maze[0])
    coin_indices = {tuple(c): i for i, c in enumerate(coins)}
    total_states = 1 << len(coins)

    dist = {}
    pq = [(0, start[0], start[1], 0)]  # (distance, x, y, bitmask)
    dist[(start[0], start[1], 0)] = 0

    prev = {}

    while pq:
        cost, x, y, mask = heapq.heappop(pq)
        if (x, y) == end:
            end_mask = mask
            break
        if dist.get((x, y, mask), math.inf) < cost:
            continue

        for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < w and 0 <= ny < h):
                continue
            if maze[ny][nx] == 1:
                continue

            new_mask = mask
            new_cost = cost + 1

            if (nx, ny) in coin_indices:
                bit = 1 << coin_indices[(nx, ny)]
                if not (mask & bit):
                    new_mask |= bit
                    new_cost -= 10  # coin reduces distance by 10

            if new_cost < dist.get((nx, ny, new_mask), math.inf):
                dist[(nx, ny, new_mask)] = new_cost
                prev[(nx, ny, new_mask)] = (x, y, mask)
                heapq.heappush(pq, (new_cost, nx, ny, new_mask))

    # find minimal end state
    best_mask = min(
        [m for (ex, ey, m) in dist.keys() if (ex, ey) == end],
        key=lambda mm: dist[(end[0], end[1], mm)],
        default=None,
    )

    if best_mask is None:
        return [], math.inf

    path = []
    cur = (end[0], end[1], best_mask)
    while cur in prev:
        path.append((cur[0], cur[1]))
        cur = prev[cur]
    path.append(start)
    path.reverse()

    return path, dist[(end[0], end[1], best_mask)]

def key_to_dir(key):
    if key in [pygame.K_LEFT, pygame.K_a]: return (-1, 0)
    if key in [pygame.K_RIGHT, pygame.K_d]: return (1, 0)
    if key in [pygame.K_UP, pygame.K_w]: return (0, -1)
    if key in [pygame.K_DOWN, pygame.K_s]: return (0, 1)
    return None

def draw_path(screen, path):
    if len(path) < 2:
        return
    points = [(x*CELL_SIZE + CELL_SIZE//2, y*CELL_SIZE + CELL_SIZE//2) for (x,y) in path]
    pygame.draw.lines(screen, PATH_COLOR, False, points, 5)

def run_game_loop(screen, clock, font, hud_font):
    grid_w = GRID_W if GRID_W % 2 == 1 else GRID_W+1
    grid_h = GRID_H if GRID_H % 2 == 1 else GRID_H+1

    maze = make_maze(grid_w, grid_h)
    player_x, player_y = 1, 1

    exit_x, exit_y = grid_w-2, grid_h-2
    if maze[exit_y][exit_x] == 1:
        found = False
        for y in range(grid_h-2, 0, -1):
            for x in range(grid_w-2, 0, -1):
                if maze[y][x] == 0:
                    exit_x, exit_y = x, y
                    found = True
                    break
            if found: break

    coin_count = random.randint(2,4)
    coins = place_coins(maze, coin_count)

    distance = 0
    game_over = False
    win = False
    show_help = False

    shortest_path, optimal_distance = dijkstra_with_coins(maze, (1,1), (exit_x, exit_y), coins)

    window_w = grid_w * CELL_SIZE
    hud_h = 80
    window_h = grid_h * CELL_SIZE + hud_h

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return 'quit'
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    return 'quit'
                if event.key == pygame.K_r:
                    return 'restart'

                if not game_over:
                    if event.key == pygame.K_h:
                        show_help = not show_help

                    dir = key_to_dir(event.key)
                    if dir:
                        dx,dy = dir
                        nx,ny = player_x + dx, player_y + dy
                        if 0 <= nx < grid_w and 0 <= ny < grid_h and maze[ny][nx] == 0:
                            player_x, player_y = nx, ny
                            distance += 1
                            for c in coins[:]:
                                if (player_x, player_y) == tuple(c):
                                    coins.remove(c)
                                    distance = max(0, distance - 10)  # coin reduces actual distance too
                            if player_x == exit_x and player_y == exit_y:
                                game_over = True
                                win = True

        screen.fill(BG_COLOR)

        if show_help:
            draw_path(screen, shortest_path)

        for y in range(grid_h):
            for x in range(grid_w):
                ch = CHAR_WALL if maze[y][x] == 1 else CHAR_PATH
                pos = (x*CELL_SIZE, y*CELL_SIZE)
                surf = font.render(ch, True, TEXT_COLOR)
                rect = surf.get_rect()
                rect.center = (pos[0] + CELL_SIZE//2, pos[1] + CELL_SIZE//2)
                screen.blit(surf, rect)

        for (cx,cy) in coins:
            surf = font.render(CHAR_COIN, True, HUD_COLOR)
            rect = surf.get_rect(center=(cx*CELL_SIZE + CELL_SIZE//2, cy*CELL_SIZE + CELL_SIZE//2))
            screen.blit(surf, rect)

        surf_exit = font.render(CHAR_EXIT, True, (120,220,120))
        rect_exit = surf_exit.get_rect(center=(exit_x*CELL_SIZE + CELL_SIZE//2, exit_y*CELL_SIZE + CELL_SIZE//2))
        screen.blit(surf_exit, rect_exit)

        surf_p = font.render(CHAR_PLAYER, True, (220,120,120))
        rect_p = surf_p.get_rect(center=(player_x*CELL_SIZE + CELL_SIZE//2, player_y*CELL_SIZE + CELL_SIZE//2))
        screen.blit(surf_p, rect_p)

        hud_y0 = grid_h*CELL_SIZE + 8
        hud1 = hud_font.render(f'Distance: {distance}   Coins left: {len(coins)}', True, TEXT_COLOR)
        hud2 = hud_font.render('Press H: Show/Hide Help  |  R: Restart  |  Q: Quit', True, HUD_COLOR)
        screen.blit(hud1, (8, hud_y0))
        screen.blit(hud2, (8, hud_y0+28))

        if game_over:
            overlay = pygame.Surface((window_w, window_h), pygame.SRCALPHA)
            overlay.fill((0,0,0,180))
            screen.blit(overlay, (0,0))

            msg = 'You Win! Reached the exit.' if win else 'Game Over'
            msg2 = f'Total distance: {distance}'
            msg3 = f'Optimal distance (with coins): {optimal_distance}'
            msg4 = 'Press R to Restart or Q to Quit'
            m1 = hud_font.render(msg, True, (255,255,255))
            m2 = hud_font.render(msg2, True, (200,200,200))
            m3 = hud_font.render(msg3, True, (200,200,200))
            m4 = hud_font.render(msg4, True, (200,200,200))

            screen.blit(m1, (window_w//2 - m1.get_width()//2, window_h//2 - 60))
            screen.blit(m2, (window_w//2 - m2.get_width()//2, window_h//2 - 30))
            screen.blit(m3, (window_w//2 - m3.get_width()//2, window_h//2))
            screen.blit(m4, (window_w//2 - m4.get_width()//2, window_h//2 + 30))

            draw_path(screen, shortest_path)

        pygame.display.flip()
        clock.tick(FPS)

def main():
    pygame.init()
    clock = pygame.time.Clock()

    try:
        font = pygame.font.SysFont('malgungothic', CELL_SIZE-4)
    except:
        font = pygame.font.SysFont(None, CELL_SIZE-4)
    hud_font = pygame.font.SysFont(None, 26)

    screen = pygame.display.set_mode((GRID_W * CELL_SIZE, GRID_H * CELL_SIZE + 80))
    pygame.display.set_caption('Maze Game')

    while True:
        result = run_game_loop(screen, clock, font, hud_font)
        if result == 'quit':
            pygame.quit()
            sys.exit()
        if result == 'restart':
            continue

if __name__ == '__main__':
    main()