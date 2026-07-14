# 单货币对报价工作台与方向化比较设计
# Focused Pair Workbench and Directional Comparison Design

**日期 / Date:** 2026-07-14  
**状态 / Status:** 已批准的设计，待实施计划 / Approved design, pending implementation plan  
**范围 / Scope:** 前端布局精修与报价比较逻辑纠正；不修改数据库结构或历史记录 / Frontend layout refinement and quote-comparison correction; no database schema or historical-record changes

## 1. 目标 / Goals

- 首屏同时显示选中货币对、CFETS 市场参考、八家银行报价、客户报价录入和计算结果。  
  Show the selected currency pair, CFETS reference, eight bank quotes, quote entry, and calculation results within the first desktop viewport.
- 保持现有深色金融终端风格，同时减少嵌套卡片、重复边框和英文标签噪音。  
  Keep the current dark financial-terminal style while reducing nested cards, repeated borders, and noisy English labels.
- 明确银行买入与卖出方向，使用相应的 CFETS 买入价或卖出价计算市场利润。  
  Define bank buy and sell directions explicitly and use the corresponding CFETS bid or ask for market-profit calculations.
- 保留当前时间、历史时间、最近录入和历史图表功能。  
  Preserve current-time entry, historical-time entry, recent entries, and historical charts.

## 2. 非目标 / Non-goals

- 不新增银行、货币对或数据源。  
  Do not add banks, currency pairs, or data sources.
- 不修改 SQLite 表结构，不迁移、删除、覆盖或回填历史数据。  
  Do not change the SQLite schema or migrate, delete, overwrite, or backfill historical data.
- 不修改抓取频率、抓取器或云端部署方式。  
  Do not change refresh frequency, fetchers, or cloud deployment.
- 不新增前端框架、字体包或第三方依赖。  
  Do not add frontend frameworks, font packages, or third-party dependencies.

## 3. 数据与货币对范围 / Data and Currency-pair Scope

页面只使用系统现有四个货币对：`USDCNY`、`EURCNY`、`HKDCNY`、`JPYCNY`。`JPYCNY` 对应 `100JPY/CNY`。  
The page uses only the four existing pairs: `USDCNY`, `EURCNY`, `HKDCNY`, and `JPYCNY`. `JPYCNY` represents `100JPY/CNY`.

数据来源保持为 CFETS 和八家银行：中国银行、招商银行、建设银行、杭州银行、工商银行、农业银行、邮储银行、民生银行。  
Sources remain CFETS plus eight banks: Bank of China, China Merchants Bank, China Construction Bank, Bank of Hangzhou, ICBC, Agricultural Bank of China, Postal Savings Bank of China, and China Minsheng Bank.

## 4. 首屏信息架构 / First-viewport Information Architecture

1. 顶部品牌条压缩为约 44 像素高，只显示品牌、实时状态和更新时间。  
   Compress the brand bar to about 44 pixels and show only identity, live status, and update time.
2. 货币对使用紧凑标签切换，一次聚焦一个货币对。默认选择 `USDCNY`。  
   Use compact pair tabs and focus on one pair at a time. Default to `USDCNY`.
3. CFETS 在行情面板标题区显示为市场参考，不占用银行卡片。  
   Show CFETS as the market reference in the quote-board header rather than as a bank tile.
4. 八家银行在同一个连续行情面板内按四列两行排列，只使用细分隔线。  
   Arrange eight banks in one continuous four-by-two quote board using only subtle dividers.
5. 客户报价录入和报价结果组成同一个工作台，桌面端左右并排。  
   Combine quote entry and results into one workbench, side by side on desktop.
6. 最近录入压缩为工作台底部的单行活动条。  
   Compress recent entries into a single-line activity strip below the workbench.
7. “报价录入 / 历史图表”使用紧凑标签切换；历史图表不得删除。  
   Keep compact “Quote Entry / Historical Chart” tabs; the historical chart must not be removed.

## 5. 视觉系统 / Visual System

- 保留深蓝黑背景、薄荷绿买入价和柔和珊瑚红卖出价。买卖颜色属于数据语义色。  
  Keep the blue-black background, mint bid, and soft coral ask. Bid and ask colors remain semantic data colors.
- 银行报价共用一个面板，避免每家银行都使用独立圆角卡片和外阴影。  
  Use one shared bank board instead of separate rounded, shadowed cards for every bank.
- 中文正文使用系统中文字体栈；价格使用系统等宽字体和等宽数字。  
  Use the system Chinese font stack for text and system monospace with tabular figures for prices.
- 减少全大写英文副标题，只在品牌或必要的短标签中保留。  
  Reduce all-caps English sublabels and keep them only for identity or necessary short metadata.
