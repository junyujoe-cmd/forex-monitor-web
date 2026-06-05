CURRENCY_PAIRS = ["USDCNY", "EURCNY", "HKDCNY", "JPYCNY"]

BANKS = ["中国银行", "招商银行", "建设银行"]

BANK_SPREADS = {
    "中国银行": {"bid_offset": -0.0020, "ask_offset": 0.0020},
    "招商银行": {"bid_offset": -0.0015, "ask_offset": 0.0015},
    "建设银行": {"bid_offset": -0.0020, "ask_offset": 0.0020},
}

API_URLS = {
    "exchangerate-api": "https://api.exchangerate-api.com/v4/latest/USD",
    "openexchangerates": "https://open.er-api.com/v6/latest/USD",
}

FETCH_INTERVAL_SECONDS = 60

# 数据库文件存放在 data/ 子目录，与 Docker 卷挂载 /app/data 相匹配
DB_PATH = "data/forex_data.db"
