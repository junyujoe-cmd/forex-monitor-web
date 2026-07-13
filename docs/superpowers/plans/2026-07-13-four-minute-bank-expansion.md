# Four Minute-Level Bank Expansion Implementation Plan / 四家分钟级银行扩展实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal / 目标:** Add truthful minute-level quotes from ICBC, ABC, PSBC, and CMBC, store their real bid/ask history, and display eight banks plus CFETS in the approved compact matrix. / 接入工商银行、农业银行、邮储银行和民生银行的真实分钟级报价，保存真实买卖价历史，并用已批准的紧凑矩阵展示八家银行和 CFETS。

**Architecture / 架构:** Four source-specific fetchers normalize official JSON or JSONP into the existing quote dictionary. The server fetches independent bank sources concurrently, saves only current-cycle valid values, and never caches the four new banks indefinitely. The existing single-file frontend renders a scroll-safe matrix without changing the entry or chart panel structure. / 四个抓取函数把银行官方 JSON 或 JSONP 统一成现有报价字典；服务器并行抓取相互独立的银行源，只保存本轮有效数据，四家新增银行绝不无限缓存；现有单文件前端改成可在窄窗口滚动的报价矩阵，不重构录入和图表面板。

**Tech Stack / 技术栈:** Python 3.11 virtual environment, `requests`, FastAPI, APScheduler, SQLite, `unittest`/pytest runner, plain HTML/CSS/JavaScript, ECharts. / Python 3.11 虚拟环境、`requests`、FastAPI、APScheduler、SQLite、`unittest`/pytest 执行器、原生 HTML/CSS/JavaScript、ECharts。

---

## File Map / 文件分工

- Modify `bank_fetcher.py`: official requests, parsing, unit normalization, three-minute freshness validation. / 官方请求、解析、单位统一和三分钟时效校验。
- Modify `config.py`: canonical eight-bank list. / 统一的八家银行清单。
- Modify `server.py`: concurrent bank collection, current-only saving for new banks, truthful entry errors. / 并行银行采集、新银行仅保存本轮数据、录入接口真实缺失提示。
- Modify `static/index.html`: approved matrix, status display, and eight-bank selectors. / 已批准的矩阵、状态显示和八家银行下拉框。
- Create `tests/test_four_minute_banks.py`: parser, pipeline, storage, entry, and frontend contract tests. / 解析、流水线、存储、录入和前端契约测试。
- Modify `tests/test_hangzhou_bank.py`: patch the new bank-collection seam so the existing regression test never calls live networks. / 使用新的银行采集边界，确保杭州银行回归测试不会访问真实网络。

**Dirty-worktree rule / 脏工作区规则:** `server.py` and `static/index.html` already contain unrelated uncommitted user changes. Preserve them exactly. Use partial staging and confirm `git diff --cached` before every commit. / `server.py` 和 `static/index.html` 已有与本功能无关的用户未提交改动，必须原样保留。每次提交使用局部暂存，并检查 `git diff --cached`。

### Task 1: Official Fetchers and Quote Validation / 官方抓取器与报价校验

**Files:**
- Create: `tests/test_four_minute_banks.py`
- Modify: `bank_fetcher.py`

- [ ] **Step 1: Record the existing green baseline / 记录现有通过基线**

Run / 运行：

```bash
rtk /Users/jun/Downloads/projects/.venvs/forex-monitor-web/bin/python -m pytest -q
```

Expected / 预期：`6 passed`.

- [ ] **Step 2: Write failing parser tests / 编写失败的解析测试**

Create `tests/test_four_minute_banks.py` with current timestamps and official field names. The test data below is complete and intentionally uses simple values for exact unit assertions. / 使用当前时间和官方字段名创建测试文件；以下数据完整，并使用便于精确断言单位的数值。

