---
name: elo
description: Office ELO ladder. Use when someone wants to log a match ("X beat Y", "log a game"), see rankings, who's on the rise, recent results, or head to head stats.
---

Files in repo root:
- matches.csv - source of truth, one row per match: date,winner,loser,score (score optional, winner's points first, like "11-3, 11-8"). Score is recorded only - ratings use match win/loss (Ratings Central style, mean +- SD). Still ask for the score, people like seeing it.
- players.txt - roster, one name per line. Add new people here first.
- elo.py - stdlib only, rebuilds README.md from matches.csv
- README.md - generated, never hand edit

Log a match:
1. `git pull --rebase`
2. `python elo.py add "Winner" "Loser" ["YYYY-MM-DD"] ["11-3, 11-8"]` (date and score optional). If someone gives games listed from one side, they win the match - log one match, not one per game. Names must match README exactly - if elo.py prints "new player", check the spelling with the user before committing.
3. Repeat step 2 for each extra match, then `git add matches.csv README.md && git commit -m "Winner beat Loser" && git push`

Show rankings / rise / recent / h2h:
- Run `python elo.py` and show the section asked for. Don't work out ELO yourself.

Fix a wrong result: edit the row in matches.csv, run `python elo.py`, commit both files.
