# Institutional Trading Terminal UI Redesign Implementation Plan / 机构交易终端界面重设计实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the existing engineering-style page with the approved institutional trading terminal interface while preserving all truthful quote, entry, chart, API, and database behavior. / 在保留全部真实报价、录入、图表、API 与数据库行为的前提下，将现有工程后台式页面升级为已确认的机构交易终端界面。

**Architecture:** Keep the existing single-page vanilla HTML/CSS/JavaScript architecture. Limit production changes to `static/index.html`, and keep UI contract tests in `tests/test_four_minute_banks.py`. Do not change the server, fetchers, database schema, refresh cadence, or price calculations. / 保持现有单页原生 HTML/CSS/JavaScript 架构。正式代码仅修改 `static/index.html`，界面契约测试保留在 `tests/test_four_minute_banks.py`。不修改服务端、抓取器、数据库结构、刷新频率或价格计算。

**Tech Stack:** HTML5, CSS custom properties and responsive Grid, vanilla JavaScript, ECharts 5.5.0, Python `unittest`, Node.js render harness. / HTML5、CSS 变量与响应式 Grid、原生 JavaScript、ECharts 5.5.0、Python `unittest`、Node.js 渲染测试工具。

---

## Working Context / 工作环境

- **Worktree / 工作树:** `/Users/jun/Downloads/projects/forex-monitor-web/.worktrees/four-minute-banks`
- **Branch / 分支:** `feat/four-minute-banks`
- **Approved design / 已确认设计:** `docs/superpowers/specs/2026-07-13-institutional-terminal-ui-redesign-design.md`
- **Python / Python 路径:** `/Users/jun/Downloads/projects/.venvs/forex-monitor-web/bin/python`
- **Local URL after implementation / 实施后的本地地址:** `http://127.0.0.1:8000/`
- **Production files allowed to change / 允许修改的正式文件:** `static/index.html`, `tests/test_four_minute_banks.py`
- **Protected paths / 受保护路径:** `data/`, `server.py`, `database.py`, `bank_fetcher.py`

## Success Criteria / 成功标准

1. The centered application shell, professional header, nine-source quote matrix, two-column entry workspace, and full-width chart match approved Direction A. / 居中应用外壳、专业顶部栏、九来源报价矩阵、两栏录入工作区和全宽图表符合已确认的 A 方向。
2. Missing values remain `--`; partial and unavailable states remain truthful; no synthetic or stale-current-cycle prices appear. / 缺失值继续显示 `--`，部分缺失与暂无数据状态保持真实，不出现合成价或冒充本轮的新鲜旧价。
3. All 30 baseline tests plus six new UI contracts pass. / 现有 30 项基线测试与新增 6 项界面契约测试全部通过。
4. At 390 px width, the page itself does not scroll horizontally; only the quote matrix scrolls, with the source column remaining sticky. / 在 390 像素宽度下，页面本身不横向滚动，只有报价矩阵可以横向滚动，数据来源列保持固定。
5. Entry, “Now,” historical time, recent entries, tab switching, chart filters, and chart rendering remain functional. / 报价录入、“现在”、历史时间、最近记录、标签切换、图表筛选与渲染继续正常工作。
6. No Alibaba Cloud deployment occurs, and local `data/` remains untracked and uncommitted. / 本阶段不执行阿里云部署，本地 `data/` 保持未跟踪且不提交。

## Task 0: Confirm the Baseline and Boundaries / 确认基线与边界

**Files / 文件:**

- Read only / 只读: `static/index.html`
- Read only / 只读: `tests/test_four_minute_banks.py`
- Read only / 只读: `docs/superpowers/specs/2026-07-13-institutional-terminal-ui-redesign-design.md`

- [ ] **Step 1: Confirm the worktree contains no unexpected tracked edits / 确认工作树没有意外的已跟踪改动**

Run / 运行：

```bash
rtk git status --short
```

Expected / 预期：only `?? data/` is shown. Stop and report any tracked-file change before continuing. / 只显示 `?? data/`。如出现任何已跟踪文件改动，先停止并报告。

- [ ] **Step 2: Run the baseline suite / 运行基线测试**

```bash
rtk /Users/jun/Downloads/projects/.venvs/forex-monitor-web/bin/python -m unittest discover -s tests -v
```

Expected / 预期：`Ran 30 tests` and `OK`. The simulated offline/403 log lines are expected test fixtures, not failures. / 显示 `Ran 30 tests` 与 `OK`；模拟离线和 403 的日志是测试场景，不是失败。

- [ ] **Step 3: Re-read the implementation boundary / 再次确认实施边界**

Do not touch `data/`, API routes, fetchers, persistence, refresh timers, or calculation formulas. Do not deploy. / 不修改 `data/`、API 路由、抓取器、持久化、刷新定时器或计算公式，也不部署。

## Task 1: Build the Institutional Shell and Quote Matrix / 构建机构终端外壳与报价矩阵

**Files / 文件:**

- Modify / 修改: `tests/test_four_minute_banks.py` (`QuoteMatrixFrontendTests`)
- Modify / 修改: `static/index.html` (global CSS, header markup, quote markup, `renderQuotes`)

- [ ] **Step 1: Add failing shell, matrix-count, and source-time contracts / 新增会失败的外壳、矩阵数量和来源时间契约测试**

Add these methods to `QuoteMatrixFrontendTests`: / 在 `QuoteMatrixFrontendTests` 中加入：

```python
def test_institutional_shell_brand_and_palette(self):
    required = [
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
    ]
    for token in required:
        self.assertIn(token, self.html)
    for emoji in ["🔄", "📝", "📊", "📋"]:
        self.assertNotIn(emoji, self.html)

@unittest.skipUnless(NODE_BINARY, "Node.js is required for dynamic frontend rendering")
def test_dynamic_matrix_keeps_nine_sources_and_thirty_six_cells(self):
    rendered = self.render_quotes({}, {}, "2026-07-13 12:30:00")
    self.assertEqual(rendered.count('class="source-row'), 9)
    self.assertEqual(rendered.count('class="quote-cell"'), 36)
    self.assertEqual(rendered.count('class="source-time"'), 9)
```

