#!/usr/bin/env python3
"""Checks whether now matches a scheduled Au Gratin slot and, if so,
publishes the corresponding post from THIS WEEK'S APPROVED PLAN.

Nothing is selected at posting time anymore -- that happens ahead of time in
generate_week_plan.py and must be explicitly approved (approve_week_plan.py)
by Rob before this poller will touch it. If the week's plan is missing or
still "pending_approval", the poller refuses to post and just warns -- same
review-before-publish model as Bernardino's/GM Hamburgueria's automation.

Schedule (adjust here if Rob wants different days/times):
  Mon-Fri     12:00 -> 1 story (image or video, from Stories Iasmim pool)
  Friday      11:00 -> weekly feed slot -- EITHER a reel OR a carousel,
                        whichever generate_week_plan.py picked for that week
                        (never both in the same week).

Catch-up, not a narrow window: fires as soon as "now" is at or past a
scheduled time (same day), and keeps trying on every later tick until that
slot's "posted" flag is set in the plan -- GitHub's own cron schedule has
proven unreliable about landing near its configured time on the sibling
Bernardino/TopTop automations, so a narrow match window can cause entire
days to silently post nothing.

Partial-failure safety: if posting crashes partway through (e.g. the FB leg
of a story succeeds but the Instagram leg errors), the plan entry is still
marked posted (so the next tick doesn't blindly retry and duplicate whatever
already went out for real) and a GitHub Issue is opened so a human can check
what actually posted. Same fix applied to Bernardino's automation after a
real duplicate-post incident on 2026-08-05.

Defaults to --dry-run (prints what it would do, does NOT call Facebook).
Pass --live to actually publish.
"""
import datetime
import json
import os
import subprocess
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
PLANS_DIR = os.path.join(PROJECT_DIR, "content", "week_plans")

# weekday(): Monday=0 ... Sunday=6
SCHEDULE = [
    {"slot": "story", "weekdays": {0, 1, 2, 3, 4}, "hour": 12, "minute": 0},  # Mon-Fri only, buffet is closed weekends
    {"slot": "weekly", "weekdays": {4}, "hour": 11, "minute": 0},
]

DRY_RUN = "--live" not in sys.argv[1:]


def run(cmd):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env=env)
    if result.returncode != 0:
        print(f"ERRO rodando {cmd}:\n{result.stderr}", file=sys.stderr)
        # NAO usar SystemExit -- nao e subclasse de Exception, entao o
        # "except Exception" que aciona a protecao contra post duplicado
        # nunca capturava isso (confirmado 2026-08-13 no Bernardino: post
        # duplicado real no Facebook por causa exatamente disso).
        raise RuntimeError(f"comando falhou (exit {result.returncode}): {cmd}")
    return result.stdout.strip()


def bash(script_rel, *args):
    return run(["bash", os.path.join(SCRIPTS_DIR, script_rel), *args])


def python(script_rel, *args):
    return run([sys.executable, os.path.join(SCRIPTS_DIR, script_rel), *args])


def resolve_caption_file(post):
    """caption_text is decided once, when the plan was generated (and
    reviewed/approved) -- never re-picked at posting time, so what actually
    gets posted always matches what was shown for approval. Falls back to
    calling make_caption.py only for older plans that predate this field."""
    if post.get("caption_text"):
        import tempfile
        fd, path = tempfile.mkstemp(prefix="caption_live_", suffix=".txt", dir=os.path.join(PROJECT_DIR, "content"))
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(post["caption_text"])
        return path
    return python("make_caption.py", "reel" if post["slot"] == "reel" else "feed")


def path_for_story(item):
    base = os.environ["AUGRATIN_STORIES_DIR"]
    return os.path.join(base, item["file"])


def path_for_reel(item):
    base = os.environ["AUGRATIN_VIDEOS_DIR"]
    return os.path.join(base, item["folder"], item["file"])


def path_for_feed(item):
    base = os.environ["AUGRATIN_IMAGES_DIR"]
    return os.path.join(base, item["folder"], item["file"])