```python
import asyncio
import json
import tempfile
import unittest
from datetime import datetime, time, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import server
from bank_fetcher import (
    fetch_abc_rates,
    fetch_cmbc_rates,
    fetch_icbc_rates,
    fetch_psbc_rates,
)
from config import BANKS
from database import Database


def current_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class NewBankFetcherTests(unittest.TestCase):
    @patch("bank_fetcher.requests.post")
    def test_icbc_normalizes_four_pairs(self, mock_post):
        now = datetime.now()
        rows = []
        for code, bid, ask in [
            ("USD", "676.40", "679.20"),
            ("EUR", "772.00", "778.00"),
            ("HKD", "86.20", "86.60"),
            ("JPY", "4.1600", "4.2000"),
        ]:
            rows.append({
                "currencyENName": code,
                "foreignBuy": bid,
                "foreignSell": ask,
                "publishDate": now.strftime("%Y-%m-%d"),
                "publishTime": now.strftime("%H:%M:%S"),
            })
        response = Mock()
        response.json.return_value = {"code": 0, "data": rows}
        response.raise_for_status.return_value = None
        mock_post.return_value = response

        rates = fetch_icbc_rates()

        self.assertEqual(set(rates), {"USDCNY", "EURCNY", "HKDCNY", "JPYCNY"})
        self.assertEqual(rates["USDCNY"]["bid"], 6.7640)
        self.assertEqual(rates["JPYCNY"]["ask"], 4.2000)

    @patch("bank_fetcher.requests.get")
    def test_abc_uses_current_official_endpoint_and_units(self, mock_get):
        publish_time = datetime.now().astimezone().isoformat(timespec="seconds")
        table = [
            {"CurrId": "14", "BuyingPrice": "676.40", "SellPrice": "679.20", "PublishTime": publish_time},
            {"CurrId": "38", "BuyingPrice": "772.00", "SellPrice": "778.00", "PublishTime": publish_time},
            {"CurrId": "13", "BuyingPrice": "86.20", "SellPrice": "86.60", "PublishTime": publish_time},
            {"CurrId": "27", "BuyingPrice": "4.1600", "SellPrice": "4.2000", "PublishTime": publish_time},
        ]
        response = Mock()
        response.json.return_value = {"ErrorCode": "0", "Data": {"Table": table}}
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        rates = fetch_abc_rates()

        self.assertEqual(rates["USDCNY"]["ask"], 6.7920)
        self.assertEqual(rates["JPYCNY"]["bid"], 4.1600)
        self.assertEqual(
            mock_get.call_args.args[0],
            "https://www.abchina.com.cn/creditCardService/DataService/ExchangeRate",
        )

    @patch("bank_fetcher.requests.get")
    def test_psbc_parses_jsonp_and_units(self, mock_get):
        now = datetime.now()
        rows = [
            {"cur": "USD", "fe_buy_prc": "676.40", "fe_sell_prc": "679.20"},
            {"cur": "EUR", "fe_buy_prc": "772.00", "fe_sell_prc": "778.00"},
            {"cur": "HKD", "fe_buy_prc": "86.20", "fe_sell_prc": "86.60"},
            {"cur": "JPY", "fe_buy_prc": "4.1600", "fe_sell_prc": "4.2000"},
        ]
        for row in rows:
            row["effect_date"] = now.strftime("%Y%m%d")
            row["effect_time"] = now.strftime("%H%M%S")
        response = Mock(text="cb(" + json.dumps({"retCode": "000", "resultList": rows}) + ")")
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        rates = fetch_psbc_rates()

        self.assertEqual(rates["HKDCNY"]["bid"], 0.8620)
        self.assertEqual(rates["JPYCNY"]["ask"], 4.2000)

    @patch("bank_fetcher.requests.post")
    def test_cmbc_keeps_already_normalized_units(self, mock_post):
        source_time = current_text()
        rows = [
            {"foreignCurrency": "USD", "buyPrice": 6.7640, "sellPrice": 6.7920, "updateTime": source_time},
            {"foreignCurrency": "EUR", "buyPrice": 7.7200, "sellPrice": 7.7800, "updateTime": source_time},
            {"foreignCurrency": "HKD", "buyPrice": 0.8620, "sellPrice": 0.8660, "updateTime": source_time},
            {"foreignCurrency": "JPY", "buyPrice": 4.1600, "sellPrice": 4.2000, "updateTime": source_time},
        ]
        response = Mock()
        response.json.return_value = {"returnCode": {"type": "S"}, "result": rows}
        response.raise_for_status.return_value = None
        mock_post.return_value = response

        rates = fetch_cmbc_rates()

        self.assertEqual(rates["USDCNY"]["bid"], 6.7640)
        self.assertEqual(rates["JPYCNY"]["ask"], 4.2000)

    @patch("bank_fetcher.requests.post")
    def test_stale_and_invalid_cmbc_rows_are_rejected(self, mock_post):
        stale = (datetime.now() - timedelta(minutes=4)).strftime("%Y-%m-%d %H:%M:%S")
        current = current_text()
        rows = [
            {"foreignCurrency": "USD", "buyPrice": 6.76, "sellPrice": 6.79, "updateTime": stale},
            {"foreignCurrency": "EUR", "buyPrice": 7.80, "sellPrice": 7.70, "updateTime": current},
            {"foreignCurrency": "HKD", "buyPrice": 0, "sellPrice": 0.86, "updateTime": current},
            {"foreignCurrency": "JPY", "buyPrice": 4.16, "sellPrice": 4.20, "updateTime": current},
        ]
        response = Mock()
        response.json.return_value = {"returnCode": {"type": "S"}, "result": rows}
        response.raise_for_status.return_value = None
        mock_post.return_value = response

        rates = fetch_cmbc_rates()

        self.assertEqual(set(rates), {"JPYCNY"})
```

- [ ] **Step 3: Run the parser tests and verify RED / 运行解析测试并确认失败**

Run / 运行：

