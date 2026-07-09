"""py-fgo automation worker package.

Controls a MuMu emulator over ADB, recognizes FGO UI with OpenCV, and drives
a configurable battle state machine. Imported lazily by the backend so the
API can run without OpenCV installed; only the worker path pulls it in.
"""

__version__ = "0.1.0"
