# Neon Maze Runner

A fast, arcade-style maze game built with Python and Pygame. You move through a procedurally generated labyrinth, chain smooth turns into speed streaks, and race to reach the glowing exit before the maze traps you.

It blends old-school maze gameplay with modern presentation: neon HUD styling, CRT scanlines, screen shake, particles, sound effects, and a dynamic trail that heats up as you build momentum.

## Features

- Procedurally generated maze layouts
- Full-screen arcade presentation with CRT-style overlays
- Smooth movement with momentum-based glide physics
- Heat trail that changes color as your speed streak rises
- Hint system to reveal the shortest path
- Undo support for recovery after a mistake
- Dynamic size selection from the start screen
- Particle effects, shockwaves, and screen shake on win/lose events
- Built-in procedural sound effects for movement, hints, and dead ends

## Gameplay

The game starts in a configuration screen where you can enter a maze size. Odd values are preferred, and even numbers are automatically bumped to the next odd size.

Once the maze loads:

- Move with W, A, S, D
- Reach the glowing exit tile
- Avoid dead ends and trapped loops
- Use hint and undo strategically
- Press R to reset the maze and N to return to size selection

## Controls

| Action | Key |
| --- | --- |
| Move Up | W |
| Move Down | S |
| Move Left | A |
| Move Right | D |
| Undo Move | Z |
| Trigger Hint | H |
| Reset Maze | R |
| Return to Size Menu | N |
| Quit Game | Esc |

## Installation

1. Clone or download this repository.
2. Open a terminal in the project folder.
3. Create and activate a virtual environment if desired.
4. Install the requirements:

   ```bash
   pip install -r requirements.txt
   ```

5. Launch the game:

   ```bash
   python main.py
   ```

## Project Structure

```text
maze/
├── game.py      # Core maze logic, rendering, movement, effects, and audio
├── main.py      # Game loop and input handling
├── requirements.txt
├── README.md
└── .gitignore   # optional project ignore file if added later
```

## Notes

- The game defaults to fullscreen mode.
- The maze is designed to feel arcade-like rather than puzzle-precise, so best results come from experimenting with different board sizes.
- If audio devices are unavailable or mixer initialization fails, the game continues without sound effects.

## Requirements

- Python 3.9+
- Pygame 2.5+

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

Press Esc at any time to exit the game.
