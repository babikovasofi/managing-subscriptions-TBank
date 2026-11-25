---
name: review
description: Review a finished change against its plan. Runs 1 reviewer subagent in a fresh context, reports ship/rework with severity-tagged findings. Use after a build or for an existing PR. Triggers (RU) — ревью, проверь, отревьюй.
---

# Skill: review

ORCHESTRATOR. One reviewer subagent. Read-only — the reviewer does not fix.

## Invocation
`review <slug>` (Claude: `/review`, Codex: `$review`)

## How to spawn a subagent
- Claude Code: Agent tool, `subagent_type: reviewer`.
- Codex: "Spawn the `reviewer` custom agent with this prompt and wait for it."
- OMP: Run built-in `task` with the full `modelRoles.default` selector including `:medium` and
  `isolated: true`. Pass the repository reviewer instructions explicitly and
  request its verdict format. Discard any patch produced by the review.
- Neither available: start a NEW session and give it the prompt below. Never review your
  own build in the same context — the point is a second pair of eyes.

## Steps
1. **Gather evidence.**
   - For an existing PR, use its description, available checks and merge-base-to-head
     diff. Pin the base and head revisions. Use the request as acceptance criteria
     when no plan exists. Review the PR without editing the worktree or index.
   - For a local build, use the plan, build report and diff. For a one-line fix
     without a plan, use the user's request. Include untracked files in the review
     by reading them separately from the tracked diff.
2. **Spawn 1 reviewer**. Prompt:
   > Answer TERSE. Read `.claude/agents/reviewer.md` and follow it exactly.
   > Acceptance criteria: plan, user request, or existing PR description.
   > Build evidence or PR checks, when available.
   > Diff below:
   > <paste git diff here>

   Paste the diff INTO the prompt — the reviewer must not re-read the whole repo.
3. **Report** the verdict verbatim. For a local build with a slug, also write
   `swarm-report/<slug>-review.md`. For review-only requests, stop after reporting.
4. `verdict: ship` → ask the user for OK to commit and push. **No commit/push without the
   user's OK.** On OK: set the stage to `[x]` in AGENTS.md «Прогресс», commit, push.
5. `verdict: rework` → the findings are the input to a `build <slug>` retry (or `debug`).
   Do not auto-fix here; the user decides.
