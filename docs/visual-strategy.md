# Visual Strategy

## Purpose

Mermaid diagrams are useful in Devo docs when they explain stable concepts faster than prose. They are not the final dashboard source of truth.

Use diagrams for concepts that change slowly:

- Devo architecture
- agent workflow
- work-package lifecycle
- approval bundle flow
- backup flow
- PersonalOS operating model

Do not add diagrams everywhere. A diagram should reduce confusion, show relationships, or make a sequence easier to recover after context loss. If a paragraph is already clear, leave it as prose.

## Maintenance Rules

- Keep diagrams short.
- Put a source/freshness note near each diagram.
- Update a diagram when the related workflow or document changes.
- Avoid duplicating every paragraph visually.
- Prefer one diagram per stable concept, not one diagram per command.
- Avoid diagrams for volatile command flags, temporary task status, or generated workspace paths.

## Dashboard Direction

The future dashboard should generate visuals from Devo structured data and artifacts, not from manually maintained Mermaid source.

Good future visualization tools may include:

- React Flow or XYFlow for interactive workflow graphs
- D3 for custom status and history views
- Cytoscape.js for graph exploration
- Graphviz/DOT for computed dependency graphs
- Mermaid rendering for lightweight embedded documentation diagrams

GraphQL is not a diagram tool. Graphviz is.

## Current Diagram Set

The intentionally small current set is:

- `docs/devo-vision.md`: Devo architecture/control-room model
- `docs/agent-workflow.md`: manual-assisted agent workflow
- `docs/how-to-use-devo.md`: work-package lifecycle and approval bundle flow
- `docs/usability-roadmap.md`: usability roadmap from current CLI flow to dashboard and later direct agents
- `docs/recovery.md`: scheduled workspace backup flow

This set should stay compact until a generated dashboard replaces hand-maintained diagrams.
