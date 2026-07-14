# Focused Pair Workbench and Directional Comparison Implementation Plan
# 单货币对报价工作台与方向化比较实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **给执行代理：** 必须使用 `subagent-driven-development`（推荐）或 `executing-plans`，逐项执行并使用复选框跟踪。

**Goal / 目标:** Replace the tall all-pair matrix with the approved focused-pair premium workbench and correct current and historical comparison formulas to use directional CFETS bid/ask prices. / 用已批准的单货币对精修工作台替换过高的全货币矩阵，并让当前及历史比较按方向使用 CFETS 买入价或卖出价。

**Architecture / 架构:** Keep the existing FastAPI, vanilla HTML/CSS/JavaScript, and SQLite architecture. `server.py` remains the calculation boundary; `static/index.html` owns presentation and interaction; the existing test file receives API and frontend regression coverage. No new production files, framework, dependency, table, or migration is introduced. / 保持现有 FastAPI、原生 HTML/CSS/JavaScript 和 SQLite 架构。`server.py` 继续负责计算，`static/index.html` 负责展示和交互，现有测试文件补充接口与前端回归测试。不新增生产文件、框架、依赖、数据表或迁移。

**Tech Stack / 技术栈:** Python 3, FastAPI, SQLite, vanilla HTML/CSS/JavaScript, ECharts, `unittest`, Node.js DOM harness. / Python 3、FastAPI、SQLite、原生 HTML/CSS/JavaScript、ECharts、`unittest`、Node.js DOM 测试工具。

**Design Spec / 设计规格:** `docs/superpowers/specs/2026-07-14-focused-pair-workbench-and-directional-comparison-design.md`

---

## File Map / 文件范围

- Modify / 修改: `server.py:226-285` — choose the directional CFETS and bank price, calculate signed results, and persist the selected references. / 选择方向对应的 CFETS 与银行价格，计算有符号结果并保存所用参考价。
- Modify / 修改: `static/index.html:10-560` — focused pair board, compact workbench, time-mode interaction, result copy, recent strip, chart preservation, and responsive polish. / 单货币对行情板、紧凑工作台、时间模式、结果文案、最近录入条、历史图表保留和响应式精修。
- Modify / 修改: `tests/test_four_minute_banks.py:311-1235` — API formula tests, HTML contracts, Node behavior tests, and responsive contracts. / 接口公式测试、HTML 契约、Node 行为测试和响应式契约。

Do not modify `database.py`, fetchers, runtime `data/`, or cloud configuration. / 不修改 `database.py`、抓取器、运行时 `data/` 或云端配置。

---

### Task 1: Directional comparison API / 方向化比较接口

**Files / 文件:**
- Modify / 修改: `tests/test_four_minute_banks.py:311-479`
- Modify / 修改: `server.py:226-285`

- [ ] **Step 1: Add failing current-time formula tests / 添加当前时间公式失败测试**

Add these methods to `NewBankPipelineTests`. / 将以下方法加入 `NewBankPipelineTests`：

```python
def test_current_entry_uses_directional_cfets_and_bank_prices(self):
    server.cfets_cache["USDCNY"] = {
        "bid": 6.7800, "ask": 6.7820, "mid": 6.7810,
    }
    server.bank_cache["中国银行"] = {
        "USDCNY": {"bid": 6.7700, "ask": 6.7900},
    }
    fake_db = Mock()

    with patch.object(server, "db", fake_db):
        buy = asyncio.run(
            server.save_entry("USDCNY", "中国银行", "买入价", 6.7750, None)
        )
        sell = asyncio.run(
            server.save_entry("USDCNY", "中国银行", "卖出价", 6.7850, None)
        )

    self.assertEqual(buy["market_cost"], 6.7800)
    self.assertEqual(buy["bp_vs_market"], 50.0)
    self.assertEqual(buy["bp_vs_bank_price"], 50.0)
    self.assertEqual(sell["market_cost"], 6.7820)
    self.assertEqual(sell["bp_vs_market"], 30.0)
    self.assertEqual(sell["bp_vs_bank_price"], 50.0)

def test_current_entry_preserves_negative_and_zero_signs(self):
    server.cfets_cache["USDCNY"] = {
        "bid": 6.7800, "ask": 6.7820, "mid": 6.7810,
    }
    server.bank_cache["中国银行"] = {
        "USDCNY": {"bid": 6.7700, "ask": 6.7900},
    }
    with patch.object(server, "db", Mock()):
        loss = asyncio.run(
            server.save_entry("USDCNY", "中国银行", "买入价", 6.7850, None)
        )
        flat = asyncio.run(
            server.save_entry("USDCNY", "中国银行", "卖出价", 6.7820, None)
        )

    self.assertEqual(loss["bp_vs_market"], -50.0)
    self.assertEqual(flat["bp_vs_market"], 0.0)
```

- [ ] **Step 2: Run the focused tests and verify RED / 运行聚焦测试并确认失败**

Run / 运行：

```bash
rtk /Users/jun/Downloads/projects/.venvs/forex-monitor-web/bin/python -m unittest \
  tests.test_four_minute_banks.NewBankPipelineTests.test_current_entry_uses_directional_cfets_and_bank_prices \
  tests.test_four_minute_banks.NewBankPipelineTests.test_current_entry_preserves_negative_and_zero_signs -v
```