```bash
rtk /Users/jun/Downloads/projects/.venvs/forex-monitor-web/bin/python -m pytest tests/test_four_minute_banks.py -q
```

Expected / 预期：collection fails because `fetch_icbc_rates`, `fetch_abc_rates`, `fetch_psbc_rates`, and `fetch_cmbc_rates` do not exist. / 因四个函数尚不存在而收集失败。

- [ ] **Step 4: Implement shared validation and four fetchers / 实现统一校验和四个抓取器**

Add `import json` and append the following focused implementation to `bank_fetcher.py`. Keep all existing fetchers unchanged. / 增加 `import json` 并把下面实现追加到 `bank_fetcher.py`，现有抓取器保持不变。

```python
NEW_BANK_PAIR_MAP = {
    "USD": "USDCNY",
    "EUR": "EURCNY",
    "HKD": "HKDCNY",
    "JPY": "JPYCNY",
}
ABC_CURRENCY_MAP = {
    "14": "USD",
    "38": "EUR",
    "13": "HKD",
    "27": "JPY",
}
NEW_BANK_MAX_AGE = timedelta(minutes=3)


def _add_new_bank_quote(result, currency, bid_raw, ask_raw, source_time, values_per_100):
    pair = NEW_BANK_PAIR_MAP.get(currency)
    if not pair:
        return
    now = datetime.now(source_time.tzinfo) if source_time.tzinfo else datetime.now()
    if now - source_time > NEW_BANK_MAX_AGE:
        return
    try:
        bid = float(bid_raw)
        ask = float(ask_raw)
    except (TypeError, ValueError):
        return
    if values_per_100 and currency != "JPY":
        bid /= 100
        ask /= 100
    if bid <= 0 or ask <= 0 or bid > ask:
        return
    result[pair] = {
        "bid": round(bid, 4),
        "ask": round(ask, 4),
        "mid": round((bid + ask) / 2, 4),
        "source_time": source_time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def fetch_icbc_rates():
    """Fetch current settlement quotes from the official ICBC JSON API."""
    try:
        response = requests.post(
            "https://papi.icbc.com.cn/exchanges/ns/getLatest",
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != 0:
            return None
        result = {}
        for item in payload.get("data", []):
            currency = item.get("currencyENName")
            if currency not in NEW_BANK_PAIR_MAP:
                continue
            try:
                source_time = datetime.strptime(
                    f"{item.get('publishDate', '')} {item.get('publishTime', '')}",
                    "%Y-%m-%d %H:%M:%S",
                )
            except (TypeError, ValueError):
                continue
            _add_new_bank_quote(
                result,
                currency,
                item.get("foreignBuy"),
                item.get("foreignSell"),
                source_time,
                values_per_100=True,
            )
        return result or None
    except Exception as exc:
        print(f"ICBC fetch error: {exc}")
        return None


def fetch_abc_rates():
    """Fetch current settlement quotes from the official ABC JSON API."""
    try:
        response = requests.get(
            "https://www.abchina.com.cn/creditCardService/DataService/ExchangeRate",
            headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("ErrorCode") != "0":
            return None
        result = {}
        for item in payload.get("Data", {}).get("Table", []):
            currency = ABC_CURRENCY_MAP.get(item.get("CurrId"))
            if not currency:
                continue
            try:
                source_time = datetime.fromisoformat(item.get("PublishTime", ""))
            except (TypeError, ValueError):
                continue
            _add_new_bank_quote(
                result,
                currency,
                item.get("BuyingPrice"),
                item.get("SellPrice"),
                source_time,
                values_per_100=True,
            )
        return result or None
    except Exception as exc:
        print(f"ABC fetch error: {exc}")
        return None


def fetch_psbc_rates():
    """Fetch current settlement quotes from the official PSBC JSONP API."""
    try:
        response = requests.get(
            "https://s.psbc.com/portal/PsbcService/foreignexchange/curr?callback=cb",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
        )
        response.raise_for_status()
        text = response.text.strip()
        if not text.startswith("cb(") or not text.endswith(")"):
            return None
        payload = json.loads(text[3:-1])
        if payload.get("retCode") != "000":
            return None
        result = {}
        for item in payload.get("resultList", []):
            if item.get("cur") not in NEW_BANK_PAIR_MAP:
                continue
            try:
                source_time = datetime.strptime(
                    f"{item.get('effect_date', '')}{item.get('effect_time', '')}",
                    "%Y%m%d%H%M%S",
                )
            except (TypeError, ValueError):
                continue
            _add_new_bank_quote(
                result,
                item.get("cur"),
                item.get("fe_buy_prc"),
                item.get("fe_sell_prc"),
                source_time,
                values_per_100=True,
            )
        return result or None
    except Exception as exc:
        print(f"PSBC fetch error: {exc}")
        return None


def fetch_cmbc_rates():
    """Fetch current settlement quotes from the official CMBC HTTPS API."""
    try:
        response = requests.post(
            "https://www.cmbc.com.cn/gw/po_web/queryExRateByForex.do",
            data={"cxfg": "1", "domesticCurrency": "RMB"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("returnCode", {}).get("type") != "S":
            return None
        result = {}
        for item in payload.get("result", []):
            if item.get("foreignCurrency") not in NEW_BANK_PAIR_MAP:
                continue
            try:
                source_time = datetime.strptime(item.get("updateTime", ""), "%Y-%m-%d %H:%M:%S")
            except (TypeError, ValueError):
                continue
            _add_new_bank_quote(
                result,
                item.get("foreignCurrency"),
                item.get("buyPrice"),
                item.get("sellPrice"),
                source_time,
                values_per_100=False,
            )
        return result or None
    except Exception as exc:
        print(f"CMBC fetch error: {exc}")
        return None
```

