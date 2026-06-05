import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import akshare as ak
import xml.etree.ElementTree as ET


def fetch_boc_rates():
    """从中国银行官网抓取实时外汇牌价（含重试）"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
        "Referer": "https://www.boc.cn/",
    }
    for attempt in range(3):
        try:
            resp = requests.get("https://www.boc.cn/sourcedb/whpj/", headers=headers, timeout=30)
            resp.encoding = "utf-8"
            soup = BeautifulSoup(resp.text, "html.parser")
            table = soup.find("table", {"id": "priceTable"})
            if not table:
                if attempt < 2:
                    time.sleep(3)
                    continue
                return None

            name_map = {
                "美元": "USDCNY",
                "港币": "HKDCNY",
                "欧元": "EURCNY",
                "日元": "JPYCNY",
            }

            result = {}
            for row in table.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) >= 6:
                    name = cells[0].text.strip()
                    if name in name_map:
                        buy_str = cells[1].text.strip()
                        sell_str = cells[3].text.strip()
                        mid_str = cells[5].text.strip()
                        if buy_str and sell_str and mid_str:
                            pair = name_map[name]
                            buy_per_100 = float(buy_str)
                            sell_per_100 = float(sell_str)
                            mid_per_100 = float(mid_str)
                            div = 1 if pair == "JPYCNY" else 100
                            result[pair] = {
                                "bid": round(buy_per_100 / div, 4),
                                "ask": round(sell_per_100 / div, 4),
                                "mid": round(mid_per_100 / div, 4),
                            }
            if result:
                return result
        except Exception as e:
            print(f"BOC fetch attempt {attempt + 1} error: {e}")
            if attempt < 2:
                time.sleep(3)
                continue
    return None


def fetch_cmb_rates():
    """从招商银行API获取实时外汇牌价"""
    try:
        url = "https://fx.cmbchina.com/api/v1/fx/rate"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Referer": "https://fx.cmbchina.com/",
        }
        resp = requests.get(url, headers=headers, timeout=8)
        data = resp.json()
        if data.get("returnCode") != "SUC0000":
            return None

        name_map = {
            "美元": "USDCNY",
            "港币": "HKDCNY",
            "欧元": "EURCNY",
            "日元": "JPYCNY",
        }

        result = {}
        for item in data.get("body", []):
            name = item.get("ccyNbr", "")
            if name in name_map:
                buy_str = item.get("rthBid", "") or item.get("rtcBid", "")
                sell_str = item.get("rthOfr", "")
                if buy_str and sell_str:
                    pair = name_map[name]
                    div = 1 if pair == "JPYCNY" else 100
                    buy_val = float(buy_str) / div
                    sell_val = float(sell_str) / div
                    result[pair] = {
                        "bid": round(buy_val, 4),
                        "ask": round(sell_val, 4),
                        "mid": round((buy_val + sell_val) / 2, 4),
                    }
        return result if result else None
    except Exception as e:
        print(f"CMB fetch error: {e}")
        return None


BOC_NAME_MAP = {"美元": "USDCNY", "港币": "HKDCNY", "欧元": "EURCNY", "日元": "JPYCNY"}


def fetch_boc_history(days=30):
    """从 akshare 获取中行历史牌价 (daily)"""
    today = datetime.now()
    start = today - timedelta(days=days)
    result = []
    for symbol, pair in BOC_NAME_MAP.items():
        try:
            df = ak.currency_boc_sina(
                symbol=symbol,
                start_date=start.strftime("%Y%m%d"),
                end_date=today.strftime("%Y%m%d"),
            )
            for _, row in df.iterrows():
                date_str = row["日期"]
                buy = float(row["中行汇买价"])
                sell = float(row["中行钞卖价/汇卖价"])
                mid_val = row["央行中间价"]
                if pd.isna(mid_val):
                    mid_val = row["中行折算价"]
                mid_val = float(mid_val)
                result.append({
                    "pair": pair,
                    "date": date_str,
                    "bid": round(buy / (1 if pair == "JPYCNY" else 100), 4),
                    "ask": round(sell / (1 if pair == "JPYCNY" else 100), 4),
                    "mid": round(mid_val / (1 if pair == "JPYCNY" else 100), 4),
                })
        except Exception as e:
            print(f"BOC history error for {symbol}: {e}")
    return result


# ── 建设银行 XML 接口 ──────────────────────────────────────────

CCB_CURRENCY_MAP = {
    "840": "USDCNY",
    "978": "EURCNY",
    "392": "JPYCNY",
    "344": "HKDCNY",
}


def fetch_ccb_rates():
    """从建设银行 XML 接口获取实时外汇牌价"""
    try:
        resp = requests.get(
            "http://forex.ccb.com/cn/home/news/jshckpj_new.xml",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        resp.encoding = "utf-8"
        root = ET.fromstring(resp.text)
        result = {}
        for item in root.findall("ReferencePriceSettlement"):
            ccy = item.findtext("Ofrd_Ccy_CcyCd") or item.findtext("Ofr_Ccy_CcyCd")
            if ccy not in CCB_CURRENCY_MAP:
                continue
            pair = CCB_CURRENCY_MAP[ccy]
            bid_str = item.findtext("BidRateOfCcy")
            ask_str = item.findtext("OfrRateOfCcy")
            mid_str = item.findtext("Mdl_ExRt_Prc")
            if not bid_str or not ask_str:
                continue
            bid_val = float(bid_str)
            ask_val = float(ask_str)
            mid_val = float(mid_str) if mid_str else round((bid_val + ask_val) / 2, 8)
            if pair == "JPYCNY":
                bid_val *= 100
                ask_val *= 100
                mid_val *= 100
            result[pair] = {
                "bid": round(bid_val, 4),
                "ask": round(ask_val, 4),
                "mid": round(mid_val, 4),
            }
        return result if result else None
    except Exception as e:
        print(f"CCB fetch error: {e}")
        return None


# ── 杭州银行 HTML 页面 ──────────────────────────────────────────

HZB_NAME_MAP = {
    "美元USD": "USDCNY",
    "欧元EUR": "EURCNY",
    "日元JPY": "JPYCNY",
    "港币HKD": "HKDCNY",
}


def fetch_hzb_rates():
    """从杭州银行官网抓取实时外汇牌价"""
    try:
        resp = requests.get(
            "https://www.hccb.com.cn/hzyh/gjyw/bjfw24/whpj/index.html",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
            verify=False,
        )
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")
        result = {}
        for tr in soup.find_all("tr"):
            cells = tr.find_all("td")
            if len(cells) < 3:
                continue
            name = cells[0].text.strip()
            if name not in HZB_NAME_MAP:
                continue
            pair = HZB_NAME_MAP[name]
            bid_str = cells[1].text.strip()
            ask_str = cells[3].text.strip()  # 现汇现钞卖出价
            if not bid_str or not ask_str:
                continue
            bid_per_100 = float(bid_str)
            ask_per_100 = float(ask_str)
            div = 1 if pair == "JPYCNY" else 100
            bid_val = round(bid_per_100 / div, 4)
            ask_val = round(ask_per_100 / div, 4)
            result[pair] = {
                "bid": bid_val,
                "ask": ask_val,
                "mid": round((bid_val + ask_val) / 2, 4),
            }
        return result if result else None
    except Exception as e:
        print(f"HZB fetch error: {e}")
        return None
