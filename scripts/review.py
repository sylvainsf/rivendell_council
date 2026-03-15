#!/usr/bin/env python3
"""
Rivendell Council – AI-powered pull request review.

Reads the council configuration, fetches the PR diff, asks each enabled council
member (via the OpenAI Chat Completions API) to review the diff, then asks Gandalf
to synthesise the reviews and deliver a final PASS/FAIL verdict.

Environment variables (all injected by action.yml):
    OPENAI_API_KEY   – OpenAI API key
    GITHUB_TOKEN     – GitHub token (read PR diff + post comment)
    GITHUB_REPOSITORY – "owner/repo"
    COUNCIL_CONFIG   – path to council.md (empty → use bundled default)
    MODEL_OVERRIDE   – optional model override
    MAX_DIFF_CHARS   – max characters of diff to send to each reviewer
    ACTION_PATH      – filesystem path to the root of this action
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any

import requests
import yaml

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GITHUB_API = "https://api.github.com"
OPENAI_API = "https://api.openai.com/v1/chat/completions"

# Core members listed in display order; any additional members defined in council.md
# (e.g. Bilbo or project-specific reviewers) are appended after these in config order.
CORE_MEMBERS = ["Elrond", "Gimli", "Aragorn", "Legolas"]

MEMBER_EMOJI: dict[str, str] = {
    "Elrond": "🌟",
    "Gimli": "⚔️",
    "Aragorn": "👑",
    "Legolas": "🏹",
    "Bilbo": "🍃",
}

# ---------------------------------------------------------------------------
# GitHub helpers
# ---------------------------------------------------------------------------


def _github_headers(token: str, accept: str = "application/vnd.github.v3+json") -> dict[str, str]:
    return {"Authorization": f"token {token}", "Accept": accept}


def get_pr_info() -> tuple[str, int]:
    """Return the (diff text, PR number) for the current event."""
    token = os.environ["GITHUB_TOKEN"]
    repo = os.environ["GITHUB_REPOSITORY"]

    # Resolve PR number from the event payload
    pr_number: int | None = None
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    if event_path and os.path.isfile(event_path):
        with open(event_path) as fh:
            event = json.load(fh)
        pr_number = (
            event.get("pull_request", {}).get("number")
            or event.get("number")
        )

    if pr_number is None:
        pr_number_env = os.environ.get("PR_NUMBER", "")
        if pr_number_env:
            pr_number = int(pr_number_env)

    if pr_number is None:
        raise RuntimeError(
            "Could not determine PR number. "
            "Make sure the action is triggered by a pull_request event, "
            "or set the PR_NUMBER environment variable."
        )

    resp = requests.get(
        f"{GITHUB_API}/repos/{repo}/pulls/{pr_number}",
        headers=_github_headers(token, accept="application/vnd.github.v3.diff"),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.text, int(pr_number)


def post_pr_comment(repo: str, pr_number: int, body: str, token: str) -> None:
    resp = requests.post(
        f"{GITHUB_API}/repos/{repo}/issues/{pr_number}/comments",
        headers=_github_headers(token),
        json={"body": body},
        timeout=30,
    )
    resp.raise_for_status()


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------


def parse_council_config(config_path: str) -> dict[str, Any]:
    """Parse YAML front matter (or plain YAML) from *config_path*."""
    with open(config_path) as fh:
        content = fh.read()

    # Try YAML front matter first (--- ... ---)
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if match:
        return yaml.safe_load(match.group(1)) or {}

    # Fall back to treating the whole file as YAML
    return yaml.safe_load(content) or {}


def resolve_config_path(action_path: str) -> str:
    """Return the path to the council.md that should be used."""
    env_path = os.environ.get("COUNCIL_CONFIG", "").strip()
    if env_path and os.path.isfile(env_path):
        return env_path

    # Default: bundled council.md at the action root
    bundled = os.path.join(action_path, "council.md")
    if os.path.isfile(bundled):
        return bundled

    raise FileNotFoundError(
        f"No council.md found. "
        f"Checked COUNCIL_CONFIG={env_path!r} and bundled path {bundled!r}."
    )


def load_prompt(name: str, action_path: str) -> str:
    prompt_path = os.path.join(action_path, "council", f"{name}.md")
    with open(prompt_path) as fh:
        return fh.read()


# ---------------------------------------------------------------------------
# OpenAI helpers
# ---------------------------------------------------------------------------


def call_openai(messages: list[dict], model: str, api_key: str) -> str:
    resp = requests.post(
        OPENAI_API,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages, "temperature": 0.2},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def extract_json(text: str) -> dict[str, Any]:
    """Extract and parse the first JSON object from *text*."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    # Return a safe fallback so the pipeline never crashes on bad JSON
    return {"raw_response": text}