Expected / 预期：FAIL because `market_cost` still uses `mid`, so buy returns `6.7810` and sell also returns `6.7810`. / 失败，因为 `market_cost` 仍统一使用 `mid`。

- [ ] **Step 3: Add failing historical and missing-side tests / 添加历史与缺失方向价失败测试**

```python
def test_historical_entry_uses_directional_market_prices(self):
    fake_db = Mock()
    fake_db.get_quotes_at_time.return_value = {
        "timestamp": "2026-07-14T09:35:12",
        "market_bid": 6.7800,
        "market_ask": 6.7820,
        "market_mid": 6.7810,
        "bank_bid": 6.7700,
        "bank_ask": 6.7900,
    }
    with patch.object(server, "db", fake_db):
        result = asyncio.run(
            server.save_entry(
                "USDCNY", "中国银行", "卖出价", 6.7850,
                "2026-07-14T09:35",
            )
        )

    self.assertEqual(result["market_cost"], 6.7820)
    self.assertEqual(result["bp_vs_market"], 30.0)
    self.assertEqual(result["compare_time"], "2026-07-14T09:35")

def test_historical_entry_rejects_missing_directional_market_price(self):
    fake_db = Mock()
    fake_db.get_quotes_at_time.return_value = {
        "timestamp": "2026-07-14T09:00:00",
        "market_bid": None,
        "market_ask": None,
        "market_mid": 6.7810,
        "bank_bid": 6.7700,
        "bank_ask": 6.7900,
    }
    with patch.object(server, "db", fake_db):
        result = asyncio.run(
            server.save_entry(
                "USDCNY", "中国银行", "买入价", 6.7750,
                "2026-07-14T09:00",
            )
        )

    self.assertFalse(result["ok"])
    self.assertIn("缺少方向化市场价", result["error"])
    fake_db.save_user_entry.assert_not_called()
```

- [ ] **Step 4: Run the historical tests and verify RED / 运行历史测试并确认失败**

Run the two exact test names above with `python -m unittest ... -v`. / 使用 `python -m unittest ... -v` 运行上述两个完整测试名。

Expected / 预期：FAIL because historical code reads only `market_mid`. / 失败，因为历史逻辑只读取 `market_mid`。

- [ ] **Step 5: Implement the minimal directional calculation / 实现最小方向化计算**

Replace the price-selection and calculation portion of `save_entry()` with this logic. / 用以下逻辑替换 `save_entry()` 中的价格选择和计算部分：

```python
if time:
    hist = db.get_quotes_at_time(pair, bank, time)
    if not hist:
        return {"ok": False, "error": f"未找到 {time} 附近的报价数据，请换个时间"}
    market_bid = hist["market_bid"]
    market_ask = hist["market_ask"]
    bank_bid = hist["bank_bid"]
    bank_ask = hist["bank_ask"]
    compare_time = hist["timestamp"][:16]
else:
    market = cfets_cache.get(pair, {})
    market_bid = market.get("bid")
    market_ask = market.get("ask")
    bq = bank_cache.get(bank, {}).get(pair, {})
    bank_bid = bq.get("bid") if bq else None
    bank_ask = bq.get("ask") if bq else None
    compare_time = "当前实时"

if bank_bid is None or bank_ask is None:
    return {
        "ok": False,
        "error": f"{bank} {pair} 暂无真实银行报价，请等待下一次更新",
    }

if direction == "买入价":
    market_cost = market_bid
    bank_cost = bank_bid
    bp_vs_market = None if market_cost is None else round((market_cost - quote) * 10000, 1)
    bp_vs_bank_price = round((quote - bank_cost) * 10000, 1)
else:
    market_cost = market_ask
    bank_cost = bank_ask
    bp_vs_market = None if market_cost is None else round((quote - market_cost) * 10000, 1)
    bp_vs_bank_price = round((bank_cost - quote) * 10000, 1)

if bp_vs_market is None:
    error = (
        "该历史时点缺少方向化市场价，无法准确计算"
        if time else "暂无市场数据，请等待报价刷新"
    )
    return {"ok": False, "error": error}
```

Update `save_user_entry()` arguments to `bank_cost=bank_cost` and `bp_vs_bank=bp_vs_bank_price`. Keep the existing response keys and return `market_cost` as the selected CFETS side. / 将 `save_user_entry()` 参数改为 `bank_cost=bank_cost` 和 `bp_vs_bank=bp_vs_bank_price`；保留现有响应字段，并让 `market_cost` 返回所选 CFETS 方向价。

- [ ] **Step 6: Run API tests and verify GREEN / 运行接口测试并确认通过**

```bash
rtk /Users/jun/Downloads/projects/.venvs/forex-monitor-web/bin/python -m unittest \
  tests.test_four_minute_banks.NewBankPipelineTests -v
```

Expected / 预期：all `NewBankPipelineTests` pass. / `NewBankPipelineTests` 全部通过。

- [ ] **Step 7: Commit Task 1 / 提交任务 1**

```bash
rtk git add server.py tests/test_four_minute_banks.py
rtk git commit -m "fix: use directional market prices for entries"
```

---

### Task 2: Focused pair quote board / 单货币对行情板

**Files / 文件:**
- Modify / 修改: `tests/test_four_minute_banks.py:480-1235`
- Modify / 修改: `static/index.html:10-170, 259-378`

- [ ] **Step 1: Replace the old matrix contract with a failing focused-board contract / 用失败的聚焦行情板契约替换旧矩阵契约**

