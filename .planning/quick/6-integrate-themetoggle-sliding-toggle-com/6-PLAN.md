# Quick Task 6: integrate ThemeToggle sliding toggle component into HTML report

## Tasks

### Task 1: Replace simple button with sliding ThemeToggle in html_renderer.py

**files:** `src/alteryx_diff/renderers/html_renderer.py`, `diff_report.html`

**action:**
- Add CSS for `.theme-toggle`, `.toggle-thumb`, `.toggle-passive`, `.moon-icon`, `.sun-icon`
- Replace `<button id="theme-toggle">` with pill-shaped div containing two icon slots
- Inline Lucide-style Moon/Sun SVGs (16x16, strokeWidth 1.5)
- Update `setTheme()` to set `data-mode` on the toggle div
- Update IIFE to always call `setTheme()` with resolved preference

**verify:** Toggle appears in diff_report.html; clicking slides the thumb and swaps icons

**done:** af1ba87