def notify_once(marker, body):
    """Best-effort GitHub Issue notification -- never raises."""
    try:
        title = f"[poller] {marker}"
        check = subprocess.run(
            ["gh", "issue", "list", "--search", f'"{title}" in:title', "--state", "open", "--json", "number"],
            capture_output=True, text=True,
        )
        if check.returncode == 0 and check.stdout.strip() and check.stdout.strip() != "[]":
            return
        subprocess.run(["gh", "issue", "create", "--title", title, "--body", body], capture_output=True, text=True)
    except Exception as e:
        print(f"AVISO: notify_once falhou (nao critico): {e}", file=sys.stderr)


def handle_partial_failure(post, plan, plan_path, now, slot_label, exc):
    """A handler crashed mid-posting. Some items may have posted for real and
    some may not have -- there's no way to tell which from here. Marking
    "posted" unconditionally is the safer failure mode: it stops the next
    tick from blindly re-running the whole handler and re-posting whatever
    already went out for real. A human has to check Facebook/Instagram
    directly and manually post anything that's actually missing."""
    print(f"##[error] Falha ao publicar '{slot_label}': {exc}", file=sys.stderr)
    post["posted"] = True
    post["posted_at"] = now.isoformat(timespec="seconds")
    post["posting_error"] = f"Falha parcial/total ao publicar -- verificar manualmente o que saiu de verdade. Erro: {exc}"
    save_plan(plan, plan_path)
    notify_once(
        f"post-falhou-{post.get('date')}-{post.get('slot')}",
        f"O poller tentou publicar '{slot_label}' ({post.get('date')}) e um erro interrompeu a publicacao no meio "
        "(alguns itens podem ter saido de verdade, outros nao -- nao da pra saber automaticamente qual). "
        "Para nao arriscar duplicar o que ja saiu, marquei esse post como 'posted:true' -- ele NAO sera tentado de "
        "novo automaticamente. Confira manualmente no Facebook/Instagram da Au Gratin o que realmente foi "
        f"publicado, e publique manualmente qualquer item que estiver faltando.\n\nErro original: {exc}"
    )


def week_monday(date):
    return date - datetime.timedelta(days=date.weekday())


def load_plan(monday):
    plan_path = os.path.join(PLANS_DIR, f"{monday.isoformat()}.json")
    if not os.path.exists(plan_path):
        return None, plan_path
    with open(plan_path, encoding="utf-8") as f:
        return json.load(f), plan_path


def save_plan(plan, plan_path):
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)


def handle_story(post):
    item = post["items"][0]
    path = path_for_story(item)
    if DRY_RUN:
        print(f"[DRY-RUN] postaria story {item['type']}: {path}")
        return

    if item["type"] == "image":
        print(bash("post_story_all.sh", path))
    else:
        print(bash("post_story_video_fb.sh", path))
        folder_id = os.environ.get("AUGRATIN_STORIES_DRIVE_FOLDER_ID", "1rBwVvcmUZTDMjU3C1WcUR8sbtaqIG8s9")
        video_url = python("resolve_drive_url.py", item["file"], folder_id)
        print(bash("post_story_video_instagram.sh", video_url))


def handle_reel(post):
    item = post["items"][0]
    path = path_for_reel(item)
    caption_file = resolve_caption_file(post)
    if DRY_RUN:
        print(f"[DRY-RUN] postaria reel: {path}")
        return

    print(bash("post_reel_fb.sh", path, caption_file))
    video_url = python("resolve_drive_url.py", item["file"], item["drive_folder_id"])
    print(bash("post_reel_instagram.sh", caption_file, video_url))


def handle_feed(post):
    heic_paths = [path_for_feed(item) for item in post["items"]]
    caption_file = resolve_caption_file(post)
    if DRY_RUN:
        print(f"[DRY-RUN] postaria carrossel de feed: {heic_paths}")
        return

    jpg_paths = []
    for i, heic_path in enumerate(heic_paths):
        jpg_path = os.path.join(PROJECT_DIR, f"_tmp_feed_{i}.jpg")
        bash("convert_heic_to_jpg.sh", heic_path, jpg_path)
        jpg_paths.append(jpg_path)

    fb_output = bash("post_feed.sh", caption_file, "now", *jpg_paths)
    print(fb_output)

    for jpg_path in jpg_paths:
        try:
            os.remove(jpg_path)
        except OSError:
            pass

    ig_business_id = os.environ.get("IG_BUSINESS_ID", "").strip()
    if not ig_business_id:
        print("Instagram pulado (IG_BUSINESS_ID nao configurado ainda).")
        return

    photo_urls = []
    for line in fb_output.splitlines():
        if line.startswith("PHOTO_URLS:"):
            photo_urls = json.loads(line[len("PHOTO_URLS:"):])
    if not photo_urls:
        print("AVISO: sem URL publica de foto, pulando Instagram.", file=sys.stderr)
        return
    print(bash("post_instagram.sh", caption_file, *photo_urls))