Update the existing `source_row` helper so it still works after the bank name gains a nested time label: / 更新现有 `source_row` 辅助方法，使银行名称加入嵌套时间后仍可定位行：

```python
@staticmethod
def source_row(rendered, source):
    marker = f'data-source="{source}"'
    marker_pos = rendered.index(marker)
    row_start = rendered.rfind('<div class="source-row', 0, marker_pos)
    row_end = rendered.find('<div class="source-row', marker_pos + len(marker))
    return rendered[row_start:row_end if row_end >= 0 else len(rendered)]
```

In `test_non_finite_and_partial_quotes_render_truthful_states`, replace the old `正常<br>12:30` assertion with: / 在该现有测试中替换旧断言：

```python
minsheng_row = self.source_row(rendered, "民生银行")
self.assertIn('<small class="source-time">源 12:30</small>', minsheng_row)
self.assertIn('>正常</div>', minsheng_row)
```

- [ ] **Step 2: Prove the new tests fail for the right reason / 确认新测试因预期原因失败**

```bash
rtk /Users/jun/Downloads/projects/.venvs/forex-monitor-web/bin/python -m unittest \
  tests.test_four_minute_banks.QuoteMatrixFrontendTests.test_institutional_shell_brand_and_palette \
  tests.test_four_minute_banks.QuoteMatrixFrontendTests.test_dynamic_matrix_keeps_nine_sources_and_thirty_six_cells -v
```

Expected / 预期：`FAIL`; the current page lacks `app-shell`, the approved palette, and `source-time`. / 当前页面缺少 `app-shell`、已确认色板和 `source-time`，因此测试失败。

- [ ] **Step 3: Replace the global visual foundation and quote-matrix styles / 替换全局视觉基础与报价矩阵样式**

Use these exact core tokens and selectors in the `<style>` block; retain all existing behavior selectors that later tasks have not yet replaced. / 在 `<style>` 中使用以下核心变量与选择器；暂时保留后续任务尚未替换的行为选择器。

```css
:root{--page:#070b10;--panel:#0e1620;--panel-raised:#131e29;--line:#20303d;--line-soft:#182630;--text:#dce5e8;--muted:#7f9098;--accent:#56d8b3;--bid:#56d8b3;--ask:#ff857a;--warn:#d8a84e;--danger:#e77770;--radius:16px;--control-radius:7px}
*{margin:0;padding:0;box-sizing:border-box}
html{background:var(--page)}
body{min-height:100vh;background:var(--page);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;overflow-x:hidden}
.app-shell{width:min(calc(100% - 32px),1400px);max-width:1400px;margin:24px auto 40px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius)}
.terminal-header{display:flex;align-items:center;justify-content:space-between;gap:20px;padding:4px 2px 18px}
.brand{display:flex;align-items:center;gap:12px}
.brand-mark{display:grid;place-items:center;width:38px;height:38px;border:1px solid color-mix(in srgb,var(--accent) 48%,transparent);border-radius:10px;color:var(--accent);font:700 13px ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;letter-spacing:.06em}
.brand-copy h1{font-size:20px;line-height:1.2;font-weight:700;color:#f0f5f6}
.brand-copy p{margin-top:4px;color:var(--muted);font-size:10px;letter-spacing:.18em}
.live-meta{display:flex;align-items:center;gap:14px;color:var(--muted);font-size:12px}
.live-state{display:inline-flex;align-items:center;gap:7px;color:var(--accent);font-weight:600}
.live-dot{width:7px;height:7px;border-radius:50%;background:var(--accent);box-shadow:0 0 0 3px rgba(86,216,179,.1)}
.quote-panel{overflow:hidden}
.panel-heading{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:15px 18px;border-bottom:1px solid var(--line-soft)}
.panel-heading h2{font-size:13px;color:#eef4f5;font-weight:650;letter-spacing:.04em}
.quote-legend{display:flex;gap:15px;color:var(--muted);font-size:11px}
.quote-legend span::before{content:"";display:inline-block;width:6px;height:6px;margin-right:6px;border-radius:50%;background:currentColor;vertical-align:1px}
.quote-legend .legend-bid{color:var(--bid)}
.quote-legend .legend-ask{color:var(--ask)}
.quotes{overflow-x:auto}
.quote-matrix{min-width:900px;overflow:visible}
.quote-head,.source-row{display:grid;grid-template-columns:126px repeat(4,minmax(150px,1fr)) 94px;align-items:stretch}
.quote-head{background:#0a1118;border-bottom:1px solid var(--line);color:var(--muted);font-size:10px;text-align:center}
.quote-head>div{padding:10px 8px}
.quote-head b{display:block;margin-bottom:3px;color:#dce6e8;font:650 11px ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;letter-spacing:.04em}
.quote-head .buy-label{margin-right:10px;color:var(--bid)}
.quote-head .sell-label{color:var(--ask)}
.source-row{min-height:54px;border-bottom:1px solid var(--line-soft);transition:background-color .18s ease}
.source-row:last-child{border-bottom:0}
.source-row:hover{background:#111c26}
.source-row.cfets{background:rgba(86,216,179,.035)}
.source-name{display:flex;flex-direction:column;justify-content:center;gap:3px;padding:0 14px;color:#d7e1e3;font-size:12px;font-weight:650;white-space:nowrap}
.source-time{color:var(--muted);font:400 9px ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace}
.quote-head .source-name,.source-row .source-name{position:sticky;left:0;z-index:3;background:#0a1118;text-align:left}
.source-row .source-name{z-index:2;background:var(--panel)}
.source-row.cfets .source-name{background:#0d191e}
.source-row:hover .source-name{background:#111c26}
.quote-cell{display:flex;align-items:center;justify-content:center;gap:12px;padding:0 8px;font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,"Liberation Mono",monospace;font-variant-numeric:tabular-nums;font-size:13px}
.quote-cell .buy{color:var(--bid);font-weight:650}
.quote-cell .sell{color:var(--ask);font-weight:650}
.quote-status{display:grid;place-items:center;padding:0 8px;color:var(--muted);font-size:10px;text-align:center}
.quote-status.ok{color:var(--accent)}
.quote-status.partial{color:var(--warn)}
.quote-status.missing{color:var(--danger)}
```

