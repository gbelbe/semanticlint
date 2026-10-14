---
name: craft-review
description: Get an independent craftsmanship review of your change before you push. Runs the mechanical design prompts, then hands the diff to the craft-reviewer subagent, a lead-developer reviewer with no knowledge of how the code was written. Use when finishing a change, before opening a PR, or when asked for a code review of the current branch.
---

# Craft review

A thin wrapper. The rubric is `CRAFTSMANSHIP.md` at the repo root ("New-code principles");
the reviewer itself is the `craft-reviewer` subagent, installed at
`.claude/agents/craft-reviewer.md`.

## Why a separate reviewer

Code reviewed by the agent that wrote it gets rubber-stamped: the author's reasons are in its
context and they sound convincing. The reviewer runs as a subagent with a fresh context and a
reviewer's role, and sees only the diff and the rubric.

## Steps

1. Know the base ref (default `origin/main`). Make sure the work is committed, so the reviewer
   sees exactly what a PR would.
2. Run `python3 scripts/design_review.py --base <base>` and read the prompts yourself first.
3. Launch the `craft-reviewer` subagent with the Agent tool, giving it only: "Review the change
   on this branch against `<base>`." **Do not** add your intentions, your reasoning, or a summary
   of why the code is the way it is. That would defeat the point.
4. Present its findings to the user unedited. For each one, either fix it or say in a line why
   you disagree; the user decides. Do not silently drop findings.
5. Re-run the mechanical gates after fixing (`scripts/local-craft-gate.sh` or the commands in
   `AGENTS.md`).

The review is advisory: it never blocks a push, and it is not a substitute for a human
reviewer. A finding without a quoted line and a catalog code is invalid; ask the reviewer to
retry rather than acting on it.
