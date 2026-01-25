import sqlite3
import os

# 1. Определяем путь к базе (так же, как в боте)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "database.db")

# Создаем папку data, если её вдруг нет
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

print(f"📂 Подключаемся к базе: {DB_PATH}")

# 2. Подключаемся
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 3. Создаем таблицу (на случай, если файла еще нет)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        points INTEGER DEFAULT 0
    )
''')

# 4. ВПИСЫВАЕМ ТВОИ ДАННЫЕ
# ID: 832840031
# Wins: 11
# Losses: 2
# Points: 255
try:
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, wins, losses, points)
        VALUES (?, ?, ?, ?)
    ''', (832840031, 11, 2, 255))
    
    conn.commit()
    print("✅ УСПЕХ! Данные записаны.")
    print(f"👤 ID: 832840031 | Побед: 11 | Поражений: 2 | Рейтинг: 255")

except Exception as e:
    print(f"❌ Ошибка записи: {e}")

conn.close()
