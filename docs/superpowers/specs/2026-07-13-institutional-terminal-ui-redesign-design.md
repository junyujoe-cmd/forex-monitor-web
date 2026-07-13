# 机构交易终端界面重设计 / Institutional Trading Terminal UI Redesign

**状态 / Status:** 用户已确认设计方向 A / User-approved direction A  
**日期 / Date:** 2026-07-13  
**范围 / Scope:** 仅调整前端界面，不修改报价抓取、API、数据库结构或历史数据 / Frontend presentation only; no quote-fetching, API, database-schema, or historical-data changes

## 1. 背景 / Background

当前系统已经能够展示 CFETS 和八家银行的真实报价，并支持报价录入和历史图表。功能完整，但现有界面仍像工程调试后台：亮蓝色面积过大、视觉层级较弱、数据和操作区缺少专业金融终端的秩序感。

The system already displays truthful quotes from CFETS and eight banks, supports quote entry, and provides historical charts. Its functionality is complete, but the current interface still resembles an engineering dashboard: too much bright blue, weak visual hierarchy, and insufficient structure for a professional financial terminal.

用户选择 A「机构交易终端」方向，并要求兼顾个人长时间盯盘和对客户、同事展示时的专业形象。

The user selected Direction A, “Institutional Trading Terminal,” and wants it to support both long monitoring sessions and professional presentation to clients or colleagues.

## 2. 目标 / Goals

1. 将页面升级为克制、可靠、高密度的专业金融终端。  
   Upgrade the page into a restrained, trustworthy, high-density financial terminal.
2. 让九个数据来源和四个货币对成为最明确的视觉核心。  
   Make the nine data sources and four currency pairs the clearest visual focus.
3. 提高数字对齐、扫描效率和长时间使用的舒适度。  
   Improve numeric alignment, scanning speed, and comfort during long sessions.
4. 在不改变功能和数据真实性规则的前提下，提升录入、结果和历史图表的完成度。  
   Improve quote entry, results, and historical charts without changing functionality or truthfulness rules.
5. 保持原生 HTML、CSS 和 JavaScript 技术栈，避免新增部署依赖。  
   Keep the existing vanilla HTML, CSS, and JavaScript stack and avoid new deployment dependencies.

## 3. 非目标 / Non-goals

- 不修改银行抓取器、刷新频率或三分钟新鲜度规则。  
  Do not change bank fetchers, refresh intervals, or the three-minute freshness rule.
- 不修改 FastAPI 接口、业务计算或数据库表结构。  
  Do not change FastAPI endpoints, business calculations, or database tables.
- 不增加合成价格、预测价格或新的分析指标。  
  Do not add synthetic prices, forecasts, or new analytical metrics.
- 不引入前端框架、构建工具、外部字体或新图标库。  
  Do not introduce a frontend framework, build tooling, external fonts, or a new icon library.
- 本阶段不部署阿里云。  
  Do not deploy to Alibaba Cloud in this phase.

## 4. 视觉系统 / Visual System

### 4.1 色彩 / Color

- 页面背景采用接近黑色的石墨色，避免纯黑和目前大面积亮蓝。  
  Use a graphite near-black page background instead of pure black or the current large bright-blue areas.
- 面板使用两级深灰表面，通过明度和细边框建立层级，不使用夸张阴影。  
  Use two dark-gray surface levels with subtle borders rather than exaggerated shadows.
- 主强调色为低饱和薄荷绿，用于实时状态、主要按钮、焦点和正向结果。  
  Use a desaturated mint green for live status, primary actions, focus states, and positive results.
- 银行买入价使用薄荷绿，银行卖出价使用柔和珊瑚红。两者属于数据语义色，不作为额外品牌色使用。  
  Use mint for bank bids and soft coral for bank asks. These are semantic data colors, not additional brand accents.
- 警告使用低饱和琥珀色；缺失和错误使用柔和红色并配合文字说明。  
  Use muted amber for warnings and soft red plus text labels for missing or error states.

### 4.2 字体与数字 / Typography and Numerals

- 中文界面继续使用系统字体，避免外部字体加载失败。  
  Continue using system fonts for Chinese UI text to avoid external font-loading failures.
- 报价数字使用系统等宽字体回退栈，并启用等宽数字。  
  Use a system monospace fallback stack and tabular numerals for quotes.
- 标题使用 600–700 字重，正文和标签使用 400–600 字重建立细腻层级。  
  Use 600–700 weight for headings and 400–600 for body text and labels.
- 所有报价继续显示四位小数。  
  Continue displaying all quotes to four decimal places.

### 4.3 形状与动效 / Shape and Motion

- 外层工作台使用较柔和圆角，表格、输入框和按钮使用更紧的圆角。  
  Use a softer radius for the application shell and tighter radii for tables, controls, and buttons.
