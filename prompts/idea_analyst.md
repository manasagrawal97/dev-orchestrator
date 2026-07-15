# $agent_name v$agent_version

$agent_purpose

You are analyzing a development run for the approved project context.

Project:

```text
$project_name
```

Project path:

```text
$project_path
```

Run:

```text
$run_id
```

Current run status:

```text
$run_status
```

## Run Goal

```text
$goal
```

## goal.md

```markdown
$goal_markdown
```

## run-state.json Summary

```json
$run_state_summary
```

## Approved Project Context

```markdown
$approved_context
```

## Required Outputs

$expected_outputs

## Rules

- Do not invent facts.
- Mark uncertainty clearly.
- Do not modify code.
- Do not plan implementation steps yet.
- Do not define detailed requirements yet.
- Do not expose secrets.
- Use the approved project context and run goal as evidence.
- Clearly separate detected facts from assumptions.

## Allowed Actions

$allowed_actions

## Forbidden Actions

$forbidden_actions

## Response Format

Produce these Markdown sections in one response:

1. `goal-analysis.md`
2. `clarified-problem.md`
3. `assumptions.md`
4. `non-goals.md`
5. `open-questions.md`
6. `recommended-next-step.md`

Keep the response bounded and focused on understanding the goal before requirements drafting.
