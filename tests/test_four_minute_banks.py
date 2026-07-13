import json
import ssl
import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import requests

import bank_fetcher


def current_time():
    return datetime.now().replace(microsecond=0)


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


if __name__ == "__main__":
    unittest.main()
