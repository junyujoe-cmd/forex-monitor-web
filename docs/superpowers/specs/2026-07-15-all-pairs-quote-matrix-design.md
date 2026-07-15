# 全货币对外汇工作台设计 / All-Pairs FX Workbench Design

日期 / Date: 2026-07-15

状态 / Status: 已确认设计，等待书面规格复核 / Visual design approved, pending written-spec review

## 1. 目标 / Goal

中文：在一个桌面画面内完整显示 4 个货币对、CFETS 市场参考、8 家银行的买入价和卖出价，并保留紧凑的客户报价录入及计算结果。历史图表使用独立视图，不挤压实时行情。

English: Show all four currency pairs, the CFETS market reference, and bid/ask quotes from eight banks in one desktop viewport, while retaining compact quote entry and result areas. Historical charts use a separate view so they do not reduce the live quote area.

## 2. 实时总览 / Live Overview

中文：采用矩阵布局。4 个货币对作为行，CFETS 和 8 家银行作为列。用户无需切换货币对即可横向比较同一货币对的所有报价。

English: Use a matrix layout. The four currency pairs are rows, while CFETS and the eight banks are columns. Users can compare every source for a pair without switching tabs.

固定展示顺序 / Fixed display order:

1. USD/CNY
2. EUR/CNY
3. HKD/CNY
4. JPY/CNY

银行顺序 / Bank order:

1. 中国银行 / Bank of China
2. 招商银行 / China Merchants Bank
3. 建设银行 / China Construction Bank
4. 杭州银行 / Bank of Hangzhou
5. 工商银行 / Industrial and Commercial Bank of China
6. 农业银行 / Agricultural Bank of China
7. 邮储银行 / Postal Savings Bank of China
8. 民生银行 / China Minsheng Bank

## 3. 视觉层级 / Visual Hierarchy

中文：货币对字号为 17px，CFETS 市场价为 16px，银行买入价和卖出价为 14px，时间戳为 7px。买入价使用绿色，卖出价使用红色，市场中间价使用金色。所有时间戳统一使用灰色。

English: Currency-pair labels use 17px text, CFETS market prices use 16px, bank bid/ask prices use 14px, and timestamps use 7px. Bid prices are green, ask prices are red, and market mid-prices are gold. Every timestamp uses the same neutral grey.

中文：银行表头只显示银行名称和“买入 / 卖出”，不重复显示时间。每个市场或银行报价单元的时间戳固定在右下角，颜色、格式和位置完全一致。

English: Bank headers show only the bank name and “Bid / Ask”, without repeating timestamps. Every market or bank quote cell anchors its timestamp to the bottom-right using the same color, format, and position.

## 4. 报价录入 / Quote Entry

中文：录入区固定在实时总览底部，只占一条紧凑横栏。字段顺序为货币对、银行、方向、客户报价、当前或历史模式、历史日期时间（仅历史模式显示）、计算并保存。

English: The entry area is a compact horizontal strip fixed below the live matrix. Field order is currency pair, bank, direction, client quote, current/history mode, historical date-time (history mode only), and calculate/save.

中文：点击矩阵中的货币对或银行报价时，系统自动带入相应的货币对和银行。现有买入、卖出方向及市场成本计算规则保持不变，并继续遵循已批准的方向性比较规格。

English: Clicking a pair or bank quote in the matrix automatically fills the matching pair and bank. Existing buy/sell direction and market-cost calculation rules remain unchanged and continue to follow the previously approved directional-comparison specification.

结果文案 / Result labels:

1. 对比市场成本，你赚 / Compared with market cost, you earn
2. 对比 `{银行名称}` 牌价，优惠 / Discount versus `{bank name}` board rate

## 5. 历史时间录入 / Historical-Time Entry

中文：用户可以在实时总览的录入栏中把“当前”切换为“历史”，然后手动选择日期和分钟。用户也可以进入历史图表并点击任意时间点，系统自动把该时间带入录入栏。

English: Users can switch the entry strip from “Current” to “History” and manually select a date and minute. They can also open the historical chart and click a chart point to populate the timestamp automatically.

中文：如果选定分钟没有精确记录，系统使用不晚于所选时间的最近一条记录，绝不使用未来数据。界面分别显示用户选择时间、实际采用的 CFETS 时间和实际采用的银行时间。

English: If no exact record exists for the selected minute, the system uses the nearest record at or before the selected time and never uses future data. The interface separately shows the selected time, the actual CFETS timestamp, and the actual bank timestamp used.

历史结果文案 / Historical result labels:

1. 对比当时市场成本（实际时间），你赚 / Compared with market cost at the actual timestamp, you earn
2. 对比当时 `{银行名称}` 牌价（实际时间），优惠 / Discount versus `{bank name}` board rate at the actual timestamp

## 6. 历史图表 / Historical Chart

