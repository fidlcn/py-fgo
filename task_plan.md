# Task Plan: Auto Battle Module Refactor

## Goal

Define the refactor scope for a reusable FGO auto-battle module that can be called by both current manual-entry tasks and future auto-navigation templates.

Target future chain:

```text
auto find quest entry -> select support -> auto battle module -> loop/recovery
```

## Phases

| Phase | Status | Purpose |
|---|---|---|
| 1. Current flow research | complete | Summarize current quest/battle execution behavior and gaps. |
| 2. Refactor requirements | complete | Capture required state recognition, OCR, skill, NP, and card behavior. |
| 3. Design document | complete | Write a confirmable design plan under `doc/`. |
| 4. Coordinate calibration expansion | complete | Add complete point calibration and export design/code. |
| 5. Implementation planning | pending | After user review, split battle refactor into code tasks and test plan. |
| 6. Code implementation | pending | Build the battle module and UI/API changes after plan approval. |

## Decisions So Far

- The battle executor should become a reusable module with a clear entry contract.
- Quest navigation and support selection should remain outside the battle module.
- The battle module must validate each configured action instead of falling back silently.
- Skill confirmation, target selection, skill/NP availability, and card recognition are required for correctness.
- Coordinate calibration should cover every semantic click/swipe point that the worker can execute.

## Errors Encountered

| Error | Attempt | Resolution |
|---|---|---|
| `pytest` not installed in system Python | Tried `pytest` and `python3 -m pytest` in earlier investigation | Recorded as environment limitation; only syntax compile was possible. |
