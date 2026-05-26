# 实时外汇监控系统 - 部署上线指南

> 部署日期：2026-05-25
> 服务器：阿里云 ECS 香港地域
> 公网 IP：47.238.90.211

---

## 一、技术架构

```
用户浏览器 (手机/电脑)
       │
       ▼  http://47.238.90.211:8000
┌──────────────────────────┐
│  ECS 云服务器 (香港)      │
│                          │
│  ┌────────────────────┐  │
│  │  前端 (HTML+ECharts)│  │
│  │  static/index.html  │  │
│  └──────┬─────────────┘  │
│         │ HTTP API       │
│  ┌──────▼─────────────┐  │
│  │  后端 (FastAPI)     │  │
│  │  server.py          │  │
│  └──────┬─────────────┘  │
│         │                │
│  ┌──────▼─────────────┐  │
│  │  数据层             │  │
│  │  fetcher.py         │  │  ← 每60秒自动抓取外汇数据
│  │  database.py        │  │  ← SQLite 存储
│  │  bank_fetcher.py    │  │
│  └────────────────────┘  │
└──────────────────────────┘
```

---

## 二、常用命令速查

### 1. SSH 登录服务器

```bash
ssh -i ~/Downloads/my-key.pem root@47.238.90.211
```

> `-i` 指定密钥文件路径
> `root` 是登录用户名
> `47.238.90.211` 是服务器公网 IP

### 2. 查看服务运行状态

登录服务器后：

```bash
# 查看进程是否在跑
ps aux | grep server.py

# 查看最近日志
tail -20 /root/forex-monitor-web/server.log

# 实时查看日志（按 Ctrl+C 退出）
tail -f /root/forex-monitor-web/server.log
```

### 3. 重启服务

```bash
# 先杀掉旧进程
pkill -f server.py

# 重新启动
cd /root/forex-monitor-web
nohup python3.11 server.py > server.log 2>&1 &
```

### 4. 查看最新报价（测试 API）

```bash
curl http://localhost:8000/api/quotes
curl http://localhost:8000/api/chart?pair=USDCNY&bank=中国银行
```

---

## 三、文件上传

从 Mac 传文件到服务器：

```bash
# 打压缩包
cd /Users/junyu/opencode/projects
tar czf forex-monitor-web.tar.gz forex-monitor-web

# 上传
scp -i ~/Downloads/my-key.pem forex-monitor-web.tar.gz root@47.238.90.211:/root/

# 登录服务器后解压
ssh -i ~/Downloads/my-key.pem root@47.238.90.211
cd /root
tar xzf forex-monitor-web.tar.gz
```

**命令拆解：**

| 命令 | 含义 |
|------|------|
| `tar czf 文件名 文件夹` | 把文件夹打包成 `.tar.gz` 压缩包 |
| `scp -i 密钥 文件 用户@IP:路径` | 安全复制文件到远程服务器 |
| `tar xzf 文件名` | 解压 `.tar.gz` 压缩包 |

---

## 四、项目文件说明

```
forex-monitor-web/
├── server.py              # 后端入口（FastAPI 服务）
├── static/index.html      # 前端页面（浏览器打开就是这个）
├── config.py              # 配置（货币对、银行、API地址）
├── database.py            # 数据库操作（SQLite）
├── fetcher.py             # 中国外汇交易中心数据抓取
├── bank_fetcher.py        # 中国银行、招商银行数据抓取
├── calculator.py          # BP 计算公式
├── requirements.txt       # Python 依赖列表
├── Dockerfile             # Docker 构建文件（可选）
├── deploy.sh              # 部署脚本
└── DEPLOY_GUIDE.md        # 本指南
```

---

## 五、阿里云 ECS 配置

### 安全组（开放端口）

在阿里云控制台 → 安全组 → 入方向规则：

| 协议 | 端口 | 来源 | 说明 |
|------|------|------|------|
| TCP | 8000 | 0.0.0.0/0 | Web 服务访问 |
| TCP | 22 | 0.0.0.0/0 | SSH 登录 |

> `0.0.0.0/0` 表示允许所有 IP 访问
> 端口 22 用于 SSH，端口 8000 用于网页

### 开机自启配置

```bash
# 创建启动脚本
cat > /root/start-forex.sh << 'EOF'
#!/bin/bash
cd /root/forex-monitor-web && nohup python3.11 server.py > server.log 2>&1 &
EOF

chmod +x /root/start-forex.sh

# 添加到定时任务
echo '@reboot root /root/start-forex.sh' > /etc/cron.d/forex-monitor
crontab /etc/cron.d/forex-monitor
```

---

## 六、第一次部署全流程（速查）

```bash
# 1. 登录服务器
ssh -i ~/Downloads/my-key.pem root@47.238.90.211

# 2. 安装 Python 3.11
dnf install -y python3.11 python3.11-pip python3.11-devel

# 3. 安装依赖
python3.11 -m pip install fastapi uvicorn apscheduler requests beautifulsoup4 lxml pandas akshare

# 4. 上传代码（在 Mac 终端执行，不是服务器）
cd /Users/junyu/opencode/projects
tar czf forex-monitor-web.tar.gz forex-monitor-web
scp -i ~/Downloads/my-key.pem forex-monitor-web.tar.gz root@47.238.90.211:/root/

# 5. 解压（在服务器执行）
cd /root
tar xzf forex-monitor-web.tar.gz

# 6. 启动服务
cd /root/forex-monitor-web
nohup python3.11 server.py > server.log 2>&1 &

# 7. 验证
curl http://localhost:8000/api/quotes

# 8. 浏览器打开
# http://47.238.90.211:8000
```

---

## 七、知识点总结

### SSH 是什么
Secure Shell，加密的远程登录协议。让你能在自己电脑上操作远在云端的服务器。

### nohup 是什么
"no hang up" 的缩写。让程序在后台持续运行，即使你关掉了 SSH 终端也不会停止。

### FastAPI 是什么
Python 的 Web 框架。把我们的外汇监控逻辑包装成 HTTP API，浏览器能直接调用。

### ECharts 是什么
百度的开源图表库，在浏览器里画交互式的股票/曲线图，触摸屏也支持。

---

*最后更新：2026-05-25*