- 结果数字是录入流程的视觉终点，字号和对比度高于其他辅助信息。  
  Make result numbers the visual endpoint of the entry flow with stronger size and contrast.

## 6. 货币对与录入联动 / Pair and Entry Synchronization

点击货币对标签后，行情面板、录入货币对和默认图表货币对同步切换。页面不再重复显示一个独立的录入货币对下拉框。  
Selecting a pair tab updates the quote board, entry pair, and default chart pair together. The entry form no longer repeats a separate pair selector.

银行、方向和客户报价仍由用户选择或输入。  
The user still selects the bank and direction and enters the customer quote.

## 7. 时间录入 / Time Entry

- 默认状态为“当前”，不显示日期和时间输入框。  
  Default to “Current” and hide date and time inputs.
- 选择“历史”后，在同一表单行展开日期和时间；两项都必填。  
  Selecting “Historical” reveals date and time inputs in the same form row; both are required.
- 历史结果必须显示实际匹配到的报价时间，不得暗示正好命中用户输入的分钟。  
  Historical results must show the actual matched quote timestamp and must not imply an exact minute match when the nearest cycle was used.

## 8. 方向定义 / Direction Definitions

`买入价` 表示银行买入外币、客户卖出外币。`卖出价` 表示银行卖出外币、客户买入外币。界面标签显示为：  
`买入价` means the bank buys foreign currency and the customer sells it. `卖出价` means the bank sells foreign currency and the customer buys it. UI labels are:

- `银行买入（客户卖出）` / `Bank buys (customer sells)`
- `银行卖出（客户买入）` / `Bank sells (customer buys)`

## 9. 计算公式 / Calculation Formulas

系统沿用现有点值口径：`结果 = 价格差 × 10,000`，即价格变化 `0.0001` 记为 `1 bp`。本次不改变单位定义。  
The system keeps its existing point convention: `result = price difference × 10,000`, so a `0.0001` price move is displayed as `1 bp`. This change does not redefine the unit.

| 方向 / Direction | 对比市场 / Market comparison | 对比银行牌价 / Bank-board comparison |
|---|---|---|
| 银行买入 / Bank buys | `(CFETS bid - customer quote) × 10,000` | `(customer quote - bank bid) × 10,000` |
| 银行卖出 / Bank sells | `(customer quote - CFETS ask) × 10,000` | `(bank ask - customer quote) × 10,000` |

市场比较的正数代表银行相对市场价格有正利润；银行牌价比较的正数代表客户相对该银行牌价获得优惠。  
A positive market result means the bank has a positive margin versus the market. A positive bank-board result means the customer receives an improvement versus that bank's board price.

## 10. 计算示例 / Calculation Examples

假设 CFETS 买入价 `6.7800`、卖出价 `6.7820`，中国银行买入价 `6.7700`、卖出价 `6.7900`。  
Assume CFETS bid `6.7800`, CFETS ask `6.7820`, Bank of China bid `6.7700`, and Bank of China ask `6.7900`.

- 银行买入报价 `6.7750`：市场结果 `(6.7800 - 6.7750) × 10,000 = +50 bp`；银行优惠 `(6.7750 - 6.7700) × 10,000 = +50 bp`。  
  Bank-buy quote `6.7750`: market result `(6.7800 - 6.7750) × 10,000 = +50 bp`; bank-board improvement `(6.7750 - 6.7700) × 10,000 = +50 bp`.
- 银行卖出报价 `6.7850`：市场结果 `(6.7850 - 6.7820) × 10,000 = +30 bp`；银行优惠 `(6.7900 - 6.7850) × 10,000 = +50 bp`。  
  Bank-sell quote `6.7850`: market result `(6.7850 - 6.7820) × 10,000 = +30 bp`; bank-board improvement `(6.7900 - 6.7850) × 10,000 = +50 bp`.

## 11. 结果文案 / Result Copy

市场结果第一行不显示银行名称：  
The first market-result line does not include a bank name:

- 正数 / Positive: `对比市场成本，你赚：X bp` / `Compared with market cost, you earn: X bp`
- 负数 / Negative: `对比市场成本，你亏：X bp` / `Compared with market cost, you lose: X bp`
- 零 / Zero: `对比市场成本，持平：0 bp` / `Compared with market cost, flat: 0 bp`

银行结果第二行动态带入所选银行名称，并显示绝对值：  
The second bank-result line inserts the selected bank name dynamically and displays an absolute value:

- 正数 / Positive: `对比中国银行牌价，优惠：X bp` / `Compared with Bank of China board price, improvement: X bp`
- 负数 / Negative: `对比中国银行牌价，更差：X bp` / `Compared with Bank of China board price, worse: X bp`
- 零 / Zero: `对比中国银行牌价，持平：0 bp` / `Compared with Bank of China board price, flat: 0 bp`

