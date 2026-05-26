"""
一次性导入脚本：将 外汇数据抓取 项目中的 BOC/CFETS CSV 数据导入现有 SQLite 数据库。
"""
import sys, os, csv, sqlite3
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH

# 外汇数据抓取目录（可从命令行覆盖）
DATA_DIR = os.environ.get("HIST_DATA_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "historical"))

# BOC→CFETS 反推偏移（已验证，单位：价格点）
OFFSETS = {"美元": 0.0025, "欧元": 0.0015, "日元": -0.0001, "港币": 0.0}

# 货币名 → 货币对
PAIR_MAP = {"美元": "USDCNY", "欧元": "EURCNY", "日元": "JPYCNY", "港币": "HKDCNY"}

# 需要 ÷100 的货币（日元已是 /100JPY 单位）
DIV100 = {"美元", "欧元", "港币"}


def iso_ts(csv_dt: str) -> str:
    """把 CSV 的 2026/05/18 23:59:53 转为 2026-05-18T23:59:53"""
    return csv_dt.replace("/", "-").replace(" ", "T")


def main():
    conn = sqlite3.connect(DB_PATH)
    inserted_bank = 0
    inserted_market = 0

    # ── 1. 遍历所有 BOC CSV ──
    for fname in sorted(os.listdir(DATA_DIR)):
        if not fname.startswith("boc_") or not fname.endswith(".csv"):
            continue
        fpath = os.path.join(DATA_DIR, fname)
        currency = fname.split("_")[1]  # "美元"
        pair = PAIR_MAP.get(currency)
        div = 100 if currency in DIV100 else 1
        offset = OFFSETS.get(currency, 0.0)

        with open(fpath, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    buy = float(row["buy_remittance"]) / div
                    sell = float(row["sell_remittance"]) / div
                    ts = iso_ts(row["publish_datetime"])
                    fc = f"hist_{ts}"  # fetch_cycle
                except (ValueError, KeyError):
                    continue

                # 跳过当天数据（已有实时数据）
                if ts.startswith(datetime.now().strftime("%Y-%m-%d")):
                    continue

                # bank_quotes
                conn.execute(
                    "INSERT INTO bank_quotes (fetch_cycle, timestamp, bank, pair, bid, ask) VALUES (?, ?, ?, ?, ?, ?)",
                    (fc, ts, "中国银行", pair, round(buy, 4), round(sell, 4)),
                )
                inserted_bank += 1

                # market_quotes: 推导 CFETS
                boc_mid = (buy + sell) / 2
                cfets = boc_mid - offset
                conn.execute(
                    "INSERT INTO market_quotes (fetch_cycle, timestamp, pair, bid, ask, mid, source) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (fc, ts, pair, None, None, round(cfets, 4), "推导"),
                )
                inserted_market += 1

    # ── 2. 导入精确 CFETS 小时数据 ──
    cfets_path = os.path.join(DATA_DIR, "cfets_hourly.csv")
    if os.path.exists(cfets_path):
        hour_cols = [f"{h}:00" for h in [10, 11, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23]]
        with open(cfets_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                date_str = row["date"]  # "2026-05-26"
                raw_pair = row["currency"]  # "USD/CNY"
                # 转成我们的货币对名
                pair_map_cfets = {"USD/CNY": "USDCNY", "EUR/CNY": "EURCNY",
                                  "100JPY/CNY": "JPYCNY", "HKD/CNY": "HKDCNY"}
                pair = pair_map_cfets.get(raw_pair)
                if not pair:
                    continue

                for hc in hour_cols:
                    v = row.get(hc, "").strip()
                    if not v or v in ("", "---", "/"):
                        continue
                    try:
                        cfets_val = round(float(v), 4)
                        h = int(hc.split(":")[0])
                        ts = f"{date_str}T{h:02d}:00:00"
                        fc = f"hist_cfets_{ts}"
                    except (ValueError, KeyError):
                        continue

                    # 跳过当天（已有实时数据）
                    if ts.startswith(datetime.now().strftime("%Y-%m-%d")):
                        continue

                    # 检查该时间点是否已有推导的 market_quotes
                    existing = conn.execute(
                        "SELECT id FROM market_quotes WHERE pair = ? AND timestamp = ? AND source = '推导' LIMIT 1",
                        (pair, ts),
                    ).fetchone()

                    if existing:
                        # 更新为精确值
                        conn.execute(
                            "UPDATE market_quotes SET mid = ?, source = '精确' WHERE id = ?",
                            (cfets_val, existing[0]),
                        )
                    else:
                        # 插入新行
                        conn.execute(
                            "INSERT INTO market_quotes (fetch_cycle, timestamp, pair, bid, ask, mid, source) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (fc, ts, pair, None, None, cfets_val, "精确"),
                        )

    conn.commit()
    conn.close()
    print(f"✅ 导入完成: bank_quotes {inserted_bank} 条, market_quotes {inserted_market} 条")


if __name__ == "__main__":
    main()