- [ ] **Step 4: Replace the page header and quote wrapper / 替换页面顶部栏与报价外层结构**

Replace the visible page opening with this markup, keeping the existing `quotesContainer` ID used by JavaScript: / 用以下结构替换可见页面开头，并保留 JavaScript 依赖的 `quotesContainer` ID：

```html
<main class="app-shell">
  <header class="terminal-header">
    <div class="brand">
      <div class="brand-mark" aria-hidden="true">FX</div>
      <div class="brand-copy">
        <h1>外汇报价工作台</h1>
        <p>FOREIGN EXCHANGE MONITOR</p>
      </div>
    </div>
    <div class="live-meta">
      <span class="live-state"><span class="live-dot" aria-hidden="true"></span>实时采集中</span>
      <span id="updateTime">最后更新 --</span>
    </div>
  </header>

  <section class="panel quote-panel" aria-labelledby="quoteTitle">
    <div class="panel-heading">
      <h2 id="quoteTitle">实时银行报价</h2>
      <div class="quote-legend" aria-label="价格图例">
        <span class="legend-bid">买入价</span>
        <span class="legend-ask">卖出价</span>
      </div>
    </div>
    <div class="quotes" id="quotesContainer">
      <div class="loading" role="status">加载报价中</div>
    </div>
  </section>
```

Keep the existing tab bar and tab content immediately after this quote section, move them inside `<main>`, and add `</main>` immediately after the existing tab content. This keeps the Task 1 commit valid before Task 2 replaces the workspace. / 将现有标签栏与标签内容紧接在报价区之后并移入 `<main>`，在现有标签内容之后立即添加 `</main>`。这样任务 1 的提交在任务 2 替换工作区之前仍是完整有效的页面。

- [ ] **Step 5: Render source time beneath each bank and keep status truthful / 在银行名下显示来源时间并保持状态真实**

Replace `renderQuotes` with this implementation. It preserves four-decimal formatting, `--`, ARIA labels, nine sources, and the current-cycle truthfulness contract: / 用以下实现替换 `renderQuotes`。它保留四位小数、`--`、ARIA 标签、九个来源和本轮数据真实性契约：

```javascript
function renderQuotes(cfets, banks, timestamp) {
  const el = document.getElementById('quotesContainer');
  document.getElementById('updateTime').textContent = '最后更新 ' + (timestamp || '--');
  let html = '<div class="quote-matrix" role="table" aria-label="外汇买入卖出报价矩阵"><div class="quote-head" role="row">'
    + '<div class="source-name" role="columnheader">数据来源</div>'
    + PAIRS.map(pair => '<div role="columnheader"><b>' + pair + '</b><span class="buy-label">买入</span><span class="sell-label">卖出</span></div>').join('')
    + '<div role="columnheader">状态</div></div>';

  for (const source of BANK_NAMES) {
    let cells = '';
    let validPairCount = 0;
    let sourceTime = '';
    let fetchTime = '';
    for (const pair of PAIRS) {
      const quote = source === 'CFETS' ? (cfets[pair] || {}) : ((banks[source] && banks[source][pair]) || {});
      const bidValue = Number(quote.bid);
      const askValue = Number(quote.ask);
      const hasBid = quote.bid != null && String(quote.bid).trim() !== '' && Number.isFinite(bidValue);
      const hasAsk = quote.ask != null && String(quote.ask).trim() !== '' && Number.isFinite(askValue);
      const bid = hasBid ? bidValue.toFixed(4) : '--';
      const ask = hasAsk ? askValue.toFixed(4) : '--';
      if (hasBid && hasAsk) validPairCount += 1;
      if (!sourceTime && quote.source_time) sourceTime = quote.source_time;
      if (!fetchTime && quote.fetch_time) fetchTime = quote.fetch_time;
      cells += '<div class="quote-cell" role="cell" aria-label="' + source + ' ' + pair
        + ' 买入 ' + bid + '，卖出 ' + ask + '"><span class="buy">' + bid
        + '</span><span class="sell">' + ask + '</span></div>';
    }

    let statusClass = 'ok';
    let statusText = source === 'CFETS' ? '市场基准' : '正常';
    if (validPairCount === 0) {
      statusClass = 'missing';
      statusText = '暂无新数据';
    } else if (validPairCount < PAIRS.length) {
      statusClass = 'partial';
      statusText = '部分缺失';
    }

    let sourceMeta = source === 'CFETS' ? '市场中间价' : '真实报价';
    if (source !== 'CFETS' && sourceTime) {
      sourceMeta = '源 ' + sourceTime.slice(11, 16);
    } else if (source !== 'CFETS' && fetchTime) {
      sourceMeta = (fetchTime === timestamp ? '本轮抓取 ' : '上次抓取 ') + fetchTime.slice(11, 16);
    } else if (source !== 'CFETS' && validPairCount === 0) {
      sourceMeta = '等待数据';
    }

    html += '<div class="source-row ' + (source === 'CFETS' ? 'cfets' : '') + '" data-source="' + source + '" role="row">'
      + '<div class="source-name" role="rowheader"><span>' + source + '</span><small class="source-time">' + sourceMeta + '</small></div>'
      + cells + '<div class="quote-status ' + statusClass + '" role="cell">' + statusText + '</div></div>';
  }
  el.innerHTML = html + '</div>';
}
```

- [ ] **Step 6: Run the quote-matrix frontend tests / 运行报价矩阵前端测试**

```bash
rtk /Users/jun/Downloads/projects/.venvs/forex-monitor-web/bin/python -m unittest tests.test_four_minute_banks.QuoteMatrixFrontendTests -v
```

Expected / 预期：`Ran 8 tests` and `OK`. / 显示 `Ran 8 tests` 与 `OK`。

- [ ] **Step 7: Commit the shell and matrix / 提交应用外壳与报价矩阵**

```bash
rtk git add static/index.html tests/test_four_minute_banks.py
rtk git commit -m "feat: add institutional terminal quote matrix"
```

Expected / 预期：one commit containing only the two allowed files. / 生成一个只包含两份允许文件的提交。

## Task 2: Polish the Entry Workspace and Request States / 完善录入工作区与请求状态

**Files / 文件:**

