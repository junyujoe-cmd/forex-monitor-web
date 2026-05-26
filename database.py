import os
import sqlite3
from datetime import datetime, timedelta
from config import DB_PATH


class Database:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        # 确保数据库所在目录存在
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._init_tables()
        self._clean_dirty_data()

    def _clean_dirty_data(self):
        conn = self._get_conn()
        # 清理无效数据：NULL、NaN（SQLite 中 NaN != NaN）、或过小的值
        conn.execute("DELETE FROM market_quotes WHERE mid IS NULL OR mid < 0.01 OR NOT (mid = mid)")
        # 注意：不再删除 boc_hist_ 数据，确保中行历史数据持久保留
        conn.execute("DELETE FROM bank_quotes WHERE bid IS NULL OR ask IS NULL OR NOT (bid = bid) OR NOT (ask = ask)")
        conn.commit()
        conn.close()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_tables(self):
        conn = self._get_conn()
        c = conn.cursor()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS market_quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fetch_cycle TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                pair TEXT NOT NULL,
                bid REAL,
                ask REAL,
                mid REAL,
                source TEXT
            );
            CREATE TABLE IF NOT EXISTS bank_quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fetch_cycle TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                bank TEXT NOT NULL,
                pair TEXT NOT NULL,
                bid REAL,
                ask REAL
            );
            CREATE TABLE IF NOT EXISTS user_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                pair TEXT NOT NULL,
                bank TEXT NOT NULL,
                direction TEXT NOT NULL,
                user_quote REAL,
                market_cost REAL,
                bank_cost REAL,
                bp_vs_market REAL,
                bp_vs_bank REAL
            );
        """)
        conn.commit()
        conn.close()

    def save_market_quotes_batch(self, fetch_cycle, quotes_dict, source):
        """保存一轮抓取的所有市场报价（同一 fetch_cycle）"""
        now = datetime.now().isoformat()
        conn = self._get_conn()
        for pair, data in quotes_dict.items():
            conn.execute(
                "INSERT INTO market_quotes (fetch_cycle, timestamp, pair, bid, ask, mid, source) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (fetch_cycle, now, pair, data.get("bid"), data.get("ask"), data["mid"], source),
            )
        conn.commit()
        conn.close()

    def save_bank_quotes_batch(self, fetch_cycle, bank_quotes_list):
        now = datetime.now().isoformat()
        conn = self._get_conn()
        for bank, pair, bid, ask in bank_quotes_list:
            conn.execute(
                "INSERT INTO bank_quotes (fetch_cycle, timestamp, bank, pair, bid, ask) VALUES (?, ?, ?, ?, ?, ?)",
                (fetch_cycle, now, bank, pair, bid, ask),
            )
        conn.commit()
        conn.close()

    def save_boc_history(self, history_data):
        conn = self._get_conn()
        for item in history_data:
            exists = conn.execute(
                "SELECT 1 FROM bank_quotes WHERE fetch_cycle = ? AND bank = '中国银行' AND pair = ?",
                (f"boc_hist_{item['date']}", item['pair']),
            ).fetchone()
            if exists:
                continue
            ts = f"{item['date']}T09:00:00"
            conn.execute(
                "INSERT INTO bank_quotes (fetch_cycle, timestamp, bank, pair, bid, ask) VALUES (?, ?, ?, ?, ?, ?)",
                (f"boc_hist_{item['date']}", ts, "中国银行", item['pair'], item['bid'], item['ask']),
            )
            conn.execute(
                "INSERT INTO market_quotes (fetch_cycle, timestamp, pair, bid, ask, mid, source) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (f"boc_hist_{item['date']}", ts, item['pair'], None, None, item['mid'], "BOC"),
            )
        conn.commit()
        conn.close()

    def has_boc_history(self):
        conn = self._get_conn()
        row = conn.execute("SELECT 1 FROM bank_quotes WHERE fetch_cycle LIKE 'boc_hist_%' LIMIT 1").fetchone()
        conn.close()
        return row is not None

    def get_chart_data(self, pair, bank, limit=1440, date_str=None):
        """获取图表数据，默认查今天，可指定日期"""
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
        conn = self._get_conn()
        # 统一时间轴：当天 09:30 → 次日 09:29
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        next_day = (dt + timedelta(days=1)).strftime("%Y-%m-%d")
        time_start = f"{date_str}T09:30:00"
        time_end = f"{next_day}T09:29:59"
        rows = conn.execute("""
            SELECT m.timestamp, m.mid, b.bid, b.ask, COALESCE(m.source, '实时')
            FROM market_quotes m
            LEFT JOIN bank_quotes b ON m.fetch_cycle = b.fetch_cycle AND b.pair = m.pair AND b.bank = ?
            WHERE m.pair = ? AND m.timestamp >= ? AND m.timestamp <= ?
            ORDER BY m.timestamp ASC LIMIT ?
        """, (bank, pair, time_start, time_end, limit)).fetchall()
        if not rows:
            rows = conn.execute("""
                SELECT timestamp, bid, ask, '日线' FROM bank_quotes
                WHERE bank = ? AND pair = ? AND fetch_cycle = ?
                ORDER BY id ASC LIMIT 1
            """, (bank, pair, f"boc_hist_{date_str}")).fetchall()
            conn.close()
            if rows:
                r = rows[0]
                mid = round((r[1] + r[2]) / 2, 4)
                return [(r[0], mid, r[1], r[2], r[3])]
            return []
        conn.close()
        return rows

    def get_latest_cycle_quotes(self):
        """获取最新一轮抓取的所有报价"""
        conn = self._get_conn()
        cycle = conn.execute(
            "SELECT fetch_cycle FROM market_quotes ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if not cycle:
            conn.close()
            return None
        rows = conn.execute(
            "SELECT pair, bid, ask, mid FROM market_quotes WHERE fetch_cycle = ?",
            (cycle[0],),
        ).fetchall()
        conn.close()
        return {row[0]: {"bid": row[1], "ask": row[2], "mid": row[3]} for row in rows}

    def get_chart_data_by_date(self, pair, bank, date_str, limit=480):
        """按指定日期查询图表数据（兼容中行历史数据）"""
        return self.get_chart_data(pair, bank, limit=limit, date_str=date_str)

    def get_available_dates(self):
        """返回数据库中有数据的日期列表（去重排序）"""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT DISTINCT substr(timestamp, 1, 10) AS d
            FROM (
                SELECT timestamp FROM market_quotes
                UNION
                SELECT timestamp FROM bank_quotes
            )
            WHERE d IS NOT NULL
            ORDER BY d DESC
            LIMIT 100
        """).fetchall()
        conn.close()
        return [r[0] for r in rows]

    def get_recent_market_quotes(self, pair, limit=100):
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT timestamp, bid, ask, mid FROM market_quotes WHERE pair = ? ORDER BY id DESC LIMIT ?",
            (pair, limit),
        ).fetchall()
        conn.close()
        return list(reversed(rows))

    def save_user_entry(self, pair, bank, direction, user_quote, market_cost, bank_cost, bp_vs_market, bp_vs_bank):
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO user_entries (timestamp, pair, bank, direction, user_quote, market_cost, bank_cost, bp_vs_market, bp_vs_bank) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (datetime.now().isoformat(), pair, bank, direction, user_quote, market_cost, bank_cost, bp_vs_market, bp_vs_bank),
        )
        conn.commit()
        conn.close()

    def get_recent_user_entries(self, limit=20):
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT timestamp, pair, bank, direction, user_quote, market_cost, bank_cost, bp_vs_market, bp_vs_bank FROM user_entries ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        return list(reversed(rows))