Update `test_matrix_contains_all_nine_sources()` into the following test. / 将 `test_matrix_contains_all_nine_sources()` 更新为：

```python
def test_focused_pair_board_contains_all_sources_and_real_pairs(self):
    for source in [
        "CFETS", "中国银行", "招商银行", "建设银行", "杭州银行",
        "工商银行", "农业银行", "邮储银行", "民生银行",
    ]:
        self.assertIn(source, self.html)
    for pair in ["USDCNY", "EURCNY", "HKDCNY", "JPYCNY"]:
        self.assertIn(f'"{pair}"', self.html)
    self.assertNotIn("GBPCNY", self.html)
    for marker in [
        'id="pairTabs"', 'id="marketReference"',
        "bank-quote-board", "bank-quote",
        "button.dataset.pair = pair",
    ]:
        self.assertIn(marker, self.html)
    self.assertNotIn('class="quote-matrix"', self.html)
```

Add a contract proving that one pair, not four, is rendered at a time. / 增加一次只渲染一个货币对的契约：

```python
def test_quote_board_tracks_one_active_pair(self):
    source = self.extract_js(
        'const PAIRS = ["USDCNY"',
        "async function fetchQuotes()",
    )
    self.assertIn('let activePair = "USDCNY"', source)
    self.assertIn("function selectPair(pair)", source)
    self.assertRegex(source, r"const\s+pair\s*=\s*activePair")
```

- [ ] **Step 2: Run the focused frontend tests and verify RED / 运行聚焦前端测试并确认失败**

```bash
rtk /Users/jun/Downloads/projects/.venvs/forex-monitor-web/bin/python -m unittest \
  tests.test_four_minute_banks.QuoteMatrixFrontendTests.test_focused_pair_board_contains_all_sources_and_real_pairs \
  tests.test_four_minute_banks.QuoteMatrixFrontendTests.test_quote_board_tracks_one_active_pair -v
```

Expected / 预期：FAIL because the old nine-row matrix is still present. / 失败，因为旧九行矩阵仍存在。

- [ ] **Step 3: Replace the quote-panel markup / 替换行情区标记**

Use this structure inside the existing quote panel. / 在现有行情面板中使用以下结构：

```html
<section class="panel market-panel" aria-labelledby="quotePanelTitle">
  <div class="market-head">
    <div class="pair-tabs" id="pairTabs" role="tablist" aria-label="货币对"></div>
    <div class="market-reference" id="marketReference" role="status" aria-live="polite">
      <span>CFETS 市场参考</span><strong id="marketReferenceValue">--</strong><small id="marketReferenceState">等待数据</small>
    </div>
  </div>
  <div class="quotes" id="quotesContainer" aria-labelledby="quotePanelTitle"></div>
</section>
```

- [ ] **Step 4: Implement focused pair state and rendering / 实现聚焦货币对状态与渲染**

Use the actual pair list and synchronize entry and chart selectors. / 使用真实货币对列表，并同步录入与图表选择器：

```javascript
const PAIRS = ["USDCNY", "EURCNY", "HKDCNY", "JPYCNY"];
const BANK_NAMES = [
  "中国银行", "招商银行", "建设银行", "杭州银行",
  "工商银行", "农业银行", "邮储银行", "民生银行"
];
let activePair = "USDCNY";
let latestQuotes = null;

function selectPair(pair) {
  if (!PAIRS.includes(pair)) return;
  activePair = pair;
  document.getElementById('entryPair').value = pair;
  document.getElementById('chartPair').value = pair;
  const entryPairLabel = document.getElementById('activeEntryPair');
  if (entryPairLabel) entryPairLabel.textContent = pair;
  renderPairTabs();
  if (latestQuotes) {
    renderQuotes(latestQuotes.cfets, latestQuotes.banks, latestQuotes.timestamp);
  }
}

function renderPairTabs() {
  const tabs = document.getElementById('pairTabs');
  tabs.replaceChildren(...PAIRS.map(pair => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'pair-tab' + (pair === activePair ? ' active' : '');
    button.dataset.pair = pair;
    button.setAttribute('role', 'tab');
    button.setAttribute('aria-selected', String(pair === activePair));
    button.textContent = pair;
    button.addEventListener('click', () => selectPair(pair));
    return button;
  }));
}
```

Extend the existing Node test `MockNode` constructor with `this.dataset = {}; this.listeners = {};` and add `addEventListener(type, handler) { this.listeners[type] = handler; }` so pair buttons render in the behavior harness. / 在现有 Node 测试 `MockNode` 中增加 `dataset`、`listeners` 和 `addEventListener`，让货币对按钮可以在行为测试中渲染。

Replace `renderQuoteSkeleton()` and `renderQuotes()` with the focused versions below. / 用以下聚焦版本替换 `renderQuoteSkeleton()` 和 `renderQuotes()`：

