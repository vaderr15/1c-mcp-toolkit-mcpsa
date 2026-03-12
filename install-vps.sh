#!/bin/bash

# 1C MCP Toolkit Proxy - VPS Installation Script
# Автоматическая установка на Ubuntu VPS

set -e

echo "🚀 Установка 1C MCP Toolkit Proxy на VPS..."

# Проверка что скрипт запущен от root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Пожалуйста, запустите скрипт от root: sudo ./install-vps.sh"
    exit 1
fi

# Обновление системы
echo "📦 Обновление системы..."
apt update && apt upgrade -y

# Установка Docker
echo "🐳 Установка Docker..."
apt install -y apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
apt update
apt install -y docker-ce docker-ce-cli containerd.io

# Установка Docker Compose
echo "🔧 Установка Docker Compose..."
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose

# Создание директории проекта
echo "📁 Создание директории проекта..."
mkdir -p /opt/onec-mcp-toolkit
cd /opt/onec-mcp-toolkit

# Копирование файлов (предполагается что они уже загружены)
echo "📋 Убедитесь что файлы проекта находятся в /opt/onec-mcp-toolkit"

# Установка systemd service
echo "⚙️ Настройка автозапуска..."
cp onec-mcp-toolkit.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable onec-mcp-toolkit.service

# Запуск сервиса
echo "🚀 Запуск сервиса..."
systemctl start onec-mcp-toolkit.service

# Проверка статуса
echo "✅ Проверка статуса..."
systemctl status onec-mcp-toolkit.service

echo ""
echo "🎉 Установка завершена!"
echo ""
echo "📋 Полезные команды:"
echo "  Статус:      systemctl status onec-mcp-toolkit"
echo "  Перезапуск:  systemctl restart onec-mcp-toolkit"
echo "  Логи:        docker-compose logs -f"
echo "  Остановка:   systemctl stop onec-mcp-toolkit"
echo ""
echo "🌐 Сервер доступен по адресу: http://YOUR_VPS_IP:6003"
echo "🔗 SuperAssistant endpoint: http://YOUR_VPS_IP:6003/sse"
echo ""
echo "⚠️  Не забудьте:"
echo "  1. Открыть порт 6003 в файрволе"
echo "  2. Настроить 1C клиент для подключения к серверу"
echo "  3. Проверить подключение: curl http://YOUR_VPS_IP:6003/health"