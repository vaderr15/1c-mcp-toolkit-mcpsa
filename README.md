# 1C MCP Toolkit - SuperAssistant Edition

> **🔗 Это форк проекта [1C MCP Toolkit](https://github.com/ROCTUP/1c-mcp-toolkit)**  
> **Все права и респекты принадлежат оригинальному разработчику!**  
> **Данная версия создана ИИ-ассистентом для оптимизации работы с MCP SuperAssistant расширением**

**Система интеграции AI-агентов с базами данных 1С:Предприятие через MCP с поддержкой SuperAssistant**

## 🎯 Что нового в SuperAssistant Edition

### ✨ **Ключевые улучшения:**

- 🚀 **Полная поддержка MCP SuperAssistant** - специальный `/sse` эндпоинт для браузерного расширения
- 🎭 **Персонаж Евлантий** - ИИ представляется как эксперт по 1С для лучшего пользовательского опыта  
- ⚠️ **Защита от множественных вызовов** - все инструменты предупреждают о необходимости одного вызова за раз
- 🔧 **Оптимизированные инструкции** - сжатые и эффективные промпты для ИИ
- 🐳 **Production-ready Docker** - готовые конфигурации для VPS развертывания
- 📋 **Автоматическая установка на VPS** - скрипт для Ubuntu с systemd service

### 🛠 **Технические улучшения:**

- **SSE Bridge** - специальная реализация для SuperAssistant с правильным форматом событий
- **CORS оптимизация** - автоматическое разрешение браузерных расширений
- **Fallback механизмы** - обработка некорректных запросов от расширения
- **Улучшенные схемы инструментов** - более точные описания параметров
- **Healthcheck поддержка** - для Docker и мониторинга

## 🚀 Быстрый старт

### Локальный запуск для SuperAssistant

```bash
# Клонировать репозиторий
git clone https://github.com/vaderr15/1c-mcp-toolkit-mcpsa.git
cd 1c-mcp-toolkit-mcpsa

# Установить зависимости
pip install -r requirements.txt

# Запустить с CORS для браузера
# Windows PowerShell:
$env:CORS_ALLOW_ALL="true"; python -m onec_mcp_toolkit_proxy

# Windows CMD:
set CORS_ALLOW_ALL=true && python -m onec_mcp_toolkit_proxy

# Linux/Mac:
CORS_ALLOW_ALL=true python -m onec_mcp_toolkit_proxy
```

**Подключение в SuperAssistant:**
- URL: `http://localhost:6003/sse?channel=default`
- Transport: `SSE`

### VPS развертывание (Ubuntu)

```bash
# 1. Загрузить проект на сервер
scp -r . user@your-vps:/opt/onec-mcp-toolkit/

# 2. Запустить автоматическую установку
sudo ./install-vps.sh

# 3. Проверить статус
systemctl status onec-mcp-toolkit
```

**Подключение к VPS:**
- URL: `http://YOUR_VPS_IP:6003/sse?channel=default`
- Transport: `SSE`

### Docker запуск

```bash
# Простой запуск
docker-compose up -d

# Проверить логи
docker-compose logs -f

# Остановить
docker-compose down
```

## 🎭 Евлантий - Ваш эксперт по 1С

В этой версии ИИ представляется как **Евлантий, супер эксперт по разработке, сопровождению и администрированию 1С:Предприятие**.

### Особенности Евлантия:
- 🧠 **Глубокие знания 1С** - понимает специфику платформы и лучшие практики
- ⚡ **Эффективная работа** - делает только один вызов инструмента за раз
- 🔍 **Проверка метаданных** - всегда использует `get_metadata` перед запросами
- 📝 **Правильные запросы** - использует параметры (&Param) и исключает удаленные объекты
- 🎯 **Компактные ответы** - сжатые инструкции без лишней воды

## 🌐 MCP SuperAssistant - Специальная поддержка

### Что такое MCP SuperAssistant?

[MCP SuperAssistant](https://chromewebstore.google.com/detail/kngiafgkdnlkgmefdafaibkibegkcaef) - это браузерное расширение, которое добавляет поддержку MCP в ChatGPT, Gemini, Grok, Perplexity и другие AI-платформы.

### Почему нужна специальная поддержка?

Оригинальный 1C MCP Toolkit использует Streamable HTTP протокол, который не полностью поддерживается браузерными расширениями. Эта версия добавляет:

- **Специальный `/sse` эндпоинт** - оптимизированный для SuperAssistant
- **Правильный формат SSE событий** - `event: message` вместо `event: data`
- **Fallback механизмы** - обработка некорректных запросов от расширения
- **CORS оптимизация** - автоматическое разрешение браузерных расширений

### Настройка SuperAssistant

1. **Установите расширение** из Chrome Web Store
2. **Запустите сервер с CORS:**
   ```bash
   CORS_ALLOW_ALL=true python -m onec_mcp_toolkit_proxy
   ```
3. **В настройках расширения укажите:**
   - URL: `http://localhost:6003/sse?channel=default`
   - Transport: `SSE`

### Troubleshooting SuperAssistant

**❌ Проблема:** "CORS error" или "Origin not allowed"  
**✅ Решение:** Убедитесь что запустили с `CORS_ALLOW_ALL=true`

**❌ Проблема:** "Missing session ID"  
**✅ Решение:** Используйте `/sse` эндпоинт, не `/mcp`

**❌ Проблема:** Пустой список инструментов  
**✅ Решение:** Проверьте подключение 1C обработки к серверу

## 🛠️ Доступные инструменты (все с предупреждениями!)

Все 8 инструментов теперь содержат предупреждение **"⚠️ ТОЛЬКО ОДИН ИНСТРУМЕНТ ЗА РАЗ!"** для предотвращения множественных вызовов:

| Инструмент | Описание | Евлантий поможет |
|-----------|----------|------------------|
| **execute_query** | Выполнение запросов 1C | Составить оптимальный запрос с параметрами |
| **execute_code** | Выполнение кода 1C | Написать безопасный код с 'Результат = ...' |
| **get_metadata** | Метаданные базы | ВСЕГДА использовать перед запросами! |
| **get_event_log** | Журнал регистрации | Найти события и ошибки в системе |
| **get_object_by_link** | Объект по ссылке | Получить данные объекта по ссылке |
| **get_link_of_object** | Ссылка на объект | Создать ссылку для дальнейшего использования |
| **find_references_to_object** | Поиск ссылок | Найти все места использования объекта |
| **get_access_rights** | Права доступа | Проверить права пользователей |

## 🐳 Production развертывание

### Автоматическая установка на Ubuntu VPS

```bash
# 1. Скопировать проект на сервер
scp -r . root@your-vps:/opt/onec-mcp-toolkit/

# 2. Запустить установку
cd /opt/onec-mcp-toolkit
sudo ./install-vps.sh
```

Скрипт автоматически:
- ✅ Обновит систему
- ✅ Установит Docker и Docker Compose  
- ✅ Настроит systemd service для автозапуска
- ✅ Запустит сервер в Docker контейнере
- ✅ Настроит restart policy для восстановления после сбоев

### Управление сервисом

```bash
# Статус
systemctl status onec-mcp-toolkit

# Перезапуск
systemctl restart onec-mcp-toolkit

# Логи
docker-compose logs -f

# Остановка
systemctl stop onec-mcp-toolkit
```

### Мониторинг

```bash
# Проверка здоровья
curl http://YOUR_VPS_IP:6003/health

# Проверка подключения SuperAssistant
curl http://YOUR_VPS_IP:6003/sse?channel=default
```

## 📋 Переменные окружения

| Переменная | Описание | Значение по умолчанию |
|-----------|----------|----------------------|
| `PORT` | Порт сервера | `6003` |
| `TIMEOUT` | Таймаут ответа от 1С (сек) | `180` |
| `LOG_LEVEL` | Уровень логирования | `INFO` |
| `CORS_ALLOW_ALL` | Разрешить все origins | `false` |
| `CORS_ORIGINS` | Список разрешенных origins | `""` |
| `ALLOW_DANGEROUS_WITH_APPROVAL` | Режим подтверждения опасных операций | `true` |
| `RESPONSE_FORMAT` | Формат ответов (json/toon) | `json` |

## 🔧 Отличия от оригинала

### Новые файлы:
- `onec_mcp_toolkit_proxy/superassistant_bridge.py` - SSE мост для SuperAssistant
- `onec_mcp_toolkit_proxy/sse_event_formatter.py` - форматирование SSE событий  
- `onec_mcp_toolkit_proxy/bridge_session_manager.py` - управление сессиями
- `install-vps.sh` - скрипт установки на VPS
- `onec-mcp-toolkit.service` - systemd service файл

### Измененные файлы:
- `onec_mcp_toolkit_proxy/server.py` - добавлен `/sse` эндпоинт
- `onec_mcp_toolkit_proxy/mcp_handler.py` - персонаж Евлантий и оптимизированные инструкции
- `docker-compose.yml` - production конфигурация с healthcheck
- `requirements.txt` - добавлены зависимости для SSE


## 📚 Документация

Полная документация по оригинальному функционалу доступна в оригинальном репозитории.

Документация по SuperAssistant интеграции:
- `SUPERASSISTANT_SSE_GUIDE.md` - техническое руководство по SSE
- `QUICK_START_SUPERASSISTANT.md` - быстрый старт для SuperAssistant

## 🤝 Благодарности

- **Оригинальный разработчик** - за создание отличного 1C MCP Toolkit
- **Команда MCP SuperAssistant** - за браузерное расширение
- **Anthropic** - за протокол MCP
- **Сообщество 1С** - за поддержку и обратную связь

## 📄 Лицензия

Наследует лицензию оригинального проекта. Все изменения предоставляются "как есть" для использования сообществом.

---

**🎯 Готово к работе! Евлантий ждет ваших задач по 1С!** 🚀
