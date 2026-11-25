---
name: debug
description: Find the root cause of a bug or failing check. Runs 1 debugger subagent that reproduces, ladders hypotheses, isolates with evidence, and applies the minimal fix. Use when a check fails, build reports blocked, review says rework because of a bug, or "X stopped working". Does NOT design features (that's plan). Triggers (RU) — дебаг, почини, сломалось, ошибка.
---

# Skill: debug

ORCHESTRATOR. One debugger subagent. It diagnoses before it touches anything.

## Invocation
`debug "<error text / failing check / what broke>"` or `debug <slug>`
(Claude: `/debug`, Codex: `$debug`)

## How to spawn a subagent
- Claude Code: Agent tool, `subagent_type: debugger`.
- Codex: "Spawn the `debugger` custom agent with this prompt and wait for it."
- OMP: Run built-in `task` with the full `modelRoles.default` selector including `:medium` and the debugger
  role prompt. Keep diagnosis with Codex. For an approved mechanical fix, use the
  OMP build route.
- Neither available: follow `.claude/agents/debugger.md` yourself.

## Steps
1. **Gather the symptom**: error / stack / failing check from the user, plus
   `swarm-report/<slug>-build.md` if a slug was given.
2. **Spawn 1 debugger**. Prompt:
   > Answer TERSE. Read `.claude/agents/debugger.md` and follow it exactly.
   > Symptom: <verbatim error / failing check>. Feature slug (if any): <slug>.
3. **Report** the debugger's return verbatim: root cause, evidence, proposed fix.
4. **Route the outcome:**
   - `root_cause_found` → show root cause + proposed fix + which zone owns it. On the
     user's OK, re-spawn the debugger with "Fix approved: <fix>" (or route the fix to the
     zone's exec agent via `build`). Then suggest `review <slug>`.
   - `fixed` (only after an approved fix) → suggest `review <slug>`.
   - `stuck` → show the hypothesis ladder; the user decides.
   - `cannot_reproduce` → ask the user for exact repro steps; do not guess-patch.

## Where it sits in the loop
`plan → (user OK) → build → review → (user OK) → commit + push`. Check fails or review
says `rework` → `debug` → back to `build`.
