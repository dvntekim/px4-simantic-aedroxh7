#!/bin/bash
# Build PX4 AEDROXH7 (pinned commit + px4/patches), run it on Simantic, and
# commit the change together with Simantic's raw output.
#   usage: scripts/sim-commit.sh "commit subject"
set -uo pipefail
[ $# -ge 1 ] || { echo 'usage: scripts/sim-commit.sh "commit subject"'; exit 2; }
SUBJECT="$1"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PX4="${PX4_DIR:-$REPO/../PX4-Autopilot}"
TARGET=aedrox_aedroxh7_default
PIN="$(cat "$REPO/px4/PX4_COMMIT")"
RES="$REPO/results"

# 1. Board files back to the pinned commit, then our patches on top.
cd "$PX4" || exit 1
[ "$(git rev-parse HEAD)" = "$PIN" ] || { echo "PX4 is not at $PIN"; exit 1; }
git checkout -q -- boards/aedrox/aedroxh7
PATCHES=""
for p in "$REPO"/px4/patches/*.patch; do
  [ -e "$p" ] || continue
  git apply "$p" || { echo "patch failed: $p"; exit 1; }
  PATCHES="$PATCHES $p"
done
if [ -n "$PATCHES" ]; then
  SET="$(cat $PATCHES | shasum | cut -c1-12)"
  PLIST="$(for p in $PATCHES; do basename "$p"; done | paste -sd, -)"
else
  SET=none; PLIST="none (stock PX4)"
fi

# 2. Build. NuttX builds in-tree, so a new patch set needs a clean NuttX build.
STAMP="build/$TARGET/.patchset"
if [ "$(cat "$STAMP" 2>/dev/null)" != "$SET" ]; then
  echo "== patch set changed ($SET): clean NuttX build"
  rm -rf "build/$TARGET"
  git -C platforms/nuttx/NuttX/nuttx clean -qdfX
  git -C platforms/nuttx/NuttX/apps clean -qdfX
fi
source .venv/bin/activate
make "$TARGET" || { echo "build failed"; exit 1; }
echo "$SET" > "$STAMP"

# 3. Run on Simantic. Output is saved as printed.
cd "$REPO/sim" || exit 1
python3 tests/check_peers_offline.py || exit 1
mkdir -p "$RES"
CMD="sim run --scenario scenario-aedroxh7.yaml --ascii --output ../results/console.txt --frames ../results/frames.full.txt"
echo "\$ $CMD" > "$RES/sim-output.txt"
$CMD 2>&1 | tee -a "$RES/sim-output.txt"
STATUS=${PIPESTATUS[0]}
grep -E "imu0|baro" "$RES/frames.full.txt" 2>/dev/null | head -200 > "$RES/sensor-bus.txt"
if [ "$STATUS" -eq 0 ]; then VERDICT=PASS; else VERDICT=FAIL; fi

# 4. Commit code + raw results.
cd "$REPO" || exit 1
echo "| $(date '+%Y-%m-%d %H:%M') | $SUBJECT | $PLIST | **$VERDICT** |" >> RUNS.md
{
  echo "$SUBJECT"
  echo
  echo "Simantic: $VERDICT (sim exit $STATUS)"
  echo "PX4 ${PIN:0:10} + patches: $PLIST"
  echo
  tail -n 25 "$RES/sim-output.txt"
} > .git/SIM_MSG
git add -A
git commit -q --cleanup=verbatim -F .git/SIM_MSG || exit 1
echo
git log -1 --stat