```javascript
function renderQuoteSkeleton() {
  const cards = BANK_NAMES.map(() =>
    '<div class="bank-quote skeleton-quote" aria-hidden="true">'
    + '<span class="skeleton-line"></span><span class="skeleton-line"></span></div>'
  ).join('');
  document.getElementById('quotesContainer').innerHTML =
    '<div role="status" aria-live="polite" aria-label="正在加载外汇报价">'
    + '<div class="bank-quote-board skeleton-board">' + cards + '</div></div>';
}

function renderQuotes(cfets, banks, timestamp) {
  latestQuotes = {cfets, banks, timestamp};
  const pair = activePair;
  const market = cfets[pair] || {};
  const marketMid = Number(market.mid);
  document.getElementById('marketReferenceValue').textContent = Number.isFinite(marketMid)
    ? marketMid.toFixed(4) : '--';
  document.getElementById('marketReferenceState').textContent = Number.isFinite(marketMid)
    ? '市场中间价' : '暂无新数据';
  document.getElementById('updateTime').textContent = '最后更新 ' + (timestamp || '--');

  const cards = BANK_NAMES.map(bank => {
    const quote = (banks[bank] && banks[bank][pair]) || {};
    const bidValue = Number(quote.bid);
    const askValue = Number(quote.ask);
    const hasBid = quote.bid != null && Number.isFinite(bidValue);
    const hasAsk = quote.ask != null && Number.isFinite(askValue);
    const bid = hasBid ? bidValue.toFixed(4) : '--';
    const ask = hasAsk ? askValue.toFixed(4) : '--';
    let meta = '等待数据';
    if (quote.source_time) meta = '源 ' + String(quote.source_time).slice(11, 16);
    else if (quote.fetch_time) {
      meta = (quote.fetch_time === timestamp ? '本轮抓取 ' : '上次抓取 ')
        + String(quote.fetch_time).slice(11, 16);
    } else if (hasBid || hasAsk) meta = '真实报价';
    const status = hasBid && hasAsk ? '正常' : (hasBid || hasAsk ? '部分缺失' : '暂无新数据');
    return '<article class="bank-quote" data-source="' + bank + '" aria-label="'
      + bank + ' ' + pair + ' 买入 ' + bid + '，卖出 ' + ask + '">'
      + '<div class="bank-quote-head"><span>' + bank + '</span><small>' + meta + '</small></div>'
      + '<div class="bank-price-line"><span class="buy">' + bid + '</span><span class="sell">' + ask + '</span></div>'
      + '<div class="bank-price-labels"><span>买入</span><span>卖出</span></div>'
      + '<div class="quote-status">' + status + '</div></article>';
  }).join('');
  document.getElementById('quotesContainer').innerHTML =
    '<div class="bank-quote-board">' + cards + '</div>';
}
```

Keep the existing `fetchQuotes()` call signature: `renderQuotes(data.cfets || {}, data.banks || {}, data.timestamp)`. Preserve `--`, `暂无新数据`, source time, and fetch-time truthfulness rules. / 保持现有 `fetchQuotes()` 调用形式，并保留缺失值和时间真实性规则。

- [ ] **Step 5: Add the continuous-board CSS / 添加连续行情板样式**

Add these layout rules and map existing semantic colors to the new elements. / 添加以下布局规则并沿用现有语义色：

```css
.market-panel{margin-top:8px;background:rgba(14,22,32,.96);border:1px solid var(--line)}
.market-head{min-height:45px;padding:0 12px;display:flex;align-items:center;justify-content:space-between;gap:14px;border-bottom:1px solid var(--line-soft)}
.pair-tabs{display:flex;gap:3px}.pair-tab{padding:7px 12px;border:0;border-bottom:2px solid transparent;background:transparent;color:var(--muted)}
.pair-tab.active{color:var(--text);border-bottom-color:var(--accent);background:#12211f}
.market-reference{display:flex;align-items:baseline;gap:8px;color:var(--muted);font-size:9px}.market-reference strong{color:var(--text);font:700 14px ui-monospace,SFMono-Regular,Menlo,monospace}
.bank-quote-board{display:grid;grid-template-columns:repeat(4,minmax(0,1fr))}.bank-quote{min-height:67px;padding:10px 11px;border-right:1px solid var(--line-soft);border-bottom:1px solid var(--line-soft)}
.bank-quote:nth-child(4n){border-right:0}.bank-quote:nth-child(n+5){border-bottom:0}
```

- [ ] **Step 6: Run focused-board tests and verify GREEN / 运行行情板测试并确认通过**

Run the two focused tests from Step 2, then run the entire `QuoteMatrixFrontendTests` class to identify old matrix assumptions that must be updated in Tasks 3 and 4. / 先运行步骤 2 的两个测试，再运行完整 `QuoteMatrixFrontendTests`，记录将在任务 3 和 4 更新的旧矩阵假设。

- [ ] **Step 7: Commit Task 2 / 提交任务 2**

```bash
rtk git add static/index.html tests/test_four_minute_banks.py
rtk git commit -m "feat: add focused pair quote board"
```

---
### Task 3: Compact entry, historical time, and truthful result copy / 紧凑录入、历史时间与真实结果文案

**Files / 文件:**
- Modify / 修改: `tests/test_four_minute_banks.py:850-1195`
- Modify / 修改: `static/index.html:170-255, 498-530`

- [ ] **Step 1: Add failing entry-workbench contracts / 添加录入工作台失败契约**

Add these methods to `QuoteMatrixFrontendTests`. / 将以下方法加入 `QuoteMatrixFrontendTests`：

