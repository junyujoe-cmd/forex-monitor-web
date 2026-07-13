# Hangzhou Bank Freshness Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace stale or synthetic Hangzhou Bank prices with verified current official quotes and restore real bid/ask history collection.

**Architecture:** Keep the existing fetch-save-query flow. Make the Hangzhou Bank fetcher validate HTTP status and official source time, remove the backend's indefinite Hangzhou Bank cache fallback, and remove frontend synthetic bank-price generation. Preserve the SQLite schema.

**Tech Stack:** Python 3.11, requests, BeautifulSoup, FastAPI, SQLite, unittest, vanilla JavaScript.

---

### Task 1: Add regression tests

**Files:**
- Create: `tests/test_hangzhou_bank.py`
- Read: `bank_fetcher.py`, `server.py`, `database.py`, `static/index.html`

- [ ] **Step 1: Ask DeepSeek to generate the test file**

Provide DeepSeek with the exact existing function signatures and require standard-library `unittest` only. Use this complete target structure:

```python
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import requests

import server
from bank_fetcher import fetch_hzb_rates
from database import Database


def official_html(source_time):
    rows = [
        ("美元USD", "677.15", "671.40", "680.17"),
        ("港币HKD", "86.329", "85.729", "86.760"),
        ("日元JPY", "4.1609", "4.1139", "4.2085"),
        ("欧元EUR", "770.29", "765.69", "776.07"),
    ]
    body = "".join(
        f"<tr><td>{name}</td><td>{bid}</td><td>{cash}</td>"
        f"<td>{ask}</td><td>{source_time}</td></tr>"
        for name, bid, cash, ask in rows
    )
    return f"<table>{body}</table>"


class HangzhouBankFetcherTests(unittest.TestCase):
    @patch("bank_fetcher.requests.get")
    def test_current_official_html_returns_four_pairs(self, mock_get):
        source_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        response = Mock(text=official_html(source_time))
        response.raise_for_status.return_value = None
        mock_get.return_value = response
        rates = fetch_hzb_rates()
        self.assertEqual(set(rates), {"USDCNY", "HKDCNY", "JPYCNY", "EURCNY"})
        self.assertEqual(rates["USDCNY"]["bid"], 6.7715)
        self.assertEqual(rates["USDCNY"]["ask"], 6.8017)
        self.assertEqual(rates["USDCNY"]["source_time"], source_time)

    @patch("bank_fetcher.requests.get")
    def test_http_error_returns_none(self, mock_get):
        mock_get.return_value.raise_for_status.side_effect = requests.HTTPError("403")
        self.assertIsNone(fetch_hzb_rates())

    @patch("bank_fetcher.requests.get")
    def test_stale_official_timestamp_returns_none(self, mock_get):
        stale = (datetime.now() - timedelta(minutes=11)).strftime("%Y-%m-%d %H:%M:%S")
        response = Mock(text=official_html(stale))
        response.raise_for_status.return_value = None
        mock_get.return_value = response
        self.assertIsNone(fetch_hzb_rates())

class HangzhouBankPipelineTests(unittest.TestCase):
    def test_failed_fetch_does_not_reuse_old_hangzhou_quotes(self):
        server.bank_cache.clear()
        server.bank_cache["杭州银行"] = {"USDCNY": {"bid": 9, "ask": 10}}
        market = {"USDCNY": {"bid": 6.78, "ask": 6.79, "mid": 6.785}}
        fake_db = Mock()
        with patch.object(server, "db", fake_db), \
             patch.object(server, "fetch_all_quotes", return_value=market), \
             patch.object(server, "fetch_boc_rates", return_value=None), \
             patch.object(server, "fetch_cmb_rates", return_value=None), \
             patch.object(server, "fetch_ccb_rates", return_value=None), \
             patch.object(server, "fetch_hzb_rates", return_value=None):
            server.fetch_and_save()
        self.assertNotIn("杭州银行", server.bank_cache)

    def test_saved_hangzhou_quotes_are_returned_by_chart_query(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(str(Path(tmp) / "quotes.db"))
            cycle = datetime.now().isoformat()
            db.save_market_quotes_batch(cycle, {"USDCNY": {"bid": 6.78, "ask": 6.79, "mid": 6.785}}, "CFETS")
            db.save_bank_quotes_batch(cycle, [("杭州银行", "USDCNY", 6.77, 6.80)])
            rows = db.get_chart_data("USDCNY", "杭州银行", date_str=datetime.now().strftime("%Y-%m-%d"))
        self.assertTrue(any(row[2] == 6.77 and row[3] == 6.80 for row in rows))

    def test_frontend_has_no_synthetic_bank_price_fallback(self):
        html = (Path(__file__).parents[1] / "static" / "index.html").read_text()
        self.assertNotIn("md + sp.bid_offset", html)
        self.assertNotIn("md + sp.ask_offset", html)
```

