#!/usr/bin/env bash
# parse-config.sh — Parse council.md and emit JSON outputs for the workflow.
#
# Usage: parse-config.sh <config_file>
#
# Outputs (written to $GITHUB_OUTPUT if set, else printed):
#   members       — JSON array of enabled member names (excluding Gandalf)
#   weights       — JSON object mapping member name → weight
#   model         — model identifier string
#   threshold     — passing_threshold number
#   gandalf       — "true" or "false"

set -euo pipefail

CONFIG_FILE="${1:?Usage: parse-config.sh <config_file>}"

# Extract YAML front matter (between --- markers), or treat whole file as YAML
if head -1 "$CONFIG_FILE" | grep -q '^---$'; then
  yaml_content=$(sed -n '/^---$/,/^---$/{ /^---$/d; p; }' "$CONFIG_FILE")
else
  yaml_content=$(cat "$CONFIG_FILE")
fi

# Parse with yq (pre-installed on GitHub-hosted runners)
config=$(printf '%s' "$yaml_content" | yq -o=json)

# Extract model and threshold
model=$(printf '%s' "$config" | jq -r '.model // "openai/gpt-4o"')
threshold=$(printf '%s' "$config" | jq -r '.passing_threshold // 6.0')

# Build members list and weights — exclude Gandalf (he gets his own job)
members_json=$(printf '%s' "$config" | jq -c '
  [.members // {} | to_entries[]
   | select(.key != "Gandalf")
   | select(.value.enabled // true)
   | .key]')

weights_json=$(printf '%s' "$config" | jq -c '
  [.members // {} | to_entries[]
   | select(.key != "Gandalf")
   | select(.value.enabled // true)
   | {(.key): (.value.weight // 1.0)}]
  | add // {}')

# Check if Gandalf is enabled
gandalf_enabled=$(printf '%s' "$config" | jq -r '
  .members.Gandalf.enabled // true')

echo "Parsed council config:"
echo "  Members: $members_json"
echo "  Weights: $weights_json"
echo "  Model:   $model"
echo "  Threshold: $threshold"
echo "  Gandalf: $gandalf_enabled"

# Write outputs
if [ -n "${GITHUB_OUTPUT:-}" ]; then
  echo "members=$members_json" >> "$GITHUB_OUTPUT"
  echo "weights=$weights_json" >> "$GITHUB_OUTPUT"
  echo "model=$model" >> "$GITHUB_OUTPUT"
  echo "threshold=$threshold" >> "$GITHUB_OUTPUT"
  echo "gandalf=$gandalf_enabled" >> "$GITHUB_OUTPUT"
else
  echo "members=$members_json"
  echo "weights=$weights_json"
  echo "model=$model"
  echo "threshold=$threshold"
  echo "gandalf=$gandalf_enabled"
fi
