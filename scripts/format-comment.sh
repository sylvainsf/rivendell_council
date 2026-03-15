#!/usr/bin/env bash
# format-comment.sh — Format Rivendell Council reviews into a PR comment.
#
# Usage: format-comment.sh <reviews_dir> <verdict_file>
#   reviews_dir:  directory containing {member}/review.json files
#   verdict_file: path to Gandalf's verdict JSON
#
# Outputs the formatted Markdown comment to stdout.

set -euo pipefail

REVIEWS_DIR="${1:?Usage: format-comment.sh <reviews_dir> <verdict_file>}"
VERDICT_FILE="${2:?Usage: format-comment.sh <reviews_dir> <verdict_file>}"

# Member display metadata
member_emoji() {
  case "$1" in
    elrond)  echo "🌟" ;;
    gimli)   echo "⚔️" ;;
    aragorn) echo "👑" ;;
    legolas) echo "🏹" ;;
    bilbo)   echo "🍃" ;;
    *)       echo "📜" ;;
  esac
}

member_title() {
  case "$1" in
    elrond)  echo "Elrond · Correctness" ;;
    gimli)   echo "Gimli · Strength" ;;
    aragorn) echo "Aragorn · Maintainability" ;;
    legolas) echo "Legolas · Performance" ;;
    bilbo)   echo "Bilbo · Style" ;;
    *)       echo "$1" ;;
  esac
}

# ── Header ──────────────────────────────────────────────────────────────────

echo "# 🧙 Rivendell Council Review"
echo ""
echo "## Council Members' Assessment"
echo ""

# ── Individual reviews ──────────────────────────────────────────────────────

for review_file in "$REVIEWS_DIR"/*/review.json; do
  [ -f "$review_file" ] || continue
  member=$(basename "$(dirname "$review_file")")
  emoji=$(member_emoji "$member")
  title=$(member_title "$member")

  score=$(jq -r '.score // "N/A"' "$review_file" 2>/dev/null || echo "N/A")
  summary=$(jq -r '.summary // empty' "$review_file" 2>/dev/null || true)

  echo "### $emoji $title  ·  Score: $score/10"
  echo ""
  [ -n "$summary" ] && echo "$summary" && echo ""

  # Concerns
  concern_count=$(jq -r '.concerns | length // 0' "$review_file" 2>/dev/null || echo 0)
  if [ "$concern_count" -gt 0 ] 2>/dev/null; then
    echo "**Concerns:**"
    jq -r '.concerns[]' "$review_file" 2>/dev/null | while IFS= read -r c; do
      echo "- $c"
    done
    echo ""
  fi

  # Suggestions
  suggestion_count=$(jq -r '.suggestions | length // 0' "$review_file" 2>/dev/null || echo 0)
  if [ "$suggestion_count" -gt 0 ] 2>/dev/null; then
    echo "**Suggestions:**"
    jq -r '.suggestions[]' "$review_file" 2>/dev/null | while IFS= read -r s; do
      echo "- $s"
    done
    echo ""
  fi

  # Raw response fallback
  raw=$(jq -r '.raw_response // empty' "$review_file" 2>/dev/null || true)
  if [ -n "$raw" ]; then
    echo "<details><summary>Raw response</summary>"
    echo ""
    echo "$raw"
    echo ""
    echo "</details>"
    echo ""
  fi
done

# ── Gandalf's verdict ──────────────────────────────────────────────────────

echo "---"
echo ""

if verdict=$(jq -r '.verdict // "UNKNOWN"' "$VERDICT_FILE" 2>/dev/null); then
  verdict_upper=$(echo "$verdict" | tr '[:lower:]' '[:upper:]')
else
  verdict_upper="UNKNOWN"
fi

if [ "$verdict_upper" = "PASS" ]; then
  echo "## 🧙‍♂️ Gandalf's Verdict: ✅ **PASS**"
else
  echo "## 🧙‍♂️ Gandalf's Verdict: ❌ **$verdict_upper**"
fi
echo ""

v_summary=$(jq -r '.summary // empty' "$VERDICT_FILE" 2>/dev/null || true)
[ -n "$v_summary" ] && echo "$v_summary" && echo ""

reasoning=$(jq -r '.reasoning // empty' "$VERDICT_FILE" 2>/dev/null || true)
[ -n "$reasoning" ] && echo "**Reasoning:** $reasoning" && echo ""

feedback=$(jq -r '.feedback // empty' "$VERDICT_FILE" 2>/dev/null || true)
[ -n "$feedback" ] && echo "**Feedback:** $feedback" && echo ""