def review_diff(member: str, prompt: str, diff: str, model: str, api_key: str) -> dict[str, Any]:
    """Ask a council member to review *diff* and return parsed JSON."""
    messages = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": (
                "Please review the following pull request diff and respond with JSON only.\n\n"
                f"```diff\n{diff}\n```"
            ),
        },
    ]
    raw = call_openai(messages, model, api_key)
    result = extract_json(raw)
    if "score" not in result:
        result["score"] = 5  # safe default
    return result


def gandalf_decision(
    prompt: str,
    diff: str,
    reviews: dict[str, dict],
    model: str,
    api_key: str,
) -> dict[str, Any]:
    """Ask Gandalf to synthesise the council reviews and deliver a verdict."""
    messages = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": (
                "Here is the pull request diff under review:\n\n"
                f"```diff\n{diff}\n```\n\n"
                "Here are the council members' reviews:\n\n"
                f"{json.dumps(reviews, indent=2)}\n\n"
                "Deliver your final verdict. Respond with JSON only."
            ),
        },
    ]
    raw = call_openai(messages, model, api_key)
    result = extract_json(raw)
    if "verdict" not in result:
        # Best-effort fallback
        result["verdict"] = "FAIL" if "FAIL" in raw.upper() else "PASS"
    return result


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def format_review_comment(
    reviews: dict[str, dict],
    decision: dict[str, Any],
    members_cfg: dict[str, Any],
) -> str:
    lines: list[str] = ["# 🧙 Rivendell Council Review\n"]

    # Individual member reviews
    lines.append("## Council Members' Assessment\n")
    for member, review in reviews.items():
        emoji = MEMBER_EMOJI.get(member, "📜")
        weight = members_cfg.get(member, {}).get("weight", 1.0)
        score = review.get("score", "N/A")
        lines.append(f"### {emoji} {member}  ·  Score: {score}/10  ·  Weight: {weight}\n")

        if summary := review.get("summary"):
            lines.append(f"{summary}\n")

        if concerns := review.get("concerns"):
            lines.append("**Concerns:**")
            for c in concerns:
                lines.append(f"- {c}")
            lines.append("")

        if suggestions := review.get("suggestions"):
            lines.append("**Suggestions:**")
            for s in suggestions:
                lines.append(f"- {s}")
            lines.append("")

        if "raw_response" in review:
            lines.append("<details><summary>Raw response</summary>\n")
            lines.append(f"\n{review['raw_response']}\n\n</details>\n")

    # Gandalf's verdict
    verdict = decision.get("verdict", "UNKNOWN").upper()
    verdict_emoji = "✅" if verdict == "PASS" else "❌"
    lines.append("---\n")
    lines.append(f"## 🧙‍♂️ Gandalf's Verdict: {verdict_emoji} **{verdict}**\n")

    if summary := decision.get("summary"):
        lines.append(f"{summary}\n")

    if reasoning := decision.get("reasoning"):
        lines.append(f"**Reasoning:** {reasoning}\n")

    if feedback := decision.get("feedback"):
        lines.append(f"**Feedback:** {feedback}\n")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# GitHub Actions output
# ---------------------------------------------------------------------------


