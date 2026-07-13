# Four Minute-Level Bank Expansion / 四家分钟级银行扩展

## Goal / 目标

Add four official minute-level bank quote sources—Industrial and Commercial Bank of China, Agricultural Bank of China, Postal Savings Bank of China, and China Minsheng Bank—while keeping every displayed and stored bank price truthful, fresh, and traceable.

新增四个官方分钟级银行报价源——中国工商银行、中国农业银行、中国邮政储蓄银行和中国民生银行，并确保页面展示和数据库保存的每一条银行报价都真实、有效且可追踪。

After this change, the system contains eight banks plus the CFETS market reference, for nine visible data sources in total. CFETS is not counted as a bank.

改造后，系统共有八家银行和一个 CFETS 市场基准，页面合计展示九个数据来源。CFETS 不计入银行数量。

## Confirmed Scope / 已确认范围

- Add real bid and ask quotes for USD/CNY, EUR/CNY, HKD/CNY, and JPY/CNY from the four new banks.
- Poll the official sources once per minute through the existing scheduler.
- Store only accepted real quotes in the existing SQLite bank history table.
- Add all four banks to live quotes, manual quote entry, and historical chart selection.
- Replace the current long quote-card list with the approved compact quote matrix.
- Keep implementation and testing local until the user separately approves cloud deployment.

- 为四家新增银行接入 USD/CNY、EUR/CNY、HKD/CNY 和 JPY/CNY 的真实买入价与卖出价。
- 继续使用现有调度器，每分钟访问一次银行官方数据源。
- 只有通过校验的真实报价才写入现有 SQLite 银行历史表。
- 在实时报价、手工报价录入和历史图表中加入四家银行。
- 用已批准的紧凑报价矩阵替换当前较长的报价卡片列表。
- 在用户单独批准上云之前，只在本地开发和测试。

## Official Data Sources / 官方数据源

| Bank / 银行 | Official interface / 官方接口 | Format / 格式 | Observed source cadence / 已观测源时间频率 |
|---|---|---|---|
| ICBC / 工商银行 | `POST https://papi.icbc.com.cn/exchanges/ns/getLatest` | JSON | About 60 seconds / 约 60 秒 |
| ABC / 农业银行 | `GET https://ewealth.abchina.com/app/data/api/DataService/ExchangeRateV2` | JSON | About 60 seconds / 约 60 秒 |
| PSBC / 邮储银行 | `GET https://s.psbc.com/portal/PsbcService/foreignexchange/curr` | JSONP | About 60–80 seconds / 约 60–80 秒 |
| CMBC / 民生银行 | `POST https://www.cmbc.com.cn/gw/po_web/queryExRateByForex.do` | JSON | About 60 seconds / 约 60 秒 |

The selected CMBC endpoint has been re-verified over HTTPS. A changing official timestamp with an unchanged price is valid; it produces a truthful flat segment in the historical chart.

民生银行接口已经重新确认可通过 HTTPS 使用。银行官方时间发生变化但价格不变属于正常情况；历史图中的水平线代表真实报价没有变化。

## Backend Architecture / 后端架构

### `bank_fetcher.py`

Add one fetcher per new bank. Each fetcher performs only three jobs: request the official interface, parse the four required currencies, and return the normalized quote structure.

为每家新增银行增加一个抓取函数。每个函数只负责三件事：请求银行官方接口、解析四种目标货币、返回统一格式的报价。

Normalized quote example / 统一报价示例：

```python
{
    "USDCNY": {
        "bid": 6.7650,
        "ask": 6.7946,
        "mid": 6.7798,
        "source_time": "2026-07-13 18:36:00",
    }
}
```

No new Python dependency is required. ICBC, ABC, and CMBC use normal JSON parsing. PSBC removes only the JSONP callback wrapper before JSON parsing.

不引入新的 Python 依赖。工商银行、农业银行和民生银行直接解析 JSON；邮储银行只需先去掉 JSONP 回调外壳，再按 JSON 解析。

### `server.py`

The existing `fetch_and_save()` cycle calls the four new fetchers, combines successful results with existing bank results, saves accepted bid/ask rows, and exposes current-cycle data through `/api/quotes`.

现有 `fetch_and_save()` 每轮调用四个新增抓取函数，把成功结果与现有银行结果合并，保存通过校验的买入价和卖出价，并通过 `/api/quotes` 提供本轮数据。

The four new banks never use an indefinite last-success cache. If a current fetch fails or is stale, that bank or pair is absent from the live cache and the frontend displays `--`.

四家新增银行不使用无限期的上次成功缓存。本轮抓取失败或报价过期时，该银行或货币对不会进入实时缓存，前端显示 `--`。

## Freshness and Integrity Rules / 时效与完整性规则

A parsed quote is accepted only when all applicable checks pass:

一条解析后的报价只有在适用检查全部通过后才会被接受：

1. The official source timestamp is no more than three minutes old. / 银行官方时间不超过三分钟。
2. Bid and ask are numeric and greater than zero. / 买入价和卖出价是大于零的数字。
3. Bid is less than or equal to ask. / 买入价小于或等于卖出价。
4. Currency and unit mapping are explicitly known. / 货币代码和报价单位有明确映射。
5. Missing or invalid pairs are skipped individually rather than fabricated. / 缺失或异常的货币对单独跳过，不生成模拟价格。

Price units remain compatible with existing history: USD, EUR, and HKD are CNY per one foreign-currency unit; JPY is CNY per 100 yen.

价格单位与现有历史保持一致：美元、欧元和港币按一单位外币折合人民币展示；日元按一百日元折合人民币展示。

## Frontend Design / 前端设计

