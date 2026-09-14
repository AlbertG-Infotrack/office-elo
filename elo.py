#!/usr/bin/env python3
"""Office ELO. matches.csv is the source of truth, README.md is generated.

  python elo.py                       rebuild README.md and print it
  python elo.py add WINNER LOSER [YYYY-MM-DD]   log a match, then rebuild
"""
import csv, sys
from collections import defaultdict
from datetime import date, timedelta

K, START, RECENT, TREND_DAYS = 32, 1000, 10, 7
MATCHES, README = "matches.csv", "README.md"


def load():
    with open(MATCHES, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["winner"] and r["loser"]]
    rows.sort(key=lambda r: r["date"])  # stable, so same-day order is kept
    return rows


def compute(matches):
    rating = defaultdict(lambda: START)
    wins, losses = defaultdict(int), defaultdict(int)
    h2h = defaultdict(int)          # (a, b) -> times a beat b
    history = defaultdict(list)     # player -> [(date, rating after)]
    results = []
    for m in matches:
        w, l, d = m["winner"], m["loser"], m["date"]
        expected = 1 / (1 + 10 ** ((rating[l] - rating[w]) / 400))
        delta = round(K * (1 - expected))
        rating[w] += delta
        rating[l] -= delta
        wins[w] += 1
        losses[l] += 1
        h2h[(w, l)] += 1
        history[w].append((d, rating[w]))
        history[l].append((d, rating[l]))
        results.append((d, w, l, delta))
    return rating, wins, losses, h2h, history, results


def trend(hist, asof):
    """Rating change over the last TREND_DAYS, relative to the latest match date (deterministic)."""
    cutoff = (date.fromisoformat(asof) - timedelta(days=TREND_DAYS)).isoformat()
    before = START
    for d, r in hist:
        if d < cutoff:
            before = r
    return hist[-1][1] - before


def build(matches):
    rating, wins, losses, h2h, history, results = compute(matches)
    players = sorted(rating, key=lambda p: (-rating[p], p))
    asof = matches[-1]["date"] if matches else date.today().isoformat()
    out = ["# Office ELO", "", f"{len(matches)} matches, {len(players)} players. Last match {asof}.", ""]

    out += ["## Rankings", "", f"| # | Player | Rating | W | L | Last {TREND_DAYS} days |", "|--:|---|--:|--:|--:|--:|"]
    for i, p in enumerate(players, 1):
        t = trend(history[p], asof)
        icon = "🔥" if t >= 30 else "📈" if t > 0 else "📉" if t < 0 else "➖"
        out.append(f"| {i} | {p} | {rating[p]} | {wins[p]} | {losses[p]} | {icon} {t:+d} |")

    movers = sorted(((trend(history[p], asof), p) for p in players), reverse=True)
    rising = [f"{p} ({t:+d})" for t, p in movers if t > 0][:3]
    out += ["", "## On the rise", "", ", ".join(rising) or "Nobody yet."]

    out += ["", "## Recent results", "", "| Date | Winner | Loser | +/- |", "|---|---|---|--:|"]
    out += [f"| {d} | {w} | {l} | {delta} |" for d, w, l, delta in reversed(results[-RECENT:])]

    out += ["", "## Head to head", "", "Row vs column, shown as wins-losses.", ""]
    out += ["| | " + " | ".join(players) + " |", "|---|" + "--:|" * len(players)]
    for p in players:
        cells = ["-" if p == q else f"{h2h.get((p, q), 0)}-{h2h.get((q, p), 0)}" for q in players]
        out.append(f"| {p} | " + " | ".join(cells) + " |")
    return "\n".join(out) + "\n"


def add(winner, loser, when=None):
    when = when or date.today().isoformat()
    date.fromisoformat(when)  # raises on bad date
    if not winner.strip() or not loser.strip() or winner == loser:
        sys.exit("need two different names")
    known = {p for m in load() for p in (m["winner"], m["loser"])}
    for p in (winner, loser):
        if p not in known:
            print(f"note: new player '{p}' (check spelling matches README)", file=sys.stderr)
    with open(MATCHES, "a", newline="", encoding="utf-8") as f:
        csv.writer(f, lineterminator="\n").writerow([when, winner, loser])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # windows console
    if len(sys.argv) > 1 and sys.argv[1] == "add":
        add(*sys.argv[2:5])
    elif len(sys.argv) > 1:
        sys.exit(__doc__)
    md = build(load())
    with open(README, "w", encoding="utf-8", newline="\n") as f:
        f.write(md)
    print(md)
