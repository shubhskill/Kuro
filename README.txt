KURO RACING UPDATE

Files included:
- main.py: complete updated main bot file based on the uploaded current main (1).py
- games/number_game.py: current uploaded Number Combination module, unchanged
- games/racing_game.py: new Racing game logic
- games/__init__.py: package marker
- requirements.txt: current dependency, unchanged

Racing features:
- Solo race against KURO AI
- Multiplayer group race for 2-10 players
- 90-second join lobby; creator joins automatically; race starts at 10 players or after timeout with at least 2
- 100 m finish line
- Progressive stages; hazards become more frequent as the race advances
- Inline Accelerate button and race progress board
- Separate Solo Racing and Multiplayer Racing state

Deploy by replacing the repository's main.py and adding games/racing_game.py. Keep games/number_game.py and requirements.txt as included. Ensure games/__init__.py exists.

Checks performed:
- Python compilation passed for main.py, games/number_game.py, and games/racing_game.py.
- Racing logic smoke tests passed for solo and multiplayer state progression.
- Live Telegram/Railway integration was not tested in this environment.
