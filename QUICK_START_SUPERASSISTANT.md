# Быстрый старт с MCP SuperAssistant

⚠️ **ВАЖНО: Проблема с поддержкой SSE в SuperAssistant**

Расширение SuperAssistant имеет неполную реализацию SSE (Server-Sent Events). Хотя сервер 1C MCP Toolkit работает корректно и отправляет все ответы, расширение не читает SSE события правильно. Это приводит к тому, что Tools и Instructions остаются пустыми в UI.

**Статус:** Сервер полностью функционален. Проблема на стороне расширения.

**Подробности:** См. [SUPERASSISTANT_DIAGNOSIS.md](SUPERASSISTANT_DIAGNOSIS.md) для детального анализа и логов.

---

## Проблема, которую вы видели

```
CORS: No origins configured, CORS headers will not be added
CORS preflight rejected for origin: chrome-extension://...
```

Это означает, что переменная окружения `CORS_ALLOW_ALL` не применилась.

## Решение

### Вариант 1: Используйте готовый скрипт (рекомендуется)

**PowerShell:**
```powershell
.\start_with_cors.ps1
```

**CMD:**
```cmd
start_with_cors.bat
```

### Вариант 2: Запустите вручную с правильным синтаксисом

**PowerShell:**
```powershell
$env:CORS_ALLOW_ALL="true"
$env:LOG_LEVEL="DEBUG"
python -m onec_mcp_toolkit_proxy
```

**CMD:**
```cmd
set CORS_ALLOW_ALL=true
set LOG_LEVEL=DEBUG
python -m onec_mcp_toolkit_proxy
```

## Проверка

После запуска в логах должна появиться строка:
```
CORS: Allowing all origins (*)
```

Если видите эту строку - всё работает правильно!

## Подключение расширения

1. Откройте ChatGPT (или другой AI-чат)
2. Нажмите на иконку MCP SuperAssistant
3. В настройках укажите:
   - URL: `http://localhost:6003/mcp`
   - Transport: `SSE` (рекомендуется для SuperAssistant)
4. Нажмите "Connect"

Расширение должно подключиться и показать список инструментов.

## Что изменилось

Теперь CORS middleware автоматически разрешает запросы от браузерных расширений (chrome-extension://, moz-extension://), даже если не указаны конкретные origins.

Это безопасно, так как расширения работают локально в браузере пользователя.
