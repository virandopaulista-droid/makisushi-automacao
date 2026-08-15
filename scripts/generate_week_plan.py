#!/usr/bin/env python3
"""Generates a week's posting plan for Au Gratin and writes it to
content/week_plans/<monday>.json with status "pending_approval" -- nothing
gets posted from a plan until approve_week_plan.py flips that to "approved"
(same review-before-publish model as Bernardino's/GM Hamburgueria's
automation; content is never picked live at posting time).

Picks (from the manifests in content/, marking each pick "used" there so
the same item doesn't repeat until its pool cycles through):
  - 1 story per day, Mon-Fri ONLY (augratin_stories_manifest.json) -- the
    buffet only operates Monday to Friday (Rob, 2026-08-05), so there is
    nothing to post about on Sat/Sun, unlike GM Hamburgueria which posts
    every day.
  - 1 weekly feed post, Friday -- EITHER a reel OR a carousel of 5 photos,
    never both in the same week (augratin_reels_manifest.json /
    augratin_feed_manifest.json), chosen at random each week.

Usage: generate_week_plan.py [YYYY-MM-DD]
  Date is any day in the target week; defaults to next Monday. Prints the
  path to the generated plan file.
"""
import datetime
import json
import os
import random
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_DIR = os.path.join(PROJECT_DIR, "content")
PLANS_DIR = os.path.join(CONTENT_DIR, "week_plans")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_caption import build_caption  # noqa: E402

WEEKDAY_NAMES = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]

# Which dish_tags (from the manifests' visual classification, see
# augratin_feed_manifest.json / augratin_reels_manifest.json) confirm that
# weekday's special dish. Mirrors make_caption.WEEKDAY_SPECIALS -- a weekday
# is only passed to build_caption() if at least one picked item's dish_tags
# intersects this set; otherwise the caption stays generic (no dish claim).
WEEKDAY_DISH_TAGS = {
    "quarta": {"feijoada"},
    "quinta": {"massas", "sushi", "costela_no_bafo"},
    "sexta": {"salmao", "rabada"},
}


def items_match_weekday(picks, weekday):
    """True if any picked manifest entry's dish_tags confirms weekday's special."""
    wanted = WEEKDAY_DISH_TAGS.get(weekday)
    if not wanted:
        return False
    return any(wanted & set(p.get("dish_tags") or []) for p in picks)


def week_monday(date):
    return date - datetime.timedelta(days=date.weekday())


def load_manifest(name):
    path = os.path.join(CONTENT_DIR, name)
    with open(path, encoding="utf-8") as f:
        return json.load(f), path


def save_manifest(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def pick_unused(data, n=1, prefer_tags=None, tries=8):
    """Pick n unused entries at random, resetting the pool if it's too small.

    If prefer_tags is given, make a few extra attempts (up to `tries`) to
    land a draw where at least one picked entry's dish_tags intersects
    prefer_tags -- e.g. so Friday's weekly post sometimes actually shows
    salmao/rabada and can get the specific-dish caption. Not a hard
    requirement: if no attempt matches, the last draw is used as-is (falls
    back to the generic caption).
    """
    assets = data["assets"]
    pool = [a for a in assets if not a["used"]]
    if len(pool) < n:
        for a in assets:
            a["used"] = False
            a["used_at"] = None
        pool = assets

    attempts = tries if prefer_tags else 1
    picks = random.sample(pool, min(n, len(pool)))
    for _ in range(attempts):
        if prefer_tags and any(set(p.get("dish_tags") or []) & prefer_tags for p in picks):
            break
        picks = random.sample(pool, min(n, len(pool)))

    now = datetime.datetime.now().isoformat(timespec="seconds")
    for entry in picks:
        entry["used"] = True
        entry["used_at"] = now
    return picks


def main():
    if len(sys.argv) > 1:
        ref_date = datetime.date.fromisoformat(sys.argv[1])
    else:
        today = datetime.date.today()
        ref_date = today + datetime.timedelta(days=(7 - today.weekday()) % 7 or 7)
    monday = week_monday(ref_date)

    stories_data, stories_path = load_manifest("augratin_stories_manifest.json")
    reels_data, reels_path = load_manifest("augratin_reels_manifest.json")
    feed_data, feed_path = load_manifest("augratin_feed_manifest.json")

    posts = []
    for i in range(5):  # Mon-Fri only -- buffet is closed Sat/Sun
        day = monday + datetime.timedelta(days=i)
        pick = pick_unused(stories_data, 1)[0]
        posts.append({
            "date": day.isoformat(),
            "weekday": WEEKDAY_NAMES[i],
            "slot": "story",
            "items": [{"file": pick["file"], "type": pick["type"]}],
        })

    # One weekly feed post -- reel OR carousel, never both the same week.
    # The manifests now carry dish_tags from a visual classification pass
    # (see augratin_feed_manifest.json / augratin_reels_manifest.json), so
    # the weekly slot's weekday ("sexta" today, but this generalizes if the
    # schedule ever changes) is only passed to build_caption() -- and a
    # dish is only named in the caption -- when the actual picked items'
    # dish_tags confirm that day's special. pick_unused() makes a few extra
    # attempts to draw a matching item so the specific-dish caption is
    # achievable sometimes; when no attempt matches, caption stays generic
    # (confirmed 2026-08-05: a random Friday carousel showed dining room,
    # rice, feijoada, pudim and raw steak -- no salmon/rabada -- so it must
    # never claim a dish the media doesn't show).
    friday = monday + datetime.timedelta(days=4)
    weekly_weekday = "sexta"
    wanted_tags = WEEKDAY_DISH_TAGS.get(weekly_weekday)
    weekly_kind = random.choice(["reel", "feed"])
    if weekly_kind == "reel":
        reel_pick = pick_unused(reels_data, 1, prefer_tags=wanted_tags)
        caption_weekday = weekly_weekday if items_match_weekday(reel_pick, weekly_weekday) else None
        reel_pick = reel_pick[0]
        posts.append({
            "date": friday.isoformat(),
            "weekday": weekly_weekday,
            "slot": "reel",
            "items": [{
                "file": reel_pick["file"],
                "folder": reel_pick["folder"],
                "drive_folder_id": reel_pick["drive_folder_id"],
                "dish_tags": reel_pick.get("dish_tags", []),
            }],
            "caption_text": build_caption("reel", caption_weekday),
        })
    else:
        feed_picks = pick_unused(feed_data, 5, prefer_tags=wanted_tags)
        caption_weekday = weekly_weekday if items_match_weekday(feed_picks, weekly_weekday) else None
        posts.append({
            "date": friday.isoformat(),
            "weekday": weekly_weekday,
            "slot": "feed",
            "items": [
                {"file": p["file"], "folder": p["folder"], "dish_tags": p.get("dish_tags", [])}
                for p in feed_picks
            ],
            "caption_text": build_caption("feed", caption_weekday),
        })

    posts.sort(key=lambda p: (p["date"], p["slot"] != "story"))

    plan = {
        "week_start": monday.isoformat(),
        "status": "pending_approval",
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "posts": posts,
    }

    os.makedirs(PLANS_DIR, exist_ok=True)
    plan_path = os.path.join(PLANS_DIR, f"{monday.isoformat()}.json")
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    save_manifest(stories_data, stories_path)
    save_manifest(reels_data, reels_path)
    save_manifest(feed_data, feed_path)

    print(plan_path)


if __name__ == "__main__":
    main()
