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
   `docs/**`, `AGENTS.md` → do it yourself. No match → ask the user.
5. **Spawn the matched exec agents.** Prompt each:
   > Answer TERSE. Read `.claude/agents/<role>.md` and follow it exactly.
   > Plan: swarm-report/<slug>-plan.md. Your scope: <the files for this agent>.
   API contract changes: run `python-fastapi` first, pass its `api_changes` to `react-ts`.
   Otherwise independent scopes run in parallel.
6. **Verify**: read each agent's test result. Any `blocked` or failing check → do NOT
   claim success. Report failures verbatim, suggest `debug`.
7. **Write** `swarm-report/<slug>-build.md`: per-agent changed files, commands + real
   results, cross-layer notes.
8. **Report** to user: status per scope + real check output. Next step: `review <slug>`.