## 12. 当前与历史数据流 / Current and Historical Data Flow

当前时间从 `cfets_cache[pair].bid/ask` 和 `bank_cache[bank][pair].bid/ask` 读取。  
Current-time comparison reads `cfets_cache[pair].bid/ask` and `bank_cache[bank][pair].bid/ask`.

历史时间通过 `get_quotes_at_time()` 读取同一抓取轮次的 `market_bid`、`market_ask`、`bank_bid` 和 `bank_ask`。  
Historical comparison uses `get_quotes_at_time()` to read `market_bid`, `market_ask`, `bank_bid`, and `bank_ask` from the same fetch cycle.

不得再把市场中间价统一用于两个方向。`market_mid` 继续用于行情展示和历史图表，不用于新的方向化利润计算。  
Do not use the market midpoint for both directions. `market_mid` remains available for quote display and charts but is not used for the new directional profit calculation.

## 13. 缺失数据与错误状态 / Missing-data and Error States

- 当前方向需要的 CFETS 买入价或卖出价缺失时，不计算市场利润并显示明确错误。  
  If the required current CFETS bid or ask is missing, do not calculate market profit and show a clear error.
- 所选银行方向价格缺失时，不计算银行优惠，不使用旧缓存或合成价格代替。  
  If the selected bank-side price is missing, do not calculate the bank improvement and do not substitute stale or synthetic prices.
- 旧历史记录只有中间价而没有市场买入价或卖出价时，保留记录但市场结果显示“该历史时点缺少方向化市场价”。  
  When a legacy historical record has only a midpoint and lacks market bid or ask, preserve the record but show “Directional market price unavailable for this historical time.”
- 日期或时间只填写一项时禁止提交，并在字段旁显示提示。  
  Prevent submission when only date or time is filled and show an inline field message.

## 14. 响应式与可访问性 / Responsive Design and Accessibility

- 在 `1280 × 900` 桌面视口中，品牌条、货币对、八家银行、录入表单、结果和最近录入应完整进入首屏。  
  At a `1280 × 900` desktop viewport, the header, pair tabs, eight banks, entry form, results, and recent activity must fit within the first viewport.
- 窄屏将银行报价改为两列，录入和结果纵向排列；页面不得产生整体横向溢出。  
  On narrow screens, use two bank columns and stack entry and results; the page must not create document-level horizontal overflow.
- 所有标签、按钮和输入项支持键盘操作，并保留清晰焦点样式。  
  All tabs, buttons, and inputs must support keyboard operation and retain visible focus styles.
- 颜色不能是盈亏与状态的唯一表达方式，必须同时显示文字。  
  Color must not be the only indication of result or status; text labels are required.

## 15. 测试范围 / Test Scope

- 单元测试覆盖银行买入、银行卖出、正数、负数、零值和历史报价。  
  Unit tests cover bank buy, bank sell, positive, negative, zero, and historical comparisons.
- 回归测试证明买入使用 CFETS bid、卖出使用 CFETS ask，不能使用 mid。  
  Regression tests prove that bank buy uses CFETS bid and bank sell uses CFETS ask rather than mid.
- 前端测试覆盖货币对标签、八家银行、动态银行名称、时间模式、负数文案和历史图表入口。  
  Frontend tests cover pair tabs, eight banks, dynamic bank name, time mode, negative copy, and the historical-chart entry point.
- 浏览器验收覆盖 `1280 × 900` 桌面视口和窄屏布局。  
  Browser acceptance covers a `1280 × 900` desktop viewport and a narrow layout.

## 16. 验收标准 / Acceptance Criteria

1. 默认首屏选择 `USDCNY`，显示 CFETS 参考和八家银行买入、卖出价。  
   The default first viewport selects `USDCNY` and shows the CFETS reference plus bid and ask for all eight banks.
2. 切换货币对会同步行情、录入和默认图表货币对。  
   Pair switching synchronizes quotes, entry, and the default chart pair.
3. 当前和历史录入均按本设计的方向公式返回结果。  
   Current and historical entries both follow the directional formulas in this design.
4. 结果文案正确显示“你赚/你亏/持平”和“优惠/更差/持平”，并动态显示银行名称。  
   Result copy correctly shows earn/lose/flat and improvement/worse/flat and dynamically inserts the bank name.
5. 历史图表、缺失状态、加载状态和真实数据规则保持可用。  
   Historical charts, missing states, loading states, and truthful-data rules remain functional.
6. 不改变数据库结构，不删除或改写任何已有历史记录。  
   The database schema is unchanged and no existing historical records are deleted or rewritten.