```python
def test_compact_entry_keeps_history_mode_and_chart_access(self):
    for marker in [
        'class="workbench"', 'class="deal-ticket"',
        'class="result-summary"', 'class="recent-activity"',
        'id="entryTimeCurrent"', 'id="entryTimeHistorical"',
        'id="historicalTimeFields"', 'id="entryDate"', 'id="entryTime"',
        'id="entryTab"', 'id="chartTab"', 'id="chart"',
    ]:
        self.assertIn(marker, self.html)
    self.assertIn('type="hidden" id="entryPair"', self.html)
    self.assertNotIn('<label class="field">货币对', self.html)

def test_result_copy_uses_dynamic_bank_and_signed_labels(self):
    source = self.extract_js(
        "function describeSignedResult(",
        "async function loadEntries()",
    )
    for marker in [
        "你赚", "你亏", "优惠", "更差", "持平",
        "bank + '牌价'", "Math.abs",
    ]:
        self.assertIn(marker, source)
```

- [ ] **Step 2: Add a failing Node truth-table test / 添加 Node 真值表失败测试**

```python
def test_signed_result_descriptor_truth_table(self):
    if not NODE_BINARY:
        self.skipTest("Node.js is required for result-copy behavior")
    source = self.extract_js(
        "function describeSignedResult(",
        "function renderEntryResult(",
    )
    result = self.run_node_json(source + """
process.stdout.write(JSON.stringify([
  describeSignedResult(7.4, '优惠', '更差'),
  describeSignedResult(-2.5, '优惠', '更差'),
  describeSignedResult(0, '优惠', '更差')
]));
""")
    self.assertEqual(result, [
        {"label": "优惠", "value": 7.4, "tone": "positive"},
        {"label": "更差", "value": 2.5, "tone": "negative"},
        {"label": "持平", "value": 0, "tone": "neutral"},
    ])
```

- [ ] **Step 3: Run the new entry tests and verify RED / 运行新增录入测试并确认失败**

Run the three exact test methods above with `python -m unittest ... -v`. / 使用 `python -m unittest ... -v` 运行上述三个完整测试名。

Expected / 预期：FAIL because the old always-visible date/time fields and old result copy remain. / 失败，因为旧日期时间字段始终显示，结果仍使用旧文案。

- [ ] **Step 4: Replace entry markup with the compact workbench / 用紧凑工作台替换录入标记**

Keep the existing workspace tabs, but use this entry-panel structure. / 保留现有工作区标签页，并使用以下录入结构：

```html
<input type="hidden" id="entryPair" value="USDCNY">
<div class="workbench">
  <section class="deal-ticket" aria-labelledby="entryPanelTitle">
    <div class="section-heading">
      <h2 id="entryPanelTitle">客户报价录入</h2>
      <span id="activeEntryPair">USDCNY</span>
    </div>
    <div class="ticket-fields">
      <label class="field">银行<select id="entryBank"><!-- existing eight options --></select></label>
      <label class="field">方向<select id="entryDir">
        <option value="买入价">银行买入（客户卖出）</option>
        <option value="卖出价">银行卖出（客户买入）</option>
      </select></label>
      <label class="field">客户报价<input type="number" id="entryQuote" step="0.0001" inputmode="decimal"></label>
      <div class="time-mode" aria-label="报价时间模式">
        <button type="button" id="entryTimeCurrent" aria-pressed="true">当前</button>
        <button type="button" id="entryTimeHistorical" aria-pressed="false">历史</button>
      </div>
      <div class="historical-time-fields" id="historicalTimeFields" hidden>
        <label class="field">日期<input type="date" id="entryDate"></label>
        <label class="field">时间<input type="time" id="entryTime"></label>
      </div>
      <button type="button" class="btn ticket-submit" onclick="submitEntry()">计算并保存</button>
    </div>
    <p class="entry-context" id="entryContext">使用当前实时市场价与银行牌价计算</p>
  </section>
  <aside class="result-summary" id="entryResult" role="status" aria-live="polite">
    <div class="result-empty">录入后显示计算结果</div>
  </aside>
</div>
<div class="recent-activity" id="entryRecent" role="status" aria-live="polite">暂无录入记录</div>
```

Copy the existing eight bank `<option>` elements exactly; do not create new banks. / 原样复制现有八家银行选项，不新增银行。

- [ ] **Step 5: Implement time-mode interaction and validation / 实现时间模式交互与校验**

```javascript
let entryTimeMode = 'current';

function setEntryTimeMode(mode) {
  entryTimeMode = mode === 'historical' ? 'historical' : 'current';
  const historical = entryTimeMode === 'historical';
  document.getElementById('historicalTimeFields').hidden = !historical;
  document.getElementById('entryTimeCurrent').setAttribute('aria-pressed', String(!historical));
  document.getElementById('entryTimeHistorical').setAttribute('aria-pressed', String(historical));
  document.getElementById('entryContext').textContent = historical
    ? '将使用所选历史时点对应的市场价与银行牌价计算'
    : '使用当前实时市场价与银行牌价计算';
}

document.getElementById('entryTimeCurrent').addEventListener('click', () => setEntryTimeMode('current'));
document.getElementById('entryTimeHistorical').addEventListener('click', () => setEntryTimeMode('historical'));
```

In `submitEntry()`, use `activePair`, and only append `time=` when `entryTimeMode === 'historical'`. If either historical field is empty, set `entryResult.textContent = '请选择完整的历史日期和时间'` and return before `fetch`. / 在 `submitEntry()` 中使用 `activePair`；只有历史模式才添加 `time=`。历史日期或时间缺一项时，在请求前显示错误并返回。

- [ ] **Step 6: Implement signed result descriptors and dynamic bank copy / 实现有符号结果与动态银行文案**