def set_output(name: str, value: str) -> None:
    """Write a GitHub Actions step output."""
    github_output = os.environ.get("GITHUB_OUTPUT", "")
    if github_output:
        with open(github_output, "a") as fh:
            if "\n" in value:
                delimiter = "RIVENDELL_EOF"
                fh.write(f"{name}<<{delimiter}\n{value}\n{delimiter}\n")
            else:
                fh.write(f"{name}={value}\n")
    else:
        # Legacy fallback (older runners)
        print(f"::set-output name={name}::{value}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    api_key = os.environ["OPENAI_API_KEY"]
    token = os.environ["GITHUB_TOKEN"]
    repo = os.environ["GITHUB_REPOSITORY"]
    action_path = os.environ.get("ACTION_PATH", os.path.dirname(__file__) + "/..")
    max_diff_chars = int(os.environ.get("MAX_DIFF_CHARS", "30000"))
    model_override = os.environ.get("MODEL_OVERRIDE", "").strip()

    print("🧙 The Rivendell Council is assembling…")

    # Load configuration
    config_path = resolve_config_path(action_path)
    print(f"  Config: {config_path}")
    config = parse_council_config(config_path)
    members_cfg: dict[str, Any] = config.get("members", {})
    model: str = model_override or config.get("model", "gpt-4o")
    passing_threshold: float = float(config.get("passing_threshold", 6.0))
    print(f"  Model:  {model}")

    # Fetch PR diff
    print("\nFetching PR diff from GitHub…")
    diff, pr_number = get_pr_info()
    print(f"  PR #{pr_number}  ({len(diff)} chars)")

    if not diff.strip():
        print("No diff detected — skipping review.")
        set_output("decision", "PASS")
        set_output("summary", "No changes to review.")
        return

    if len(diff) > max_diff_chars:
        print(f"  Diff truncated to {max_diff_chars} chars.")
        diff = diff[:max_diff_chars] + "\n\n… (diff truncated due to length)"

    # Build the ordered list of non-Gandalf reviewers: core members first, then any
    # extra members defined in the config (e.g. Bilbo or project-specific reviewers).
    extra_members = [m for m in members_cfg if m not in CORE_MEMBERS and m != "Gandalf"]
    all_reviewers = CORE_MEMBERS + extra_members

    # Gather reviews from each enabled council member
    reviews: dict[str, dict] = {}
    print("\nConvening council members…")

    for member in all_reviewers:
        cfg = members_cfg.get(member, {})
        if not cfg.get("enabled", True):
            print(f"  ⏭️  {member} is absent from this council.")
            continue

        weight = float(cfg.get("weight", 1.0))
        print(f"  {MEMBER_EMOJI.get(member, '📜')} {member} reviewing (weight={weight})…", end="", flush=True)

        try:
            prompt = load_prompt(member, action_path)
            review = review_diff(member, prompt, diff, model, api_key)
            review["weight"] = weight
            reviews[member] = review
            print(f" score={review.get('score', '?')}/10")
        except Exception as exc:  # noqa: BLE001
            print(f" ERROR: {exc}")
            reviews[member] = {"score": 5, "weight": weight, "error": str(exc)}

    # Gandalf's final decision
    print("\n🧙 Gandalf is deliberating…")
    gandalf_cfg = members_cfg.get("Gandalf", {})

    if not gandalf_cfg.get("enabled", True):
        print("  Gandalf is absent — using weighted average.")
        if reviews:
            weighted_sum = sum(
                float(r.get("score", 5)) * float(r.get("weight", 1.0))
                for r in reviews.values()
            )
            total_weight = sum(float(r.get("weight", 1.0)) for r in reviews.values())
            avg = weighted_sum / total_weight
        else:
            avg = 5.0
        verdict = "PASS" if avg >= passing_threshold else "FAIL"
        decision: dict[str, Any] = {
            "verdict": verdict,
            "summary": f"Weighted-average score: {avg:.1f}/10 (threshold: {passing_threshold}).",
            "reasoning": "Gandalf was absent; the decision was made by weighted average.",
            "feedback": "" if verdict == "PASS" else "Please address the council's concerns.",
        }
    else:
        try:
            gandalf_prompt = load_prompt("Gandalf", action_path)
            decision = gandalf_decision(gandalf_prompt, diff, reviews, model, api_key)
        except Exception as exc:  # noqa: BLE001
            print(f"  ERROR during Gandalf's deliberation: {exc}")
            decision = {
                "verdict": "FAIL",
                "summary": "An error occurred during Gandalf's deliberation.",
                "reasoning": str(exc),
                "feedback": "Check the GitHub Actions logs for details.",
            }

    # Format and post the PR comment
    comment = format_review_comment(reviews, decision, members_cfg)
    try:
        post_pr_comment(repo, pr_number, comment, token)
        print("  ✅ Review comment posted to PR.")
    except Exception as exc:  # noqa: BLE001
        print(f"  ⚠️  Failed to post PR comment: {exc}")
        print("\n--- Council Review Output ---")
        print(comment)
        print("----------------------------\n")

    # Emit outputs
    verdict = decision.get("verdict", "FAIL").upper()
    set_output("decision", verdict)
    set_output("summary", decision.get("summary", ""))

    print(f"\n🧙 Gandalf's verdict: {verdict}")

    if verdict != "PASS":
        print("You shall not pass! Address the council's feedback before merging.")
        sys.exit(1)
    else:
        print("The council has spoken. This pull request may pass.")


if __name__ == "__main__":
    main()
