# 🧙 Rivendell Council

> *"Even the smallest pull request can change the course of the future."*

Rivendell Council is a GitHub Action that assembles a fellowship of AI code reviewers to evaluate
every pull request. Each council member brings domain expertise; Gandalf the White synthesises their
wisdom and delivers the final **PASS** or **FAIL** verdict as a comment on your PR.

---

## The Council

| Member | Role | Domain |
|--------|------|--------|
| 🧙 **Gandalf** | Arbiter | Synthesises all reviews, weighs the council's input, and delivers the final PASS/FAIL verdict. |
| 🌟 **Elrond** | Correctness | Logic correctness, goal alignment, edge-case handling, and test adequacy. |
| ⚔️ **Gimli** | Strength | Security vulnerabilities, input validation, robustness, and error handling. |
| 👑 **Aragorn** | Maintainability | Code structure, idiomatic style, naming conventions, and documentation. |
| 🏹 **Legolas** | Performance | Algorithmic efficiency, data-structure choices, and resource usage. |
| 🍃 **Bilbo** *(optional)* | Style | Subjective craft, readability, consistency, and expressiveness — disabled by default. |

Each reviewer (except Gandalf) scores the diff on a **1–10 scale** and provides a list of
concerns and suggestions. Gandalf reads all reviews, weighs their importance, and decides
whether the PR may be merged.

---

## Quick Start

### 1. Add Rivendell Council as a submodule

From the root of your repository:

```bash
git submodule add https://github.com/sylvainsf/rivendell_council.git .github/rivendell_council
git submodule update --init --recursive
git commit -m "Add Rivendell Council as submodule"
```

### 2. Add your OpenAI API key as a GitHub secret

