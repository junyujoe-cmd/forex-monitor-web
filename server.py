import os
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.background import BackgroundScheduler

from database import Database
from fetcher import fetch_all_quotes
from bank_fetcher import (
    fetch_abc_rates,
    fetch_boc_history,
    fetch_boc_rates,
    fetch_ccb_rates,
    fetch_cmb_rates,
    fetch_cmbc_rates,
    fetch_hzb_rates,
    fetch_icbc_rates,
    fetch_psbc_rates,
)
from config import BANKS, CURRENCY_PAIRS, DB_PATH

# ── 初始化数据库 ──────────────────────────────────────────
db = Database()

# ── 内存缓存（最新一轮报价 + 银行牌价缓存） ─────────────────
cfets_cache: dict = {}
bank_cache: dict = {}
last_boc_rates: dict = {}   # 最近一次成功的银行牌价，抓取失败时作为后备
last_cmb_rates: dict = {}
last_ccb_rates: dict = {}
last_update: str = ""
CURRENT_ONLY_BANKS = ("杭州银行", "工商银行", "农业银行", "邮储银行", "民生银行")


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


def fetch_and_save():
    """定时抓取任务（和原来 main_window.py 逻辑一致）"""
    global cfets_cache, bank_cache, last_boc_rates, last_cmb_rates, last_ccb_rates, last_update

    cycle_id = datetime.now().isoformat()
    quotes = fetch_all_quotes() or {}
    current_rates = _fetch_all_bank_rates()
    if not quotes:
        for bank in CURRENT_ONLY_BANKS:
            bank_cache.pop(bank, None)
        return

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
    try:
        db.save_market_quotes_batch(cycle_id, quotes, "CFETS")
        if bank_data:
            db.save_bank_quotes_batch(cycle_id, bank_data)
    except Exception:
        for bank in CURRENT_ONLY_BANKS:
            bank_cache.pop(bank, None)
        raise

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
    from fastapi.responses import Response
    content = (STATIC / "index.html").read_bytes()
    return Response(content=content, media_type="text/html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})


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


@app.get("/api/history")
async def get_history(
    pair: str = Query("USDCNY"),
    banks: str = Query("中国银行,杭州银行"),
    hours: int = Query(24),
    start: str = Query(None),
    end: str = Query(None),
):
    """返回 CFETS 中间价和最多两家银行的买入、卖出曲线。"""
    if pair not in CURRENCY_PAIRS:
        return {"ok": False, "error": "不支持该货币对"}

    selected_banks = [name for name in banks.split(",") if name in BANKS][:2]
    try:
        end_dt = datetime.fromisoformat(end) if end else datetime.now()
        start_dt = datetime.fromisoformat(start) if start else end_dt - timedelta(hours=max(1, hours))
    except ValueError:
        return {"ok": False, "error": "历史时间格式不正确"}
    if start_dt >= end_dt:
        return {"ok": False, "error": "开始时间必须早于结束时间"}

    data = db.get_history_series(
        pair,
        selected_banks,
        start_dt.isoformat(),
        end_dt.isoformat(),
    )
    return {
        "ok": True,
        "pair": pair,
        "start": start_dt.isoformat(),
        "end": end_dt.isoformat(),
        **data,
    }


@app.post("/api/entry")
async def save_entry(
    pair: str = Query(...),
    bank: str = Query(...),
    direction: str = Query(...),
    quote: float = Query(...),
    time: str = Query(None, description="比较时间点，格式 YYYY-MM-DDTHH:MM，为空则用当前实时报价"),
):
    """录入报价，支持指定历史时间点比价"""
    if time:
        hist = db.get_quotes_at_time(pair, bank, time)
        if not hist:
            return {"ok": False, "error": f"未找到 {time} 之前的报价数据，请换个时间"}
        market_cost = (
            hist.get("market_bid") if direction == "买入价"
            else hist.get("market_ask")
        )
        if market_cost is None:
            return {"ok": False, "error": f"{time} 附近报价缺少方向化市场价"}
        bank_bid = hist["bank_bid"]
        bank_ask = hist["bank_ask"]
        market_timestamp = hist.get("market_timestamp") or hist.get("timestamp")
        bank_timestamp = hist.get("bank_timestamp", market_timestamp)
        market_compare_time = market_timestamp[:16]
        bank_compare_time = bank_timestamp[:16] if bank_timestamp else None
        compare_time = market_compare_time
    else:
        market = cfets_cache.get(pair, {})
        market_cost = (
            market.get("bid") if direction == "买入价"
            else market.get("ask")
        )
        if not market_cost:
            return {"ok": False, "error": "暂无市场数据，请等待报价刷新"}
        bq = bank_cache.get(bank, {}).get(pair, {})
        bank_bid = bq.get("bid") if bq else None
        bank_ask = bq.get("ask") if bq else None
        compare_time = "当前实时"
        market_compare_time = compare_time
        bank_compare_time = compare_time

    if bank_bid is None or bank_ask is None:
        return {
            "ok": False,
            "error": f"{bank} {pair} 暂无真实银行报价，请等待下一次更新",
        }

    if direction == "买入价":
        bank_cost = bank_bid
        bp_vs_market = round((market_cost - quote) * 10000, 1)
        bp_vs_bank_price = round((quote - bank_bid) * 10000, 1)
    else:
        bank_cost = bank_ask
        bp_vs_market = round((quote - market_cost) * 10000, 1)
        bp_vs_bank_price = round((bank_ask - quote) * 10000, 1)

    db.save_user_entry(
        pair=pair, bank=bank, direction=direction,
        user_quote=quote,
        market_cost=market_cost,
        bank_cost=bank_cost,
        bp_vs_market=bp_vs_market,
        bp_vs_bank=bp_vs_bank_price,
    )

    return {
        "ok": True,
        "bp_vs_market": bp_vs_market,
        "bp_vs_bank_price": bp_vs_bank_price,
        "market_cost": market_cost,
        "bank_bid": bank_bid,
        "bank_ask": bank_ask,
        "compare_time": compare_time,
        "market_compare_time": market_compare_time,
        "bank_compare_time": bank_compare_time,
    }


@app.get("/api/target_quote")
async def target_quote(
    pair: str = Query(...),
    bank: str = Query(...),
    direction: str = Query(...),
    target_bp: float = Query(...),
):
    """按拟定赚取点数反算银行应报价，并对比该银行当前牌价的优惠 bp（只计算，不保存）"""
    market = cfets_cache.get(pair, {})
    market_bid = market.get("bid")
    market_ask = market.get("ask")
    if not market_bid or not market_ask:
        return {"ok": False, "error": "暂无 CFETS 买卖价，请等待报价刷新"}
    bq = bank_cache.get(bank, {}).get(pair, {})
    bank_bid = bq.get("bid") if bq else None
    bank_ask = bq.get("ask") if bq else None
    if bank_bid is None or bank_ask is None:
        return {"ok": False, "error": f"{bank} {pair} 暂无真实银行报价，请等待下一次更新"}

    offset = target_bp / 10000
    if direction == "买入价":
        target_price = round(market_bid - offset, 4)
        bp_vs_bank_price = round((target_price - bank_bid) * 10000, 1)
    else:
        target_price = round(market_ask + offset, 4)
        bp_vs_bank_price = round((bank_ask - target_price) * 10000, 1)

    return {
        "ok": True,
        "target_price": target_price,
        "bank_bid": bank_bid,
        "bank_ask": bank_ask,
        "bp_vs_bank_price": bp_vs_bank_price,
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
