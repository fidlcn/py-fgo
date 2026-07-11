# Progress: Auto Battle Module Refactor

## 2026-07-10

- Reviewed the current battle flow with the user.
- Identified that current execution is mostly large-state recognition plus fixed-coordinate taps.
- Confirmed that `target_slot=0` is intended to mean no target.
- Confirmed that the next step is a design document, not code changes.
- Created planning files for the auto-battle refactor.
- Created `doc/auto_battle_module_refactor_plan.md` as the review document.
- Noted that `.gitignore` currently ignores `doc/`, so the new document exists locally but is not shown as an untracked git file.
- Expanded coordinate calibration to include all known click/swipe points.
- Added calibration export API and frontend JSON download button.
- Updated direct point calls so party target, order change, AP recovery, support refresh confirmation, and support scroll can use calibrated keys.
- Created `doc/coordinate_calibration_plan.md`.
- Verified Python syntax with `python3 -m py_compile`.
- Verified frontend with `npm run build`.
- Implemented the first auto-battle refactor pass based on `doc/auto_battle_module_refactor_plan.md`.
- Added battle substates, target semantics, skill confirmation flow, strict skill/NP/card failure behavior, and battle-plan UI fields.
- Updated related unit/e2e tests and verified the focused test set.
- Fixed test isolation by giving `app_client` a fresh `EventBus`.
- Full `.venv/bin/python -m pytest` now passes: 54/54.
- Investigated a runtime failure where servant skills failed before tapping with `skill is not ready`.
- Root cause: readiness templates such as `battle/skill_ready_1_3.png` were missing, and the strict readiness check treated missing templates as unavailable.
- Changed readiness checks so missing readiness templates do not block execution; present templates remain strict.
- Full `.venv/bin/python -m pytest` now passes: 56/56.
- Updated the battle skill flow to avoid per-skill readiness templates entirely.
- Skill actions now tap the configured skill coordinate first, detect whether the screen entered a release flow, then use target coordinates and the common confirm/cancel points.
- Skill confirmation now checks screenshots before and after the common confirm tap; if the confirm tap does not advance the flow, the executor taps cancel and returns a battle error.
- Updated `doc/auto_battle_module_refactor_plan.md` so `skill_ready_*` templates are no longer listed as required battle-flow templates.
