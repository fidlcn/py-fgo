"""Vision layer: OpenCV template matching, ROI, OCR, and the VisionDetector.

All coordinates/ROIs here are in the 1280x720 base resolution; the detector
normalizes each captured frame to that base before matching (spec section 7).
"""