- Modify / 修改: `tests/test_four_minute_banks.py` (`QuoteMatrixFrontendTests`)
- Modify / 修改: `static/index.html` (workspace markup/styles, tab behavior, loading/error helpers, entry rendering)

- [ ] **Step 1: Add failing workspace and inline-state contracts / 新增会失败的工作区与行内状态契约测试**

Add these methods: / 新增以下方法：

```python
def test_entry_workspace_has_professional_structure_and_live_regions(self):
    required = [
        'class="workspace-tabs"',
        'class="entry-layout"',
        'class="entry-panel"',
        'class="recent-panel"',
        'class="field"',
        'class="result-card"',
        'aria-live="polite"',
        'role="status"',
        'type="date" id="entryDate"',
        'type="time" id="entryTime"',
        '>现在</button>',
    ]
    for token in required:
        self.assertIn(token, self.html)
    self.assertNotIn('id="entryDate" style=', self.html)
    self.assertNotIn('id="entryTime" style=', self.html)

def test_loading_and_request_failures_are_inline_and_retryable(self):
    for token in [
        "function renderQuoteSkeleton()",
        "function showInlineError(containerId, message)",
        "报价暂时无法获取，系统将在下一轮自动重试",
        "最近录入暂时无法获取，请稍后重试",
        "图表暂时无法获取，请稍后重试",
    ]:
        self.assertIn(token, self.html)
    self.assertNotIn("alert(", self.html)
```

- [ ] **Step 2: Run the two tests and confirm RED / 运行两项测试并确认 RED**

```bash
rtk /Users/jun/Downloads/projects/.venvs/forex-monitor-web/bin/python -m unittest \
  tests.test_four_minute_banks.QuoteMatrixFrontendTests.test_entry_workspace_has_professional_structure_and_live_regions \
  tests.test_four_minute_banks.QuoteMatrixFrontendTests.test_loading_and_request_failures_are_inline_and_retryable -v
```

Expected / 预期：both fail because the old form and console-only errors are still present. / 两项均失败，因为旧表单结构与仅控制台错误仍然存在。

- [ ] **Step 3: Add the workspace, field, result, recent-entry, skeleton, and error styles / 添加工作区、字段、结果、最近记录、骨架与错误样式**

Append these selectors inside the existing `<style>` block: / 在现有 `<style>` 中加入：

```css
.workspace-panel{margin-top:16px;overflow:hidden}
.workspace-tabs{display:flex;align-items:center;gap:4px;padding:8px 10px 0;border-bottom:1px solid var(--line-soft)}
.tab-btn{min-height:40px;padding:0 14px;border:0;border-bottom:2px solid transparent;background:transparent;color:var(--muted);font-size:12px;font-weight:600;cursor:pointer;transition:color .18s ease,border-color .18s ease}
.tab-btn:hover{color:#d9e2e4}
.tab-btn.active{border-bottom-color:var(--accent);color:var(--accent)}
.tab-content{padding:18px}
.tab-pane{display:none}
.tab-pane.active{display:block}
.entry-layout{display:grid;grid-template-columns:minmax(0,1.45fr) minmax(280px,.55fr);gap:16px}
.entry-panel,.recent-panel{min-width:0;padding:18px;border:1px solid var(--line-soft);border-radius:10px;background:#0b131b}
.section-kicker{margin-bottom:14px;color:var(--muted);font-size:10px;font-weight:650;letter-spacing:.14em;text-transform:uppercase}
.form-grid{display:grid;grid-template-columns:repeat(4,minmax(120px,1fr));gap:12px}
.field{display:grid;gap:6px;color:var(--muted);font-size:11px}
.field-wide{grid-column:span 2}
.field select,.field input,.chart-controls select,.chart-controls input{width:100%;height:38px;padding:0 10px;border:1px solid var(--line);border-radius:var(--control-radius);outline:0;background:#081018;color:var(--text);font-size:13px}
.form-actions{display:flex;align-items:center;justify-content:flex-end;gap:9px;margin-top:14px}
.btn{min-height:38px;padding:0 17px;border:1px solid transparent;border-radius:var(--control-radius);background:var(--accent);color:#06110e;font-size:12px;font-weight:700;cursor:pointer;transition:background-color .18s ease,transform .18s ease}
.btn:hover{background:#70e3c2}
.btn:active{transform:translateY(1px)}
.btn-secondary{border-color:var(--line);background:transparent;color:#c4d0d3}
.result-card{min-height:108px;margin-top:16px;padding:15px;border:1px solid var(--line-soft);border-radius:9px;background:#081018;color:#aebdc1;font-size:12px;line-height:1.65}
.result-card b{color:var(--text)}
.result-positive{color:var(--bid)}
.result-negative{color:var(--ask)}
.recent-list{display:grid;gap:8px}
.recent-entry{display:grid;gap:3px;padding:10px 0;border-bottom:1px solid var(--line-soft);font-size:11px}
.recent-entry:last-child{border-bottom:0}
.recent-entry-main{color:#d0dadd;font-variant-numeric:tabular-nums}
.recent-entry-meta{color:var(--muted)}
.inline-state{display:grid;place-items:center;min-height:110px;padding:18px;color:var(--muted);font-size:12px;text-align:center}
.inline-error{color:var(--danger)}
.skeleton-line{height:8px;border-radius:4px;background:#17252f}
.skeleton-matrix .skeleton-line{width:72%}
```

- [ ] **Step 4: Replace the old tab bar and entry/chart workspace markup / 替换旧标签栏与录入、图表工作区结构**

Replace the old `.tab-bar`, `.tab-content`, and the following `</main>` with this complete block: / 用以下完整结构替换旧 `.tab-bar`、`.tab-content` 及其后的 `</main>`：

