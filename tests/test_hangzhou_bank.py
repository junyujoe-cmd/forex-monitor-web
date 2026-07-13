import tempfile
import unittest
from datetime import datetime, time, timedelta
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
        self.assertEqual(
            mock_get.call_args.args[0],
            "https://www.hzbank.com.cn/hzyh/gjyw/bjfw24/whpj/index.html",
        )

    @patch("bank_fetcher.requests.get")
    def test_http_error_returns_none(self, mock_get):
        source_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        response = Mock(text=official_html(source_time))
        response.raise_for_status.side_effect = requests.HTTPError("403")
        mock_get.return_value = response

        self.assertIsNone(fetch_hzb_rates())
        response.raise_for_status.assert_called_once_with()

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
        if hasattr(server, "last_hzb_rates"):
            server.last_hzb_rates.clear()
            server.last_hzb_rates["USDCNY"] = {"bid": 9, "ask": 10, "mid": 9.5}
        market = {"USDCNY": {"bid": 6.78, "ask": 6.79, "mid": 6.785}}
        fake_db = Mock()

        with (
            patch.object(server, "db", fake_db),
            patch.object(server, "fetch_all_quotes", return_value=market),
            patch.object(server, "fetch_boc_rates", return_value=None),
            patch.object(server, "fetch_cmb_rates", return_value=None),
            patch.object(server, "fetch_ccb_rates", return_value=None),
            patch.object(server, "fetch_hzb_rates", return_value=None),
        ):
            server.fetch_and_save()

        self.assertNotIn("杭州银行", server.bank_cache)

    def test_saved_hangzhou_quotes_are_returned_by_chart_query(self):
        now = datetime.now()
        chart_date = now - timedelta(days=1) if now.time() < time(9, 30) else now
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(str(Path(tmp) / "quotes.db"))
            cycle = now.isoformat()
            db.save_market_quotes_batch(
                cycle,
                {"USDCNY": {"bid": 6.78, "ask": 6.79, "mid": 6.785}},
                "CFETS",
            )
            db.save_bank_quotes_batch(cycle, [("杭州银行", "USDCNY", 6.77, 6.80)])
            rows = db.get_chart_data(
                "USDCNY",
                "杭州银行",
                date_str=chart_date.strftime("%Y-%m-%d"),
            )

        self.assertTrue(any(row[2] == 6.77 and row[3] == 6.80 for row in rows))

    def test_frontend_has_no_synthetic_bank_price_fallback(self):
        html = (Path(__file__).parents[1] / "static" / "index.html").read_text()

        self.assertNotIn("md + sp.bid_offset", html)
        self.assertNotIn("md + sp.ask_offset", html)


if __name__ == "__main__":
    unittest.main()
