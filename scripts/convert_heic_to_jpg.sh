#!/usr/bin/env bash
# Converts a HEIC image to JPEG via ffmpeg, two passes (extract frame, then
# re-encode) -- a single-pass "-i in.heic -vf scale ... out.jpg" fails with
# "Filtergraph was specified for a stream fed from a complex filtergraph"
# because HEIC uses an internal tile-grid ffmpeg can't filter directly.
# Facebook/Instagram's upload APIs don't reliably accept raw HEIC bytes, so
# every feed image goes through this before posting.
# Usage: convert_heic_to_jpg.sh <input.heic> <output.jpg>
set -euo pipefail

IN="$1"
OUT="$2"
FULL="$(mktemp --suffix=.jpg)"

ffmpeg -y -i "$IN" -frames:v 1 "$FULL" >/dev/null 2>&1
ffmpeg -y -i "$FULL" -vf "scale=1600:-2" -q:v 3 "$OUT" >/dev/null 2>&1
rm -f "$FULL"

if [ ! -s "$OUT" ]; then
  echo "ERRO: conversao HEIC->JPG falhou para $IN" >&2
  exit 1
fi
