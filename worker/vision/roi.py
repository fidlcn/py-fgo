"""Region of interest in base-resolution (1280x720) pixel space."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Tuple

if TYPE_CHECKING:  # pragma: no cover
    import numpy as np


@dataclass(frozen=True)
class ROI:
    """A rectangular region in base-resolution space."""

    x: int
    y: int
    w: int
    h: int

    def crop(self, image: "np.ndarray") -> "np.ndarray":
        return image[self.y : self.y + self.h, self.x : self.x + self.w]

    def scale(self, sx: float, sy: float) -> "ROI":
        return ROI(
            round(self.x * sx),
            round(self.y * sy),
            round(self.w * sx),
            round(self.h * sy),
        )

    def as_tuple(self) -> Tuple[int, int, int, int]:
        return (self.x, self.y, self.w, self.h)
