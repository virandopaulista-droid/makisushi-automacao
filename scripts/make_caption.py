#!/usr/bin/env python3
"""Writes a simple, ready-to-post caption (feed or reel) to a temp file and
prints its path. No AI generation -- templates modeled directly on Au
Gratin's real Instagram captions (Rob sent 4 real examples 2026-08-05),
picked at random so consecutive posts don't read identically.

Au Gratin is dine-in only (buffet by weight, salão), NOT delivery -- never
write "peça já"/delivery-style CTAs here. Address uses an en-dash "–"
(meia-risca), matching the real captions -- NOT an em-dash "—" (travessão,
banned per Rob's standing rule for GM Hamburgueria's captions too).

Real info: address Rua Amador Bueno, 771, Santo Amaro; hours segunda a
sexta, das 11h às 15h (only shown in some captions, not all -- matches real
usage). Buffet changes daily, by weight.

Day-specific specials (Rob, 2026-08-05): pass --weekday
<segunda|terca|quarta|quinta|sexta> to get a caption naming that day's dish
(falls back to generic buffet copy otherwise):
  quarta: feijoada
  quinta: massas, sushi e costela no bafo
  sexta: salmão e rabada
segunda/terça have no standout dish (pratos variados).

Usage: make_caption.py <feed|reel> [--weekday <dia>]
Prints: path to the temp file containing the caption.
"""
import random
import sys
import tempfile

ADDRESS = "📍 Rua Amador Bueno, 771 – Santo Amaro"
HOURS = "⏰ Segunda a sexta, das 11h às 15h"

GENERIC_HASHTAGS = "#restaurantesantoamaro #selfservicesp #comidacaseira #buffetsp #almocoespecial"

SPECIAL_HASHTAGS = {
    "quarta": "#feijoada #restaurantesantoamaro #selfservicesp #buffetsp",
    "quinta": "#massas #sushi #costelanobafo #restaurantesantoamaro #buffetsp",
    "sexta": "#salmao #rabada #restaurantesantoamaro #selfservicesp #almocoemsp",
}

WEEKDAY_SPECIALS = {
    "quarta": "feijoada",
    "quinta": "massas, sushi e costela no bafo",
    "sexta": "salmão fresco e rabada",
}

# Generic templates (no standout dish that day, or a plain feed/reel post
# not tied to a specific weekday) -- address always included, hours only
# on some (matches the real mix Rob sent: 2 of 4 examples had no hours line).
GENERIC_TEMPLATES = [
    "✨ Todos os dias, um buffet completo espera por você. Monte seu prato do seu jeito e aproveite uma refeição preparada com cuidado, variedade e aquele sabor que transforma a pausa do almoço no melhor momento do dia.\n\n{address}\n\n{hashtags}",
    "🍽️ Se você procura o melhor lugar para almoçar em Santo Amaro, o AU GRATIN tem tudo pra te conquistar!\n\nAqui você encontra inúmeras opções no buffet, comida caseira preparada com carinho e sabores que deixam qualquer almoço muito mais especial...✨\n\n{address}\n{hours}\n\n{hashtags}",
    "✨ Que tal passar no AU GRATIN hoje?\n\nVenha nos visitar e aproveite um almoço delicioso no nosso buffet... 🍽️\n\n{address}\n{hours}",
]

# Special-dish templates -- used when the post falls on quarta/quinta/sexta.
SPECIAL_TEMPLATES = [
    "🍽️ {weekday_cap} pede um almoço à altura. Hoje, o destaque fica por conta do nosso {prato}, preparados com todo o cuidado para entregar muito sabor em cada detalhe.\nE, claro, o buffet ainda conta com diversas outras opções esperando por você.\n\n{address}\n\n{hashtags}",
    "✨ Hoje tem {prato} esperando por você no nosso buffet! Chega, monte seu prato à vontade e aproveite.\n\n{address}\n{hours}\n\n{hashtags}",
]

TEMPLATES = {"feed": GENERIC_TEMPLATES, "reel": GENERIC_TEMPLATES}
WEEKDAY_LABEL = {"quarta": "Quarta-feira", "quinta": "Quinta-feira", "sexta": "Sexta-feira"}


def build_caption(kind, weekday=None):
    prato = WEEKDAY_SPECIALS.get(weekday)
    if prato:
        template = random.choice(SPECIAL_TEMPLATES)
        return template.format(
            weekday_cap=WEEKDAY_LABEL[weekday],
            prato=prato,
            address=ADDRESS,
            hours=HOURS,
            hashtags=SPECIAL_HASHTAGS[weekday],
        )
    template = random.choice(GENERIC_TEMPLATES)
    return template.format(address=ADDRESS, hours=HOURS, hashtags=GENERIC_HASHTAGS)


def main():
    args = sys.argv[1:]
    if not args or args[0] not in TEMPLATES:
        print("Uso: make_caption.py <feed|reel> [--weekday <dia>]", file=sys.stderr)
        raise SystemExit(1)
    kind = args[0]
    weekday = None
    if "--weekday" in args:
        idx = args.index("--weekday")
        if idx + 1 < len(args):
            weekday = args[idx + 1]
    caption = build_caption(kind, weekday)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(caption)
        path = f.name
    print(path)


if __name__ == "__main__":
    main()