```html
  <section class="panel workspace-panel" aria-label="报价操作工作区">
    <nav class="workspace-tabs" role="tablist" aria-label="工作区视图">
      <button class="tab-btn active" type="button" role="tab" aria-selected="true" aria-controls="tab-entry" data-tab="entry">录入报价</button>
      <button class="tab-btn" type="button" role="tab" aria-selected="false" aria-controls="tab-chart" data-tab="chart">历史图表</button>
    </nav>

    <div class="tab-content">
      <section class="tab-pane active" id="tab-entry" role="tabpanel">
        <div class="entry-layout">
          <div class="entry-panel">
            <div class="section-kicker">QUOTE ENTRY / 报价录入</div>
            <div class="form-grid">
              <label class="field">货币对
                <select id="entryPair">
                  <option>USDCNY</option><option>EURCNY</option><option>HKDCNY</option><option>JPYCNY</option>
                </select>
              </label>
              <label class="field field-wide">银行
                <select id="entryBank">
                  <option>中国银行</option><option>招商银行</option><option>建设银行</option><option>杭州银行</option>
                  <option>工商银行</option><option>农业银行</option><option>邮储银行</option><option>民生银行</option>
                </select>
              </label>
              <label class="field">方向
                <select id="entryDir"><option>买入价</option><option>卖出价</option></select>
              </label>
              <label class="field">报价
                <input type="number" id="entryQuote" step="0.0001" placeholder="7.2400" inputmode="decimal">
              </label>
              <label class="field">日期
                <input type="date" id="entryDate">
              </label>
              <label class="field">时间
                <input type="time" id="entryTime">
              </label>
            </div>
            <div class="form-actions">
              <button class="btn btn-secondary" type="button" onclick="document.getElementById('entryDate').value='';document.getElementById('entryTime').value=''">现在</button>
              <button class="btn" type="button" onclick="submitEntry()">录入并计算</button>
            </div>
            <div class="result-card" id="entryResult" role="status" aria-live="polite">录入后显示计算结果</div>
          </div>

          <aside class="recent-panel" aria-labelledby="recentTitle">
            <div class="section-kicker" id="recentTitle">RECENT ENTRIES / 最近录入</div>
            <div class="recent-list" id="entryRecent" role="status" aria-live="polite">暂无录入记录</div>
          </aside>
        </div>
      </section>

      <section class="tab-pane" id="tab-chart" role="tabpanel">
        <div class="section-kicker">HISTORICAL VIEW / 历史走势</div>
        <div class="chart-controls">
          <label class="field">货币对
            <select id="chartPair" onchange="loadChart()">
              <option>USDCNY</option><option>EURCNY</option><option>HKDCNY</option><option>JPYCNY</option>
            </select>
          </label>
          <label class="field">银行
            <select id="chartBank" onchange="loadChart()">
              <option>中国银行</option><option>招商银行</option><option>建设银行</option><option>杭州银行</option>
              <option>工商银行</option><option>农业银行</option><option>邮储银行</option><option>民生银行</option>
            </select>
          </label>
          <label class="field">日期
            <input type="date" id="chartDate" onchange="loadChart()">
          </label>
        </div>
        <div id="chart" role="img" aria-label="银行报价与市场成本历史走势"></div>
      </section>
    </div>
  </section>
</main>
```

- [ ] **Step 5: Keep tab ARIA state synchronized / 同步标签页 ARIA 状态**

Replace the current tab listener with: / 用以下代码替换当前标签监听器：

```javascript
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(button => {
      const active = button === btn;
      button.classList.toggle('active', active);
      button.setAttribute('aria-selected', String(active));
    });
    document.querySelectorAll('.tab-pane').forEach(pane => {
      pane.classList.toggle('active', pane.id === 'tab-' + btn.dataset.tab);
    });
    if (btn.dataset.tab === 'chart') {
      setTimeout(() => { if (chartInstance) chartInstance.resize(); else loadChart(); }, 50);
    }
  });
});
```

- [ ] **Step 6: Add skeleton and inline-error helpers / 添加骨架与行内错误辅助函数**

Place these functions immediately after `BANK_NAMES`: / 将以下函数放在 `BANK_NAMES` 之后：

```javascript
function renderQuoteSkeleton() {
  const el = document.getElementById('quotesContainer');
  const headers = PAIRS.map(pair => '<div><b>' + pair + '</b><span>买入&nbsp;&nbsp;卖出</span></div>').join('');
  const rows = BANK_NAMES.map(source =>
    '<div class="source-row"><div class="source-name"><span>' + source + '</span><small class="source-time">加载中</small></div>'
    + PAIRS.map(() => '<div class="quote-cell"><span class="skeleton-line"></span></div>').join('')
    + '<div class="quote-status"><span class="skeleton-line"></span></div></div>'
  ).join('');
  el.innerHTML = '<div class="quote-matrix skeleton-matrix" role="status" aria-live="polite" aria-label="正在加载外汇报价">'
    + '<div class="quote-head"><div class="source-name">数据来源</div>' + headers + '<div>状态</div></div>' + rows + '</div>';
}

function showInlineError(containerId, message) {
  const el = document.getElementById(containerId);
  const state = document.createElement('div');
  state.className = 'inline-state inline-error';
  state.setAttribute('role', 'status');
  state.setAttribute('aria-live', 'polite');
  state.textContent = message;
  el.replaceChildren(state);
}
```

Call `renderQuoteSkeleton();` once immediately before the first `fetchQuotes();` at the bottom of the script. Do not add a new timer. / 在脚本底部首次调用 `fetchQuotes();` 之前调用一次 `renderQuoteSkeleton();`，不要新增定时器。

- [ ] **Step 7: Show request failures inline and render recent entries as structured rows / 行内显示请求失败并结构化渲染最近记录**

Use explicit HTTP checks in `fetchQuotes` and `loadChart`: / 在 `fetchQuotes` 与 `loadChart` 中加入明确的 HTTP 检查：

```javascript
async function fetchQuotes() {
  try {
    const res = await fetch('/api/quotes');
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    renderQuotes(data.cfets || {}, data.banks || {}, data.timestamp);
  } catch(e) {
    console.error('fetchQuotes error:', e);
    showInlineError('quotesContainer', '报价暂时无法获取，系统将在下一轮自动重试');
  }
}
```

```javascript
async function loadChart() {
  const pair = document.getElementById('chartPair').value;
  const bank = document.getElementById('chartBank').value;
  const dateInput = document.getElementById('chartDate').value;
  let url = '/api/chart?pair=' + pair + '&bank=' + encodeURIComponent(bank);
  if (dateInput) url += '&date=' + dateInput;
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    renderChart(data);
  } catch(e) {
    console.error('loadChart error:', e);
    if (chartInstance) { chartInstance.dispose(); chartInstance = null; }
    showInlineError('chart', '图表暂时无法获取，请稍后重试');
  }
}
```