- [ ] **Step 5: Run parser tests and verify GREEN / 运行解析测试并确认通过**

Run / 运行：

```bash
rtk /Users/jun/Downloads/projects/.venvs/forex-monitor-web/bin/python -m pytest tests/test_four_minute_banks.py -q
```

Expected / 预期：`5 passed`.

- [ ] **Step 6: Commit Task 1 only / 只提交任务一**

```bash
rtk git add bank_fetcher.py tests/test_four_minute_banks.py
rtk git diff --cached --check
rtk git commit -m "feat: add four minute-level bank fetchers"
```

### Task 2: Concurrent Pipeline, Storage, and Truthful Entry / 并行流水线、存储和真实录入

**Files:**
- Modify: `config.py`
- Modify: `server.py`
- Modify: `tests/test_four_minute_banks.py`
- Modify: `tests/test_hangzhou_bank.py`

- [ ] **Step 1: Add failing pipeline and entry tests / 增加失败的流水线和录入测试**

Append the following tests to `tests/test_four_minute_banks.py`. / 把以下测试追加到测试文件。

```python
class NewBankPipelineTests(unittest.TestCase):
    def setUp(self):
        server.cfets_cache.clear()
        server.bank_cache.clear()

    def test_current_new_bank_quote_is_saved_and_exposed(self):
        market = {"USDCNY": {"bid": 6.77, "ask": 6.78, "mid": 6.775}}
        icbc = {"USDCNY": {"bid": 6.76, "ask": 6.79, "mid": 6.775, "source_time": current_text()}}
        fake_db = Mock()
        bank_rates = {name: {} for name in [
            "中国银行", "招商银行", "建设银行", "杭州银行",
            "工商银行", "农业银行", "邮储银行", "民生银行",
        ]}
        bank_rates["工商银行"] = icbc

        with (
            patch.object(server, "db", fake_db),
            patch.object(server, "fetch_all_quotes", return_value=market),
            patch.object(server, "_fetch_all_bank_rates", return_value=bank_rates),
        ):
            server.fetch_and_save()

        self.assertEqual(server.bank_cache["工商银行"], icbc)
        saved = fake_db.save_bank_quotes_batch.call_args.args[1]
        self.assertIn(("工商银行", "USDCNY", 6.76, 6.79), saved)

    def test_failed_new_bank_fetch_does_not_reuse_previous_quote(self):
        server.bank_cache["工商银行"] = {"USDCNY": {"bid": 9, "ask": 10}}
        market = {"USDCNY": {"bid": 6.77, "ask": 6.78, "mid": 6.775}}
        bank_rates = {name: {} for name in [
            "中国银行", "招商银行", "建设银行", "杭州银行",
            "工商银行", "农业银行", "邮储银行", "民生银行",
        ]}

        with (
            patch.object(server, "db", Mock()),
            patch.object(server, "fetch_all_quotes", return_value=market),
            patch.object(server, "_fetch_all_bank_rates", return_value=bank_rates),
        ):
            server.fetch_and_save()

        self.assertNotIn("工商银行", server.bank_cache)

    def test_entry_rejects_missing_real_bank_quote(self):
        server.cfets_cache["USDCNY"] = {"bid": 6.77, "ask": 6.78, "mid": 6.775}
        fake_db = Mock()

        with patch.object(server, "db", fake_db):
            result = asyncio.run(
                server.save_entry("USDCNY", "工商银行", "买入价", 6.77, None)
            )

        self.assertFalse(result["ok"])
        self.assertIn("暂无真实银行报价", result["error"])
        fake_db.save_user_entry.assert_not_called()

    def test_canonical_bank_list_contains_eight_banks(self):
        self.assertEqual(BANKS, [
            "中国银行", "招商银行", "建设银行", "杭州银行",
            "工商银行", "农业银行", "邮储银行", "民生银行",
        ])

    def test_saved_new_bank_quotes_are_returned_by_chart_query(self):
        now = datetime.now()
        chart_date = now - timedelta(days=1) if now.time() < time(9, 30) else now
        with tempfile.TemporaryDirectory() as tmp:
            database = Database(str(Path(tmp) / "quotes.db"))
            cycle = now.isoformat()
            database.save_market_quotes_batch(
                cycle,
                {"USDCNY": {"bid": 6.77, "ask": 6.78, "mid": 6.775}},
                "CFETS",
            )
            database.save_bank_quotes_batch(
                cycle,
                [("工商银行", "USDCNY", 6.76, 6.79)],
            )
            rows = database.get_chart_data(
                "USDCNY",
                "工商银行",
                date_str=chart_date.strftime("%Y-%m-%d"),
            )

        self.assertTrue(any(row[2] == 6.76 and row[3] == 6.79 for row in rows))
```

