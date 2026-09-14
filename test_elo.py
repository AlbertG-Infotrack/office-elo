# ponytail: one check that fails if the rating maths, decay or h2h breaks. run: python test_elo.py
from elo import compute, build, update, widen, win_prob, START, START_SD

# equal players: 50/50, winner gains what loser drops, both get more certain
assert abs(win_prob(START, START_SD, START) - 0.5) < 1e-9
(rw, sw), (rl, sl) = update(START, START_SD, START, START_SD, 1), update(START, START_SD, START, START_SD, 0)
assert abs((rw - START) + (rl - START)) < 1e-9 and rw > START and sw < START_SD
# a confident player moves less than an uncertain one, and SD widens with time off
assert update(START, 50, START, START_SD, 1)[0] - START < rw - START
assert abs(widen(50, 365) ** 2 - (50 ** 2 + 70 ** 2)) < 1e-9

ms = [{"date": "2026-09-01", "winner": "A", "loser": "B"},
      {"date": "2026-09-02", "winner": "A", "loser": "B"},
      {"date": "2026-09-03", "winner": "B", "loser": "A", "score": "11-9, 11-9"}]
rating, sd, wins, losses, h2h, history, results = compute(ms)
assert rating["A"] > rating["B"] and (wins["A"], losses["A"], h2h[("A", "B")], h2h[("B", "A")]) == (2, 1, 2, 1)
md = build(ms)
assert "| 1 | A |" in md and "| A | - | 2-1 |" in md and "A (+" in md and "11-9, 11-9" in md
print("ok")