Replace `loadEntries` with a DOM-based renderer so each row has a readable hierarchy and API text is not injected as HTML: / 用基于 DOM 的渲染替换 `loadEntries`，让每条记录层级清楚，并避免将 API 文本直接注入 HTML：

```javascript
async function loadEntries() {
  const el = document.getElementById('entryRecent');
  try {
    const res = await fetch('/api/entries?limit=10');
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    if (!data.entries || data.entries.length === 0) {
      el.textContent = '暂无录入记录';
      return;
    }
    const fragment = document.createDocumentFragment();
    for (const entry of data.entries) {
      const row = document.createElement('div');
      row.className = 'recent-entry';
      const main = document.createElement('div');
      main.className = 'recent-entry-main';
      main.textContent = entry.pair + ' · ' + entry.bank + ' · ' + entry.direction + ' ' + entry.quote.toFixed(4);
      const meta = document.createElement('div');
      meta.className = 'recent-entry-meta';
      meta.textContent = entry.time + ' · 银行赚取 ' + entry.bp_vs_market + 'bp';
      row.append(main, meta);
      fragment.appendChild(row);
    }
    el.replaceChildren(fragment);
  } catch(e) {
    console.error('loadEntries error:', e);
    showInlineError('entryRecent', '最近录入暂时无法获取，请稍后重试');
  }
}
```

- [ ] **Step 8: Replace inline result colors with semantic classes / 用语义类替换结果中的行内颜色**

In the success branch of `submitEntry`, use: / 在 `submitEntry` 成功分支中使用：

```javascript
const market = data.market_cost.toFixed(4);
const bankPrice = dir === '买入价' ? data.bank_bid.toFixed(4) : data.bank_ask.toFixed(4);
const priceLabel = bank + (dir === '买入价' ? '买入价' : '卖出价');
const compareLabel = data.compare_time || '当前实时';
const bankTone = data.bp_vs_bank_price >= 0 ? 'result-positive' : 'result-negative';
document.getElementById('entryResult').innerHTML =
  '<div>比较基准 <b>' + compareLabel + '</b></div>'
  + '<div>市场成本 ' + market + ' · 你的报价 ' + quote.toFixed(4) + '</div>'
  + '<div>银行赚取 <strong class="result-positive">' + data.bp_vs_market + 'bp</strong></div>'
  + '<div>' + priceLabel + ' ' + bankPrice + ' · 你比银行牌价'
  + '<strong class="' + bankTone + '">' + (data.bp_vs_bank_price >= 0 ? '优惠 ' : '更差 ')
  + Math.abs(data.bp_vs_bank_price) + 'bp</strong></div>';
loadEntries();
```

Keep the existing invalid-number and API-error text in `entryResult`; do not introduce `alert()`. / 保留现有无效数字与 API 错误在 `entryResult` 中的文字提示，不引入 `alert()`。

- [ ] **Step 9: Run all frontend contracts / 运行全部前端契约测试**

```bash
rtk /Users/jun/Downloads/projects/.venvs/forex-monitor-web/bin/python -m unittest tests.test_four_minute_banks.QuoteMatrixFrontendTests -v
```

Expected / 预期：`Ran 10 tests` and `OK`. / 显示 `Ran 10 tests` 与 `OK`。

- [ ] **Step 10: Commit the workspace and states / 提交工作区与状态设计**

```bash
rtk git add static/index.html tests/test_four_minute_banks.py
rtk git commit -m "feat: polish quote entry workspace and states"
```

## Task 3: Finish the Chart Theme, Focus States, and Responsive Layout / 完成图表主题、焦点状态与响应式布局

**Files / 文件:**

- Modify / 修改: `tests/test_four_minute_banks.py` (`QuoteMatrixFrontendTests`)
- Modify / 修改: `static/index.html` (responsive CSS, chart palette, resize listener)

- [ ] **Step 1: Add failing chart and responsive contracts / 新增会失败的图表与响应式契约测试**

Add these methods: / 新增以下方法：

```python
def test_chart_uses_terminal_palette_and_one_resize_listener(self):
    for token in [
        "{name:'银行卖价', color:'#ff857a'",
        "{name:'银行成本', color:'#d8a84e'",
        "{name:'市场成本', color:'#98a6ae'",
        "{name:'银行买价', color:'#56d8b3'",
        "backgroundColor: '#0e1620'",
        "backgroundColor: 'rgba(14,22,32,.96)'",
    ]:
        self.assertIn(token, self.html)
    self.assertEqual(self.html.count("window.addEventListener('resize'"), 1)

def test_focus_and_mobile_layout_keep_scroll_inside_quote_matrix(self):
    for token in [
        ":focus-visible",
        "overflow-x:hidden",
        ".quotes{overflow-x:auto}",
        "@media(max-width:640px)",
        ".entry-layout{grid-template-columns:1fr}",
        ".app-shell{width:calc(100% - 16px)",
    ]:
        self.assertIn(token, self.html)
    self.assertEqual(self.html.count("overflow-x:auto"), 1)
```

- [ ] **Step 2: Run both tests and confirm RED / 运行两项测试并确认 RED**

```bash
rtk /Users/jun/Downloads/projects/.venvs/forex-monitor-web/bin/python -m unittest \
  tests.test_four_minute_banks.QuoteMatrixFrontendTests.test_chart_uses_terminal_palette_and_one_resize_listener \
  tests.test_four_minute_banks.QuoteMatrixFrontendTests.test_focus_and_mobile_layout_keep_scroll_inside_quote_matrix -v
```

Expected / 预期：both fail because the chart still uses the old blue/green/red palette and the mobile entry layout is not yet complete. / 两项均失败，因为图表仍使用旧色板，手机端录入布局尚未完成。

- [ ] **Step 3: Add keyboard focus, chart controls, and responsive CSS / 添加键盘焦点、图表控件与响应式 CSS**

Add or replace with these exact rules: / 添加或替换为以下规则：

