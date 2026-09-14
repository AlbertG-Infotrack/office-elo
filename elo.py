#!/usr/bin/env python3
"""Office table tennis ratings. matches.csv is the source of truth, README.md is generated.

  python elo.py                                 rebuild README.md and print it
  python elo.py add WINNER LOSER [YYYY-MM-DD] [SCORE]   log a match, then rebuild

Rating model follows Ratings Central (ratingscentral.com/HowItWorks.php): each player is a normal
distribution, mean +- SD. Wins move you by more when your SD is high (new or rusty) and less once the
system is confident. SD shrinks with every match and widens by a 70-points-per-year random walk when you
don't play. Only who won the match counts - the score is recorded but not used, same as Ratings Central.
The Bayesian update itself is Glicko's closed form (Ratings Central doesn't publish its upset function).
"""
import csv, html, math, string, sys
from collections import defaultdict
from datetime import date

START, START_SD, RECENT, TREND_DAYS = 850, 150, 10, 7
DRIFT = 70  # SD variance grows by DRIFT^2 per year of not playing (Ratings Central's figure)
Q = math.log(10) / 400
MATCHES, README, PLAYERS, TEMPLATE, INDEX = "matches.csv", "README.md", "players.txt", "template.html", "index.html"
REPO = "https://github.com/AlbertG-Infotrack/office-elo"


def load():
    with open(MATCHES, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["winner"] and r["loser"]]
    rows.sort(key=lambda r: r["date"])  # stable, so same-day order is kept
    return rows


def roster():
    with open(PLAYERS, encoding="utf-8") as f:
        return [p.strip() for p in f if p.strip()]


def g(sd):
    return 1 / math.sqrt(1 + 3 * Q * Q * sd * sd / math.pi ** 2)


def win_prob(r, sd_other, r_other):
    return 1 / (1 + 10 ** (-g(sd_other) * (r - r_other) / 400))


def widen(sd, days):
    return math.sqrt(sd * sd + DRIFT * DRIFT * days / 365)


def update(r, sd, r_other, sd_other, won):
    """Glicko posterior for one match. Returns new (mean, sd)."""
    gj, e = g(sd_other), win_prob(r, sd_other, r_other)
    d2 = 1 / (Q * Q * gj * gj * e * (1 - e))
    prec = 1 / (sd * sd) + 1 / d2
    return r + Q / prec * gj * (won - e), math.sqrt(1 / prec)


def compute(matches, players=()):
    rating = defaultdict(lambda: START)
    sd = defaultdict(lambda: START_SD)
    last = {}
    wins, losses = defaultdict(int), defaultdict(int)
    h2h = defaultdict(int)          # (a, b) -> times a beat b
    history = defaultdict(list)     # player -> [(date, rating after)]
    results = []
    for p in players:
        rating[p]  # seed everyone so they show up with 0-0
    for m in matches:
        w, l, d = m["winner"], m["loser"], m["date"]
        day = date.fromisoformat(d)
        for p in (w, l):
            if p in last:
                sd[p] = widen(sd[p], (day - last[p]).days)
            last[p] = day
        # ponytail: both updated from each other's pre-match law. Ratings Central's "adjusted laws"
        # loop only matters when a whole event is rated at once; we rate one match at a time.
        new_w = update(rating[w], sd[w], rating[l], sd[l], 1)
        new_l = update(rating[l], sd[l], rating[w], sd[w], 0)
        delta = round(new_w[0]) - round(rating[w])
        (rating[w], sd[w]), (rating[l], sd[l]) = new_w, new_l
        wins[w] += 1
        losses[l] += 1
        h2h[(w, l)] += 1
        history[w].append((d, round(rating[w])))
        history[l].append((d, round(rating[l])))
        results.append((d, w, l, delta, m.get("score") or ""))
    return rating, sd, wins, losses, h2h, history, results


def trend(hist, asof):
    """Rating change over the last TREND_DAYS, relative to the latest match date (deterministic)."""
    if not hist:
        return 0
    cutoff = date.fromisoformat(asof).toordinal() - TREND_DAYS
    before = START
    for d, r in hist:
        if date.fromisoformat(d).toordinal() < cutoff:
            before = r
    return hist[-1][1] - before


