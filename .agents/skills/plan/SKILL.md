---
name: plan
description: Design a stage or feature before writing code. Runs planner + skeptic subagents that read the Memory Bank and the stage in AGENTS.md, argue, and write a plan to swarm-report/. Use BEFORE build, for any change touching 2+ files or with unclear scope. Skip for typos and one-line fixes. Triggers (RU) — план, спланируй, распланируй.
---

# Skill: plan

You are the ORCHESTRATOR. You do not design the plan yourself — you run two subagents
and merge their output. No code edits here.

## Invocation
`plan "<stage number or one-sentence feature>"` (Claude: `/plan`, Codex: `$plan`)

## How to spawn a subagent
- Claude Code: Agent tool, `subagent_type` = the role name (`planner`, `skeptic`).
- Codex: ask explicitly — "Spawn the `planner` and `skeptic` custom agents in parallel
  with these prompts, wait for both, then continue." (defined in `.codex/agents/`).
- OMP: Run `planner` and `skeptic` in separate built-in `task` sessions, each with
  the full `modelRoles.default` selector including `:medium`. Pass the corresponding role instructions,
  acceptance criteria and project context explicitly.
- Neither available: play each role yourself, one after another, re-reading its role file
  `.claude/agents/<role>.md` before each.

## Steps
1. **Slugify** the feature → `<slug>` (kebab-case, short, e.g. `stage-21-confidence`).
2. **Read context yourself**: `.memory-bank/index.md`, the stage in AGENTS.md «План
   работы», «Прогресс», «Открытые вопросы».
3. **Spawn 2 subagents in parallel.** Prefix EACH prompt with:
   > Answer TERSE: terse, drop filler, keep all technical substance.

   - **planner** — "Read `.claude/agents/planner.md` and follow it exactly. Feature: <verbatim + stage text from AGENTS.md>."
   - **skeptic** — "Read `.claude/agents/skeptic.md` and follow it exactly. Feature: <same>."

   (Sharper variant for risky changes: planner first, then pass its YAML to skeptic.)
4. **Merge**: take the planner's plan, apply the skeptic's HIGH/MED fixes, list anything
   unresolved under **Blockers**.
5. **Write** `swarm-report/<slug>-plan.md`:
   ```
   # Plan: <feature>   (slug: <slug>)
   Status: draft
   ## TL;DR
   ## Acceptance criteria  — observable "done" conditions; review checks these
   ## Plan                 — merged steps + affected files + tests
   ## Blockers             — skeptic HIGH not yet resolved (human decides)
   ## Out of scope
   ## Assumptions
   ```
6. **Report to user**: TL;DR + Blockers, and ask for approval. **No build without the
   user's explicit OK on the plan.**
7. **On the user's OK**: change the plan's line to `Status: approved <YYYY-MM-DD>`, set the
   stage's items to `[~]` in AGENTS.md «Прогресс», commit `chore: start <stage>` (plan +
   AGENTS.md). This is the start-of-task commit from the sync protocol.
