# Historical Bid/Ask Comparison Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show CFETS mid-price plus bid and ask lines for up to two selected banks in the historical chart.

**Architecture:** Keep the existing SQLite schema. Change the history query to return one market-mid series and two series per bank, then render a fixed semantic color set in the existing ECharts view.

**Tech Stack:** Python, SQLite, FastAPI, vanilla JavaScript, ECharts, unittest

---

### Task 1: History data contract

**Files:**
- Modify: `database.py`
- Modify: `server.py`
- Test: `tests/test_four_minute_banks.py`

- [ ] Add a failing database test asserting this response shape:

```python
{
    "market": [[timestamp, mid]],
    "banks": {
        "中国银行": {
            "bid": [[timestamp, bid]],
            "ask": [[timestamp, ask]],
        }
    },
}
```

- [ ] Run the targeted test and confirm it fails against the old single-price contract.

- [ ] Update `Database.get_history_series` to query `mid` for CFETS and both `bid` and `ask` for every selected bank. Apply the existing point limit independently to every series.

- [ ] Update `/api/history` to accept at most two valid banks and return the new contract without a price selector.

- [ ] Run the targeted backend tests and confirm they pass.

### Task 2: Five-line historical chart

**Files:**
- Modify: `static/index.html`
- Test: `tests/test_four_minute_banks.py`

- [ ] Add failing frontend assertions for removal of `historyPriceType`, a two-bank selection limit, and these five series labels and colors:

```javascript
CFETS: "#e7bd66"
Bank 1 bid: "#57d9b5"
Bank 1 ask: "#ff8178"
Bank 2 bid: "#8bdcc5"
Bank 2 ask: "#ffaaa3"
```

- [ ] Run the targeted frontend tests and confirm they fail.

- [ ] Remove the bid/ask selector, default to two banks, enforce a maximum of two checked banks, and render both bid and ask for each selected bank. Include bank name and price type in every legend label.

- [ ] Keep the existing 24-hour, 7-day, 30-day, custom-range, and chart-point-to-entry interactions unchanged.

- [ ] Run the frontend and JavaScript syntax tests and confirm they pass.

### Task 3: Integrated verification

**Files:**
- Verify only; do not modify `data/`.

- [ ] Run `python -m unittest discover -s tests -v` and confirm all active tests pass.

- [ ] Restart the local service and verify `/`, `/api/quotes`, and `/api/history` return HTTP 200.

- [ ] Confirm `git status --short` lists no tracked changes outside the intended source, test, spec, and plan files, and keeps `data/` untracked.

- [ ] Commit the implementation locally. Do not upload to Alibaba Cloud until the user accepts the local result.
