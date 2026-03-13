# 1C MCP Toolkit - SuperAssistant Edition

> **🔗 Это форк проекта [1C MCP Toolkit](https://github.com/ROCTUP/1c-mcp-toolkit)**  
> **Все права и респекты принадлежат оригинальному разработчику!**  
> **Данная версия создана для оптимизации работы с MCP SuperAssistant расширением**

**Система интеграции AI-агентов с базами данных 1С:Предприятие через MCP с поддержкой SuperAssistant**

## 🎯 Что нового в SuperAssistant Edition

### ✨ **Ключевые улучшения:**

- 🚀 **Полная поддержка MCP SuperAssistant** - специальный `/sse` эндпоинт для браузерного расширения
- 📱 **Обычная форма для толстого клиента** - полная поддержка 1С 8.2.13+ и 8.3.25+ (толстый клиент)
- 🔧 **Все 8 MCP инструментов в обычной форме** - идентичная функциональность управляемой форме
- ⚠️ **Защита от множественных вызовов** - все инструменты предупреждают о необходимости одного вызова за раз
- 🐳 **Production-ready Docker** - готовые конфигурации для VPS развертывания
- 📋 **Автоматическая установка на VPS** - скрипт для Ubuntu с systemd service

### 🛠 **Технические улучшения:**

- **SSE Bridge** - специальная реализация для SuperAssistant с правильным форматом событий
- **CORS оптимизация** - автоматическое разрешение браузерных расширений
- **Обычная форма 1С** - совместимость с толстым клиентом и старыми версиями
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

# Linux/Mac:
CORS_ALLOW_ALL=true python -m onec_mcp_toolkit_proxy
```

**Подключение в SuperAssistant:**
- URL: `http://localhost:6003/sse?channel=default`
- Transport: `SSE`

### VPS развертывание (Ubuntu)

```bash
# 1. Подключиться к серверу и клонировать репозиторий
ssh user@your-vps
sudo su
cd /opt
git clone https://github.com/vaderr15/1c-mcp-toolkit-mcpsa.git onec-mcp-toolkit
cd onec-mcp-toolkit

# 2. Запустить автоматическую установку
chmod +x install-vps.sh
sudo ./install-vps.sh

# 3. Проверить статус
systemctl status onec-mcp-toolkit
```

### Docker запуск

```bash
# Простой запуск
docker-compose up -d

# Проверить логи
docker logs onec-mcp -f

# Остановить
docker-compose down
```

## 📱 Обычная форма для толстого клиента

### Что это дает?

Обычная форма позволяет использовать MCP Toolkit в толстом клиенте 1С без управляемых форм. Это полезно для:
- Старых версий 1С (8.2.13+)
- Систем, где управляемые формы недоступны
- Максимальной совместимости

### Установка обычной формы

1. **Скопировать файл модуля:**
   ```
   1c/MCPToolkit/Forms/ФормаОбычная/Ext/Form/Module.bsl
   ```

2. **Создать элементы формы в конфигураторе:**
   - Реквизиты: АдресСервера, ИдентификаторКанала, Статус, Подключено, АвтоРазрешитьЗаписать, АвтоРазрешитьПривилегированныйРежим
   - Элементы: ПолеВвода для адреса и канала, Кнопки (Подключиться, Отключиться, Очистить лог)
   - **ПолеТекстовогоДокумента "Лог"** с ПереносПоСловам = Истина

3. **Скомпилировать и протестировать**

### Функциональность обычной формы

Все 8 MCP инструментов полностью реализованы:

| Инструмент | Статус | Особенности |
|-----------|--------|-----------|
| **execute_query** | ✅ Полная | Параметры, схема результата, лимиты |
| **execute_code** | ✅ Полная | Автоматическое удаление точки с запятой |
| **get_metadata** | ✅ Полная | Список и детали объектов |
| **get_event_log** | ✅ Полная | 10+ параметров фильтрации |
| **get_object_by_link** | ✅ Полная | Парсинг и поиск объектов |
| **get_link_of_object** | ✅ Полная | Создание навигационных ссылок |
| **find_references_to_object** | ✅ Полная | Поиск со всеми параметрами |
| **get_access_rights** | ✅ Полная | Проверка прав доступа |

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

## 🛠️ Доступные инструменты

Все 8 инструментов полностью функциональны как в управляемой форме, так и в обычной форме:

| Инструмент | Описание |
|-----------|----------|
| **execute_query** | Выполнение запросов 1C с параметрами и схемой результата |
| **execute_code** | Выполнение кода 1C с автоматической обработкой синтаксиса |
| **get_metadata** | Получение метаданных базы данных |
| **get_event_log** | Журнал регистрации с расширенной фильтрацией |
| **get_object_by_link** | Получение данных объекта по навигационной ссылке |
| **get_link_of_object** | Создание навигационной ссылки по описанию объекта |
| **find_references_to_object** | Поиск всех ссылок на объект в базе |
| **get_access_rights** | Проверка прав доступа к объектам метаданных |

## 🐳 Production развертывание

### Автоматическая установка на Ubuntu VPS

```bash
# 1. Подключиться к серверу и клонировать репозиторий
ssh root@your-vps
cd /opt
git clone https://github.com/vaderr15/1c-mcp-toolkit-mcpsa.git onec-mcp-toolkit
cd onec-mcp-toolkit

# 2. Запустить установку
chmod +x install-vps.sh
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
docker logs onec-mcp -f

# Остановка
systemctl stop onec-mcp-toolkit
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

### Новые компоненты:

**Python:**
- `onec_mcp_toolkit_proxy/superassistant_bridge.py` - SSE мост для SuperAssistant
- `onec_mcp_toolkit_proxy/sse_event_formatter.py` - форматирование SSE событий  
- `onec_mcp_toolkit_proxy/bridge_session_manager.py` - управление сессиями

**1C:**
- `1c/MCPToolkit/Forms/ФормаОбычная/` - обычная форма для толстого клиента
- `ordinary_form_module_complete.bsl` - полный модуль обычной формы

**DevOps:**
- `install-vps.sh` - скрипт установки на VPS
- `onec-mcp-toolkit.service` - systemd service файл

### Измененные файлы:

- `onec_mcp_toolkit_proxy/server.py` - добавлен `/sse` эндпоинт
- `docker-compose.yml` - production конфигурация с healthcheck
- `requirements.txt` - добавлены зависимости для SSE

## 📚 Документация

Полная документация по оригинальному функционалу доступна в оригинальном репозитории.

## 🤝 Благодарности

- **Оригинальный разработчик** - за создание отличного 1C MCP Toolkit
- **Команда MCP SuperAssistant** - за браузерное расширение
- **Anthropic** - за протокол MCP
- **Сообщество 1С** - за поддержку и обратную связь

## 📄 Лицензия

Наследует лицензию оригинального проекта. Все изменения предоставляются "как есть" для использования сообществом.

---

**🎯 Готово к работе! Используйте MCP Toolkit с SuperAssistant или толстым клиентом 1С!** 🚀