```javascript
function describeSignedResult(value, positiveLabel, negativeLabel) {
  const numeric = Number(value);
  if (numeric > 0) return {label: positiveLabel, value: Math.abs(numeric), tone: 'positive'};
  if (numeric < 0) return {label: negativeLabel, value: Math.abs(numeric), tone: 'negative'};
  return {label: '持平', value: 0, tone: 'neutral'};
}

function renderEntryResult(data, bank) {
  const market = describeSignedResult(data.bp_vs_market, '你赚', '你亏');
  const board = describeSignedResult(data.bp_vs_bank_price, '优惠', '更差');
  const root = document.getElementById('entryResult');
  const makeRow = (prefix, result) => {
    const row = document.createElement('div');
    const label = document.createElement('div');
    const value = document.createElement('div');
    row.className = 'result-row ' + result.tone;
    label.className = 'result-label';
    value.className = 'result-value';
    label.textContent = prefix + result.label + '：';
    value.textContent = result.value.toFixed(1) + ' bp';
    row.append(label, value);
    return row;
  };
  root.replaceChildren(
    makeRow('对比市场成本，', market),
    makeRow('对比' + bank + '牌价，', board),
  );
}
```

Call `renderEntryResult(data, bank)` after a successful entry. Keep failed requests as plain `textContent`; do not place error text through `innerHTML`. / 成功后调用 `renderEntryResult(data, bank)`；失败继续使用纯 `textContent`，不要用 `innerHTML` 写错误内容。

- [ ] **Step 7: Run entry tests and verify GREEN / 运行录入测试并确认通过**

Run the three Task 3 tests, then the existing frontend security/state test. Update the Node harness to return `entryResult.children.flatMap(row => row.children.map(child => child.textContent)).join(' | ')` as `successText`; assert that `successText` contains `对比市场成本`, `对比中国银行牌价`, `你赚`, and `优惠`, and assert `entryResult.innerHTMLWrites == 0`. Remove the obsolete `successHTML` assertions. / 运行任务 3 的三个测试和现有前端安全状态测试；让 Node 工具返回结果行子节点的组合文本 `successText`，断言包含四个新文案并确认没有写入 `innerHTML`，删除旧 `successHTML` 断言。

- [ ] **Step 8: Commit Task 3 / 提交任务 3**

```bash
rtk git add static/index.html tests/test_four_minute_banks.py
rtk git commit -m "feat: add compact quote entry workbench"
```

---

### Task 4: Premium visual hierarchy, chart preservation, and responsive layout / 美工层级、历史图表保留与响应式布局

**Files / 文件:**
- Modify / 修改: `tests/test_four_minute_banks.py:540-900, 1195-1235`
- Modify / 修改: `static/index.html:10-258`

- [ ] **Step 1: Add failing visual and responsive contracts / 添加视觉与响应式失败契约**

```python
def test_premium_workbench_reduces_nested_card_noise(self):
    for marker in [
        ".terminal-header{min-height:44px",
        ".bank-quote-board{display:grid;grid-template-columns:repeat(4",
        ".workbench{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(280px,.7fr)",
        ".recent-activity{",
        ".result-value{",
    ]:
        self.assertIn(marker, self.html)
    self.assertNotIn("border-radius:10px", self.html)
    self.assertNotIn("box-shadow:0 8px", self.html)

def test_narrow_layout_stacks_workbench_without_page_overflow(self):
    media = self.html[self.html.index("@media(max-width:800px)"):]
    for marker in [
        ".bank-quote-board{grid-template-columns:repeat(2,minmax(0,1fr))}",
        ".workbench{grid-template-columns:1fr}",
        ".ticket-fields{grid-template-columns:1fr 1fr}",
    ]:
        self.assertIn(marker, media)
    self.assertNotIn("min-width:820px", media)

def test_chart_tab_and_chart_controls_are_preserved(self):
    for marker in [
        'id="entryTab"', 'id="chartTab"', 'id="tab-chart"',
        'id="chartPair"', 'id="chartBank"', 'id="chartDate"', 'id="chart"',
    ]:
        self.assertIn(marker, self.html)
```

- [ ] **Step 2: Run the visual contracts and verify RED / 运行视觉契约并确认失败**

Run the three exact tests above. / 运行上述三个完整测试名。

Expected / 预期：FAIL until the approved compact hierarchy and responsive rules replace the old layout. / 在旧布局被替换前失败。

- [ ] **Step 3: Apply the approved compact shell / 应用已批准的紧凑外壳**

Change the existing shell rather than introducing a new component system. / 修改现有外壳，不新增组件系统：

```css
.app-shell{width:min(100%,1400px);margin:0 auto;padding:8px}
.terminal-header{min-height:44px;padding:8px 13px;border:1px solid var(--line);border-bottom-color:var(--accent);background:var(--panel);display:flex;align-items:center;justify-content:space-between}
.brand-mark{width:28px;height:28px;font-size:10px}.brand-copy h1{font-size:13px}.brand-copy p{font-size:7px;letter-spacing:.16em}
.workspace-panel{margin-top:8px;background:var(--panel);border:1px solid var(--line)}
.workbench{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(280px,.7fr)}
.deal-ticket{border-right:1px solid var(--line)}.result-summary{min-width:0}.recent-activity{display:flex;align-items:center;gap:18px;padding:8px 12px;border-top:1px solid var(--line-soft);white-space:nowrap;overflow:hidden;color:var(--muted);font-size:8px}
.ticket-fields{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:7px;padding:11px 12px 8px}.historical-time-fields{display:grid;grid-template-columns:1fr 1fr;gap:7px}.historical-time-fields[hidden]{display:none}
.result-row{padding:12px;border-bottom:1px solid var(--line-soft)}.result-value{font:800 23px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--accent);font-variant-numeric:tabular-nums}
```

