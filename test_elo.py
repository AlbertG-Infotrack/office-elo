# ponytail: one check that fails if the maths or h2h breaks. run: python test_elo.py
from elo import compute, build, START

ms = [{"date": "2026-09-01", "winner": "A", "loser": "B"},
      {"date": "2026-09-02", "winner": "A", "loser": "B"},
      {"date": "2026-09-03", "winner": "B", "loser": "A"}]
rating, wins, losses, h2h, history, results = compute(ms)
assert results[0][3] == 16 and rating["A"] + rating["B"] == 2 * START
assert (wins["A"], losses["A"], h2h[("A", "B")], h2h[("B", "A")]) == (2, 1, 2, 1)
md = build(ms)
assert "| 1 | A |" in md and "| A | - | 2-1 |" in md and "A (+" in md
print("ok")