In your repository go to **Settings → Secrets and variables → Actions** and create a new secret
named `OPENAI_API_KEY` with your [OpenAI API key](https://platform.openai.com/api-keys).

### 3. Create the workflow file

Copy the example workflow into your repository:

```bash
cp .github/rivendell_council/examples/council-review.yml .github/workflows/council-review.yml
git add .github/workflows/council-review.yml
git commit -m "Add Rivendell Council workflow"
```

Or create `.github/workflows/council-review.yml` manually:

```yaml
name: Rivendell Council Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  council:
    name: Convene the Council
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
      contents: read

    steps:
      - name: Checkout code (with submodules)
        uses: actions/checkout@v4
        with:
          submodules: recursive

      - name: Convene Rivendell Council
        uses: ./.github/rivendell_council
        with:
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
          github-token:   ${{ secrets.GITHUB_TOKEN }}
```

That's it. The next pull request you open will automatically receive a full council review.

---

## Configuration (`council.md`)

The bundled [`council.md`](council.md) at the root of this repository provides sensible defaults.
You can override it by creating your own `council.md` anywhere in your project and pointing the
action at it:

```yaml
- uses: ./.github/rivendell_council
  with:
    openai-api-key: ${{ secrets.OPENAI_API_KEY }}
    council-config: .github/council.md   # ← your custom config
```

### Configuration reference

```yaml
members:
  Gandalf:
    enabled: true   # set to false to skip Gandalf (uses weighted average instead)
    weight: 1.0

  Elrond:
    enabled: true
    weight: 1.0

  Gimli:
    enabled: true
    weight: 2.0     # double Gimli's influence (great for security-critical projects)

  Aragorn:
    enabled: true
    weight: 1.0

  Legolas:
    enabled: false  # opt out of performance reviews

  # Bilbo is a project/company-specific reviewer focused on subjective style.
  # Enable him when style polish matters to your team.
  Bilbo:
    enabled: true
    weight: 0.5     # half-weight — style is advisory, not a blocker

passing_threshold: 6.0  # minimum weighted-average score when Gandalf is disabled
model: gpt-4o           # OpenAI model to use
```

| Field | Description |
|-------|-------------|
| `members.<Name>.enabled` | `true` to include the member, `false` to skip them |
| `members.<Name>.weight` | Score multiplier (default `1.0`; `2.0` doubles influence; `0.5` halves it) |
| `passing_threshold` | Minimum weighted-average score (1–10) used only when Gandalf is disabled |
| `model` | OpenAI model for all reviews (can be overridden by the `model` action input) |

### Action inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `openai-api-key` | ✅ | — | Your OpenAI API key |
| `github-token` | ✅ | `${{ github.token }}` | Token used to post the review comment |
| `council-config` | ❌ | bundled `council.md` | Path to a custom `council.md` |
| `model` | ❌ | value in `council.md` | OpenAI model override |
| `max-diff-chars` | ❌ | `30000` | Max characters of the diff sent to each reviewer |

### Action outputs

| Output | Description |
|--------|-------------|
| `decision` | `PASS` or `FAIL` |
| `summary` | Prose summary of the council's findings |

---

## How the Council Works

```
Pull Request opened / updated
        │
        ▼
┌───────────────────────────────────────────┐
│  Fetch PR diff from GitHub API            │
└───────────────────┬───────────────────────┘
                    │ (truncated to max-diff-chars)
        ┌───────────┼───────────────────┐
        ▼           ▼                   ▼           ▼
  🌟 Elrond    ⚔️ Gimli           👑 Aragorn   🏹 Legolas
  Correctness  Strength          Maintain.    Performance
  score+review score+review      score+review score+review
        └───────────┬───────────────────┘
                    ▼
              🧙 Gandalf
         (reads all reviews)
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
        PASS                FAIL
  (PR comment +         (PR comment +
   exit 0)               exit 1)
```

1. The action fetches the unified diff of the pull request.
2. Each enabled council member receives the diff and their role-specific system prompt.
   They respond with a JSON object containing a `score` (1–10), `summary`, `concerns`, and `suggestions`.
3. Gandalf receives the diff **and** all member reviews. He synthesises the findings and
   responds with a JSON object containing a `verdict` (`PASS` or `FAIL`), `summary`, `reasoning`,
   and `feedback`.
4. The full council review is posted as a comment on the PR.
5. The action exits with code `0` (PASS) or `1` (FAIL), failing the CI check when the
   council rejects the PR.

---

## Customising Council Member Prompts

Each council member's system prompt lives in the [`council/`](council/) directory.
If you want to fork and customise how a member reviews code, simply edit the relevant `.md` file.

| File | Member |
|------|--------|
| [`council/Gandalf.md`](council/Gandalf.md) | Arbiter prompt |
| [`council/Elrond.md`](council/Elrond.md) | Correctness prompt |
| [`council/Gimli.md`](council/Gimli.md) | Strength prompt |
| [`council/Aragorn.md`](council/Aragorn.md) | Maintainability prompt |
| [`council/Legolas.md`](council/Legolas.md) | Performance prompt |
| [`council/Bilbo.md`](council/Bilbo.md) | Style prompt (example custom reviewer) |

To add your own project-specific reviewer, create a new prompt file (e.g. `council/Frodo.md`)
and add the member to your `council.md` with the desired `enabled` flag and `weight`.
The action will automatically include any member that has a matching prompt file and is
enabled in the configuration.

---

## Keeping the Submodule Up to Date

To pull the latest version of Rivendell Council:

```bash
git submodule update --remote .github/rivendell_council
git add .github/rivendell_council
git commit -m "Update Rivendell Council submodule"
```

To pin to a specific release tag:

```bash
cd .github/rivendell_council
git checkout v1.0.0
cd ../..
git add .github/rivendell_council
git commit -m "Pin Rivendell Council to v1.0.0"
```

---

## Requirements

- An [OpenAI API key](https://platform.openai.com/api-keys) stored as the `OPENAI_API_KEY` secret.
- A GitHub token with `pull-requests: write` permission (the default `GITHUB_TOKEN` works).
- The workflow must check out the repository **with submodules** (`submodules: recursive`).

---

## License

[MIT](LICENSE)
