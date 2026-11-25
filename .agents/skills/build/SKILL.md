---
name: build
description: Implement an already-approved plan from swarm-report/<slug>-plan.md. Routes each task to the executing subagent that owns its file scope (python-fastapi / react-ts / devops), runs the checks, writes a build report. Use AFTER plan is approved by the user, never before. Triggers (RU) — билд, собери, реализуй, делай.
---

# Skill: build

ORCHESTRATOR. You route work to executing subagents by file scope.

## Invocation
`build <slug>` (Claude: `/build`, Codex: `$build`)

## How to spawn a subagent
- Claude Code: Agent tool, `subagent_type` = the role name.
- Codex: "Spawn the `<role>` custom agent with this prompt and wait for it."
- OMP: Codex owns implementation that requires decisions. Send mechanical items only
  to built-in `sonic`. Use the profile's exact `modelRoles.mechanical` selector as
  the item's `model`, with `isolated: true`. Follow the OMP batch and patch rules in
  `docs/omp.md`. A failed dispatch blocks that item.
- Neither available: do the work yourself, following `.claude/agents/<role>.md`.

## Steps
1. **Find the plan**: `swarm-report/<slug>-plan.md`. Missing → abort: "Run plan first."
2. **Check approval and Blockers.** The plan must say `Status: approved <date>`. `draft`
   → abort: "Plan not approved — show it to the user first." Any unresolved HIGH blocker
   → abort and name it; the user resolves or waives it.
3. **Progress**: the stage should already be `[~]` (set by plan on approval). If not, set it.
4. **Route by scope** (table in AGENTS.md «Харнесс»):
   `ml/**`, `data/**`, `api/**`, `*.py` → `python-fastapi`; `web/**` → `react-ts`;
   `Dockerfile`, `docker-compose*`, `Caddyfile`, deploy config → `devops`;
   `docs/**`, `AGENTS.md` → orchestrator owns the scope. No match → ask the user.
5. **Dispatch by runtime and file scope.** In OMP, apply the Codex/DeepSeek split
   above within each scope. For a DeepSeek task, use the handoff template below.
   Other executors receive their role instructions, approved plan or relevant
   excerpt, and file scope.
   API contract changes: run `python-fastapi` first, pass its `api_changes` to `react-ts`.
   Otherwise independent scopes run in parallel.
6. **Verify**: read each agent's test result. Any `blocked` or failing check → do NOT
   claim success. Report failures verbatim, suggest `debug`.
7. **Write** `swarm-report/<slug>-build.md`: per-agent changed files, commands + real
   results, cross-layer notes. In OMP, include the resolved model and patch disposition
   for each delegated item.
8. **Report** to user: status per scope + real check output. Next step: `review <slug>`.

## DeepSeek handoff (OMP)

Codex writes a self-contained brief for every DeepSeek call, including retries.
Fill every field before dispatch. Keep design, diagnosis, behavior decisions
and review with Codex. If the steps or expected result cannot be specified
precisely, Codex handles the item.

```text
Objective: the exact result to produce.
Scope: exact paths to read or change and behavior to preserve.
Steps:
1. Where to start and what to locate.
2. The exact change to make, including a before/after example or mapping.
3. Repeat only for the listed cases and paths.
Acceptance criteria:
- Observable outcome for each requested change.
- Exact verification commands and expected results, when applicable.
  If acceptance is via diff inspection, specify what the diff must contain.
Return: changed files, checks run and actual results, or the exact blocker.
If the input differs from the brief, a check fails, or a decision is needed,
stop at that point and report the evidence. Leave other files untouched.
```

Codex inspects the patch against the brief and reruns the relevant checks after
integration. The worker's completion report alone does not establish acceptance.
