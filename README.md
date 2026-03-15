# 🧙 Rivendell Council

> *"Even the smallest pull request can change the course of the future."*

Rivendell Council is a GitHub Action that assembles a fellowship of AI code reviewers to evaluate
every pull request. Each council member brings domain expertise and reviews in **parallel**;
Gandalf the White synthesises their wisdom and delivers the final **PASS** or **FAIL** verdict
as a comment on your PR.

Powered by [GitHub Models](https://github.com/marketplace/models) via
[`actions/ai-inference`](https://github.com/actions/ai-inference) — **no external API keys
required**. Just add `models: read` permission and you're set.

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

Create `.github/workflows/council-review.yml` in your repository:

```yaml
name: Rivendell Council Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  council:
    name: Convene the Council
    uses: sylvainsf/rivendell_council/.github/workflows/council.yml@v2
    permissions:
      contents: read
      pull-requests: write
      models: read
    with:
      model: openai/gpt-4o
      # council-config: .github/council.md  # optional custom config
```

That's it. No API keys, no secrets, no submodules. The next pull request you open will
automatically receive a full council review with all members reviewing in parallel.

> **Tip:** We recommend pinning to a specific release tag (e.g. `@v2`) rather than `@main`
> to avoid unexpected changes. See [Pinning a Version](#pinning-a-version) below.

The council is fully configurable — enable/disable members, adjust weights, change models,
or add custom reviewers — via a `council.md` file. See [Configuration](#configuration) below.

### Model options

Any model from the [GitHub Models marketplace](https://github.com/marketplace/models) can be used:

| Model | Identifier |
|-------|-----------|
| GPT-4o | `openai/gpt-4o` (default) |
| GPT-4o mini | `openai/gpt-4o-mini` (faster, lower cost) |
| GPT-4.1 | `openai/gpt-4.1` |
| GPT-4.1 mini | `openai/gpt-4.1-mini` |
| GPT-5 | `openai/gpt-5` |
| GPT-5 mini | `openai/gpt-5-mini` |
| o3 | `openai/o3` |
| o4-mini | `openai/o4-mini` |
| Grok 3 | `xai/grok-3` |
| DeepSeek-R1 | `deepseek/deepseek-r1` |

---

## How It Works

```
Pull Request opened / updated
        │
        ▼
┌───────────────────────────────────────────┐
│  prepare job:                             │
│  • Parse council.md (members, weights)    │
│  • Fetch PR diff                          │
└───────────────────┬───────────────────────┘
                    │
        ┌───────────┼───────────────────┐
        ▼           ▼                   ▼           ▼
  🌟 Elrond    ⚔️ Gimli           👑 Aragorn   🏹 Legolas
  (parallel     (parallel         (parallel     (parallel
   matrix)       matrix)           matrix)       matrix)
        └───────────┬───────────────────┘
                    ▼
              🧙 Gandalf
         (reads all reviews)
              ai-inference
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
        PASS                FAIL
  (PR comment +         (PR comment +
   exit 0)               exit 1)
```

1. The **prepare** job parses `council.md` to determine which members are enabled, their
   weights, and the model to use. It also fetches the unified diff of the pull request.
2. Each enabled council member runs as a **parallel matrix job** — each receives the diff
   and its role-specific prompt via `actions/ai-inference`. They respond with a JSON object
   containing a `score` (1–10), `summary`, `concerns`, and `suggestions`.
3. **Gandalf** receives the diff **and** all member reviews. He synthesises the findings
   and responds with a `verdict` (`PASS` or `FAIL`), `summary`, `reasoning`, and `feedback`.
4. The full council review is posted as a comment on the PR.
5. The workflow exits with code `0` (PASS) or `1` (FAIL), failing the CI check when the
   council rejects the PR.

---

## Configuration

### Reusable workflow inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `model` | ❌ | from config | GitHub Models model identifier (overrides `council.md`) |
| `council-config` | ❌ | bundled default | Path to a `council.md` in your repo |
| `max-diff-chars` | ❌ | `30000` | Max characters of the diff sent to each reviewer |

### Workflow outputs

| Output | Description |
|--------|-------------|
| `decision` | `PASS` or `FAIL` |
| `summary` | Prose summary of the council's findings |

### Permissions required

```yaml
permissions:
  contents: read        # read the repository
  pull-requests: write  # post the review comment
  models: read          # call GitHub Models via actions/ai-inference
```

### `council.md` configuration

The bundled [`council.md`](council.md) provides sensible defaults. To customise the council,
create your own `council.md` in your repository and pass its path:

```yaml
jobs:
  council:
    uses: sylvainsf/rivendell_council/.github/workflows/council.yml@v2
    permissions:
      contents: read
      pull-requests: write
      models: read
    with:
      council-config: .github/council.md
```

#### Configuration reference

```yaml
members:
  Gandalf:
    enabled: true
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
    enabled: false   # opt out of performance reviews

  Bilbo:
    enabled: true
    weight: 0.5      # half-weight — style is advisory, not a blocker

passing_threshold: 6.0           # minimum weighted-average score when Gandalf is disabled
model: openai/gpt-4o             # GitHub Models identifier
```

| Field | Description |
|-------|-------------|
| `members.<Name>.enabled` | `true` to include the member, `false` to skip them |
| `members.<Name>.weight` | Score multiplier (default `1.0`; `2.0` doubles influence; `0.5` halves it) |
| `passing_threshold` | Minimum weighted-average score (1–10) used only when Gandalf is disabled |
| `model` | Default model for all reviews (can be overridden by the `model` workflow input) |

---

## Alternative: Composite Action (sequential)

If you prefer a simpler single-job setup (reviews run sequentially instead of in parallel),
you can use the composite action directly. Add Rivendell Council as a submodule:

```bash
git submodule add https://github.com/sylvainsf/rivendell_council.git .github/rivendell_council
git submodule update --init --recursive
```

Then add a workflow:

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
      contents: read
      pull-requests: write
      models: read

    steps:
      - uses: actions/checkout@v4
        with:
          submodules: recursive

      - name: Convene Rivendell Council
        uses: ./.github/rivendell_council
        with:
          model: openai/gpt-4o
          # council-config: .github/council.md  # optional custom config
```

This uses the same `actions/ai-inference` calls but runs each council member one after
another in a single job.

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

---

## Requirements

- A GitHub token with `pull-requests: write` and `models: read` permissions (the default
  `GITHUB_TOKEN` works — just declare the permissions in your workflow).
- **No external API keys needed.** LLM inference is handled by
  [GitHub Models](https://github.com/marketplace/models) through `actions/ai-inference`.

### Rate limits

GitHub Models provides free rate-limited usage with every GitHub account. Limits vary by
model tier and your Copilot plan. For most projects this is more than sufficient. Enterprises
can opt into paid usage for higher limits — see the
[GitHub Models documentation](https://docs.github.com/en/github-models) for details.

- A GitHub token with `pull-requests: write` and `models: read` permissions (the default
  `GITHUB_TOKEN` works — just declare the permissions in your workflow).
- **No external API keys needed.** LLM inference is handled by
  [GitHub Models](https://github.com/marketplace/models) through `actions/ai-inference`.

## Pinning a Version

We recommend pinning to a **specific release tag** rather than `@main` so that workflow
behaviour doesn't change unexpectedly when the action is updated.

```yaml
# Recommended: pin to a major version tag — receives backward-compatible updates
uses: sylvainsf/rivendell_council/.github/workflows/council.yml@v2

# Pin to an exact release for maximum reproducibility
uses: sylvainsf/rivendell_council/.github/workflows/council.yml@v2.0.0

# Pin to a specific commit SHA
uses: sylvainsf/rivendell_council/.github/workflows/council.yml@e36f694
```

Check the [Releases](https://github.com/sylvainsf/rivendell_council/releases) page for
available versions.

---

## Contributing

Rivendell Council is built on our collective wisdom — the prompts, the roles, and the review
philosophy are all shaped by the community. If you have ideas to improve a council member's prompt,
suggestions for better review criteria, or want to propose a new member to join the fellowship,
contributions are very welcome.

- **Improve existing prompts** — Open a PR with changes to any file in `council/`. Better
  phrasing, sharper focus, or fewer false positives are all valuable improvements.
- **Add new council members** — Have a domain that deserves its own reviewer? Create a new
  prompt file in `council/` and open a PR. Include a brief explanation of the role and what
  kind of feedback the new member should provide.
- **General suggestions** — Open an issue to discuss ideas, share feedback on review quality,
  or propose changes to how the council works.

All perspectives make the council stronger. Don't hesitate to contribute.

---

## License

[MIT](LICENSE)