- [ ] **Step 2: Run tests and verify red state**

Run:

```bash
/Users/jun/Downloads/projects/.venvs/forex-monitor-web/bin/python -m unittest tests.test_hangzhou_bank -v
```

Expected: failures for the old URL, missing timestamp freshness validation, stale cache reuse, and frontend fallback.

- [ ] **Step 3: Commit the failing tests**

```bash
git add tests/test_hangzhou_bank.py
git commit -m "test: cover Hangzhou Bank quote freshness"
```

### Task 2: Fix the official Hangzhou Bank fetcher

**Files:**
- Modify: `bank_fetcher.py:205-242`
- Test: `tests/test_hangzhou_bank.py`

- [ ] **Step 1: Ask DeepSeek for the minimal fetcher patch**

The implementation must retain the existing function signature and use the existing `datetime` and `timedelta` imports:

```python
def fetch_hzb_rates():
    try:
        resp = requests.get(
            "http://www.hzbank.com.cn/hzyh/gjyw/bjfw24/whpj/index.html",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
        )
        resp.raise_for_status()
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")
        result = {}
        for tr in soup.find_all("tr"):
            cells = tr.find_all("td")
            if len(cells) < 5:
                continue
            name = cells[0].text.strip()
            if name not in HZB_NAME_MAP:
                continue
            source_time_text = cells[4].text.strip()
            source_time = datetime.strptime(source_time_text, "%Y-%m-%d %H:%M:%S")
            if datetime.now() - source_time > timedelta(minutes=10):
                continue
            pair = HZB_NAME_MAP[name]
            divisor = 1 if pair == "JPYCNY" else 100
            bid = round(float(cells[1].text.strip()) / divisor, 4)
            ask = round(float(cells[3].text.strip()) / divisor, 4)
            result[pair] = {
                "bid": bid,
                "ask": ask,
                "mid": round((bid + ask) / 2, 4),
                "source_time": source_time_text,
            }
        return result if result else None
    except Exception as exc:
        print(f"HZB fetch error: {exc}")
        return None
```

- [ ] **Step 2: Run fetcher tests**

Run the three `HangzhouBankFetcherTests`; expect all to pass.

- [ ] **Step 3: Commit the fetcher fix**

```bash
git add bank_fetcher.py
git commit -m "fix: validate Hangzhou Bank quote freshness"
```

### Task 3: Remove stale backend and synthetic frontend fallbacks

**Files:**
- Modify: `server.py:20-86`
- Modify: `static/index.html:164-191`
- Test: `tests/test_hangzhou_bank.py`

- [ ] **Step 1: Remove Hangzhou Bank's indefinite backend cache**

Apply only these changes:

```python
# Remove last_hzb_rates from the module variable, global statement,
# successful-fetch copy block, and bank_quotes_full fallback tuple.
("杭州银行", hzb_rates)
```

- [ ] **Step 2: Remove frontend synthetic price generation**

Delete the `BANK_SPREADS` JavaScript constant and this branch:

```javascript
else if (md) {
  const sp = BANK_SPREADS[source] || {bid_offset:0,ask_offset:0};
  bid = +(md + sp.bid_offset).toFixed(4);
  ask = +(md + sp.ask_offset).toFixed(4);
  mid = md;
}
```

When `bq` is absent, existing formatting must render `--`.

- [ ] **Step 3: Run the full regression test file**

Run:

```bash
/Users/jun/Downloads/projects/.venvs/forex-monitor-web/bin/python -m unittest tests.test_hangzhou_bank -v
```

Expected: six tests pass.

- [ ] **Step 4: Commit backend and frontend fixes**

```bash
git add server.py static/index.html
git commit -m "fix: stop displaying stale bank quotes"
```

### Task 4: Local integration verification

**Files:**
- Verify: `bank_fetcher.py`, `server.py`, `static/index.html`, `data/forex_data.db`

- [ ] **Step 1: Stop the old local server and remove only the local test database**
- [ ] **Step 2: Start `server.py` with the external Python 3.11 virtual environment**
- [ ] **Step 3: Verify `/` and `/api/quotes` return HTTP 200**
- [ ] **Step 4: Compare Hangzhou Bank API values and source time with the official page**
- [ ] **Step 5: Wait for a completed fetch cycle and verify new Hangzhou Bank rows exist in SQLite**
- [ ] **Step 6: Verify `/api/chart` contains non-null Hangzhou Bank bid/ask values**
- [ ] **Step 7: Run all unittest tests and confirm zero failures**
- [ ] **Step 8: Present local evidence and do not deploy to cloud without user confirmation**
