---
# Rivendell Council Configuration
#
# Enable or disable council members with `enabled: true/false`.
# Adjust `weight` to increase or decrease a member's influence on the final decision.
# A weight of 1.0 is standard. Use 2.0 to double a member's influence, 0.5 to halve it.
#
# `passing_threshold` is the minimum weighted-average score (out of 10) required to pass
# when Gandalf is disabled. It is ignored when Gandalf is enabled (he makes the call).
#
# `model` sets the OpenAI model used for all council members.

members:
  Gandalf:
    enabled: true
    weight: 1.0

  Elrond:
    enabled: true
    weight: 1.0

  Gimli:
    enabled: true
    weight: 1.0

  Aragorn:
    enabled: true
    weight: 1.0

  Legolas:
    enabled: true
    weight: 1.0

  # Example of a project-specific or company-specific reviewer.
  # Bilbo evaluates subjective style and craft. He is disabled by default — enable him
  # when you want an opinionated style pass, or raise his weight if style matters a lot
  # to your team. His prompt lives in council/Bilbo.md; copy the pattern to add your own
  # custom reviewers (e.g. council/Frodo.md for domain-specific business-logic checks).
  Bilbo:
    enabled: false
    weight: 0.5

passing_threshold: 6.0

model: gpt-4o
---

# Rivendell Council

Adjust the YAML front matter above to configure how the council operates:

| Field | Description |
|-------|-------------|
| `members.<Name>.enabled` | `true` to include the member, `false` to skip them |
| `members.<Name>.weight` | Multiplier for the member's score (default `1.0`) |
| `passing_threshold` | Minimum weighted-average score (1–10) when Gandalf is disabled |
| `model` | OpenAI model to use for all reviews (default `gpt-4o`) |

## Roles

| Member | Domain |
|--------|--------|
| **Gandalf** | Arbiter — synthesizes all reviews and delivers the final PASS/FAIL verdict |
| **Elrond** | Correctness — logic, goal alignment, edge cases, and tests |
| **Gimli** | Strength — security, robustness, input validation, and error handling |
| **Aragorn** | Maintainability — structure, idioms, naming, and documentation |
| **Legolas** | Performance — algorithmic efficiency and resource usage |