中文：顶部导航提供“实时总览”和“历史图表”两个入口。历史图表视图使用一个主图，不把不同价格尺度的四个货币对叠加在同一坐标轴上。

English: The top navigation contains “Live Overview” and “Historical Chart”. The historical view uses one primary chart and does not overlay all four differently scaled currency pairs on one axis.

历史视图控件 / Historical view controls:

- 货币对选择 / Currency-pair selector
- 每分钟数据间隔 / One-minute data interval
- 24 小时、7 天、30 天、自定义范围 / 24-hour, 7-day, 30-day, and custom ranges
- 最多两家银行选择 / Selection of up to two banks

中文：用户不再选择买入价或卖出价。CFETS 固定显示一条市场中间价曲线；每家已选银行同时显示买入价和卖出价。选择一家银行时共显示 3 条线，选择两家银行时共显示 5 条线。

English: Users no longer choose between bid and ask. CFETS always shows one market-mid curve, while every selected bank shows both bid and ask. Selecting one bank produces three lines; selecting two banks produces five lines.

中文：CFETS 中间价使用金色。第一家银行的买入价使用翠绿色、卖出价使用红色；第二家银行使用差异明显的黄绿色和玫红色。图例必须同时写明银行名称和价格类型，例如“中国银行 买入价”。

English: The CFETS mid-price is gold. The first bank uses emerald green for bid and red for ask; the second bank uses clearly differentiated yellow-green and rose-red. Every legend item includes both the bank name and price type, such as “Bank of China Bid”.

中文：图表将各来源时间统一到分钟后再绘制，使相差少量毫秒的 CFETS 与银行数据落在同一横坐标。鼠标提示框必须始终包含该分钟的 CFETS 中间价，以及已选银行的买入价和卖出价。此显示对齐不修改数据库原始时间。

English: Before charting, source timestamps are normalized to the minute so CFETS and bank records separated by only milliseconds share the same x-axis value. The tooltip must include the CFETS mid-price and bid/ask values for every selected bank at that minute. This display alignment does not modify stored timestamps.

中文：CFETS 曲线宽度为 1.2px，银行曲线宽度为 1px，数据点直径为 2px。悬停时只突出当前数据点，不加粗整条曲线。

English: The CFETS line is 1.2px wide, bank lines are 1px wide, and data points are 2px in diameter. Hover emphasis highlights only the active point without thickening the entire curve.

## 7. 响应与状态 / Interaction and States

中文：价格刷新时保持当前页面、筛选条件和录入内容，不因数据更新重置用户操作。正数结果使用绿色，负数结果使用红色。抓取失败或数据过旧应使用明确文字状态，不通过改变时间戳颜色表达。

English: Price refreshes preserve the current view, filters, and entry values. Positive results are green and negative results are red. Fetch failures or stale data use explicit text status and are never communicated by changing timestamp color.

## 8. 验收标准 / Acceptance Criteria

- 中文：在 1280px 及以上桌面宽度中，4 个货币对、CFETS、8 家银行、录入区和结果区无需横向滚动即可完整显示。
- English: At desktop widths of 1280px or greater, all four pairs, CFETS, eight banks, entry fields, and results are visible without horizontal scrolling.
- 中文：共 36 个报价时间戳，使用同一颜色、同一格式，并在每行保持相同的底部位置。
- English: All 36 quote timestamps use one color and format and share the same bottom alignment within each row.
- 中文：当前录入和历史录入都能完成计算与保存。
- English: Both current-time and historical-time entries can be calculated and saved.
- 中文：历史计算明确展示选定时间和实际采用的数据时间，且不使用未来数据。
- English: Historical calculations clearly show selected and actual data timestamps and never use future data.
- 中文：历史图表固定显示 CFETS 中间价，并同时显示最多两家银行各自的买入价和卖出价，不提供买入或卖出的单选控件。
- English: The historical chart always shows the CFETS mid-price together with both bid and ask prices for up to two selected banks, without a bid-or-ask selector.
- 中文：历史图表提示框包含 CFETS 中间价，第二家银行与第一家银行颜色可清晰区分，线宽和点大小符合已确认的精细参数。
- English: The historical tooltip includes the CFETS mid-price, the second bank is visually distinct from the first, and line and point sizes match the approved precision values.
- 中文：现有历史数据库继续沿用，不删除、不重建历史数据。
- English: The existing historical database is preserved without deletion or rebuilding.

## 9. 范围限制 / Scope Limits

中文：本次只调整前端信息架构、展示样式和历史时间选择交互。不会修改抓取频率、银行数据源、数据库结构或既有方向性计算公式，除非实现过程中发现当前代码无法满足已批准规则。

English: This change only updates frontend information architecture, presentation, and historical-time selection. It does not change fetch frequency, bank sources, database schema, or approved directional formulas unless implementation reveals that current code cannot satisfy the approved rules.
