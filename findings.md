# Findings: Auto Battle Module Refactor

## Current Architecture

- `QuestRunner` owns the full quest loop: entry/support/party/battle/result/AP handling.
- `BattleExecutor` owns turn execution: wait for command phase, execute actions, attack, wait for card select, tap NP cards, fill face cards.
- `StateDetector` currently recognizes large UI states using OpenCV templates.
- `ActionExecutor` performs fixed-coordinate ADB taps and swipes.

## Current Battle Limitations

- Skill execution only taps the skill icon and optionally taps a party member target.
- There is no modeled state for skill confirmation, enemy target selection, party target selection, or skill detail confirmation.
- `target_slot=0` effectively means no target because only target slots `1/2/3` map to coordinates.
- Skill and NP availability are currently assumed true.
- Card recognition is not implemented; fallback card positions are used.
- Status updates can show a stale `last_action` because `record_action()` does not publish by itself.

## User Requirements Captured

- Battle flow should be packaged as a reusable module.
- Future auto-navigation should only need to find entry and then call the same battle module.
- State recognition must be expanded for skill dialogs, target selection dialogs, and related battle sub-states.
- OCR should be available for those recognition flows where template matching alone is insufficient.
- Skill and NP availability must be checked; if unavailable, return an error instead of fallback behavior.
- Card recognition must follow configured card policy.
- Skill confirmation must cover:
  - no target skills,
  - own-party target skills,
  - enemy target skills,
  - numbered target selection by `1/2/3`,
  - skip/error if the configured target slot is not available.

## Coordinate Calibration Findings

- Existing calibration UI only exposed a small subset of point keys.
- Existing `ActionExecutor.tap_named()` already supports overrides, but direct `tap_point()` and `tap_xy()` calls bypassed calibration.
- To make full calibration meaningful, direct points for party targets, order change, AP recovery, support refresh confirm, and support scroll endpoints need semantic keys.
- Current local repo did not have `configs/coordinates.json`, so all points were using defaults.