Replace `tests/test_hangzhou_bank.py::test_failed_fetch_does_not_reuse_old_hangzhou_quotes` with this exact network-free version. / 用以下不访问网络的完整版本替换杭州银行失败测试。

```python
def test_failed_fetch_does_not_reuse_old_hangzhou_quotes(self):
    server.bank_cache.clear()
    market = {"USDCNY": {"bid": 6.78, "ask": 6.79, "mid": 6.785}}
    bank_rates = {name: {} for name in [
        "中国银行", "招商银行", "建设银行", "杭州银行",
        "工商银行", "农业银行", "邮储银行", "民生银行",
    ]}

    with (
        patch.object(server, "db", Mock()),
        patch.object(server, "fetch_all_quotes", return_value=market),
        patch.object(server, "_fetch_all_bank_rates", return_value=bank_rates),
    ):
        server.fetch_and_save()

    self.assertNotIn("杭州银行", server.bank_cache)
```

- [ ] **Step 2: Run focused tests and verify RED / 运行聚焦测试并确认失败**

```bash
rtk /Users/jun/Downloads/projects/.venvs/forex-monitor-web/bin/python -m pytest tests/test_four_minute_banks.py tests/test_hangzhou_bank.py -q
```

Expected / 预期：fails because `_fetch_all_bank_rates` and new-bank integration do not exist, and entry still synthesizes a quote. / 因并行采集函数、新银行整合尚不存在且录入接口仍生成模拟价而失败。

- [ ] **Step 3: Expand the canonical bank list / 扩展统一银行清单**

Replace `config.BANKS` with the exact ordered list below. Leave `BANK_SPREADS` untouched because it may still be used by non-web legacy code; the web server will stop using it for fallback prices. / 用以下顺序替换 `config.BANKS`。保留 `BANK_SPREADS`，因为旧的非 Web 代码可能仍使用它；Web 服务不再用它生成回退价格。

```python
BANKS = [
    "中国银行",
    "招商银行",
    "建设银行",
    "杭州银行",
    "工商银行",
    "农业银行",
    "邮储银行",
    "民生银行",
]
```

- [ ] **Step 4: Implement concurrent collection and current-only new-bank behavior / 实现并行采集和新增银行仅本轮有效**

In `server.py`, import `ThreadPoolExecutor` and the four new fetchers. Remove `BANK_SPREADS` from the server import after the entry fallback is removed. Add this collection seam above `fetch_and_save()`. / 在 `server.py` 中导入线程池和四个新抓取器；删除录入回退后移除 `BANK_SPREADS` 导入；在 `fetch_and_save()` 上方增加以下采集边界。

```python
def _fetch_all_bank_rates():
    fetchers = {
        "中国银行": fetch_boc_rates,
        "招商银行": fetch_cmb_rates,
        "建设银行": fetch_ccb_rates,
        "杭州银行": fetch_hzb_rates,
        "工商银行": fetch_icbc_rates,
        "农业银行": fetch_abc_rates,
        "邮储银行": fetch_psbc_rates,
        "民生银行": fetch_cmbc_rates,
    }
    results = {}
    with ThreadPoolExecutor(max_workers=len(fetchers)) as pool:
        futures = {bank: pool.submit(fetcher) for bank, fetcher in fetchers.items()}
        for bank, future in futures.items():
            try:
                results[bank] = future.result() or {}
            except Exception as exc:
                print(f"{bank} fetch pipeline error: {exc}")
                results[bank] = {}
    return results
```

Replace the bank-specific branches in `fetch_and_save()` with this complete flow. Preserve the existing `last_boc_rates`, `last_cmb_rates`, and `last_ccb_rates` behavior only for those three pre-existing banks. / 用以下完整流程替换原先逐银行分支；只有原有的中国银行、招商银行和建设银行继续保留现有上次成功缓存。