The approved design is **Option A: Compact Quote Matrix**.

已批准的设计是 **方案 A：紧凑报价矩阵**。

- Rows: CFETS followed by eight banks. / 行：CFETS，其后为八家银行。
- Columns: data source, four currency pairs, and status. / 列：数据来源、四个货币对和状态。
- Each currency cell shows green bid and red ask only. / 每个货币格只显示绿色买入价和红色卖出价。
- Repeated market and bank midpoint text is removed from the matrix to keep it readable. / 矩阵中不再重复显示市场价和银行中间成本价，避免拥挤。
- CFETS remains the dedicated market-reference row. / CFETS 继续作为独立的市场基准行。
- Missing data displays `--` with “No fresh data.” / 缺少有效数据时显示 `--` 和“暂无新数据”。
- A valid source displays “Normal” and its official source time when available. / 有效数据显示“正常”，并在可取得时显示银行官方时间。
- When an existing source has no parseable official time, the interface labels the current-cycle fetch time as a fetch time rather than pretending it is an official quote time. / 现有数据源如果没有可解析的官方时间，界面会明确标注本轮抓取时间，不冒充银行官方报价时间。

On narrow screens the matrix remains a single comparison surface with compact cells; if the available width is insufficient, the quote area may scroll horizontally while the bank-name column remains visually identifiable.

在较窄窗口中，矩阵仍保持为同一个比较区域并使用紧凑单元格；宽度不足时允许报价区域横向滚动，同时确保银行名称容易识别。

## Existing Features / 现有功能

The manual quote-entry bank selector and historical-chart bank selector receive the same eight-bank list. Market midpoint and bank midpoint calculations remain available in manual comparison results and historical charts even though they are removed from the dense live matrix.

手工报价录入和历史图表的银行下拉框统一扩展为八家银行。虽然紧凑实时矩阵不再重复展示中间价，但市场中间价和银行成本中间价仍保留在手工比较结果和历史图表中。

## Database Behavior / 数据库行为

No database schema migration is needed. The current `bank_quotes.bank` text field already distinguishes banks, and the chart query already filters by bank name.

不需要修改数据库结构。现有 `bank_quotes.bank` 文本字段已经可以区分银行，历史图查询也已经按银行名称筛选。

Only current accepted bid/ask values are inserted. The change does not download, replace, delete, or rewrite existing historical data, and it does not backfill periods before a new bank is enabled.

数据库只写入当前通过校验的真实买入价和卖出价。本次改动不会下载、替换、删除或改写已有历史数据，也不会回补新增银行启用之前的历史。

## Error Handling / 错误处理

- HTTP errors, invalid JSON/JSONP, unknown units, stale timestamps, and invalid price relationships produce no accepted quote for the affected data.
- One bank failure does not block other banks or CFETS from being saved.
- The frontend always renders all expected rows so a missing bank is visible rather than silently disappearing.
- No market-derived synthetic bank quote is permitted.

- HTTP 错误、JSON/JSONP 异常、未知单位、过期时间或买卖价关系异常时，相关数据不会被接受。
- 一家银行失败不会阻止其他银行或 CFETS 保存数据。
- 前端始终渲染所有预期银行行，缺失数据会明确可见，而不是静默消失。
- 禁止根据市场价生成模拟银行报价。

## Verification and Acceptance / 验证与验收

- Parser tests cover valid responses for all four banks and all four pairs.
- Unit tests cover JPY scaling, source-time parsing, three-minute freshness rejection, non-positive prices, and bid-greater-than-ask rejection.
- Integration tests confirm failed or stale new-bank results are not cached or saved.
- Storage/chart tests confirm accepted new-bank bid/ask values appear in historical chart data alongside market mid values.
- Frontend checks confirm nine source rows, correct bid/ask coloring, `--` failure states, and all eight banks in entry/chart selectors.
- Regression tests preserve the Hangzhou Bank freshness fix and existing quote-entry/chart behavior.
- Local smoke tests verify `/`, `/api/quotes`, and `/api/chart` before user review.

- 解析测试覆盖四家银行的有效响应和四个货币对。
- 单元测试覆盖日元单位换算、官方时间解析、超过三分钟拒绝、非正数价格拒绝以及买入价高于卖出价拒绝。
- 集成测试确认失败或过期的新增银行结果不会被缓存或写入数据库。
- 存储与图表测试确认新增银行的真实买卖价能与市场中间价一起出现在历史图数据中。
- 前端检查确认九个来源行、正确的买卖价颜色、`--` 失败状态，以及录入和图表下拉框中的八家银行。
- 回归测试确保杭州银行时效修复以及现有报价录入和历史图功能不被破坏。
- 用户审阅前，在本地验证 `/`、`/api/quotes` 和 `/api/chart`。

## Non-Goals / 非目标

- Do not add banks that update only daily or materially slower than minute-level cadence. / 不接入只按日更新或明显慢于分钟级频率的银行。
- Do not redesign the quote-entry or historical-chart panels beyond adding bank options. / 除增加银行选项外，不重新设计报价录入和历史图面板。
- Do not backfill historical quotes from unofficial sources. / 不通过非官方来源回补历史报价。
- Do not deploy to Alibaba Cloud in this implementation stage. / 本开发阶段不部署到阿里云。

## Deployment Boundary / 上云边界

Implementation, automated tests, and browser verification happen locally. After the user reviews the running local system and explicitly approves deployment, the same reviewed code may be synchronized to Alibaba Cloud in a separate step.

开发、自动化测试和浏览器验证都在本地进行。用户检查本地运行效果并明确批准上云后，才在单独步骤中把同一份已审阅代码同步到阿里云。
