# Placeholder packaging script for the .NET WebView2 desktop shell (later phase).
# MVP runs as FastAPI + React; this is wired up when the desktop shell lands.
# Usage (PowerShell): ./scripts/build-windows.ps1
$ErrorActionPreference = "Stop"
Write-Host "Desktop packaging is a post-MVP step (see doc/ai_implementation_spec.md section 15, item 13)."
