#!/bin/bash
# 阿里云 ECS 一键部署脚本（Ubuntu 22.04 / Alibaba Cloud Linux）
# 用法：ssh root@你的IP 'bash -s' < deploy.sh

set -e

echo "=== 1. 安装 Docker ==="
if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com | bash
  systemctl enable docker
  systemctl start docker
fi

echo "=== 2. 创建项目目录 ==="
mkdir -p /opt/forex-monitor
mkdir -p /opt/forex-monitor/data
cd /opt/forex-monitor

echo "=== 3. 克隆/部署代码 ==="
# 方式 A: 从 GitHub 私有仓库拉取（推荐）
# git clone https://github.com/你的账号/forex-monitor-web.git .

# 方式 B: 如果你没有私有仓库，用下面命令在本地打包上传
# 在本地执行: tar czf forex-monitor-web.tar.gz forex-monitor-web/
# 然后: scp forex-monitor-web.tar.gz root@你的IP:/opt/forex-monitor/
# 然后: tar xzf forex-monitor-web.tar.gz

echo "=== 4. 构建 Docker 镜像 ==="
docker build -t forex-monitor .

echo "=== 5. 启动服务 ==="
docker stop forex-monitor 2>/dev/null || true
docker rm forex-monitor 2>/dev/null || true
docker run -d \
  --name forex-monitor \
  --restart unless-stopped \
  -p 8000:8000 \
  -e TZ=Asia/Shanghai \
  -v /opt/forex-monitor/data:/app/data \
  forex-monitor

echo "=== 6. 检查状态 ==="
sleep 2
curl -s http://localhost:8000/api/quotes | head -100

echo ""
echo "✅ 部署完成！访问 http://$(curl -s http://checkip.amazonaws.com):8000"