```css
:is(button,select,input):focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.chart-controls{display:grid;grid-template-columns:160px minmax(220px,320px) 170px;gap:12px;align-items:end;margin-bottom:14px}
#chart{width:100%;height:440px;border:1px solid var(--line-soft);border-radius:10px;overflow:hidden}
@media(max-width:860px){
  .entry-layout{grid-template-columns:1fr}
  .form-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
  .chart-controls{grid-template-columns:repeat(3,minmax(0,1fr))}
}
@media(max-width:640px){
  .app-shell{width:calc(100% - 16px);margin:12px auto 24px}
  .terminal-header{align-items:flex-start;flex-direction:column}
  .live-meta{width:100%;justify-content:space-between}
  .panel-heading{padding:13px 12px}
  .quote-matrix{min-width:820px}
  .quote-head,.source-row{grid-template-columns:108px repeat(4,minmax(142px,1fr)) 86px}
  .tab-content{padding:10px}
  .entry-layout{grid-template-columns:1fr}
  .entry-panel,.recent-panel{padding:14px}
  .form-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
  .field-wide{grid-column:span 2}
  .chart-controls{grid-template-columns:1fr}
  #chart{height:330px}
}
```

Remove the old responsive rules that conflict with these values. Keep `.quotes{overflow-x:auto}` as the only horizontal scrolling container. / 删除与上述值冲突的旧响应式规则，并让 `.quotes{overflow-x:auto}` 成为唯一的横向滚动容器。

- [ ] **Step 4: Apply the approved terminal palette to ECharts / 将已确认的终端色板应用到 ECharts**

Replace `LINE_STYLE` with: / 替换 `LINE_STYLE`：

```javascript
const LINE_STYLE = [
  {name:'银行卖价', color:'#ff857a', width:1.5},
  {name:'银行成本', color:'#d8a84e', width:1.5, type:'dashed'},
  {name:'市场成本', color:'#98a6ae', width:1.5},
  {name:'银行买价', color:'#56d8b3', width:1.5},
];
```

Use the same four colors in the `series` array and explicitly pass each color to the line and points: / 在 `series` 中使用同样四种颜色，并明确传给曲线与数据点：

```javascript
const series = [
  {name:'银行卖价', data:data.asks, color:'#ff857a'},
  {name:'银行成本', data:data.costs, color:'#d8a84e'},
  {name:'市场成本', data:data.mids, color:'#98a6ae'},
  {name:'银行买价', data:data.bids, color:'#56d8b3'},
].map((seriesItem, index) => ({
  name: seriesItem.name,
  type: 'line',
  data: seriesItem.data,
  connectNulls: true,
  smooth: false,
  symbol: 'circle',
  symbolSize: 2,
  lineStyle: {
    color: seriesItem.color,
    width: LINE_STYLE[index].width,
    type: LINE_STYLE[index].type || 'solid',
  },
  itemStyle: { color: seriesItem.color },
}));
```

Replace the ECharts surface and axis styling with these values: / 将 ECharts 表面与坐标样式替换为：

```javascript
backgroundColor: '#0e1620',
grid: { left: 54, right: 18, top: 38, bottom: 32 },
tooltip: {
  trigger: 'axis',
  backgroundColor: 'rgba(14,22,32,.96)',
  borderColor: '#2a3b47',
  textStyle: { color: '#dce5e8', fontSize: 12 },
```

Inside the tooltip formatter use: / tooltip formatter 内使用：

```javascript
const colors = ['#ff857a','#d8a84e','#98a6ae','#56d8b3'];
```

Also replace the two source-quality marker colors inside that formatter: use `#56d8b3` for “精确” and `#d8a84e` for “推导”. / 同时替换 formatter 内两个来源质量标记色：“精确”使用 `#56d8b3`，“推导”使用 `#d8a84e`。

Use these legend and axis colors while preserving the current data, four-decimal formatter, zoom, and series names: / 使用以下图例和坐标颜色，同时保留现有数据、四位小数格式、缩放和系列名称：

```javascript
legend: {
  data: ['银行卖价','银行成本','市场成本','银行买价'],
  textStyle: { color: '#91a1a8', fontSize: 10 },
  top: 8,
},
xAxis: {
  type: 'category',
  data: data.times,
  axisLine: { lineStyle: { color: '#2c3b46' } },
  axisLabel: { color: '#7f9098', fontSize: 10 },
  splitLine: { show: true, lineStyle: { color: '#192833', width: 0.5 } },
},
yAxis: {
  type: 'value',
  scale: true,
  axisLine: { lineStyle: { color: '#2c3b46' } },
  axisLabel: { color: '#7f9098', fontSize: 10, formatter: function(v) { return v.toFixed(4); } },
  splitLine: { show: true, lineStyle: { color: '#192833', width: 0.5 } },
},
```

- [ ] **Step 5: Register chart resize once / 只注册一次图表缩放监听**

Immediately after `let chartInstance = null;`, add: / 紧跟 `let chartInstance = null;` 添加：

```javascript
window.addEventListener('resize', () => {
  if (chartInstance) chartInstance.resize();
});
```

Remove the `window.addEventListener` call from inside `renderChart` so repeated data refreshes do not accumulate listeners. / 删除 `renderChart` 内部的监听注册，避免每次数据刷新都累积监听器。

- [ ] **Step 6: Run the frontend and full suites / 运行前端与完整测试**

```bash
rtk /Users/jun/Downloads/projects/.venvs/forex-monitor-web/bin/python -m unittest tests.test_four_minute_banks.QuoteMatrixFrontendTests -v
rtk /Users/jun/Downloads/projects/.venvs/forex-monitor-web/bin/python -m unittest discover -s tests -v
```

Expected / 预期：frontend shows `Ran 12 tests` and `OK`; full suite shows `Ran 36 tests` and `OK`. / 前端显示 `Ran 12 tests` 与 `OK`，完整测试显示 `Ran 36 tests` 与 `OK`。

- [ ] **Step 7: Commit chart and responsive polish / 提交图表与响应式完善**

```bash
rtk git add static/index.html tests/test_four_minute_banks.py
rtk git commit -m "feat: finish terminal chart and responsive polish"
```

## Task 4: Automated and Browser Acceptance / 自动化与浏览器验收

**Files / 文件:**