```python
current_rates = _fetch_all_bank_rates()
if not quotes:
    return

db.save_market_quotes_batch(cycle_id, quotes, "CFETS")

fetched_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
for rates in current_rates.values():
    for quote in rates.values():
        quote["fetch_time"] = fetched_at

if current_rates["中国银行"]:
    last_boc_rates = dict(current_rates["中国银行"])
if current_rates["招商银行"]:
    last_cmb_rates = dict(current_rates["招商银行"])
if current_rates["建设银行"]:
    last_ccb_rates = dict(current_rates["建设银行"])

bank_data = []
for bank, rates in current_rates.items():
    for pair in quotes:
        if pair in rates:
            quote = rates[pair]
            bank_data.append((bank, pair, quote["bid"], quote["ask"]))
if bank_data:
    db.save_bank_quotes_batch(cycle_id, bank_data)

display_rates = dict(current_rates)
display_rates["中国银行"] = current_rates["中国银行"] or last_boc_rates
display_rates["招商银行"] = current_rates["招商银行"] or last_cmb_rates
display_rates["建设银行"] = current_rates["建设银行"] or last_ccb_rates

bank_quotes_full = {bank: rates for bank, rates in display_rates.items() if rates}
cfets_cache.clear()
cfets_cache.update(quotes)
bank_cache.clear()
bank_cache.update(bank_quotes_full)
last_update = fetched_at
```

Replace the synthetic block in `save_entry()` with an explicit error. / 用明确错误替换 `save_entry()` 中的模拟价格逻辑。

```python
if bank_bid is None or bank_ask is None:
    return {
        "ok": False,
        "error": f"{bank} {pair} 暂无真实银行报价，请等待下一次更新",
    }
```

- [ ] **Step 5: Run pipeline regressions and verify GREEN / 运行流水线回归并确认通过**

```bash
rtk /Users/jun/Downloads/projects/.venvs/forex-monitor-web/bin/python -m pytest tests/test_four_minute_banks.py tests/test_hangzhou_bank.py -q
```

Expected / 预期：new parser and pipeline tests pass together with all Hangzhou Bank regressions. / 新解析与流水线测试和杭州银行回归测试全部通过。

- [ ] **Step 6: Commit Task 2 without unrelated dirty hunks / 提交任务二且不带入无关改动**

Stage `config.py`, both test files, and only the feature hunks from `server.py`. Confirm that the pre-existing bank-cost removal hunk is not staged. / 暂存配置、两个测试文件以及 `server.py` 的本功能片段，确认原有银行成本删除片段没有进入暂存区。

```bash
rtk git add config.py tests/test_four_minute_banks.py tests/test_hangzhou_bank.py
rtk git add -p server.py
rtk git diff --cached --check
rtk git diff --cached -- server.py
rtk git commit -m "feat: integrate truthful minute bank quotes"
```

### Task 3: Compact Quote Matrix and Eight-Bank Selectors / 紧凑报价矩阵和八家银行下拉框

**Files:**
- Modify: `static/index.html`
- Modify: `tests/test_four_minute_banks.py`

- [ ] **Step 1: Add failing frontend contract tests / 增加失败的前端契约测试**

Append this class to `tests/test_four_minute_banks.py`. / 追加以下测试类。

```python
class QuoteMatrixFrontendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (Path(__file__).parents[1] / "static" / "index.html").read_text()

    def test_matrix_contains_all_nine_sources(self):
        expected = [
            "CFETS", "中国银行", "招商银行", "建设银行", "杭州银行",
            "工商银行", "农业银行", "邮储银行", "民生银行",
        ]
        for source in expected:
            self.assertIn(source, self.html)
        self.assertIn("quote-matrix", self.html)
        self.assertIn("quote-status", self.html)

    def test_entry_and_chart_selectors_contain_new_banks(self):
        for bank in ["工商银行", "农业银行", "邮储银行", "民生银行"]:
            self.assertEqual(self.html.count(f"<option>{bank}</option>"), 2)

    def test_matrix_has_no_repeated_midpoint_cost_line(self):
        self.assertNotIn("pair-card .costs", self.html)
        self.assertNotIn("市场' + mc + ' 银行' + bc", self.html)
        self.assertIn("暂无新数据", self.html)
        self.assertIn("上次抓取", self.html)
```

- [ ] **Step 2: Run frontend tests and verify RED / 运行前端测试并确认失败**

```bash
rtk /Users/jun/Downloads/projects/.venvs/forex-monitor-web/bin/python -m pytest tests/test_four_minute_banks.py::QuoteMatrixFrontendTests -q
```

Expected / 预期：fails because the current page still uses quote cards and contains only four bank options. / 因当前页面仍使用报价卡片且只有四家银行选项而失败。

- [ ] **Step 3: Implement the approved matrix CSS / 实现已批准的矩阵样式**

Replace only the quote-card CSS section with the following matrix styles. / 只替换报价卡片 CSS 区域。

