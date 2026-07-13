import asyncio
import json
import re
import shutil
import sqlite3
import ssl
import subprocess
import tempfile
import unittest
from datetime import datetime, time, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import requests

import bank_fetcher
import server
from config import BANKS
from database import Database


NODE_BINARY = shutil.which("node")


def current_time():
    return datetime.now().replace(microsecond=0)


def current_text():
    return current_time().strftime("%Y-%m-%d %H:%M:%S")


def response_with_json(payload):
    response = Mock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


class FourMinuteBankFetcherTests(unittest.TestCase):
    def get_fetcher(self, name):
        fetcher = getattr(bank_fetcher, name, None)
        self.assertIsNotNone(fetcher, f"{name} must be implemented")
        return fetcher

    @patch("bank_fetcher._legacy_tls_request")
    def test_icbc_returns_four_pairs_with_correct_units(self, mock_legacy_request):
        source_time = current_time()
        rows = [
            ("USD", "677.15", "680.17"),
            ("EUR", "770.29", "776.07"),
            ("HKD", "86.329", "86.760"),
            ("JPY", "4.1609", "4.2085"),
        ]
        response = response_with_json({
            "code": 0,
            "data": [
                {
                    "currencyENName": currency,
                    "foreignBuy": bid,
                    "foreignSell": ask,
                    "publishDate": source_time.strftime("%Y-%m-%d"),
                    "publishTime": source_time.strftime("%H:%M:%S"),
                }
                for currency, bid, ask in rows
            ],
        })
        mock_legacy_request.return_value = response

        rates = self.get_fetcher("fetch_icbc_rates")()

        self.assertEqual(set(rates), {"USDCNY", "EURCNY", "HKDCNY", "JPYCNY"})
        self.assertEqual(rates["USDCNY"]["bid"], 6.7715)
        self.assertEqual(rates["USDCNY"]["ask"], 6.8017)
        self.assertEqual(rates["JPYCNY"]["bid"], 4.1609)
        self.assertEqual(rates["JPYCNY"]["ask"], 4.2085)
        self.assertEqual(rates["USDCNY"]["mid"], 6.7866)
        self.assertEqual(rates["USDCNY"]["source_time"], source_time.strftime("%Y-%m-%d %H:%M:%S"))
        self.assertTrue(mock_legacy_request.called, "ICBC must use the scoped legacy TLS path")
        self.assertEqual(
            mock_legacy_request.call_args.args[:2],
            ("POST", "https://papi.icbc.com.cn/exchanges/ns/getLatest"),
        )
        response.raise_for_status.assert_called_once_with()

    @patch("bank_fetcher.requests.get")
    def test_abc_uses_official_endpoint_iso_time_and_correct_units(self, mock_get):
        source_time = current_time().astimezone()
        rows = [
            (14, "677.15", "680.17"),
            (38, "770.29", "776.07"),
            (13, "86.329", "86.760"),
            (27, "4.1609", "4.2085"),
        ]
        mock_get.return_value = response_with_json({
            "ErrorCode": "0",
            "Data": {
                "Table": [
                    {
                        "CurrId": currency,
                        "BuyingPrice": bid,
                        "SellPrice": ask,
                        "PublishTime": source_time.isoformat(),
                    }
                    for currency, bid, ask in rows
                ],
            },
        })

        with patch("bank_fetcher.time.time", return_value=1_721_234_567.89):
            rates = self.get_fetcher("fetch_abc_rates")()

        self.assertEqual(set(rates), {"USDCNY", "EURCNY", "HKDCNY", "JPYCNY"})
        self.assertEqual(rates["USDCNY"]["bid"], 6.7715)
        self.assertEqual(rates["JPYCNY"]["bid"], 4.1609)
        self.assertEqual(rates["EURCNY"]["source_time"], source_time.strftime("%Y-%m-%d %H:%M:%S"))
        self.assertEqual(
            mock_get.call_args.args[0],
            "https://www.abchina.com.cn/creditCardService/DataService/ExchangeRate",
        )
        self.assertEqual(mock_get.call_args.kwargs.get("params"), {"_": 1_721_234_567_890})
        mock_get.return_value.raise_for_status.assert_called_once_with()

    @patch("bank_fetcher._legacy_tls_request")
    def test_psbc_parses_jsonp_and_uses_correct_units(self, mock_legacy_request):
        source_time = current_time()
        rows = [
            ("USD", "677.15", "680.17"),
            ("EUR", "770.29", "776.07"),
            ("HKD", "86.329", "86.760"),
            ("JPY", "4.1609", "4.2085"),
        ]
        payload = {
            "retCode": "000",
            "resultList": [
                {
                    "cur": currency,
                    "fe_buy_prc": bid,
                    "fe_sell_prc": ask,
                    "effect_date": source_time.strftime("%Y%m%d"),
                    "effect_time": source_time.strftime("%H%M%S"),
                }
                for currency, bid, ask in rows
            ],
        }
        response = Mock(text=f"cb({json.dumps(payload)})")
        response.raise_for_status.return_value = None
        mock_legacy_request.return_value = response

        rates = self.get_fetcher("fetch_psbc_rates")()

        self.assertEqual(set(rates), {"USDCNY", "EURCNY", "HKDCNY", "JPYCNY"})
        self.assertEqual(rates["HKDCNY"]["bid"], 0.8633)
        self.assertEqual(rates["JPYCNY"]["bid"], 4.1609)
        self.assertEqual(rates["JPYCNY"]["source_time"], source_time.strftime("%Y-%m-%d %H:%M:%S"))
        self.assertTrue(mock_legacy_request.called, "PSBC must use the scoped legacy TLS path")
        self.assertEqual(
            mock_legacy_request.call_args.args[:2],
            ("GET", "https://s.psbc.com/portal/PsbcService/foreignexchange/curr?callback=cb"),
        )
        response.raise_for_status.assert_called_once_with()

    def test_legacy_tls_compatibility_is_limited_to_two_bank_origins(self):
        legacy_request = getattr(bank_fetcher, "_legacy_tls_request", None)
        self.assertIsNotNone(legacy_request, "scoped legacy TLS request path must be implemented")

        response = Mock()
        with patch("bank_fetcher.requests.Session") as session_class:
            session = session_class.return_value
            session.request.return_value = response

            actual = legacy_request(
                "GET",
                "https://s.psbc.com/portal/PsbcService/foreignexchange/curr?callback=cb",
                timeout=10,
            )

        self.assertIs(actual, response)
        self.assertEqual(session.mount.call_args.args[0], "https://s.psbc.com/")
        adapter = session.mount.call_args.args[1]
        context = adapter.poolmanager.connection_pool_kw["ssl_context"]
        legacy_option = getattr(ssl, "OP_LEGACY_SERVER_CONNECT", 0x4)
        self.assertTrue(context.options & legacy_option)
        session.close.assert_called_once_with()
        with self.assertRaises(ValueError):
            legacy_request("GET", "https://example.com/", timeout=10)

    @patch("bank_fetcher.requests.post")
    def test_cmbc_keeps_already_normalized_values(self, mock_post):
        source_time = current_time()
        rows = [
            ("USD", "6.7715", "6.8017"),
            ("EUR", "7.7029", "7.7607"),
            ("HKD", "0.86329", "0.86760"),
            ("JPY", "4.1609", "4.2085"),
        ]
        mock_post.return_value = response_with_json({
            "returnCode": {"type": "S"},
            "result": [
                {
                    "foreignCurrency": currency,
                    "buyPrice": bid,
                    "sellPrice": ask,
                    "updateTime": source_time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                for currency, bid, ask in rows
            ],
        })

        rates = self.get_fetcher("fetch_cmbc_rates")()

        self.assertEqual(set(rates), {"USDCNY", "EURCNY", "HKDCNY", "JPYCNY"})
        self.assertEqual(rates["USDCNY"]["bid"], 6.7715)
        self.assertEqual(rates["HKDCNY"]["bid"], 0.8633)
        self.assertEqual(rates["JPYCNY"]["bid"], 4.1609)
        self.assertEqual(mock_post.call_args.args[0], "https://www.cmbc.com.cn/gw/po_web/queryExRateByForex.do")
        self.assertEqual(mock_post.call_args.kwargs["data"], {"cxfg": "1", "domesticCurrency": "RMB"})
        mock_post.return_value.raise_for_status.assert_called_once_with()

    @patch("bank_fetcher.requests.post")
    def test_cmbc_skips_stale_reversed_and_zero_rows(self, mock_post):
        now = current_time()
        stale = now - timedelta(minutes=4)
        mock_post.return_value = response_with_json({
            "returnCode": {"type": "S"},
            "result": [
                {"foreignCurrency": "USD", "buyPrice": "6.77", "sellPrice": "6.80", "updateTime": stale.strftime("%Y-%m-%d %H:%M:%S")},
                {"foreignCurrency": "EUR", "buyPrice": "7.80", "sellPrice": "7.70", "updateTime": now.strftime("%Y-%m-%d %H:%M:%S")},
                {"foreignCurrency": "HKD", "buyPrice": "0", "sellPrice": "0.87", "updateTime": now.strftime("%Y-%m-%d %H:%M:%S")},
                {"foreignCurrency": "JPY", "buyPrice": "4.16", "sellPrice": "4.21", "updateTime": now.strftime("%Y-%m-%d %H:%M:%S")},
            ],
        })

        rates = self.get_fetcher("fetch_cmbc_rates")()

        self.assertEqual(rates, {
            "JPYCNY": {
                "bid": 4.16,
                "ask": 4.21,
                "mid": 4.185,
                "source_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            },
        })

    @patch("bank_fetcher.requests.post")
    def test_future_timestamp_allows_small_skew_but_rejects_large_skew(self, mock_post):
        now = current_time()
        slightly_future = now + timedelta(seconds=15)
        too_far_future = now + timedelta(minutes=2)
        mock_post.return_value = response_with_json({
            "returnCode": {"type": "S"},
            "result": [
                {"foreignCurrency": "USD", "buyPrice": "6.77", "sellPrice": "6.80", "updateTime": too_far_future.strftime("%Y-%m-%d %H:%M:%S")},
                {"foreignCurrency": "JPY", "buyPrice": "4.16", "sellPrice": "4.21", "updateTime": slightly_future.strftime("%Y-%m-%d %H:%M:%S")},
            ],
        })

        rates = self.get_fetcher("fetch_cmbc_rates")()

        self.assertEqual(set(rates), {"JPYCNY"})

    @patch("bank_fetcher._legacy_tls_request")
    def test_malformed_icbc_row_does_not_discard_valid_row(self, mock_legacy_request):
        source_time = current_time()
        common = {
            "publishDate": source_time.strftime("%Y-%m-%d"),
            "publishTime": source_time.strftime("%H:%M:%S"),
        }
        response = response_with_json({
            "code": 0,
            "data": [
                {"currencyENName": "USD", "foreignBuy": "not-a-number", "foreignSell": "680.17", **common},
                {"currencyENName": "EUR", "foreignBuy": "770.29", "foreignSell": "776.07", **common},
                {"currencyENName": "GBP", "foreignBuy": "880.29", "foreignSell": "886.07", **common},
            ],
        })
        mock_legacy_request.return_value = response

        rates = self.get_fetcher("fetch_icbc_rates")()

        self.assertEqual(set(rates), {"EURCNY"})

    def test_request_failures_return_none(self):
        cases = [
            ("fetch_icbc_rates", "_legacy_tls_request"),
            ("fetch_abc_rates", "requests.get"),
            ("fetch_psbc_rates", "_legacy_tls_request"),
            ("fetch_cmbc_rates", "requests.post"),
        ]
        for fetcher_name, request_target in cases:
            with self.subTest(fetcher=fetcher_name):
                with patch(f"bank_fetcher.{request_target}", side_effect=requests.RequestException("offline")):
                    self.assertIsNone(self.get_fetcher(fetcher_name)())

    def test_root_payload_failures_return_none(self):
        cases = [
            ("fetch_icbc_rates", "_legacy_tls_request", {"code": 1, "data": []}, None),
            ("fetch_abc_rates", "requests.get", {"ErrorCode": "1", "Data": {}}, None),
            ("fetch_psbc_rates", "_legacy_tls_request", None, "cb({\"retCode\": \"999\"})"),
            ("fetch_cmbc_rates", "requests.post", {"returnCode": {"type": "E"}}, None),
        ]
        for fetcher_name, request_target, payload, text in cases:
            with self.subTest(fetcher=fetcher_name):
                response = response_with_json(payload)
                if text is not None:
                    response.text = text
                with patch(f"bank_fetcher.{request_target}", return_value=response):
                    self.assertIsNone(self.get_fetcher(fetcher_name)())


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
        self.assertIn("fetch_time", server.bank_cache["工商银行"]["USDCNY"])
        saved = fake_db.save_bank_quotes_batch.call_args.args[1]
        self.assertIn(("工商银行", "USDCNY", 6.76, 6.79), saved)

    def test_bank_fetch_pipeline_isolates_one_bank_failure(self):
        expected = {"USDCNY": {"bid": 6.76, "ask": 6.79}}
        with (
            patch.object(server, "fetch_boc_rates", return_value=expected),
            patch.object(server, "fetch_cmb_rates", return_value=expected),
            patch.object(server, "fetch_ccb_rates", return_value=expected),
            patch.object(server, "fetch_hzb_rates", return_value=expected),
            patch.object(server, "fetch_icbc_rates", return_value=expected),
            patch.object(server, "fetch_abc_rates", return_value=expected),
            patch.object(server, "fetch_psbc_rates", return_value=expected),
            patch.object(server, "fetch_cmbc_rates", side_effect=RuntimeError("offline")),
        ):
            results = server._fetch_all_bank_rates()

        self.assertEqual(set(results), set(BANKS))
        self.assertEqual(results["工商银行"], expected)
        self.assertEqual(results["民生银行"], {})

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

    def test_missing_market_clears_all_current_only_bank_quotes(self):
        quote = {"USDCNY": {"bid": 6.76, "ask": 6.79}}
        legacy_banks = ["中国银行", "招商银行", "建设银行"]
        current_only_banks = ["杭州银行", "工商银行", "农业银行", "邮储银行", "民生银行"]
        server.cfets_cache["USDCNY"] = {"bid": 6.77, "ask": 6.78, "mid": 6.775}

        for has_current_bank_results in (False, True):
            with self.subTest(has_current_bank_results=has_current_bank_results):
                server.bank_cache.clear()
                server.bank_cache.update({bank: quote for bank in BANKS})
                bank_rates = {
                    bank: (quote if has_current_bank_results else {})
                    for bank in BANKS
                }
                fake_db = Mock()

                with (
                    patch.object(server, "db", fake_db),
                    patch.object(server, "fetch_all_quotes", return_value={}),
                    patch.object(server, "_fetch_all_bank_rates", return_value=bank_rates),
                ):
                    server.fetch_and_save()

                    for bank in current_only_banks:
                        result = asyncio.run(
                            server.save_entry("USDCNY", bank, "买入价", 6.77, None)
                        )
                        self.assertFalse(result["ok"])
                        self.assertIn("暂无真实银行报价", result["error"])

                for bank in legacy_banks:
                    self.assertIn(bank, server.bank_cache)
                for bank in current_only_banks:
                    self.assertNotIn(bank, server.bank_cache)
                fake_db.save_user_entry.assert_not_called()

    def test_database_failure_clears_all_current_only_bank_quotes(self):
        quote = {"USDCNY": {"bid": 6.76, "ask": 6.79}}
        market = {"USDCNY": {"bid": 6.77, "ask": 6.78, "mid": 6.775}}
        legacy_banks = ["中国银行", "招商银行", "建设银行"]
        current_only_banks = ["杭州银行", "工商银行", "农业银行", "邮储银行", "民生银行"]
        server.cfets_cache.update(market)
        server.bank_cache.update({bank: quote for bank in BANKS})
        fake_db = Mock()
        fake_db.save_bank_quotes_batch.side_effect = sqlite3.OperationalError("database locked")

        with (
            patch.object(server, "db", fake_db),
            patch.object(server, "fetch_all_quotes", return_value=market),
            patch.object(server, "_fetch_all_bank_rates", return_value={bank: quote for bank in BANKS}),
        ):
            with self.assertRaises(sqlite3.OperationalError):
                server.fetch_and_save()

            for bank in current_only_banks:
                self.assertNotIn(bank, server.bank_cache)
                result = asyncio.run(server.save_entry("USDCNY", bank, "买入价", 6.77, None))
                self.assertFalse(result["ok"])
                self.assertIn("暂无真实银行报价", result["error"])

        for bank in legacy_banks:
            self.assertIn(bank, server.bank_cache)
        fake_db.save_user_entry.assert_not_called()

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


class QuoteMatrixFrontendTests(unittest.TestCase):
    NODE_DOM_PRELUDE = """
class MockNode {
  constructor(tagName = 'div') {
    this.tagName = tagName;
    this.className = '';
    this.attributes = {};
    this.children = [];
    this.value = '';
    this._innerHTML = '';
    this._textContent = '';
    this.innerHTMLWrites = 0;
    this.textContentWrites = 0;
    this.replaceChildrenCalls = 0;
    this.isFragment = false;
  }
  set innerHTML(value) {
    this._innerHTML = String(value);
    this.innerHTMLWrites += 1;
    this.children = [];
  }
  get innerHTML() { return this._innerHTML; }
  set textContent(value) {
    this._textContent = String(value);
    this.textContentWrites += 1;
    this.children = [];
  }
  get textContent() { return this._textContent; }
  setAttribute(name, value) { this.attributes[name] = String(value); }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) {
    this.replaceChildrenCalls += 1;
    this._innerHTML = '';
    this.children = [];
    nodes.forEach(node => {
      if (node && node.isFragment) this.children.push(...node.children);
      else if (node) this.children.push(node);
    });
  }
}
class MockFragment extends MockNode {
  constructor() {
    super('fragment');
    this.isFragment = true;
  }
}
"""

    @classmethod
    def setUpClass(cls):
        cls.html = (Path(__file__).parents[1] / "static" / "index.html").read_text()

    @staticmethod
    def run_node_json(script):
        result = subprocess.run(
            [NODE_BINARY, "-e", script],
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout)

    @classmethod
    def extract_js(cls, start_marker, end_marker):
        start = cls.html.index(start_marker)
        end = cls.html.index(end_marker, start)
        return cls.html[start:end]

    def test_matrix_contains_all_nine_sources(self):
        expected = [
            "CFETS", "中国银行", "招商银行", "建设银行", "杭州银行",
            "工商银行", "农业银行", "邮储银行", "民生银行",
        ]
        for source in expected:
            self.assertIn(source, self.html)
        self.assertIn("quote-matrix", self.html)
        self.assertIn("quote-status", self.html)

    def test_institutional_shell_brand_and_palette(self):
        for marker in [
            'class="app-shell"',
            'class="terminal-header"',
            'class="brand-mark"',
            "外汇报价工作台",
            "FOREIGN EXCHANGE MONITOR",
            "实时采集中",
            "--page:#070b10",
            "--panel:#0e1620",
            "--accent:#56d8b3",
            "max-width:1400px",
            "font-variant-numeric:tabular-nums",
        ]:
            self.assertIn(marker, self.html)
        for emoji in ["🔄", "📝", "📊", "📋"]:
            self.assertNotIn(emoji, self.html)

    def test_chart_uses_terminal_palette_and_one_resize_listener(self):
        line_style_source = self.extract_js(
            "const LINE_STYLE = [",
            "async function loadChart()",
        )
        expected_styles = [
            ("银行卖价", "#ff857a"),
            ("银行成本", "#d8a84e"),
            ("市场成本", "#98a6ae"),
            ("银行买价", "#56d8b3"),
        ]
        for name, color in expected_styles:
            self.assertRegex(
                line_style_source,
                rf"name\s*:\s*['\"]{name}['\"][^}}\n]*"
                rf"color\s*:\s*['\"]{color}['\"]",
            )
        self.assertRegex(
            line_style_source,
            r"name\s*:\s*['\"]银行成本['\"][^}\n]*"
            r"type\s*:\s*['\"]dashed['\"]",
        )

        state_source = self.extract_js(
            "// ── 全局状态 ──",
            "// ── Tab 切换 ──",
        )
        chart_source = self.extract_js(
            "const LINE_STYLE = [",
            "// ── 录入报价 ──",
        )
        render_chart_source = chart_source[chart_source.index("function renderChart(data)"):]
        for field in ["asks", "costs", "mids", "bids"]:
            self.assertRegex(render_chart_source, rf"data\s*:\s*data\.{field}")
        resize_pattern = (
            r"window\s*\.\s*addEventListener\s*\(\s*['\"]resize['\"]"
        )
        self.assertEqual(len(re.findall(resize_pattern, self.html)), 1)
        self.assertRegex(
            state_source,
            r"(?:let|const|var)\s+\w+\s*=\s*null\s*;\s*" + resize_pattern,
        )
        self.assertNotRegex(render_chart_source, resize_pattern)

        if not NODE_BINARY:
            self.skipTest("Node.js is required for chart lifecycle behavior")

        error_source = self.extract_js(
            "function showInlineError(containerId, message)",
            "function renderQuotes(cfets, banks, timestamp)",
        )
        result = self.run_node_json(self.NODE_DOM_PRELUDE + """
const elements = {
  chart: new MockNode(),
  chartPair: Object.assign(new MockNode('select'), { value: 'USDCNY' }),
  chartBank: Object.assign(new MockNode('select'), { value: '中国银行' }),
  chartDate: Object.assign(new MockNode('input'), { value: '2026-07-13' })
};
const document = {
  getElementById(id) { return elements[id]; },
  createElement(tagName) { return new MockNode(tagName); }
};
const listeners = {};
const window = {
  addEventListener(type, listener) {
    if (!listeners[type]) listeners[type] = [];
    listeners[type].push(listener);
  }
};
const chartInstances = [];
const echarts = {
  init(dom) {
    const instance = {
      disposed: false,
      option: null,
      resizeCalls: 0,
      setOption(option) { this.option = option; },
      on() {},
      resize() { this.resizeCalls += 1; },
      dispose() { this.disposed = true; }
    };
    chartInstances.push(instance);
    return instance;
  }
};
const chartData = {
  times: ['10:00'],
  asks: [6.8000],
  costs: [6.7900],
  mids: [6.7800],
  bids: [6.7700],
  sources: ['精确']
};
let fetchMode = 'failure';
const fetch = async () => fetchMode === 'failure'
  ? { ok: false, status: 503, json: async () => ({}) }
  : { ok: true, status: 200, json: async () => chartData };
const console = { error() {} };
""" + state_source + error_source + chart_source + """
(async () => {
  renderChart(chartData);
  const first = chartInstances[0];
  const firstSeries = first.option.series.map(item => ({
    name: item.name,
    data: item.data,
    lineColor: item.lineStyle.color,
    itemColor: item.itemStyle.color,
    type: item.lineStyle.type
  }));
  const tooltipText = first.option.tooltip.formatter([
    { axisValue: '10:00', value: 6.8000 },
    { axisValue: '10:00', value: 6.7900 },
    { axisValue: '10:00', value: 6.7800 },
    { axisValue: '10:00', value: 6.7700 }
  ]);

  renderChart(chartData);
  const second = chartInstances[1];
  const firstDisposedAfterSecond = first.disposed;
  renderChart({ times: [] });
  const emptyState = {
    secondDisposed: second.disposed,
    instanceIsNull: chartInstance === null,
    html: elements.chart.innerHTML
  };

  await loadChart();
  const errorNode = elements.chart.children[0];
  const failureState = {
    instanceIsNull: chartInstance === null,
    className: errorNode.className,
    text: errorNode.textContent
  };

  fetchMode = 'success';
  await loadChart();
  const recovered = chartInstances[2];
  listeners.resize[0]();
  process.stdout.write(JSON.stringify({
    firstSeries,
    option: {
      background: first.option.backgroundColor,
      tooltipBackground: first.option.tooltip.backgroundColor,
      tooltipBorder: first.option.tooltip.borderColor,
      tooltipTextColor: first.option.tooltip.textStyle.color,
      tooltipCallable: typeof first.option.tooltip.formatter === 'function',
      tooltipText,
      legendTextColor: first.option.legend.textStyle.color,
      xLine: first.option.xAxis.axisLine.lineStyle.color,
      xLabel: first.option.xAxis.axisLabel.color,
      xSplit: first.option.xAxis.splitLine.lineStyle.color,
      yLine: first.option.yAxis.axisLine.lineStyle.color,
      yLabel: first.option.yAxis.axisLabel.color,
      ySplit: first.option.yAxis.splitLine.lineStyle.color,
      yFormatted: first.option.yAxis.axisLabel.formatter(6.7),
      dataZoom: first.option.dataZoom[0]
    },
    lifecycle: {
      firstDisposedAfterSecond,
      listenerCount: (listeners.resize || []).length,
      instanceCount: chartInstances.length,
      emptyState,
      failureState,
      recoveredHasOption: Boolean(recovered.option),
      recoveredDomCleared: elements.chart.children.length === 0
        && elements.chart.innerHTML === '',
      recoveredResizeCalls: recovered.resizeCalls
    }
  }));
})().catch(error => {
  process.stderr.write(error.stack + '\\n');
  process.exit(1);
});
""")

        self.assertEqual(result["firstSeries"], [
            {"name": "银行卖价", "data": [6.8], "lineColor": "#ff857a", "itemColor": "#ff857a", "type": "solid"},
            {"name": "银行成本", "data": [6.79], "lineColor": "#d8a84e", "itemColor": "#d8a84e", "type": "dashed"},
            {"name": "市场成本", "data": [6.78], "lineColor": "#98a6ae", "itemColor": "#98a6ae", "type": "solid"},
            {"name": "银行买价", "data": [6.77], "lineColor": "#56d8b3", "itemColor": "#56d8b3", "type": "solid"},
        ])
        option = result["option"]
        self.assertEqual(option["background"], "#0e1620")
        self.assertEqual(option["tooltipBackground"], "rgba(14,22,32,.96)")
        self.assertEqual(option["tooltipBorder"], "#2a3b47")
        self.assertEqual(option["tooltipTextColor"], "#dce5e8")
        self.assertTrue(option["tooltipCallable"])
        self.assertIn("6.8000", option["tooltipText"])
        self.assertIn("color:#56d8b3", option["tooltipText"])
        self.assertEqual(option["legendTextColor"], "#91a1a8")
        for key in ["xLine", "yLine"]:
            self.assertEqual(option[key], "#2c3b46")
        for key in ["xLabel", "yLabel"]:
            self.assertEqual(option[key], "#7f9098")
        for key in ["xSplit", "ySplit"]:
            self.assertEqual(option[key], "#192833")
        self.assertEqual(option["yFormatted"], "6.7000")
        self.assertEqual(option["dataZoom"], {"type": "inside", "start": 0, "end": 100})

        lifecycle = result["lifecycle"]
        self.assertTrue(lifecycle["firstDisposedAfterSecond"])
        self.assertEqual(lifecycle["listenerCount"], 1)
        self.assertEqual(lifecycle["instanceCount"], 3)
        self.assertTrue(lifecycle["emptyState"]["secondDisposed"])
        self.assertTrue(lifecycle["emptyState"]["instanceIsNull"])
        self.assertIn("暂无今日数据", lifecycle["emptyState"]["html"])
        self.assertEqual(lifecycle["failureState"], {
            "instanceIsNull": True,
            "className": "inline-state inline-error",
            "text": "图表暂时无法获取，请稍后重试",
        })
        self.assertTrue(lifecycle["recoveredHasOption"])
        self.assertTrue(lifecycle["recoveredDomCleared"])
        self.assertEqual(lifecycle["recoveredResizeCalls"], 1)

    def test_focus_and_mobile_layout_keep_scroll_inside_quote_matrix(self):
        style_source = self.html[
            self.html.index("<style>") + len("<style>"):
            self.html.index("</style>")
        ]
        normalized_css = re.sub(r"\s+", "", style_source)
        focus_rule = (
            ":is(button,select,input):focus-visible{outline:2px solid "
            "var(--accent);outline-offset:2px}"
        )
        self.assertIn(re.sub(r"\s+", "", focus_rule), normalized_css)

        media_860_start = normalized_css.index("@media(max-width:860px){")
        media_640_start = normalized_css.index("@media(max-width:640px){")
        media_860 = normalized_css[media_860_start:media_640_start]
        for rule in [
            ".entry-layout{grid-template-columns:1fr}",
            ".form-grid{grid-template-columns:repeat(2,minmax(0,1fr))}",
            ".chart-controls{grid-template-columns:repeat(3,minmax(0,1fr))}",
        ]:
            self.assertIn(rule, media_860)

        media_640 = normalized_css[media_640_start:]
        for rule in [
            ".app-shell{width:calc(100%-16px);margin:12pxauto24px;",
            ".terminal-header{align-items:flex-start;flex-direction:column}",
            ".live-meta{width:100%;align-items:center;flex-direction:row;"
            "justify-content:space-between}",
            ".panel-heading{min-height:0;padding:10px0}",
            ".quote-matrix{min-width:820px}",
            ".quote-head,.source-row{grid-template-columns:108px"
            "repeat(4,minmax(142px,1fr))86px}",
            ".tab-content{padding:10px}",
            ".entry-layout{grid-template-columns:1fr}",
            ".entry-panel,.recent-panel{padding:14px}",
            ".form-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}",
            ".field-wide{grid-column:span2}",
            ".chart-controls{grid-template-columns:1fr}",
            "#chart{height:330px}",
        ]:
            self.assertIn(rule, media_640)

        self.assertRegex(normalized_css, r"body\{[^}]*overflow-x:hidden[^}]*\}")
        self.assertEqual(normalized_css.count(".quotes{overflow-x:auto}"), 1)
        self.assertEqual(normalized_css.count("overflow-x:auto"), 1)
        self.assertNotIn("@media(max-width:600px)", normalized_css)

    def test_entry_and_chart_selectors_contain_new_banks(self):
        for bank in ["工商银行", "农业银行", "邮储银行", "民生银行"]:
            self.assertEqual(self.html.count(f"<option>{bank}</option>"), 2)

    def test_entry_workspace_has_professional_structure_and_live_regions(self):
        self.assertRegex(
            self.html,
            r'<nav(?=[^>]*class="workspace-tabs")(?=[^>]*role="tablist")[^>]*>',
        )
        self.assertRegex(
            self.html,
            r'<button(?=[^>]*class="[^"]*tab-btn[^"]*")(?=[^>]*role="tab")'
            r'(?=[^>]*aria-selected="true")(?=[^>]*aria-controls="tab-entry")'
            r'(?=[^>]*data-tab="entry")[^>]*>录入报价</button>',
        )
        self.assertRegex(
            self.html,
            r'<button(?=[^>]*class="[^"]*tab-btn[^"]*")(?=[^>]*role="tab")'
            r'(?=[^>]*aria-selected="false")(?=[^>]*aria-controls="tab-chart")'
            r'(?=[^>]*data-tab="chart")[^>]*>历史图表</button>',
        )
        self.assertRegex(
            self.html,
            r'<div(?=[^>]*class="recent-list")(?=[^>]*id="entryRecent")'
            r'(?=[^>]*role="status")(?=[^>]*aria-live="polite")[^>]*>',
        )
        for marker in [
            'class="entry-layout"', 'class="entry-panel"',
            'class="recent-panel"', 'class="field"',
            'class="result-card"', 'type="date" id="entryDate"',
            'type="time" id="entryTime"', '>现在</button>',
        ]:
            self.assertIn(marker, self.html)
        self.assertNotIn('id="entryDate" style=', self.html)
        self.assertNotIn('id="entryTime" style=', self.html)
        self.assertIn(
            "setAttribute('aria-selected', String(active))",
            self.html,
        )

        if not NODE_BINARY:
            self.skipTest("Node.js is required for dynamic frontend rendering")
        tab_script = self.extract_js(
            "document.querySelectorAll('.tab-btn')",
            "// ── 报价栏渲染 ──",
        )
        result = self.run_node_json("""
function makeClassList(initial) {
  const classes = new Set(initial);
  return {
    add(name) { classes.add(name); },
    remove(name) { classes.delete(name); },
    toggle(name, force) {
      if (force) classes.add(name); else classes.delete(name);
      return classes.has(name);
    },
    contains(name) { return classes.has(name); }
  };
}
function makeButton(tab, isActive, selected) {
  return {
    dataset: { tab },
    attributes: { 'aria-selected': selected },
    listeners: {},
    classList: makeClassList(isActive ? ['active'] : []),
    addEventListener(type, listener) { this.listeners[type] = listener; },
    setAttribute(name, value) { this.attributes[name] = value; }
  };
}
const entryButton = makeButton('entry', true, 'true');
const chartButton = makeButton('chart', false, 'false');
const buttons = [entryButton, chartButton];
const panes = {
  'tab-entry': { classList: makeClassList(['active']) },
  'tab-chart': { classList: makeClassList([]) }
};
const document = {
  querySelectorAll(selector) {
    if (selector === '.tab-btn') return buttons;
    if (selector === '.tab-pane') return Object.values(panes);
    throw new Error('unexpected selector: ' + selector);
  },
  getElementById(id) { return panes[id]; }
};
let chartInstance = { resize() {} };
const setTimeout = callback => callback();
""" + tab_script + """
chartButton.listeners.click();
process.stdout.write(JSON.stringify({
  entryButton: {
    active: entryButton.classList.contains('active'),
    selected: entryButton.attributes['aria-selected']
  },
  chartButton: {
    active: chartButton.classList.contains('active'),
    selected: chartButton.attributes['aria-selected']
  },
  entryPaneActive: panes['tab-entry'].classList.contains('active'),
  chartPaneActive: panes['tab-chart'].classList.contains('active')
}));
""")
        self.assertEqual(result, {
            "entryButton": {"active": False, "selected": "false"},
            "chartButton": {"active": True, "selected": "true"},
            "entryPaneActive": False,
            "chartPaneActive": True,
        })

    def test_loading_and_request_failures_are_inline_and_retryable(self):
        for start_marker, end_marker in [
            ("async function fetchQuotes()", "// ── 图表 ──"),
            ("async function loadChart()", "function renderChart(data)"),
            ("async function loadEntries()", "// ── 日期选择器初始化为今天 ──"),
        ]:
            source = self.extract_js(start_marker, end_marker)
            self.assertIn("if (!res.ok) throw new Error(", source)
            self.assertIn("res.status", source)
        inline_error_source = self.extract_js(
            "function showInlineError(containerId, message)",
            "function renderQuotes(cfets, banks, timestamp)",
        )
        self.assertIn("textContent", inline_error_source)
        self.assertIn("replaceChildren", inline_error_source)
        self.assertNotIn("innerHTML", inline_error_source)
        load_entries_source = self.extract_js(
            "async function loadEntries()",
            "// ── 日期选择器初始化为今天 ──",
        )
        for marker in [
            "createDocumentFragment", "createElement",
            "textContent", "replaceChildren",
        ]:
            self.assertIn(marker, load_entries_source)
        self.assertNotIn("innerHTML", load_entries_source)
        load_chart_source = self.extract_js(
            "async function loadChart()",
            "function renderChart(data)",
        )
        self.assertIn("chartInstance.dispose()", load_chart_source)
        self.assertIn("chartInstance = null", load_chart_source)
        self.assertIn(
            "showInlineError('chart', '图表暂时无法获取，请稍后重试')",
            load_chart_source,
        )
        self.assertEqual(self.html.count("renderQuoteSkeleton();"), 1)
        skeleton_call = self.html.index("renderQuoteSkeleton();")
        self.assertLess(skeleton_call, self.html.index("fetchQuotes();", skeleton_call))
        self.assertEqual(self.html.count("setInterval("), 2)
        self.assertNotIn('alert(', self.html)

        if not NODE_BINARY:
            self.skipTest("Node.js is required for dynamic frontend rendering")
        behavior_script = (
            self.extract_js('const PAIRS = ["USDCNY"', "function renderChart(data)")
            + self.extract_js("async function submitEntry()", "async function loadEntries()")
            + load_entries_source
        )
        result = self.run_node_json(self.NODE_DOM_PRELUDE + """
const elements = {
  quotesContainer: new MockNode(),
  updateTime: new MockNode(),
  chart: new MockNode(),
  chartPair: Object.assign(new MockNode('select'), { value: 'USDCNY' }),
  chartBank: Object.assign(new MockNode('select'), { value: '中国银行' }),
  chartDate: Object.assign(new MockNode('input'), { value: '2026-07-13' }),
  entryPair: Object.assign(new MockNode('select'), { value: 'USDCNY' }),
  entryBank: Object.assign(new MockNode('select'), { value: '中国银行' }),
  entryDir: Object.assign(new MockNode('select'), { value: '买入价' }),
  entryQuote: Object.assign(new MockNode('input'), { value: '6.7700' }),
  entryDate: Object.assign(new MockNode('input'), { value: '' }),
  entryTime: Object.assign(new MockNode('input'), { value: '' }),
  entryResult: new MockNode(),
  entryRecent: new MockNode(),
  scratch: new MockNode()
};
const document = {
  getElementById(id) { return elements[id]; },
  createElement(tagName) { return new MockNode(tagName); },
  createDocumentFragment() { return new MockFragment(); }
};
let fetchMode = 'failure';
const fetch = async url => {
  if (fetchMode === 'entries-success' && url.startsWith('/api/entries')) {
    return {
      ok: true,
      status: 200,
      json: async () => ({
        entries: [{
          time: '<time>12:30</time>',
          pair: '<img src=x>',
          bank: '<b>银行</b>',
          direction: '<script>x</script>',
          quote: 6.77,
          bp_vs_market: 12.3
        }]
      })
    };
  }
  if (fetchMode === 'submit-failure' && url.startsWith('/api/entry?')) {
    return {
      ok: false,
      status: 503,
      json: async () => { throw new SyntaxError('Unexpected token < in JSON'); }
    };
  }
  if (fetchMode === 'submit-success' && url.startsWith('/api/entry?')) {
    return {
      ok: true,
      status: 200,
      json: async () => ({
        ok: true,
        market_cost: 6.78,
        bank_bid: 6.76,
        bank_ask: 6.80,
        bp_vs_market: 100,
        bp_vs_bank_price: 100,
        compare_time: '当前实时'
      })
    };
  }
  if (fetchMode === 'submit-success' && url.startsWith('/api/entries')) {
    return { ok: true, status: 200, json: async () => ({ entries: [] }) };
  }
  return { ok: false, status: 503, json: async () => ({}) };
};
const console = { error() {} };
let chartDisposed = false;
let chartInstance = { dispose() { chartDisposed = true; } };
""" + behavior_script + """
let loadEntriesCalls = 0;
const realLoadEntries = loadEntries;
loadEntries = async function() {
  loadEntriesCalls += 1;
  return realLoadEntries();
};
function errorState(container) {
  const error = container.children[0];
  return {
    className: error.className,
    role: error.attributes.role,
    live: error.attributes['aria-live'],
    text: error.textContent,
    innerHTMLWrites: error.innerHTMLWrites,
    replaceChildrenCalls: container.replaceChildrenCalls
  };
}
(async () => {
  renderQuoteSkeleton();
  const skeleton = elements.quotesContainer.innerHTML;
  const skeletonState = {
    rows: (skeleton.match(/class="source-row"/g) || []).length,
    cells: (skeleton.match(/class="quote-cell"/g) || []).length,
    status: skeleton.includes('role="status"'),
    live: skeleton.includes('aria-live="polite"')
  };

  showInlineError('scratch', '<strong>failure</strong>');
  const directError = errorState(elements.scratch);
  await fetchQuotes();
  const quoteError = errorState(elements.quotesContainer);
  await loadChart();
  const chartError = errorState(elements.chart);
  await loadEntries();
  const entriesError = errorState(elements.entryRecent);

  fetchMode = 'entries-success';
  await loadEntries();
  const entry = elements.entryRecent.children[0];
  const main = entry.children[0];
  const meta = entry.children[1];

  const callsBeforeSubmit = loadEntriesCalls;
  fetchMode = 'submit-failure';
  await submitEntry();
  const submitFailureText = elements.entryResult.textContent;
  const callsAfterFailure = loadEntriesCalls;

  fetchMode = 'submit-success';
  await submitEntry();
  await Promise.resolve();
  const submitSuccessHTML = elements.entryResult.innerHTML;
  const callsAfterSuccess = loadEntriesCalls;
  process.stdout.write(JSON.stringify({
    skeletonState,
    directError,
    quoteError,
    chartError,
    chartDisposed,
    chartInstanceIsNull: chartInstance === null,
    entriesError,
    entry: {
      className: entry.className,
      mainClassName: main.className,
      mainText: main.textContent,
      mainTextWrites: main.textContentWrites,
      mainInnerHTMLWrites: main.innerHTMLWrites,
      metaClassName: meta.className,
      metaText: meta.textContent,
      metaTextWrites: meta.textContentWrites,
      metaInnerHTMLWrites: meta.innerHTMLWrites
    },
    submit: {
      failureText: submitFailureText,
      callsBeforeSubmit,
      callsAfterFailure,
      successHTML: submitSuccessHTML,
      callsAfterSuccess
    }
  }));
})().catch(error => {
  process.stderr.write(error.stack + '\\n');
  process.exit(1);
});
""")
        self.assertEqual(result["skeletonState"], {
            "rows": 9, "cells": 36, "status": True, "live": True,
        })
        self.assertEqual(result["directError"], {
            "className": "inline-state inline-error",
            "role": "status",
            "live": "polite",
            "text": "<strong>failure</strong>",
            "innerHTMLWrites": 0,
            "replaceChildrenCalls": 1,
        })
        self.assertEqual(
            result["quoteError"]["text"],
            "报价暂时无法获取，系统将在下一轮自动重试",
        )
        self.assertEqual(
            result["chartError"]["text"],
            "图表暂时无法获取，请稍后重试",
        )
        self.assertTrue(result["chartDisposed"])
        self.assertTrue(result["chartInstanceIsNull"])
        self.assertEqual(
            result["entriesError"]["text"],
            "最近录入暂时无法获取，请稍后重试",
        )
        self.assertEqual(result["entry"]["className"], "recent-entry")
        self.assertEqual(result["entry"]["mainClassName"], "recent-entry-main")
        self.assertEqual(
            result["entry"]["mainText"],
            "<img src=x> · <b>银行</b>",
        )
        self.assertIn("<script>x</script>", result["entry"]["metaText"])
        self.assertGreater(result["entry"]["mainTextWrites"], 0)
        self.assertGreater(result["entry"]["metaTextWrites"], 0)
        self.assertEqual(result["entry"]["mainInnerHTMLWrites"], 0)
        self.assertEqual(result["entry"]["metaInnerHTMLWrites"], 0)
        self.assertEqual(
            result["submit"]["failureText"],
            "提交失败，请稍后重试",
        )
        self.assertNotIn("Unexpected token", result["submit"]["failureText"])
        self.assertEqual(
            result["submit"]["callsAfterFailure"],
            result["submit"]["callsBeforeSubmit"],
        )
        for marker in [
            "比较基准", "市场成本", "你的报价",
            "银行赚取", "与银行牌价比较",
        ]:
            self.assertIn(marker, result["submit"]["successHTML"])
        self.assertEqual(
            result["submit"]["callsAfterSuccess"],
            result["submit"]["callsBeforeSubmit"] + 1,
        )

    def test_matrix_has_no_repeated_midpoint_cost_line(self):
        self.assertNotIn("pair-card .costs", self.html)
        self.assertNotIn("市场' + mc + ' 银行' + bc", self.html)
        self.assertIn("暂无新数据", self.html)
        self.assertIn("上次抓取", self.html)

    @classmethod
    def render_quotes(cls, cfets, banks, timestamp):
        script_start = cls.html.index('const PAIRS = ["USDCNY"')
        script_end = cls.html.index("// ── 获取报价 ──", script_start)
        render_script = cls.html[script_start:script_end]
        harness = f"""
const elements = {{
  quotesContainer: {{ innerHTML: '' }},
  updateTime: {{ textContent: '' }}
}};
const document = {{ getElementById: id => elements[id] }};
{render_script}
renderQuotes(
  {json.dumps(cfets, ensure_ascii=False)},
  {json.dumps(banks, ensure_ascii=False)},
  {json.dumps(timestamp)}
);
process.stdout.write(elements.quotesContainer.innerHTML);
"""
        result = subprocess.run(
            [NODE_BINARY, "-e", harness],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout

    @staticmethod
    def source_row(rendered, source):
        marker = f'data-source="{source}"'
        marker_pos = rendered.index(marker)
        row_start = rendered.rfind('<div class="source-row', 0, marker_pos)
        row_end = rendered.find('<div class="source-row', marker_pos)
        return rendered[row_start:row_end if row_end >= 0 else len(rendered)]

    @unittest.skipUnless(NODE_BINARY, "Node.js is required for dynamic frontend rendering")
    def test_dynamic_matrix_keeps_nine_sources_and_thirty_six_cells(self):
        rendered = self.render_quotes({}, {}, "2026-07-13 12:30:00")

        self.assertEqual(rendered.count('class="source-row'), 9)
        self.assertEqual(rendered.count('class="quote-cell"'), 36)
        self.assertEqual(rendered.count('class="source-time"'), 9)

    @unittest.skipUnless(NODE_BINARY, "Node.js is required for dynamic frontend rendering")
    def test_non_finite_and_partial_quotes_render_truthful_states(self):
        valid = {"bid": 6.76, "ask": 6.79}
        full_bank = {
            pair: {**valid, "source_time": "2026-07-13 12:30:00"}
            for pair in ["USDCNY", "EURCNY", "HKDCNY", "JPYCNY"]
        }
        rendered = self.render_quotes(
            {
                "USDCNY": valid,
                "EURCNY": {"bid": "NaN", "ask": 7.80},
                "HKDCNY": valid,
                "JPYCNY": valid,
            },
            {
                "工商银行": {"USDCNY": {"bid": "Infinity", "ask": 6.80}},
                "招商银行": {"USDCNY": {"bid": 6.75, "ask": "NaN"}},
                "建设银行": {
                    "USDCNY": {
                        **valid,
                        "fetch_time": "2026-07-13 12:30:00",
                    },
                },
                "杭州银行": {
                    "USDCNY": {
                        **valid,
                        "fetch_time": "2026-07-13 12:29:00",
                    },
                },
                "民生银行": full_bank,
            },
            "2026-07-13 12:30:00",
        )

        self.assertNotIn("NaN", rendered)
        self.assertNotIn("Infinity", rendered)
        self.assertIn("部分缺失", self.source_row(rendered, "CFETS"))
        icbc_row = self.source_row(rendered, "工商银行")
        self.assertIn('<small class="source-time">真实报价</small>', icbc_row)
        for bank in ["工商银行", "招商银行"]:
            bank_row = self.source_row(rendered, bank)
            self.assertIn('class="quote-status partial"', bank_row)
            self.assertIn(">部分缺失</div>", bank_row)
            self.assertNotIn("暂无新数据", bank_row)
        self.assertIn(
            '<small class="source-time">本轮抓取 12:30</small>',
            self.source_row(rendered, "建设银行"),
        )
        self.assertIn(
            '<small class="source-time">上次抓取 12:29</small>',
            self.source_row(rendered, "杭州银行"),
        )
        abc_row = self.source_row(rendered, "农业银行")
        self.assertIn('<small class="source-time">等待数据</small>', abc_row)
        self.assertIn('class="quote-status missing"', abc_row)
        self.assertIn(">暂无新数据</div>", abc_row)
        minsheng_row = self.source_row(rendered, "民生银行")
        self.assertIn('<small class="source-time">源 12:30</small>', minsheng_row)
        self.assertIn(">正常</div>", minsheng_row)
        self.assertIn(
            'aria-label="工商银行 USDCNY 买入 --，卖出 6.8000"',
            rendered,
        )
        self.assertIn(
            'aria-label="招商银行 USDCNY 买入 6.7500，卖出 --"',
            rendered,
        )

    def test_source_column_stays_visible_during_horizontal_scroll(self):
        self.assertIn("overflow:visible", self.html)
        self.assertIn("position:sticky", self.html)
        self.assertIn(".source-row .source-name", self.html)
        self.assertIn(".source-row.cfets .source-name", self.html)
        self.assertIn(".source-row:hover .source-name", self.html)
        self.assertIn("z-index:3", self.html)
        self.assertIn("z-index:2", self.html)

    def test_matrix_has_accessible_table_semantics(self):
        self.assertIn('role="table"', self.html)
        self.assertIn('aria-label="外汇买入卖出报价矩阵"', self.html)
        self.assertIn('role="columnheader"', self.html)
        self.assertIn('role="rowheader"', self.html)
        self.assertIn('role="cell"', self.html)
        self.assertIn("买入 ' + bid + '，卖出 ' + ask", self.html)


if __name__ == "__main__":
    unittest.main()
