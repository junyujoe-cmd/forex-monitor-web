import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.background import BackgroundScheduler

from database import Database
from fetcher import fetch_all_quotes
from bank_fetcher import fetch_boc_rates, fetch_cmb_rates, fetch_boc_history
from config import BANK_SPREADS, CURRENCY_PAIRS, DB_PATH

# ── 初始化数据库 ──────────────────────────────────────────
db = Database()

# ── 内存缓存（最新一轮报价 + 银行牌价缓存） ─────────────────
cfets_cache: dict = {}
bank_cache: dict = {}
last_boc_rates: dict = {}   # 最近一次成功的银行牌价，抓取失败时作为后备
last_cmb_rates: dict = {}
last_update: str = ""


def fetch_and_save():
    """定时抓取任务（和原来 main_window.py 逻辑一致）"""
    global cfets_cache, bank_cache, last_boc_rates, last_cmb_rates, last_update

    cycle_id = datetime.now().isoformat()
    quotes = fetch_all_quotes() or {}
    boc_rates = fetch_boc_rates() or {}
    cmb_rates = fetch_cmb_rates() or {}
    if not quotes:
        return

    db.save_market_quotes_batch(cycle_id, quotes, "CFETS")

    # 更新银行牌价缓存（供实时报价展示用，本次成功才替换）
    if boc_rates:
        last_boc_rates = dict(boc_rates)
    if cmb_rates:
        last_cmb_rates = dict(cmb_rates)

    # 保存银行报价到数据库：只用真实数据，无数据时不保存
    bank_data = []
    for pair, data in quotes.items():
        for bank in BANK_SPREADS:
            if bank == "中国银行" and boc_rates and pair in boc_rates:
                r = boc_rates[pair]
                bank_data.append((bank, pair, r["bid"], r["ask"]))
            elif bank == "招商银行" and cmb_rates and pair in cmb_rates:
                r = cmb_rates[pair]
                bank_data.append((bank, pair, r["bid"], r["ask"]))
    if bank_data:
        db.save_bank_quotes_batch(cycle_id, bank_data)

    # 构建银行报价缓存（实时报价用，可缓存上次成功值）
    bank_quotes_full: dict = {}
    for bank, rates in [("中国银行", boc_rates or last_boc_rates), ("招商银行", cmb_rates or last_cmb_rates)]:
        if rates:
            bank_quotes_full[bank] = {}
            for pair, r in rates.items():
                bank_quotes_full[bank][pair] = r

    cfets_cache.clear()
    cfets_cache.update(quotes)
    bank_cache.clear()
    bank_cache.update(bank_quotes_full)
    last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ── 调度器 ────────────────────────────────────────────────
scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(fetch_and_save, "interval", seconds=60, id="fetch_60s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 确保 data 目录存在（数据库文件存放位置）
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)

    scheduler.start()
    # 启动时立即抓取一次
    fetch_and_save()

    # 后台异步导入中行历史数据（不阻塞启动）
    def _backfill_boc_history():
        if not db.has_boc_history():
            print("开始导入中行历史数据...")
            try:
                hist = fetch_boc_history(days=30)
                if hist:
                    db.save_boc_history(hist)
                    print(f"✅ 已导入 {len(hist)} 条中行历史数据")
                else:
                    print("⚠️ 中行历史数据导入返回为空")
            except Exception as e:
                print(f"❌ 中行历史数据导入失败: {e}")

    import threading
    threading.Thread(target=_backfill_boc_history, daemon=True).start()

    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="实时外汇监控系统", lifespan=lifespan)

# ── 静态文件 ──────────────────────────────────────────────
HERE = Path(__file__).parent
STATIC = HERE / "static"
STATIC.mkdir(exist_ok=True)


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")

# ── API ───────────────────────────────────────────────────


@app.get("/api/quotes")
async def get_quotes():
    """返回最新一轮报价"""
    return {
        "cfets": cfets_cache,
        "banks": bank_cache,
        "timestamp": last_update,
    }