Retain the existing blue-black palette and bid/ask semantic colors. Remove redundant nested borders, oversized English kickers, and rounded chart treatment; do not add gradients, image assets, web fonts, or icon libraries. / 保留现有配色和买卖语义色；移除多余嵌套边框、过大的英文标签和圆角图表处理；不新增渐变、图片、网络字体或图标库。

- [ ] **Step 4: Preserve workspace tabs and chart behavior / 保留工作区标签和图表行为**

Keep the existing `entryTab`, `chartTab`, `tab-entry`, `tab-chart`, chart controls, `loadChart()`, `renderChart()`, resize listener, loading state, empty state, and error state. Only restyle the tab bar to a compact 34-pixel control and ensure switching back to the chart still triggers resize/load exactly once. / 保留现有标签、图表控件、加载、空状态和错误状态，只把标签栏压缩到约 34 像素，并保证切回图表时仍只触发一次调整或加载。

- [ ] **Step 5: Update skeleton and source-status tests / 更新骨架屏与来源状态测试**

Change the skeleton from nine source rows × four pair cells to eight bank quote tiles plus one CFETS reference placeholder. Preserve accessible `role="status"` and `aria-live="polite"`. / 把骨架屏从九行四列改为八个银行块加一个 CFETS 参考占位，并保留可访问状态语义。

Update the `render_quotes()` Node harness elements exactly as follows. / 将 `render_quotes()` 的 Node 元素改为：

```javascript
const elements = {
  quotesContainer: { innerHTML: '' },
  updateTime: { textContent: '' },
  marketReferenceValue: { textContent: '' },
  marketReferenceState: { textContent: '' }
};
```

Replace `source_row()` with an article helper and update the dynamic count test. / 用银行文章辅助函数替换 `source_row()` 并更新动态数量测试：

```python
@staticmethod
def bank_quote(rendered, bank):
    marker = f'data-source="{bank}"'
    marker_pos = rendered.index(marker)
    start = rendered.rfind('<article class="bank-quote"', 0, marker_pos)
    end = rendered.find('</article>', marker_pos)
    return rendered[start:end + len('</article>')]

@unittest.skipUnless(NODE_BINARY, "Node.js is required for dynamic frontend rendering")
def test_dynamic_board_keeps_eight_banks_for_one_pair(self):
    rendered = self.render_quotes({}, {}, "2026-07-14 12:30:00")
    self.assertEqual(rendered.count('<article class="bank-quote"'), 8)
    self.assertEqual(rendered.count('class="bank-price-line"'), 8)
    self.assertEqual(rendered.count('class="buy"'), 8)
    self.assertEqual(rendered.count('class="sell"'), 8)
```

Update the existing non-finite, partial, missing, source-time, and fetch-time tests to call `bank_quote(rendered, bank)` and keep their current truthfulness assertions. / 更新现有非有限值、部分缺失、完全缺失、源时间和抓取时间测试，使其调用 `bank_quote()`，并保留真实性断言。

- [ ] **Step 6: Add narrow responsive rules / 添加窄屏规则**

```css
@media(max-width:800px){
  .app-shell{padding:6px}
  .terminal-header{align-items:flex-start}
  .market-head{align-items:flex-start;flex-direction:column;padding:9px 10px}
  .bank-quote-board{grid-template-columns:repeat(2,minmax(0,1fr))}
  .bank-quote:nth-child(2n){border-right:0}
  .workbench{grid-template-columns:1fr}
  .deal-ticket{border-right:0;border-bottom:1px solid var(--line)}
  .ticket-fields{grid-template-columns:1fr 1fr}
  .recent-activity{overflow-x:auto}
}
```

At narrow widths, do not force the former matrix minimum width and do not create document-level horizontal overflow. / 窄屏不再强制旧矩阵最小宽度，不产生页面级横向溢出。

- [ ] **Step 7: Run the entire frontend test class / 运行完整前端测试类**

```bash
rtk /Users/jun/Downloads/projects/.venvs/forex-monitor-web/bin/python -m unittest \
  tests.test_four_minute_banks.QuoteMatrixFrontendTests -v
```

Expected / 预期：all frontend tests pass after obsolete matrix-specific assertions are surgically updated to the focused-board contract. / 仅更新已过时的矩阵断言后，全部前端测试通过。

- [ ] **Step 8: Commit Task 4 / 提交任务 4**

```bash
rtk git add static/index.html tests/test_four_minute_banks.py
rtk git commit -m "feat: refine focused quote terminal layout"
```

---

### Task 5: Full verification and browser acceptance / 完整验证与浏览器验收

**Files / 文件:**
- Verify / 验证: `server.py`, `static/index.html`, `tests/test_four_minute_banks.py`
- Do not stage / 不暂存: `data/`

- [ ] **Step 1: Run the complete automated suite / 运行完整自动测试**

```bash
rtk /Users/jun/Downloads/projects/.venvs/forex-monitor-web/bin/python -m unittest discover -s tests -v
```