HANDLERS = {"story": handle_story, "feed": handle_feed, "reel": handle_reel}


def _arg_value(flag):
    args = sys.argv[1:]
    if flag in args:
        idx = args.index(flag)
        if idx + 1 < len(args):
            return args[idx + 1]
    return None


def _find_weekly_post(plan, today_key):
    """The weekly slot (Friday) posts whichever of reel/feed the plan has for
    today -- generate_week_plan.py already picked exactly one, never both."""
    return next((p for p in plan["posts"] if p["date"] == today_key and p["slot"] in ("reel", "feed")), None)


def _post_from_plan(post, plan, plan_path, now, slot_label):
    if post is None:
        print(f"AVISO: cronograma aprovado nao tem post de '{slot_label}' pra hoje.", file=sys.stderr)
        return
    if post.get("posted"):
        return  # already posted this window, avoid duplicate on the next tick

    print(f"Disparando slot '{post['slot']}' ({'DRY-RUN' if DRY_RUN else 'LIVE'})...")
    try:
        HANDLERS[post["slot"]](post)
    except Exception as exc:
        if not DRY_RUN:
            handle_partial_failure(post, plan, plan_path, now, post["slot"], exc)
        raise

    if not DRY_RUN:
        post["posted"] = True
        post["posted_at"] = now.isoformat(timespec="seconds")
        save_plan(plan, plan_path)


def main():
    now = datetime.datetime.now()
    today_key = now.date().isoformat()

    force_date = _arg_value("--force-date")
    force_slot = _arg_value("--force-slot")
    if force_date and force_slot:
        print(f"FORCE: postando '{force_slot}' de {force_date} agora, ignorando janela de horario...")
        monday = week_monday(datetime.date.fromisoformat(force_date))
        plan, plan_path = load_plan(monday)
        if plan is None or plan["status"] != "approved":
            print("AVISO: cronograma nao encontrado ou nao aprovado.", file=sys.stderr)
            return
        if force_slot == "weekly":
            post = _find_weekly_post(plan, force_date)
        else:
            post = next((p for p in plan["posts"] if p["date"] == force_date and p["slot"] == force_slot), None)
        _post_from_plan(post, plan, plan_path, now, force_slot)
        return

    for entry in SCHEDULE:
        if now.weekday() not in entry["weekdays"]:
            continue
        scheduled = now.replace(hour=entry["hour"], minute=entry["minute"], second=0, microsecond=0)
        if now < scheduled:
            continue

        monday = week_monday(now.date())
        plan, plan_path = load_plan(monday)
        if plan is None:
            msg = f"AVISO: nenhum cronograma encontrado pra semana de {monday} ({plan_path})."
            print(msg, file=sys.stderr)
            if not DRY_RUN:
                notify_once(f"cronograma-ausente-{monday}", msg + " Rode generate_week_plan.py e aprove.")
            return
        if plan["status"] != "approved":
            msg = f"AVISO: cronograma da semana de {monday} ainda esta '{plan['status']}', nao aprovado."
            print(msg, file=sys.stderr)
            if not DRY_RUN:
                notify_once(f"cronograma-nao-aprovado-{monday}", msg + " Nada sera postado ate ser aprovado.")
            return

        if entry["slot"] == "weekly":
            post = _find_weekly_post(plan, today_key)
        else:
            post = next((p for p in plan["posts"] if p["date"] == today_key and p["slot"] == entry["slot"]), None)

        if post is not None and post.get("posted"):
            continue  # this slot's already done today, let the loop check other slots

        _post_from_plan(post, plan, plan_path, now, entry["slot"])
        return

    print("Nenhum slot devido agora.")


if __name__ == "__main__":
    main()