def build(matches, players=()):
    rating, sd, wins, losses, h2h, history, results = compute(matches, players)
    players = sorted(rating, key=lambda p: (-rating[p], p))
    asof = matches[-1]["date"] if matches else date.today().isoformat()
    out = ["# Office Table Tennis", "", f"{len(matches)} matches, {len(players)} players. Last match {asof}.", ""]

    out += ["## Rankings", "", f"| # | Player | Rating | +- | W | L | Last {TREND_DAYS} days |", "|--:|---|--:|--:|--:|--:|--:|"]
    for i, p in enumerate(players, 1):
        t = trend(history[p], asof)
        icon = "🔥" if t >= 30 else "📈" if t > 0 else "📉" if t < 0 else "➖"
        out.append(f"| {i} | {p} | {round(rating[p])} | {round(sd[p])} | {wins[p]} | {losses[p]} | {icon} {t:+d} |")
    out += ["", "Rating is the best estimate of strength, +- is how sure the system is (shrinks as you play).", ""]

    movers = sorted(((trend(history[p], asof), p) for p in players), reverse=True)
    rising = [f"{p} ({t:+d})" for t, p in movers if t > 0][:3]
    out += ["## On the rise", "", ", ".join(rising) or "Nobody yet."]

    out += ["", "## Recent results", "", "| Date | Winner | Loser | Score | +/- |", "|---|---|---|---|--:|"]
    out += [f"| {d} | {w} | {l} | {score} | {delta} |" for d, w, l, delta, score in reversed(results[-RECENT:])]

    out += ["", "## Head to head", "", "Row vs column, shown as wins-losses.", ""]
    out += ["| | " + " | ".join(players) + " |", "|---|" + "--:|" * len(players)]
    for p in players:
        cells = ["-" if p == q else f"{h2h.get((p, q), 0)}-{h2h.get((q, p), 0)}" for q in players]
        out.append(f"| {p} | " + " | ".join(cells) + " |")
    return "\n".join(out) + "\n"


def chip(t):
    cls = "up" if t > 0 else "down" if t < 0 else "flat"
    return f'<span class="chip {cls}">{t:+d}</span>'


def page(matches, players=()):
    """Fill template.html with the same data as the README."""
    rating, sd, wins, losses, h2h, history, results = compute(matches, players)
    players = sorted(rating, key=lambda p: (-rating[p], p))
    asof = matches[-1]["date"] if matches else date.today().isoformat()
    e = html.escape
    lo, hi = (min(rating.values()), max(rating.values())) if rating else (START, START)
    rows = []
    for i, p in enumerate(players, 1):
        pct = 15 + 85 * (rating[p] - lo) / (hi - lo) if hi > lo else 50
        rows.append(
            f'<tr><td class="rank r{i}">{i}</td><td class="player">{e(p)}</td>'
            f'<td class="num"><span class="rating">{round(rating[p])}</span><span class="sd">&plusmn;{round(sd[p])}</span>'
            f'<div class="bar"><i style="width:{pct:.0f}%"></i></div></td>'
            f'<td class="wl">{wins[p]}W {losses[p]}L</td><td class="num">{chip(trend(history[p], asof))}</td></tr>')
    movers = sorted(((trend(history[p], asof), p) for p in players), reverse=True)
    rising = [f'<span class="chip up">{e(p)} {t:+d}</span>' for t, p in movers if t > 0][:3]
    recent = [f'<li><span class="date">{d}</span><span><b>{e(w)}</b> <span class="beat">beat</span> {e(l)}</span>'
              f'<span class="score">{e(score)}</span>{chip(delta)}</li>'
              for d, w, l, delta, score in reversed(results[-RECENT:])]
    head = "".join(f"<th>{e(q)}</th>" for q in players)
    grid = []
    for p in players:
        cells = []
        for q in players:
            if p == q:
                cells.append('<td class="none">&middot;</td>')
            else:
                a, b = h2h.get((p, q), 0), h2h.get((q, p), 0)
                cls = "win" if a > b else "loss" if b > a else "none" if a == b == 0 else ""
                cells.append(f'<td class="{cls}">{a}-{b}</td>')
        grid.append(f"<tr><td>{e(p)}</td>{''.join(cells)}</tr>")
    tpl = string.Template(open(TEMPLATE, encoding="utf-8").read())
    return tpl.substitute(
        meta=f"{len(matches)} matches &middot; {len(players)} players &middot; last match {asof}",
        trend_days=TREND_DAYS, rankings="".join(rows), rising="".join(rising) or '<span class="meta">Nobody yet.</span>',
        recent="".join(recent) or '<li><span class="meta">No matches yet.</span></li>',
        h2h_head=head, h2h="".join(grid), repo=REPO)


def add(winner, loser, *rest):
    when = next((a for a in rest if a[:4].isdigit() and "-" in a[4:5]), date.today().isoformat())
    score = next((a for a in rest if a != when), "")
    date.fromisoformat(when)  # raises on bad date
    if not winner.strip() or not loser.strip() or winner == loser:
        sys.exit("need two different names")
    known = set(roster()) | {p for m in load() for p in (m["winner"], m["loser"])}
    for p in (winner, loser):
        if p not in known:
            print(f"note: new player '{p}' - not in players.txt, check spelling", file=sys.stderr)
    with open(MATCHES, "a", newline="", encoding="utf-8") as f:
        csv.writer(f, lineterminator="\n").writerow([when, winner, loser, score])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # windows console
    if len(sys.argv) > 1 and sys.argv[1] == "add":
        add(*sys.argv[2:6])
    elif len(sys.argv) > 1:
        sys.exit(__doc__)
    md = build(load(), roster())
    with open(README, "w", encoding="utf-8", newline="\n") as f:
        f.write(md)
    with open(INDEX, "w", encoding="utf-8", newline="\n") as f:
        f.write(page(load(), roster()))
    print(md)
