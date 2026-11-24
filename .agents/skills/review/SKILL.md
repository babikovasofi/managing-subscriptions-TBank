---
name: review
description: Review a finished change against its plan. Runs 1 reviewer subagent in a fresh context, reports ship/rework with severity-tagged findings. Use AFTER build, before commit. Triggers (RU) — ревью, проверь, отревьюй.
---

# Skill: review

ORCHESTRATOR. One reviewer subagent. Read-only — the reviewer does not fix.

## Invocation
`review <slug>` (Claude: `/review`, Codex: `$review`)

## How to spawn a subagent
- Claude Code: Agent tool, `subagent_type: reviewer`.
- Codex: "Spawn the `reviewer` custom agent with this prompt and wait for it."
- Neither available: start a NEW session and give it the prompt below. Never review your
  own build in the same context — the point is a second pair of eyes.

## Steps
1. **Gather**: plan `swarm-report/<slug>-plan.md` + build report
   `swarm-report/<slug>-build.md` + the diff. Small change without a plan (typo, one
   line): no slug — the "plan" is the user's request, quote it verbatim instead.
   Diff must include new files: run `git add -N <new files>` (intent-to-add, nothing
   staged), then `git diff HEAD`.
2. **Spawn 1 reviewer**. Prompt:
   > Answer TERSE. Read `.claude/agents/reviewer.md` and follow it exactly.
   > Plan: swarm-report/<slug>-plan.md   (or: Request: "<user's words>")
   > Diff below:
   > <paste git diff here>

   Paste the diff INTO the prompt — the reviewer must not re-read the whole repo.
3. **Write** the verdict to `swarm-report/<slug>-review.md` (skip for no-slug changes) and
   report it verbatim.
4. `verdict: ship` → ask the user for OK to commit and push. **No commit/push without the
   user's OK.** On OK: set the stage to `[x]` in AGENTS.md «Прогресс», commit, push.
5. `verdict: rework` → the findings are the input to a `build <slug>` retry (or `debug`).
   Do not auto-fix here; the user decides.