```css
.quotes{padding:6px 8px;background:#0a1628;overflow-x:auto}
.quote-matrix{min-width:760px;background:#0d2038;border:1px solid #1d4266;border-radius:7px;overflow:hidden}
.quote-head,.source-row{display:grid;grid-template-columns:92px repeat(4,minmax(130px,1fr)) 90px;align-items:center}
.quote-head{background:#09182b;color:#8fa0b6;font-size:10px;border-bottom:1px solid #285076;text-align:center}
.quote-head>div{padding:7px 4px}
.quote-head .source-name{text-align:left;padding-left:12px}
.quote-head b{display:block;color:#dce7f5;font-size:11px}
.quote-head .buy-label{color:#4ade80;margin-right:7px}
.quote-head .sell-label{color:#ef4444}
.source-row{min-height:45px;border-bottom:1px solid rgba(43,77,108,.55)}
.source-row:last-child{border-bottom:0}
.source-row.cfets{background:#17395e}
.source-row:hover{background:#123052}
.source-name{font-size:12px;font-weight:700;color:#c5d1e0;padding-left:12px;white-space:nowrap}
.quote-cell{text-align:center;font-variant-numeric:tabular-nums}
.quote-cell .buy{color:#4ade80;font-weight:700;margin-right:7px}
.quote-cell .sell{color:#ef4444;font-weight:700}
.quote-status{text-align:center;color:#8292a8;font-size:9px;line-height:1.35}
.quote-status.ok{color:#4ade80}
.quote-status.missing{color:#ef9a9a}
@media(max-width:640px){
  .quote-matrix{min-width:700px}
  .quote-head,.source-row{grid-template-columns:78px repeat(4,minmax(120px,1fr)) 78px}
  .source-name{padding-left:8px}
}
```

- [ ] **Step 4: Implement matrix rendering and selectors / 实现矩阵渲染和下拉框**

Add the four new `<option>` elements to both `entryBank` and `chartBank`. Replace `BANK_NAMES` and `renderQuotes()` with the complete implementation below. / 在两个银行下拉框增加四个选项，并替换 `BANK_NAMES` 和 `renderQuotes()`。

Both bank selectors must contain this exact ordered option list. Keep each selector's existing `id` and `onchange` attribute. / 两个银行下拉框都使用以下固定顺序，同时保留各自原有的 `id` 和 `onchange` 属性。

```html
<option>中国银行</option><option>招商银行</option>
<option>建设银行</option><option>杭州银行</option>
<option>工商银行</option><option>农业银行</option>
<option>邮储银行</option><option>民生银行</option>
```

```javascript
const PAIRS = ["USDCNY","EURCNY","HKDCNY","JPYCNY"];
const BANK_NAMES = [
  "CFETS","中国银行","招商银行","建设银行","杭州银行",
  "工商银行","农业银行","邮储银行","民生银行"
];

function renderQuotes(cfets, banks, timestamp) {
  const el = document.getElementById('quotesContainer');
  document.getElementById('updateTime').textContent = '最后更新: ' + (timestamp || '--');
  let html = '<div class="quote-matrix"><div class="quote-head">'
    + '<div class="source-name">数据来源</div>'
    + PAIRS.map(pair => '<div><b>' + pair + '</b><span class="buy-label">买入</span><span class="sell-label">卖出</span></div>').join('')
    + '<div>状态</div></div>';

  for (const source of BANK_NAMES) {
    let cells = '';
    let hasData = false;
    let sourceTime = '';
    let fetchTime = '';
    for (const pair of PAIRS) {
      const quote = source === 'CFETS' ? (cfets[pair] || {}) : ((banks[source] && banks[source][pair]) || {});
      const bid = quote.bid != null ? Number(quote.bid).toFixed(4) : '--';
      const ask = quote.ask != null ? Number(quote.ask).toFixed(4) : '--';
      if (quote.bid != null && quote.ask != null) hasData = true;
      if (!sourceTime && quote.source_time) sourceTime = quote.source_time;
      if (!fetchTime && quote.fetch_time) fetchTime = quote.fetch_time;
      cells += '<div class="quote-cell"><span class="buy">' + bid + '</span><span class="sell">' + ask + '</span></div>';
    }

    let statusClass = 'ok';
    let statusText = '市场基准';
    if (source !== 'CFETS' && sourceTime) {
      statusText = '正常<br>' + sourceTime.slice(11, 16);
    } else if (source !== 'CFETS' && fetchTime) {
      const label = fetchTime === timestamp ? '本轮抓取' : '上次抓取';
      statusText = label + '<br>' + fetchTime.slice(11, 16);
    } else if (source !== 'CFETS') {
      statusText = '有真实数据';
    }
    if (!hasData) {
      statusClass = 'missing';
      statusText = '暂无新数据';
    }
    html += '<div class="source-row ' + (source === 'CFETS' ? 'cfets' : '') + '">'
      + '<div class="source-name">' + source + '</div>' + cells
      + '<div class="quote-status ' + statusClass + '">' + statusText + '</div></div>';
  }
  el.innerHTML = html + '</div>';
}
```