Expected / 预期：all tests pass with zero failures and zero errors. / 所有测试通过，失败和错误均为零。

- [ ] **Step 2: Run syntax and whitespace verification / 运行语法和空白检查**

```bash
rtk /Users/jun/Downloads/projects/.venvs/forex-monitor-web/bin/python -m compileall -q server.py database.py fetcher.py bank_fetcher.py calculator.py
rtk git diff --check
```

Extract and check the inline JavaScript with these exact commands. / 使用以下完整命令提取并检查内联 JavaScript：

```bash
rtk node -e "const fs=require('fs');const h=fs.readFileSync('static/index.html','utf8');const s=[...h.matchAll(/<script>([\\s\\S]*?)<\\/script>/g)].map(m=>m[1]).join('\\n');fs.writeFileSync('/tmp/forex-monitor-inline.js',s)"
rtk node --check /tmp/forex-monitor-inline.js
rtk rm /tmp/forex-monitor-inline.js
```

Remove only the temporary file afterward. / 随后只删除该临时文件。

Expected / 预期：all commands exit `0`; `git diff --check` prints nothing. / 所有命令退出码为 `0`，`git diff --check` 无输出。

- [ ] **Step 3: Start or reload the local server / 启动或重载本地服务**

```bash
rtk /Users/jun/Downloads/projects/.venvs/forex-monitor-web/bin/python server.py
```

Verify `GET /` and `GET /api/quotes` both return HTTP `200`. / 确认首页和报价接口均返回 HTTP `200`。

- [ ] **Step 4: Verify directional API examples / 验证方向化接口示例**

Using patched automated tests or a temporary database, verify these exact outcomes without editing runtime history: / 使用补丁测试或临时数据库验证以下结果，不修改运行时历史数据：

- Bank buy / 银行买入: CFETS bid `6.7800`, quote `6.7750`, bank bid `6.7700` → market `+50.0`, bank improvement `+50.0`.
- Bank sell / 银行卖出: CFETS ask `6.7820`, quote `6.7850`, bank ask `6.7900` → market `+30.0`, bank improvement `+50.0`.
- Negative / 负数: bank-buy quote `6.7850` against CFETS bid `6.7800` → market `-50.0` and UI text `你亏：50.0 bp`.
- Legacy mid-only history / 旧中间价历史: missing bid/ask → clear error, no synthesized result.

- [ ] **Step 5: Desktop browser acceptance at 1280 × 900 / 进行 1280 × 900 桌面浏览器验收**

Check all of the following in one fresh page load. / 在一次全新页面加载中检查：

1. `USDCNY` is active by default; `EURCNY`, `HKDCNY`, and `JPYCNY` tabs are visible. / 默认选中 `USDCNY`，其余三个真实货币对标签可见。
2. CFETS reference and eight bank quotes are visible; missing data remains `--` or `暂无新数据`. / CFETS 与八家银行可见，缺失数据保持真实提示。
3. Header, quote board, entry form, result area, and recent strip fit within the first viewport. / 顶部、行情、录入、结果、最近录入进入首屏。
4. Pair switching updates the quote board and hidden entry/chart pair values. / 切换货币对同步行情和录入、图表货币对。
5. Current entry submits without date/time; historical mode requires both and displays the actual matched timestamp. / 当前录入无需时间，历史模式要求日期与时间并显示实际匹配时间。
6. Dynamic bank name and positive/negative/zero labels are correct. / 动态银行名及正负零文案正确。
7. Historical chart tab still loads and resizes without console errors. / 历史图表仍能加载和调整，无控制台错误。

- [ ] **Step 6: Narrow browser acceptance / 进行窄屏浏览器验收**

At a width at or below `800px`, verify two bank columns, stacked entry/results, keyboard focus visibility, and no document-level horizontal overflow. The recent activity strip may scroll horizontally inside its own container. / 在不超过 `800px` 的宽度检查银行两列、录入结果纵向排列、键盘焦点可见且页面无整体横向溢出；最近录入条可在自身容器内横向滚动。

- [ ] **Step 7: Verify database and commit scope / 验证数据库与提交范围**

```bash
rtk git status --short
rtk git diff --stat c2841d9..HEAD
```

Expected / 预期：after approved spec commit `c2841d9`, tracked changes are limited to this plan, `server.py`, `static/index.html`, and `tests/test_four_minute_banks.py`; runtime `data/` remains untracked and unstaged; no schema or migration file exists. / 在已批准规格提交 `c2841d9` 之后，受跟踪修改仅限本计划和三个代码测试文件；`data/` 保持未跟踪未暂存，不存在数据库迁移文件。

- [ ] **Step 8: Run pre-delivery review and fix only in-scope findings / 执行交付前审查并仅修复范围内问题**

Invoke `pre-delivery-review`, then rerun Steps 1, 2, 5, 6, and 7 after any correction. Do not refactor unrelated code. / 调用 `pre-delivery-review`；若有修正，重新运行步骤 1、2、5、6、7；不重构无关代码。

- [ ] **Step 9: Final verification commit if review changes were needed / 如审查产生修改则提交最终验证修正**

```bash
rtk git add server.py static/index.html tests/test_four_minute_banks.py
rtk git commit -m "test: finalize focused quote workbench"
```

Skip this commit when the review produces no file changes. / 审查未产生文件修改时跳过此提交。
