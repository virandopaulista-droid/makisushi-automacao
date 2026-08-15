#!/usr/bin/env bash
# Entry point: sources .env then runs the poller.
# Usage: run_poller.sh [--live] [--force-slot story|feed|reel]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# shellcheck disable=SC1091
source "$PROJECT_DIR/.env"

export FB_PAGE_ACCESS_TOKEN FB_PAGE_ID IG_BUSINESS_ID
export MAKISUSHI_STORIES_DIR MAKISUSHI_VIDEOS_DIR MAKISUSHI_IMAGES_DIR

python3 "$SCRIPT_DIR/poller.py" "$@"
