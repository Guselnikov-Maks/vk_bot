# 🚗 VK Bot for Fuel Tracking

Бот для учёта заправок и расчёта эффективности расхода топлива с интеграцией с сайтом пробега.

---

## 📋 Содержание

- [Возможности](#-возможности)
- [Требования](#-требования)
- [Быстрый старт](#-быстрый-старт)
- [Настройка базы данных](#-настройка-базы-данных)
- [Конфигурация](#-конфигурация)
- [Структура проекта](#-структура-проекта)
- [Команды бота](#-команды-бота)
- [Логирование](#-логирование)
- [Обслуживание](#-обслуживание)
- [Устранение неполадок](#-устранение-неполадок)

---

## 🎯 Возможности

| Функция | Описание |
|---------|----------|
| 🔐 Регистрация | Проверка авторизации на внешнем сайте |
| 🔒 Безопасность | Шифрованное хранение паролей (Fernet) |
| ⛽ Заправки | Добавление с автоматической фиксацией времени |
| 📊 Пробег | Получение данных с сайта через Selenium |
| 📐 Расчёт | Норма 10 л = 100 км, экономия/перерасход |
| 📅 Статистика | Данные за текущий календарный месяц |
| 📎 Excel | Формирование подробных отчётов |
| 📝 Логи | Подробное логирование всех операций |

---

## 📦 Требования

- **Python**: 3.10+
- **MySQL**: 5.7+
- **Google Chrome**: для работы Selenium
- **ChromeDriver**: автоматически устанавливается через webdriver-manager

---

## 🚀 Быстрый старт

### 1. Клонирование

```bash
git clone https://github.com/Guselnikov-Maks/vk_bot.git
cd vk_bot

### 2. Виртуальное окружение
```bash
python3 -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows

### 3. Установка зависимостей
```bash
pip install -r requirements.txt

### 4. Установка Chrome (Ubuntu)
```bash
wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
sudo apt-get update
sudo apt-get install google-chrome-stable

### 5. Настройка БД (см. следующий раздел)

### 6. Запуск
```bash
python main.py

## 🗄️ Настройка базы данных

### Шаг 1: Создание БД и пользователя
```sql
-- Подключитесь к MySQL
mysql -u root -p

-- Создайте базу данных
CREATE DATABASE IF NOT EXISTS vk_bot 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

-- Создайте пользователя
CREATE USER IF NOT EXISTS 'vk_bot_user'@'localhost' 
IDENTIFIED BY 'your_strong_password';

-- Дайте права
GRANT SELECT, INSERT, UPDATE, DELETE ON vk_bot.* 
TO 'vk_bot_user'@'localhost';

FLUSH PRIVILEGES;

### Шаг 2: Создание таблиц
```sql
USE vk_bot;

-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT 'Уникальный идентификатор',
    vk_id BIGINT NOT NULL UNIQUE COMMENT 'ID пользователя в VK',
    login VARCHAR(100) NOT NULL COMMENT 'Логин пользователя для сайта',
    password_hash VARCHAR(255) NOT NULL COMMENT 'Зашифрованный пароль',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Дата регистрации',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_vk_id (vk_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Таблица заправок
CREATE TABLE IF NOT EXISTS user_values (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    value INT NOT NULL COMMENT 'Количество литров',
    added_at DATE NOT NULL COMMENT 'Дата добавления',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Дата и время',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at),
    INDEX idx_user_date (user_id, added_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

### Шаг 3: Проверка
```sql
SHOW TABLES;
DESCRIBE users;
DESCRIBE user_values;

## ⚙️ Конфигурация

### 1. Создайте .env
```bash
cp .env.example .env

### 2. Сгенерируйте ключ шифрования
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

Вывод (пример):
```bash
gAAAAABn7ZqWx8XhL3jK5mN2pQ9rS4tU6vY7wZ0aB1cD2eF3gH4iJ5kL6mN7oP8qR9sT0uV=

### 3. Заполните .env
```bash
# VK Bot
VK_TOKEN=your_vk_group_token_here

# MySQL
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=vk_bot
DB_USER=vk_bot_user
DB_PASSWORD=your_strong_password

# Encryption
ENCRYPTION_KEY=gAAAAABn7ZqWx8XhL3jK5mN2pQ9rS4tU6vY7wZ0aB1cD2eF3gH4iJ5kL6mN7oP8qR9sT0uV=

# Logging
LOG_DIR=.
LOG_LEVEL=INFO

### 4. Получение VK токена

vk.com/dev → создать приложение (тип "Сообщество")

В настройках сообщества включите:

Long Poll API

Возможности ботов

Создайте ключ доступа с правами messages

## 📁 Структура проекта
vk_bot/
├── .env                    # Конфигурация (не коммитить!)
├── .env.example            # Пример конфигурации
├── .gitignore              # Игнорируемые файлы
├── requirements.txt        # Зависимости
├── README.md              # Документация
│
├── logger.py              # Модуль логирования
├── database.py            # Работа с БД
├── site_parser.py         # Парсер сайта
├── main.py                # Основной код бота
├── generate_key.py        # Генерация ключа
├── cleanup_excel.py       # Очистка отчетов
│
├── excel_reports/         # Excel-отчеты
│
├── bot.log                # Логи бота
├── database.log           # Логи БД
├── parser.log             # Логи парсера
└── cleaner.log            # Логи очистки

##🤖 Команды бота
Команда	Что делает
начать / start	Приветственное сообщение
регистрация	Начать процесс регистрации
❓ Помощь	Показать справку
➕ Добавить заправку	Добавить новую заправку
📊 Мой пробег	Показать статистику
📋 Список заправок	Список заправок за месяц
🔄 Получить отчет Excel	Сформировать Excel-отчет
данные	Показать логин и пароль

## 📝 Логирование
### Уровни логирования
Уровень	Использование
DEBUG	Подробная отладка (запросы к БД, данные парсера)
INFO	Основные события (регистрация, добавление)
WARNING	Предупреждения (неудачная авторизация)
ERROR	Ошибки (проблемы с подключением)

### Просмотр логов
```bash
# Все логи в реальном времени
tail -f *.log

# Конкретный лог
tail -f bot.log

# Поиск ошибок
grep ERROR *.log

## 🧹 Обслуживание

###Очистка старых Excel-отчетов
```bash
# Вручную
python cleanup_excel.py

# Автоматически (crontab)
# 0 2 * * * cd /path/to/vk_bot && python cleanup_excel.py

### Резервное копирование БД
```bash
mysqldump -u vk_bot_user -p vk_bot > backup_$(date +%Y%m%d).sql
gzip backup_*.sql

### Обновление зависимостей
```bash
pip install --upgrade -r requirements.txt

## 👤 Контакты
По вопросам обращаться к администратору.