- 交互过渡控制在 150–220 毫秒，只使用颜色、透明度和轻微位移。  
  Keep interaction transitions between 150 and 220 milliseconds using only color, opacity, and slight translation.
- 不增加背景动画、闪烁数字或干扰盯盘的装饰效果。  
  Do not add background animation, flashing numbers, or decorative effects that distract from monitoring.

## 5. 页面结构 / Page Structure

### 5.1 应用外壳 / Application Shell

页面使用最大宽度约 1400 像素的居中工作台。超宽屏上保留合理边距，普通桌面屏幕上充分利用空间。

Use a centered application shell with a maximum width of approximately 1400 pixels. Preserve comfortable margins on ultrawide displays while using normal desktop space efficiently.

### 5.2 顶部栏 / Header

顶部栏包含：

The header contains:

- “外汇报价工作台”主标题和简短英文副标题。  
  The primary title “外汇报价工作台” and a short English subtitle.
- 不使用 emoji 的简洁 FX 标识。  
  A simple FX mark without emoji.
- “实时采集中”状态和状态点。  
  A “live collection” label and status dot.
- 最新一次成功更新时间。  
  The latest successful update time.

顶部栏不增加账户、设置或通知等当前不存在的功能。

The header must not add account, settings, notification, or other nonexistent functions.

### 5.3 实时报价矩阵 / Live Quote Matrix

报价矩阵继续展示 CFETS、八家银行、四个货币对和状态列。主要变化为：

The quote matrix continues to show CFETS, eight banks, four currency pairs, and the status column. Changes are limited to:

- 更明确的表头层级和买入、卖出图例。  
  Clearer header hierarchy and bid/ask legend.
- 银行名称下方显示本轮抓取时间或官方来源时间。  
  Show the current fetch time or official source time below each bank name.
- 数字采用等宽对齐，买入和卖出保持固定间距。  
  Align numbers using tabular spacing with a consistent gap between bid and ask.
- 行悬停只做轻微表面提亮。  
  Use only a subtle surface lift on row hover.
- CFETS 行保留市场基准身份，但不使用过亮的整行蓝色。  
  Preserve CFETS as the market benchmark without a bright full-row blue treatment.
- 缺失值继续显示 `--`，部分缺失和暂无新数据继续使用真实状态文字。  
  Continue showing `--` for missing values and truthful labels for partial or missing data.

### 5.4 操作工作区 / Action Workspace

报价矩阵下方保留“录入报价”和“历史图表”两个标签页。

Keep the “Quote Entry” and “Historical Chart” tabs below the quote matrix.

在桌面端，“录入报价”标签页采用两栏布局：

On desktop, the Quote Entry tab uses a two-column layout:

- 左侧：货币对、银行、方向、报价、日期、时间、“现在”和提交按钮，以及计算结果。  
  Left: currency pair, bank, direction, quote, date, time, “Now,” submit action, and calculation result.
- 右侧：最近录入记录。  
  Right: recent quote entries.

历史图表标签页使用完整可用宽度，筛选项位于图表上方。

The Historical Chart tab uses the full available width with filters above the chart.

## 6. 状态设计 / UI States

### 6.1 加载 / Loading

报价首次加载时显示与矩阵行列结构一致的骨架状态，避免空白页面或大面积文字提示。

During the initial quote load, display a skeleton matching the matrix structure instead of a blank page or oversized text message.

### 6.2 缺失与错误 / Missing and Error

- 单个报价缺失时显示 `--`。  
  Show `--` when an individual quote is missing.
- 整家银行本轮没有真实报价时显示“暂无新数据”。  
  Show “暂无新数据” when a bank has no truthful quote for the current cycle.
- 接口请求失败时在对应区域显示克制的行内错误信息，保留下一轮自动重试。  
  Show a restrained inline error message in the affected area and preserve the next automatic retry.
- 错误状态不能用旧的当前轮报价或合成报价掩盖。  
  Error states must not be hidden with stale current-cycle quotes or synthetic quotes.

### 6.3 表单 / Form

- 输入框和下拉框提供清晰的悬停、键盘焦点和无效输入状态。  
  Provide clear hover, keyboard-focus, and invalid-input states for form controls.
- 结果面板使用文字和颜色共同表达正向或负向差异。  
  Use both text and color to communicate positive or negative differences in the result panel.
- 不使用浏览器弹窗。  
  Do not use browser alert dialogs.

## 7. 响应式与无障碍 / Responsive Design and Accessibility

- 桌面端优先保证九行矩阵的扫描效率。  
  Prioritize scanning efficiency for the nine-row matrix on desktop.
- 宽度不超过 640 像素时允许矩阵横向滚动，并固定数据来源列。  
  At widths of 640 pixels or less, allow horizontal matrix scrolling and keep the source column sticky.