- [ ] **Step 5: Run frontend and full tests / 运行前端与全部测试**

```bash
rtk /Users/jun/Downloads/projects/.venvs/forex-monitor-web/bin/python -m pytest -q
```

Expected / 预期：all parser, pipeline, Hangzhou Bank, storage, entry, and frontend tests pass. / 所有解析、流水线、杭州银行、存储、录入和前端测试通过。

- [ ] **Step 6: Commit Task 3 without the pre-existing entry-result hunk / 提交任务三且不带入原有录入结果改动**

```bash
rtk git add tests/test_four_minute_banks.py
rtk git add -p static/index.html
rtk git diff --cached --check
rtk git diff --cached -- static/index.html
rtk git commit -m "feat: add compact multi-bank quote matrix"
```

### Task 4: Live Verification and Local Handoff / 实时验证和本地交付

**Files:**
- No production file changes expected. / 预计不修改生产文件。

- [ ] **Step 1: Re-index and inspect impact / 重新建立索引并检查影响**

Run codebase-memory `index_repository` in fast mode, then `detect_changes` from `0853cd8`. Confirm changed call paths are limited to bank fetching, `fetch_and_save`, quote entry, and frontend rendering. / 用快速模式重新索引，再从 `0853cd8` 检查变更影响，确认调用路径只涉及银行抓取、采集保存、报价录入和前端渲染。

- [ ] **Step 2: Run the complete automated suite / 运行完整自动化测试**

```bash
rtk /Users/jun/Downloads/projects/.venvs/forex-monitor-web/bin/python -m pytest -q
```

Expected / 预期：all tests pass with zero failures. / 全部测试通过且零失败。

- [ ] **Step 3: Run one official live-fetch smoke check / 执行一次官方实时抓取检查**

```bash
rtk /Users/jun/Downloads/projects/.venvs/forex-monitor-web/bin/python -c "from bank_fetcher import fetch_icbc_rates,fetch_abc_rates,fetch_psbc_rates,fetch_cmbc_rates; banks={'工商银行':fetch_icbc_rates,'农业银行':fetch_abc_rates,'邮储银行':fetch_psbc_rates,'民生银行':fetch_cmbc_rates}; results={name:fn() or {} for name,fn in banks.items()}; expected={'USDCNY','EURCNY','HKDCNY','JPYCNY'}; assert all(set(rates)==expected for rates in results.values()); assert all(q['bid']<=q['ask'] and q.get('source_time') for rates in results.values() for q in rates.values()); print({name:{pair:(q['bid'],q['ask'],q['source_time']) for pair,q in rates.items()} for name,rates in results.items()})"
```

Expected / 预期：each bank reports `['EURCNY', 'HKDCNY', 'JPYCNY', 'USDCNY']`; inspect one response per bank to confirm `bid <= ask` and a recent `source_time`. / 每家银行都返回四个货币对，并抽查买入价不高于卖出价且官方时间有效。

- [ ] **Step 4: Restart the local server with the project virtual environment / 使用项目虚拟环境重启本地服务**

Find the current listener with `rtk lsof -nP -iTCP:8000 -sTCP:LISTEN`, stop only that local development process, then start: / 查找 8000 端口监听，只停止该本地开发进程，然后启动：

```bash
rtk /Users/jun/Downloads/projects/.venvs/forex-monitor-web/bin/python server.py
```

Expected / 预期：`http://127.0.0.1:8000/` and `/api/quotes` return HTTP 200. / 首页和报价 API 返回 200。

- [ ] **Step 5: Verify the UI in the in-app browser / 在应用内浏览器验证界面**

Check the visible matrix contains nine rows, four pair columns, and the status column. Confirm both selectors contain eight banks, missing live data is `--`, and the history chart for a new bank shows market mid, bank bid, bank ask, and bank cost after at least one saved cycle. Check a desktop viewport and a width at or below 640 px. / 检查矩阵九行、四个货币对列和状态列；确认两个下拉框都有八家银行、缺失值显示 `--`，且至少保存一轮后新增银行历史图包含市场中间价、银行买入价、卖出价和银行成本；同时检查桌面和不超过 640px 的窄窗口。

- [ ] **Step 6: Run final repository checks / 执行最终仓库检查**

```bash
rtk git diff --check
rtk git status --short
rtk git log -5 --oneline
```

Expected / 预期：no whitespace errors; only the user's pre-existing uncommitted files and runtime artifacts remain outside the feature commits. / 没有空白错误；功能提交之外只保留用户原有未提交文件和运行产物。

- [ ] **Step 7: Stop before cloud deployment / 在上云前停止**

Present local test results and the running local URL. Do not run `deploy.sh`, SSH, SCP, or any Alibaba Cloud mutation until the user explicitly approves the reviewed local build. / 展示本地测试结果和运行地址；用户明确批准本地版本之前，不执行部署脚本、SSH、SCP 或任何阿里云写操作。