@app.get("/api/chart")
async def get_chart(
    pair: str = Query("USDCNY"),
    bank: str = Query("中国银行"),
    date: str = Query(None, description="日期，格式 YYYY-MM-DD，默认今天"),
):
    """返回图表数据，支持指定日期"""
    date_str = date or datetime.now().strftime("%Y-%m-%d")
    rows = db.get_chart_data(pair, bank, date_str=date_str)
    if not rows:
        return {"times": [], "bids": [], "asks": [], "mids": [], "costs": [], "sources": []}

    times = []
    bids = []
    asks = []
    mids = []
    costs = []
    sources = []

    for r in rows:
        ts = r[0][11:16]  # "HH:MM"
        mid = float(r[1])
        bid = float(r[2]) if r[2] is not None else None
        ask = float(r[3]) if r[3] is not None else None
        cost = round((bid + ask) / 2, 4) if bid is not None and ask is not None else None
        src = r[4] if len(r) > 4 else "实时"

        times.append(ts)
        mids.append(mid)
        bids.append(bid)
        asks.append(ask)
        costs.append(cost)
        sources.append(src)

    return {
        "times": times,
        "bids": bids,
        "asks": asks,
        "mids": mids,
        "costs": costs,
        "sources": sources,
    }


@app.post("/api/entry")
async def save_entry(
    pair: str = Query(...),
    bank: str = Query(...),
    direction: str = Query(...),
    quote: float = Query(...),
):
    """录入报价"""
    market = cfets_cache.get(pair, {})
    market_mid = market.get("mid", 0)
    if not market_mid:
        return {"ok": False, "error": "暂无市场数据，请等待报价刷新"}

    # 优先使用真实银行牌价，回退到计算值
    bq = bank_cache.get(bank, {}).get(pair, {})
    bank_bid = bq.get("bid") if bq else None
    bank_ask = bq.get("ask") if bq else None
    if bank_bid is None or bank_ask is None:
        spread = BANK_SPREADS.get(bank, {"bid_offset": 0, "ask_offset": 0})
        bank_bid = round(market_mid + spread["bid_offset"], 4)
        bank_ask = round(market_mid + spread["ask_offset"], 4)

    bank_cost = round((bank_bid + bank_ask) / 2, 4)
    market_cost = market_mid

    if direction == "买入价":
        bp_vs_market = round((market_cost - quote) * 10000, 1)
        bp_vs_bank = round((bank_cost - quote) * 10000, 1)
        bp_vs_bank_price = round((quote - bank_bid) * 10000, 1)
    else:
        bp_vs_market = round((quote - market_cost) * 10000, 1)
        bp_vs_bank = round((quote - bank_cost) * 10000, 1)
        bp_vs_bank_price = round((bank_ask - quote) * 10000, 1)

    db.save_user_entry(
        pair=pair, bank=bank, direction=direction,
        user_quote=quote,
        market_cost=market_cost,
        bank_cost=bank_cost,
        bp_vs_market=bp_vs_market,
        bp_vs_bank=bp_vs_bank,
    )

    return {
        "ok": True,
        "bp_vs_market": bp_vs_market,
        "bp_vs_bank": bp_vs_bank,
        "bp_vs_bank_price": bp_vs_bank_price,
        "market_cost": market_cost,
        "bank_cost": bank_cost,
        "bank_bid": bank_bid,
        "bank_ask": bank_ask,
    }


@app.get("/api/chart_dates")
async def get_chart_dates():
    """返回有数据可查的日期列表"""
    rows = db.get_available_dates()
    return {"dates": rows}


@app.get("/api/entries")
async def get_entries(limit: int = Query(20)):
    """最近录入记录"""
    rows = db.get_recent_user_entries(limit)
    return {
        "entries": [
            {
                "time": r[0][11:16],
                "pair": r[1],
                "bank": r[2],
                "direction": r[3],
                "quote": r[4],
                "bp_vs_market": r[7],
                "bp_vs_bank": r[8],
            }
            for r in rows
        ]
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