- 手机端录入区改为单列或两列自适应布局，按钮保持可点击尺寸。  
  On mobile, use a one- or two-column responsive entry layout and preserve comfortable button targets.
- 保留报价矩阵的 ARIA 表格语义和每个买卖价单元格的可读标签。  
  Preserve ARIA table semantics and readable labels for every bid/ask cell.
- 所有可交互元素必须具有可见键盘焦点。  
  Every interactive element must have a visible keyboard focus state.
- 状态不能只依赖颜色，必须同时显示文字。  
  Status must use text in addition to color.

## 8. 技术方案 / Technical Approach

正式实现只修改必要的前端和前端测试文件：

The implementation changes only the necessary frontend and frontend-test files:

- `static/index.html`：调整语义结构、CSS 变量、布局、状态组件和 ECharts 主题。  
  `static/index.html`: update semantic structure, CSS variables, layout, state components, and ECharts theme.
- `tests/test_four_minute_banks.py`：更新并补充视觉结构、真实缺失状态、选择项和无障碍契约测试。  
  `tests/test_four_minute_banks.py`: update and extend contracts for visual structure, truthful missing states, selectors, and accessibility.

不修改 `server.py`、`database.py`、`bank_fetcher.py` 或数据库文件。

Do not modify `server.py`, `database.py`, `bank_fetcher.py`, or any database file.

## 9. 云端历史数据库继承 / Cloud Historical Database Inheritance

这是未来部署的强制约束，不属于本次界面代码上线操作。

This is a mandatory constraint for future deployment and is not an action performed during this UI redesign.

1. 本地 `data/` 目录仅用于本地调试，绝不能覆盖阿里云生产数据库。  
   The local `data/` directory is for local debugging only and must never overwrite the Alibaba Cloud production database.
2. 未来部署前，必须备份阿里云现有 `forex_data.db` 和对应持久化数据目录。  
   Before future deployment, back up the existing Alibaba Cloud `forex_data.db` and its persistent data directory.
3. 部署时只更新代码和静态资源，继续挂载并使用阿里云现有 `/app/data` 持久化卷。  
   Deploy only code and static assets while continuing to mount and use the existing Alibaba Cloud `/app/data` persistent volume.
4. 不修改当前 `DB_PATH = "data/forex_data.db"` 约定。  
   Do not change the current `DB_PATH = "data/forex_data.db"` convention.
5. 上线前后分别校验可用历史日期、各表记录数量、最新一条报价时间和图表查询结果。  
   Before and after deployment, verify available historical dates, row counts for each table, the latest quote timestamp, and chart-query results.
6. 只有确认历史数据没有减少、最新数据继续写入后，部署才算完成。  
   Deployment is complete only after confirming that historical data has not decreased and new data continues to be written.
7. 未经用户本地验收和明确批准，不得更新阿里云。  
   Do not update Alibaba Cloud without local user acceptance and explicit approval.

## 10. 验收标准 / Acceptance Criteria

### 自动验证 / Automated Verification

- 现有后端与数据真实性测试全部通过。  
  All existing backend and data-truthfulness tests pass.
- 前端测试确认九个数据来源、八家银行选择项和四个货币对保持完整。  
  Frontend tests confirm all nine data sources, eight bank options, and four currency pairs remain present.
- 前端测试确认 `NaN`、`Infinity` 和合成银行价格不会显示。  
  Frontend tests confirm that `NaN`, `Infinity`, and synthetic bank prices are never rendered.
- 前端测试确认矩阵语义、焦点样式、缺失状态和固定来源列仍然存在。  
  Frontend tests confirm matrix semantics, focus styles, missing states, and the sticky source column.

### 浏览器验收 / Browser Acceptance

- 桌面端报价矩阵完整可见，布局在宽屏上居中且不松散。  
  The quote matrix is fully usable on desktop, centered on wide screens without becoming visually loose.
- 手机窄屏无页面级横向溢出；只有报价矩阵自身可以横向滚动。  
  Narrow mobile layouts have no page-level horizontal overflow; only the quote matrix may scroll horizontally.
- 固定来源列在横向滚动时保持可见。  
  The sticky source column remains visible during horizontal scrolling.
- 录入、当前时间、历史时间、结果显示、最近记录和历史图表均可正常操作。  
  Quote entry, current time, historical time, results, recent entries, and historical charts all remain functional.
- 加载、暂无数据、部分缺失和请求失败状态清楚且不误导。  
  Loading, empty, partial, and request-failure states are clear and non-misleading.

## 11. 实施边界 / Implementation Boundary

本次实施成功的定义是：在不改变任何真实报价、数据库和业务逻辑的情况下，将正式页面替换为已确认的 A「机构交易终端」视觉系统，并通过全部自动与浏览器验收。

Success means replacing the formal page with the approved Direction A institutional-terminal visual system, without changing truthful quotes, database behavior, or business logic, and passing all automated and browser acceptance checks.
