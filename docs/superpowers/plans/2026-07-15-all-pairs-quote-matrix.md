# All-Pairs FX Workbench Implementation Plan

> **For agentic workers:** Execute inline in this worktree. Keep changes surgical and validate once at the end.

**Goal:** Replace the single-pair quote board with the approved all-pairs matrix, retain compact current/historical entry, and add the approved history view without changing stored history data.

**Architecture:** Keep the existing FastAPI, SQLite, and single-file HTML stack. Extend only the history query and historical-entry response needed by the approved UI. Do not add dependencies or alter the database schema.

**Tech Stack:** FastAPI, SQLite, vanilla HTML/CSS/JavaScript, ECharts, unittest/pytest

---

### Task 1: Lock backend history semantics

**Files:** `database.py`, `server.py`, `tests/test_four_minute_banks.py`

- [ ] Add tests proving historical lookup never uses future data.
- [ ] Return separate market and bank record timestamps.
- [ ] Add a bounded history-series query for chart ranges without schema changes.

### Task 2: Build the all-pairs live matrix

**Files:** `static/index.html`, `tests/test_four_minute_banks.py`

- [ ] Render four pair rows and CFETS plus eight source columns.
- [ ] Use the approved font sizes, colors, and 36 aligned timestamps.
- [ ] Make quote cells populate the compact entry strip.

### Task 3: Build the dedicated history view

**Files:** `static/index.html`, `server.py`, `database.py`, `tests/test_four_minute_banks.py`

- [ ] Add live/history top navigation.
- [ ] Add pair, price type, range, and source controls.
- [ ] Plot CFETS and up to three banks and let chart clicks populate historical entry time.

### Task 4: Finish current and historical entry behavior

**Files:** `static/index.html`, `server.py`, `tests/test_four_minute_banks.py`

- [ ] Keep current entry compact.
- [ ] Reveal date-time input only in history mode.
- [ ] Show selected time and actual market/bank record times in successful results.

### Task 5: Unified verification

**Files:** no additional files

- [ ] Run targeted backend and frontend contract tests.
- [ ] Run the complete test suite.
- [ ] Start the local server and inspect both views at desktop width.
- [ ] Confirm `data/` remains untracked and untouched by commits.
