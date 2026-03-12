# 🚀 Быстрый запуск - 1C MCP Toolkit SuperAssistant Edition

## Локальный запуск (5 минут)

### 1. Установка
```bash
git clone https://github.com/vaderr15/1c-mcp-toolkit-mcpsa.git
cd 1c-mcp-toolkit-mcpsa
pip install -r requirements.txt
```

### 2. Запуск сервера
```bash
# Windows PowerShell
$env:CORS_ALLOW_ALL="true"; python -m onec_mcp_toolkit_proxy

# Windows CMD  
set CORS_ALLOW_ALL=true && python -m onec_mcp_toolkit_proxy

# Linux/Mac
CORS_ALLOW_ALL=true python -m onec_mcp_toolkit_proxy
```

### 3. Настройка SuperAssistant
- URL: `http://localhost:6003/sse?channel=default`
- Transport: `SSE`

### 4. Подключение 1C
- Открыть `build/MCP_Toolkit.epf` в 1С
- URL прокси: `http://localhost:6003`
- Нажать "Подключиться"

## VPS развертывание (10 минут)

### 1. Загрузка на сервер
```bash
scp -r . root@your-vps:/opt/onec-mcp-toolkit/
```

### 2. Автоматическая установка
```bash
cd /opt/onec-mcp-toolkit
sudo ./install-vps.sh
```

### 3. Подключение
- URL: `http://YOUR_VPS_IP:6003/sse?channel=default`
- Transport: `SSE`

## Docker запуск (2 минуты)

```bash
docker-compose up -d
```

## Проверка работы

```bash
# Здоровье сервера
curl http://localhost:6003/health

# SSE эндпоинт
curl http://localhost:6003/sse?channel=default
```

## Troubleshooting

**CORS ошибка?** → Проверьте `CORS_ALLOW_ALL=true`  
**Пустые инструменты?** → Подключите 1C обработку  
**Missing session ID?** → Используйте `/sse`, не `/mcp`

---
**🎭 Евлантий готов к работе!**