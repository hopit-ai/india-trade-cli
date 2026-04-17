# Spec: Save-PDF + Explain/Simplify for App and Web (#144)

## Problem
PDF export and explain-simply only work in the terminal CLI. The macOS app and web app
have no way to export or simplify analysis cards.

## Backend Endpoints

### POST /skills/export-pdf
- Input: `{"content": "...", "title": "..."}`
- Output: PDF file (binary) with `Content-Disposition: attachment; filename=...`
- Reuses `engine.output.export_to_pdf()` logic
- Returns the PDF bytes to the browser for download

### POST /skills/explain
- Input: `{"content": "...", "session_id": "default"}`
- Output: `{"simplified": "Here's what this analysis means..."}`
- Reuses `engine.output.explain_simply()` with the session's LLM provider

## Frontend (macOS App)

### PDF Export button
- Add download icon button to Analysis, GEX, IV Smile, Strategy, Backtest cards
- Calls `POST /skills/export-pdf` with the card's text content
- Triggers browser file download / macOS save dialog

### Simplify button
- Add "Simplify" chip/button on Analysis card
- Sends analysis text to `/skills/explain`
- Shows simplified version below in a collapsible panel
- Uses existing `contextAction` chip pattern

## Files
- `web/skills.py` — `POST /skills/export-pdf`, `POST /skills/explain`
- `macos-app/.../components/Analysis/ExportButton.jsx` — PDF download button
- `macos-app/.../components/Analysis/SimplifyButton.jsx` — explain chip

## Acceptance Criteria
- POST /skills/export-pdf with text → returns binary PDF with correct headers
- POST /skills/explain with analysis text → returns simplified JSON
- No crash if fpdf2 not installed — returns 503 with helpful message
