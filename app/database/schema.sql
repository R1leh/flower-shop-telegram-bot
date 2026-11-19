-- Схема базы данных бота цветочного магазина «Бутон»

PRAGMA foreign_keys = ON;

-- Клиенты
CREATE TABLE IF NOT EXISTS clients (
    telegram_id INTEGER PRIMARY KEY,
    full_name TEXT,
    phone TEXT,
    birth_date TEXT,
    delivery_address TEXT,
    is_vip INTEGER DEFAULT 0,
    privacy_accepted INTEGER DEFAULT 0,
    privacy_accepted_at TEXT,
    registered_at TEXT
);

-- Букеты
CREATE TABLE IF NOT EXISTS bouquets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    price REAL NOT NULL,
    occasion TEXT,
    season TEXT,
    mood TEXT,
    colors TEXT,
    recipient TEXT,
    photo_path TEXT,
    is_active INTEGER DEFAULT 1,
    rating REAL DEFAULT 0,
    orders_count INTEGER DEFAULT 0,
    created_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_bouquets_active ON bouquets(is_active);

-- Заказы
-- Статусы: new / accepted / assembling / ready / delivery / completed / cancelled / rejected
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL,
    bouquet_id INTEGER,
    bouquet_name TEXT,
    recipient_name TEXT,
    recipient_phone TEXT,
    delivery_address TEXT,
    delivery_time TEXT,
    comment TEXT,
    total_price REAL,
    status TEXT DEFAULT 'new',
    created_at TEXT,
    FOREIGN KEY (telegram_id) REFERENCES clients(telegram_id),
    FOREIGN KEY (bouquet_id) REFERENCES bouquets(id)
);

CREATE INDEX IF NOT EXISTS idx_orders_telegram_id ON orders(telegram_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);

-- История изменения статусов заказа
CREATE TABLE IF NOT EXISTS order_status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    old_status TEXT,
    new_status TEXT,
    changed_by TEXT,
    changed_at TEXT,
    FOREIGN KEY (order_id) REFERENCES orders(id)
);

CREATE INDEX IF NOT EXISTS idx_status_history_order ON order_status_history(order_id);

-- История заказов клиента (для рекомендаций и статистики)
CREATE TABLE IF NOT EXISTS order_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL,
    bouquet_id INTEGER,
    bouquet_name TEXT,
    occasion TEXT,
    season TEXT,
    price REAL,
    ordered_at TEXT,
    rating INTEGER
);

CREATE INDEX IF NOT EXISTS idx_order_history_client ON order_history(telegram_id);

-- Избранное
CREATE TABLE IF NOT EXISTS favorites (
    telegram_id INTEGER NOT NULL,
    bouquet_id INTEGER NOT NULL,
    added_at TEXT,
    PRIMARY KEY (telegram_id, bouquet_id)
);

-- Напоминания
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL,
    person_name TEXT,
    remind_date TEXT,
    occasion TEXT,
    is_active INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_reminders_active ON reminders(is_active);

-- Отзывы
CREATE TABLE IF NOT EXISTS bouquet_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bouquet_id INTEGER NOT NULL,
    telegram_id INTEGER NOT NULL,
    rating INTEGER,
    review_text TEXT,
    created_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_reviews_bouquet ON bouquet_reviews(bouquet_id);

-- Программа лояльности
-- Уровни: standard / silver (5 заказов) / gold (15 заказов) / vip (30 заказов)
CREATE TABLE IF NOT EXISTS loyalty (
    telegram_id INTEGER PRIMARY KEY,
    points INTEGER DEFAULT 0,
    total_spent REAL DEFAULT 0,
    level TEXT DEFAULT 'standard'
);

-- Сессии подбора букета (для аналитики конверсии)
CREATE TABLE IF NOT EXISTS selection_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL,
    occasion TEXT,
    budget_from REAL,
    budget_to REAL,
    season TEXT,
    recipient TEXT,
    color_preference TEXT,
    flower_preferences TEXT,
    mood TEXT,
    result_bouquet_id INTEGER,
    completed INTEGER DEFAULT 0,
    started_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_sessions_client ON selection_sessions(telegram_id);

-- Заявки, по которым менеджеру уже отправлено повторное напоминание
CREATE TABLE IF NOT EXISTS order_manager_reminders (
    order_id INTEGER PRIMARY KEY,
    sent_at TEXT
);