- Verify only / 仅验证: `static/index.html`
- Verify only / 仅验证: `tests/test_four_minute_banks.py`
- Protected runtime data / 受保护运行数据: `data/`

- [ ] **Step 1: Run final automated verification / 运行最终自动验证**

Use the `verification-before-completion` skill before claiming success. / 在宣布完成前使用 `verification-before-completion` 技能。

```bash
rtk /Users/jun/Downloads/projects/.venvs/forex-monitor-web/bin/python -m unittest discover -s tests -v
rtk /Users/jun/Downloads/projects/.venvs/forex-monitor-web/bin/python -m compileall -q server.py database.py bank_fetcher.py tests
rtk git diff --check
```

Expected / 预期：36 tests pass; `compileall` and `git diff --check` produce no error output. / 36 项测试通过，`compileall` 与 `git diff --check` 没有错误输出。

- [ ] **Step 2: Confirm change scope and data safety / 确认改动范围与数据安全**

```bash
rtk git diff --name-only HEAD~3..HEAD
rtk git status --short
```

Expected / 预期：the three implementation commits contain only `static/index.html` and `tests/test_four_minute_banks.py`; status may show only `?? data/`. Never stage `data/`. / 三个实施提交只包含两份允许文件；状态最多只显示 `?? data/`，绝不暂存 `data/`。

- [ ] **Step 3: Confirm the local server and live API / 确认本地服务与实时 API**

If the existing server is still running, reuse it. Otherwise start it from the worktree with: / 如现有服务仍在运行则复用，否则在工作树中启动：

```bash
rtk /Users/jun/Downloads/projects/.venvs/forex-monitor-web/bin/python server.py
```

In another terminal session verify: / 在另一个终端会话验证：

```bash
rtk curl -fsS http://127.0.0.1:8000/api/quotes
```

Expected / 预期：HTTP 200 JSON containing `cfets`, `banks`, and `timestamp`. Missing bank values may truthfully remain absent or render as `--`. / 返回 HTTP 200 JSON，包含 `cfets`、`banks`、`timestamp`；银行缺失值可以真实缺失，并在界面显示为 `--`。

- [ ] **Step 4: Desktop browser acceptance at 1280 × 900 / 在 1280 × 900 桌面视口验收**

Open `http://127.0.0.1:8000/` with the in-app browser and verify all of the following: / 用应用内浏览器打开本地地址并逐项验证：

1. Header shows FX mark, Chinese title, English subtitle, live status, and last update without emoji. / 顶部栏显示 FX 标识、中英文标题、实时状态与最后更新时间，且没有 emoji。
2. Matrix shows CFETS plus eight banks, four currency pairs, 36 bid/ask cells, and a status column. / 矩阵显示 CFETS、八家银行、四个货币对、36 个买卖价单元格和状态列。
3. Prices are aligned to four decimals; missing values are `--`; the page body has no horizontal overflow. / 价格四位小数对齐，缺失值为 `--`，页面主体无横向溢出。
4. Entry tab uses two columns; “Now,” current-time entry, historical-time entry, results, and recent rows all work. / 录入页为两栏，“现在”、当前时间录入、历史时间录入、结果和最近记录均可用。
5. Chart tab fills the panel; all filters work; tooltip, legend, lines, empty state, and error state remain readable. / 图表页填满面板，全部筛选可用，提示框、图例、曲线、空状态与错误状态清晰可读。

- [ ] **Step 5: Mobile browser acceptance at 390 × 844 / 在 390 × 844 手机视口验收**

Verify: / 验证：

1. The app shell fits the viewport and the body does not scroll horizontally. / 应用外壳适配视口，页面主体不横向滚动。
2. Only the quote matrix scrolls horizontally; the source column remains visible while scrolling. / 只有报价矩阵横向滚动，滚动时来源列保持可见。
3. Entry and recent panels stack vertically; fields remain readable; buttons remain easy to tap. / 录入与最近记录纵向排列，字段可读，按钮易于点击。
4. The chart canvas is visible at 330 px height and tab switching does not leave an empty chart. / 图表画布高度为 330 像素，切换标签后不会出现空白图表。
5. Keyboard focus is visible on buttons, selects, and inputs. / 按钮、下拉框与输入框的键盘焦点清楚可见。

- [ ] **Step 6: Run the pre-delivery review and report findings / 执行交付前审查并报告结果**

Use the `pre-delivery-review` skill. Fix only issues directly caused by this redesign, rerun the affected test first, then rerun all 36 tests. If a fix is required, commit it as: / 使用 `pre-delivery-review` 技能。只修复本次重设计直接造成的问题，先重跑相关测试，再重跑全部 36 项测试。如有修复，提交为：

```bash
rtk git add static/index.html tests/test_four_minute_banks.py
rtk git commit -m "fix: address terminal interface review findings"
```

If no issue is found, do not create an empty commit. / 如未发现问题，不创建空提交。

## Task 5: Handoff Without Cloud Deployment / 交付但不部署云端

- [ ] **Step 1: Present the verified local result to the user / 向用户展示已验证的本地结果**

Report the local URL, test count, changed files, and browser acceptance result in Chinese. Any document requiring user review must remain bilingual. / 用中文报告本地地址、测试数量、改动文件与浏览器验收结果；需要用户审阅的文档继续保持中英文双语。

- [ ] **Step 2: Preserve the future cloud database inheritance guard / 保留未来云端历史数据库继承保护**

Do not run `scp`, `rsync`, Docker deployment, or remote restart commands. The later cloud release must deploy code/static assets only, keep the existing `/app/data/forex_data.db`, back it up first, compare table counts and latest timestamps before and after, and require explicit user approval. / 不运行 `scp`、`rsync`、Docker 部署或远程重启命令。未来云端发布只能更新代码与静态资源，必须保留既有 `/app/data/forex_data.db`，先备份，再核对发布前后的表记录数与最新时间，并取得用户明确批准。

- [ ] **Step 3: Leave the worktree ready for local user acceptance / 保持工作树可供用户本地验收**

Final expected status: local server available at `http://127.0.0.1:8000/`, all tests green, no tracked edits, and only untracked runtime `data/` if present. / 最终预期：本地地址可访问，全部测试通过，无已跟踪改动；如存在运行数据，只留下未跟踪的 `data/`。
