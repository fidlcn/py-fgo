"""Unit: vision matching + state detection with synthetic images (spec 14.1)."""

from __future__ import annotations

from datetime import datetime, timezone

import cv2
import numpy as np

from worker.fgo.enums import FgoState
from worker.fgo.state_detector import StateDetector
from worker.screenshot import Frame
from worker.vision.detector import VisionDetector, StateDef
from worker.vision.templates import TemplateRegistry


def _make_frame(state_label: str):
    """A 1280x720 frame with a unique noise-pattern marker for the label.

    Distinct deterministic noise per label guarantees a template matches only
    its own frame (random noise is uncorrelated across labels).
    """
    seed = sum(ord(c) for c in state_label)
    rng = np.random.RandomState(seed)
    block = rng.randint(0, 256, (100, 200), dtype=np.uint8)
    img = np.zeros((720, 1280, 3), dtype=np.uint8)
    img[100:200, 100:300, :] = block[:, :, None]
    return Frame(image=img, width=1280, height=720, captured_at=datetime.now(timezone.utc), source="t")


def _save_templates(tmp_path, labels):
    """Save a template crop per label under battle/<label>.png."""
    d = tmp_path / "battle"
    d.mkdir()
    for label in labels:
        crop = _make_frame(label).image[100:200, 100:300]
        cv2.imwrite(str(d / f"{label}.png"), crop)


def test_find_template_matches(tmp_path):
    _save_templates(tmp_path, ["attack"])
    reg = TemplateRegistry(tmp_path)
    det = VisionDetector(reg, template_threshold=0.8)
    frame = _make_frame("attack")
    m = det.find_template(frame, "battle/attack")
    assert m.found is True
    assert m.confidence > 0.8


def test_find_template_misses_different_frame(tmp_path):
    _save_templates(tmp_path, ["attack"])
    reg = TemplateRegistry(tmp_path)
    det = VisionDetector(reg, template_threshold=0.8)
    frame = _make_frame("card_select")
    assert det.find_template(frame, "battle/attack").found is False


def test_detect_state_returns_best_match(tmp_path):
    _save_templates(tmp_path, ["attack", "card_select"])
    reg = TemplateRegistry(tmp_path)
    defs = [
        StateDef(state="BATTLE_COMMAND", templates=["battle/attack"], min_confidence=0.8),
        StateDef(state="BATTLE_CARD_SELECT", templates=["battle/card_select"], min_confidence=0.8),
    ]
    det = VisionDetector(reg, defs, template_threshold=0.8)
    assert det.detect_state(_make_frame("attack")).state == "BATTLE_COMMAND"
    assert det.detect_state(_make_frame("card_select")).state == "BATTLE_CARD_SELECT"


def test_state_detector_maps_to_enum(tmp_path):
    _save_templates(tmp_path, ["attack"])
    reg = TemplateRegistry(tmp_path)
    vision = VisionDetector(reg, template_threshold=0.8)
    # Inject a single registry entry so detection can map to the enum.
    from worker.fgo.state_detector import FgoStateDef, STATE_REGISTRY

    sd = StateDetector(vision, {FgoState.BATTLE_COMMAND: FgoStateDef(FgoState.BATTLE_COMMAND, ["battle/attack"], minimum_confidence=0.8)})
    state, conf, _ = sd.detect(_make_frame("attack"))
    assert state is FgoState.BATTLE_COMMAND
    assert conf > 0.8


def test_skill_ready_template_missing_does_not_block(tmp_path):
    reg = TemplateRegistry(tmp_path)
    det = VisionDetector(reg, template_threshold=0.8)
    assert det.is_skill_ready(_make_frame("attack"), 1, 3) is True


def test_skill_ready_template_must_match_when_present(tmp_path):
    _save_templates(tmp_path, ["skill_ready_1_3"])
    reg = TemplateRegistry(tmp_path)
    det = VisionDetector(reg, template_threshold=0.8)
    assert det.is_skill_ready(_make_frame("skill_ready_1_3"), 1, 3) is True
    assert det.is_skill_ready(_make_frame("attack"), 1, 3) is False
