# 实时外汇监控系统 (Web 版)

基于 FastAPI + ECharts 的实时外汇监控 Web 应用，部署在云服务器上，手机/电脑浏览器即可访问。

## 项目定位

这是 **外汇数据抓取** 项目（`~/外汇数据抓取/`）的 Web 可视化层。后端每 60 秒自动从中国外汇交易中心（CFETS）抓取实时报价，同时采集 BOC（中国银行）和 CMB（招商银行）的零售牌价，提供实时行情、历史曲线、报价录入对比等功能。

## 目录结构

```
forex-monitor-web/
├── server.py              # 后端入口 — FastAPI 服务
├── static/index.html      # 前端页面 — ECharts 图表 + 移动端适配
├── database.py            # SQLite 数据库操作层
├── fetcher.py             # CFETS 市场报价抓取（akshare）
├── bank_fetcher.py        # 中国银行、招商银行零售牌价抓取
├── calculator.py          # BP 计算公式
├── config.py              # 配置（货币对、银行、价差偏移、抓取间隔）
├── requirements.txt       # Python 依赖
├── Dockerfile             # Docker 构建配置
├── deploy.sh              # 部署脚本
├── CLAUDE.md              # AI 开发规则
├── DEPLOY_GUIDE.md        # 部署上线指南（含阿里云 ECS 配置）
└── README.md              # 本文件
```

## 数据流

```
CFETS (akshare) ──┐
                  ├──→ server.py (FastAPI) ──→ static/index.html (ECharts)
BOC/CMB (抓取)  ──┘         │
                            ▼
                      SQLite (forex_data.db)
```

- **实时数据**：每 60 秒自动抓取 CFETS 买卖报价 + 银行牌价
- **历史数据**：启动时自动回补 30 天 BOC 历史数据（后台线程，不阻塞启动）
- **报价录入**：用户可手动录入实际成交价，系统自动计算 BP 对比

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/quotes` | GET | 最新一轮报价（市场价 + 银行牌价） |
| `/api/chart?pair=USDCNY&bank=中国银行&date=2026-05-26` | GET | 图表数据，支持指定日期 |
| `/api/chart_dates` | GET | 有数据的日期列表 |
| `/api/entry?pair=USDCNY&bank=中国银行&direction=买入价&quote=6.78` | POST | 录入报价 |
| `/api/entries?limit=20` | GET | 最近录入记录 |

## 支持的货币对

- `USDCNY` — 美元/人民币
- `EURCNY` — 欧元/人民币
- `HKDCNY` — 港币/人民币
- `JPYCNY` — 日元/人民币

## 支持的银行

- 中国银行（BOC）
- 招商银行（CMB）

## 本地运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动服务（默认端口 8000）
python server.py

# 3. 浏览器打开
open http://localhost:8000
```

## 部署到云服务器

参见 `DEPLOY_GUIDE.md` 详细说明。简要步骤：

```bash
# 打包
tar czf forex-monitor-web.tar.gz forex-monitor-web

# 上传到服务器
scp forex-monitor-web.tar.gz root@你的IP:/root/

# SSH 登录后解压启动
ssh root@你的IP
tar xzf forex-monitor-web.tar.gz
cd forex-monitor-web && nohup python3 server.py > server.log 2>&1 &
```

也可用 Docker：

```bash
docker build -t forex-monitor .
docker run -d -p 8000:8000 -v ./data:/app/data forex-monitor
```

## 技术栈

| 层 | 技术 |
|----|------|
| 后端框架 | FastAPI (Python) |
| 前端图表 | ECharts (Apache) |
| 数据库 | SQLite |
| 定时任务 | APScheduler |
| 数据源 | akshare（CFETS 市场报价）+ requests（银行牌价） |
| 部署 | Docker / nohup + cron |

## 项目关系

```
~/外汇数据抓取/                  # BOC/CFETS 原始数据采集 + 分析脚本（本地）
    └── data/raw/boc_*.csv      # BOC 分钟级数据（CSV）
    └── data/raw/cfets_hourly.csv  # CFETS 每小时参考汇率
    └── scripts/verify_cfets_formula.py  # BOC→CFETS 反推公式验证

~/opencode/projects/forex-monitor/        # PyQt5 桌面版（打包为 macOS .app）
~/opencode/projects/forex-monitor-web/    # Web 版（后端 FastAPI，前端 ECharts）
```

## 注意事项

- 价格单位：USD/EUR/HKD 为 **人民币/1外币**；JPY 为 **人民币/100日元**（与 BOC 原始数据单位一致）
- BP 计算公式：`(价格差) × 10000`（非 ÷ 参考价，详见 `~/外汇数据抓取/README.md`）
- 数据库文件 `data/forex_data.db` 自动创建，建议挂载为 Docker volume 持久化
