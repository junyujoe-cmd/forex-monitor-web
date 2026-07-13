# Hangzhou Bank Quote Freshness Fix / 杭州银行报价时效修复

## Goal / 目标

Ensure Hangzhou Bank prices shown as current are official, recent, and stored with real bid/ask history. Never present stale cached or synthetic prices as live bank quotes.

确保页面展示的杭州银行当前报价来自官方、时间有效，并能保存真实买入价和卖出价历史。绝不把过期缓存或模拟价格当作实时银行报价展示。

## Confirmed Root Cause / 已确认根因

- The configured `https://www.hccb.com.cn/...` endpoint now returns HTTP 403.
- The working official endpoint is `http://www.hzbank.com.cn/...`.
- The cloud process has displayed the last successful Hangzhou Bank quote from 2026-06-24 as if it were current.
- Market quotes continue to be saved every minute, but no Hangzhou Bank rows have been saved since 2026-06-24. The chart therefore has market values but null bank bid/ask values.
- The frontend generates synthetic bank prices from market mid-price offsets when real bank data is missing.

- 当前配置的 `https://www.hccb.com.cn/...` 已返回 HTTP 403。
- 可用的官方入口是 `http://www.hzbank.com.cn/...`。
- 云端进程把 2026-06-24 最后一次成功取得的杭州银行报价持续当作当前报价展示。
- 市场价仍每分钟保存，但杭州银行从 2026-06-24 后没有新记录，因此历史图只有市场价，买卖价为空。
- 当前端缺少真实银行数据时，会根据市场中间价生成模拟银行价。

## Selected Approach / 选定方案

Use the working official endpoint, parse the official source timestamp, reject quotes older than 10 minutes, remove indefinite Hangzhou Bank cache fallback, and remove all frontend synthetic bank-price fallback.

使用可用的杭州银行官方入口，解析官网更新时间，拒绝超过 10 分钟的报价，取消杭州银行无限期旧缓存，并删除前端所有模拟银行价逻辑。

## Code Changes / 代码改动

### `bank_fetcher.py`

- Replace the inaccessible Hangzhou Bank URL with the working official URL.
- Call `raise_for_status()` before parsing.
- Require at least five table cells before reading indexes 0, 1, 3, and 4.
- Parse the official update time from column 4.
- Reject a row when its official update time is more than 10 minutes old.
- Return `source_time` with each valid quote for traceability.

- 替换杭州银行失效地址。
- 解析前检查 HTTP 状态。
- 至少存在五列时才读取货币、现汇买入、卖出和更新时间。
- 解析官网第 4 列更新时间。
- 官网更新时间超过 10 分钟时拒绝该行。
- 每条有效报价保留 `source_time`，便于追踪。

### `server.py`

- Stop storing and reusing `last_hzb_rates`.
- Add Hangzhou Bank data to the current cache and database only when the current fetch succeeds.
- Preserve the existing storage schema; `source_time` remains API metadata and is not added to the SQLite table.

- 不再保存或复用 `last_hzb_rates`。
- 只有本轮抓取成功时，才把杭州银行数据加入当前缓存和数据库。
- 不修改现有数据库结构；`source_time` 只作为 API 元数据，不新增数据库字段。

### `static/index.html`

- Remove the `market mid ± configured offset` fallback for every bank.
- Display `--` whenever a bank has no real quote.
- Continue rendering real bid/ask values without changing the page layout.

- 删除所有银行“市场中间价 ± 预设偏移”的模拟价格。
- 银行没有真实报价时显示 `--`。
- 保持现有页面布局不变，真实买卖价继续正常展示。

## Data Behavior / 数据行为

- Existing cloud history is not deleted or rewritten.
- Missing Hangzhou Bank history after 2026-06-24 is not automatically backfilled.
- After the fix starts running, each successful cycle saves real Hangzhou Bank bid/ask rows and the current chart query returns them.

- 不删除或改写云端已有历史数据。
- 不自动回补 2026-06-24 之后缺失的杭州银行历史。
- 修复运行后，每次成功抓取都会保存真实杭州银行买卖价，现有历史图查询会自动读出。

## Error Handling / 错误处理

- HTTP errors, invalid table structure, invalid numbers, or stale timestamps produce no Hangzhou Bank quote.
- Missing real data is visible as `--`; it is never silently replaced with old or estimated data.

- HTTP 错误、表格结构异常、数字异常或时间过期时，不返回杭州银行报价。
- 缺少真实数据时明确显示 `--`，不再静默替换成旧数据或估算数据。

## Verification / 验证

- Unit test: valid official HTML returns four current currency pairs with correct bid/ask/source time.
- Unit test: HTTP 403 returns no quotes.
- Unit test: a source timestamp older than 10 minutes returns no quotes.
- Regression test: a failed Hangzhou Bank fetch is not replaced with a prior cached value.
- Storage/chart test: a successful current fetch writes Hangzhou Bank bid/ask values that the chart query returns.
- Frontend check: missing bank data renders `--` and contains no synthetic-price branch.
- Local HTTP smoke test: `/` and `/api/quotes` return 200 and current Hangzhou Bank values match the official page.

- 单元测试：有效官方 HTML 返回四个当前货币对及正确买卖价和官网时间。
- 单元测试：HTTP 403 时不返回报价。
- 单元测试：官网时间超过 10 分钟时不返回报价。
- 回归测试：杭州银行抓取失败后不会回退到旧缓存。
- 存储与图表测试：成功抓取后，数据库和图表查询都能返回杭州银行买卖价。
- 前端检查：缺少银行数据时显示 `--`，并且不存在模拟价格分支。
- 本地 HTTP 冒烟测试：主页和 API 返回 200，杭州银行当前值与官网一致。

## Deployment Boundary / 上云边界

Implementation and verification happen locally only. Cloud deployment requires a separate confirmation after local results are presented.

本轮只在本地实现和验证。展示本地结果后，必须再次确认才会部署到云端。
