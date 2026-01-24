import asyncio
import logging
import re
import os
import random
import json
import sqlite3

from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.enums import ChatMemberStatus
from aiogram.types import LinkPreviewOptions
from datetime import datetime, timedelta
from aiogram.filters import CommandObject, Command
from aiogram.types import ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton, ReactionTypeEmoji
import google.generativeai as genai

# ================= НАСТРОЙКИ =================

BOT_TOKEN = "8232116536:AAH4uYukd18FZSlHqyRCAnwUnkVD6GgbYOg"
GOOGLE_API_KEY = "AIzaSyAIYu6GbRS0HtYlgEPLKgm1QuU8PZ15Z2E"

BOT_GUIDE = "https://telegra.ph/Baraholka-Bot-01-22"
LINK_TAPIR_GUIDE = "https://t.me/destinygoods/9814" 

OWNER_ID = 832840031

# Файлы
STATS_FILE = "stats.json"

# Глобальные переменные
PENDING_VERIFICATION = {}
ACTIVE_DUELS = {}   
USER_STATS = {} # Загружается из файла
PROCESSED_ALBUMS = []
LAST_MESSAGE_TIME = datetime.now()

ADMIN_CHAT_ID = -1003376406623 
CHAT_ID = -1002129048580

# --- СПИСКИ И ФРАЗЫ ---
LORE_FACTS = [
    "Шакс никогда не снимает шлем. Говорят, он в нем даже моется.",
    "Скиталец готовит рагу из Вексов. На вкус как батарейки, но питательно.",
    "Кабал взрывают планеты просто потому, что они загораживают им вид.",
    "Эрис Морн потеряла свои глаза в Яме, но теперь видит лучше тебя.",
    "Сайнт-14 однажды убил Келла Эликсни ударом головы. Буквально.",
    "Призраки ищут своих Стражей веками. Твой нашел тебя в куче мусора. Символично.",
    "Завалу больше всего бесит, когда Стражи танцуют на столе переговоров.",
    "Телесто ломало игру так часто, что у него появился свой разум.",
    "В Башне есть скрытый клуб для Охотников, но Титанам вход воспрещен.",
    "Кейд-6 был должен кучу денег половине Солнечной системы. Смерть списала долги."
]

UNMUTE_PHRASES = [
    "Свет вернулся к @username. Можешь говорить.",
    "Призрак восстановил голосовой модуль @username. Связь налажена.",
    "Стазис растаял. @username снова в эфире.",
    "Шакс разрешил тебе вернуться на арену, @username. Не подведи.",
    "Авангард снял ограничения с канала @username."
]

ADMIN_MUTE_PHRASES = [
    "Протокол 'Подавление' активирован. @username отправляется в стазис на {time} мин.",
    "Судьи Испытаний Осириса вынесли приговор. @username молчит {time} мин.",
    "Авангард лишил тебя Света на {time} мин. Подумай над поведением, @username.",
    "Шакс недоволен. @username удален с арены на {time} мин.",
    "Приказ командования: режим радиомолчания для @username на {time} мин."
]

TAPIR_PHRASES = [
    "Тапир? Это не животное, это диагноз твоему провайдеру. Врубай КВН.",
    "Опять Destiny 2 не пускает? Плак-плак. Bungie передают привет твоему айпишнику.",
    "Слышу 'тапир' — вижу человека, который забыл включить КВН.",
    "Ошибка TAPIR... Земля пухом твоему рейду. Без КВН ты тут никто.",
    "У всех всё работает, только у тебя тапир. Может, проблема в прокладке между стулом и монитором?",
    "Код ошибки: ТЫ ЗАБЫЛ КУПИТЬ НОРМАЛЬНЫЙ КВН.",
    "Тапир пришел за твоим лутом. Смирись и иди гуляй.",
    "Destiny намекает, что ты сегодня не страж, а ждун. Проверь соединение, гений.",
    "Лови тапира за хвост! А, ой, ты же даже в меню зайти не можешь...",
    "Тапир — это кара за твои грехи. Или просто Роскомнадзор шалит, врубай КВН."
]

MUTE_SHORT_PHRASES = [
    "ПОДАВЛЕНИЕ! Тебя накрыло стрелой Ночного Охотника. @username молчит 15 минут.",
    "Тьма поглотила твой голос. @username отправляется в стазис-кристалл на 15 минуточек.",
    "Скиталец отстрелил тебе руку, Страж. Где твой призрак?",
    "Вайп! @username перепутал механику и теперь сидит в муте 15 минут.",
    "Телесто снова сломало игру... и твою возможность говорить. @username молчит.",
    "Ты пойман в ловушку Вексов. Связь потеряна на 15 минут."
]

MUTE_CRITICAL_PHRASES = [
    "КРИТИЧЕСКИЙ УРОН! @username словил хедшот с ульты. Молчишь 30 МИНУТ.",
    "Вайп! Ты подвел команду. @username отправляется в мут на 30 МИНУТ.",
    "Архитекторы решили тебя уничтожить. @username замучен чате на 30 минут.",
    "Это был Голден Ган. @username, увидимся через полчаса.",
    "Что с лицом, страж? @username, помолчи полчасика."
]

SAFE_PHRASES = [
    "Странник избрал тебя. Живи пока.",
    "У тебя что, 100 Здоровья? Пуля отскочила.",
    "ЛВ выстрелил, но призрак успел тебя воскресить. Повезло.",
    "Рандом на твоей стороне, Страж. ЛВ осечку дал.",
    "Ты увернулся, как Хант с перекатом. Заряжаем ЛВ заново?"
]

KEEP_POSTED_STICKER_ID = "CAACAgIAAxkBAAEQSpppcOtmxGDL9gH882Rg8pZrq5eXVAACXZAAAtfYYEiWmZcGWSTJ5TgE"

REFUND_KEYWORDS = ["рефанд", "refund", "refound", "возврат средств", "вернуть деньги"]

VPN_PHRASES = ["Ты имел ввиду КВН? Измени сообщение, эти 3 буквы запрещены в чате."]

BAD_WORDS = ["лгбт", "цп", "казино", "цп", "child porn", "cp", "закладки", "мефедрон", 
    "шишки", "гашиш", "купить скорость", "чурка", "хач", "ниггер", "хохол", "кацап", 
    "москаль", "свинособак", "черномаз", "нигга", "nigga", "nigger", "hohol", 
    "магазин 24/7", "hydra", "kraken", "убейся", "выпей яду", "роскомнадзорнись", "мамку ебал", "Путин", "Зеленский", "война", "либераха", "гейропа", "кокс", "фашист"] 

BAN_WORDS = ["заработок в интернете", "быстрый заработок",
    "арбитраж крипты", "мамкин инвестор",
    "раскрутка счета", "Требуется команда из 5 человек для интересного проекта на 2-4 часа. Оплата начинается от 8.000 руб. Пишите в личные сообщения для уточнения деталей."]

ALLOWED_DOMAINS = ["youtube.com", "youtu.be", "google.com", "yandex.ru", "github.com", "x.com", "reddit.com", "t.me", "discord.com", "vk.com", "d2gunsmith.com", "light.gg", "d2foundry.gg", "destinyitemmanager.com", "bungie.net", "d2armorpicker.com"]

LINK_RULES = "https://telegra.ph/Pravila-kanala-i-chata-09-18" 
LINK_CHAT = "https://t.me/+Uaa0ALuvIfs1MzYy" 

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash') 

AI_SYSTEM_PROMPT = (
    "Ты — дерзкий Призрак-модератор чата по Destiny 2. "
    "Твоя задача — подкалывать Стражей (пользователей), используя сленг игры "
    "(ньюлайт, лайт, годролл, мета, вайп, дреджен, баунти, экзот). "
    "Если спрашивают чушь — отвечай в стиле Скитальца (Drifter) или лорда Шакса. "
    "Будь кратким, циничным и остроумным. Обращайся на 'ты', называй их Стражами."
)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ================= МИДЛВАРЬ (АНТИ-ФЛУД) =================
class AntiFloodMiddleware(BaseMiddleware):
    def __init__(self):
        self.flood_cache = {}

    async def __call__(self, handler, event, data):
        if isinstance(event, types.Message):
            user_id = event.from_user.id
            text = event.text or event.caption
            
            if text: 
                if user_id in self.flood_cache:
                    last_msg = self.flood_cache[user_id]
                    if last_msg['text'] == text:
                        try:
                            await event.bot.delete_message(chat_id=event.chat.id, message_id=last_msg['msg_id'])
                        except Exception:
                            pass
                self.flood_cache[user_id] = {'text': text, 'msg_id': event.message_id}
        return await handler(event, data)

# ================= ФУНКЦИИ СТАТИСТИКИ (JSON) =================

# ================= БАЗА ДАННЫХ (SQLite) =================

# 1. Определяем пути
# Получаем папку, где лежит main.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Задаем путь к папке data
DATA_DIR = os.path.join(BASE_DIR, "data")
# Задаем полный путь к файлу БД
DB_PATH = os.path.join(DATA_DIR, "database.db")

# 2. Создаем папку data, если её нет
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# 3. Подключаемся к БД по новому пути
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

# Создаем таблицу
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        points INTEGER DEFAULT 0
    )
''')
conn.commit()

# --- ФУНКЦИИ БД ---

def get_user_data(user_id):
    """Получает статистику игрока"""
    cursor.execute('SELECT wins, losses, points FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    if row:
        return {'wins': row[0], 'losses': row[1], 'points': row[2]}
    else:
        return {'wins': 0, 'losses': 0, 'points': 0}

def update_duel_stats(user_id, is_winner):
    """Обновляет очки после дуэли"""
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    
    if is_winner:
        cursor.execute('UPDATE users SET wins = wins + 1, points = points + 25 WHERE user_id = ?', (user_id,))
    else:
        cursor.execute('UPDATE users SET losses = losses + 1, points = MAX(0, points - 10) WHERE user_id = ?', (user_id,))
    
    conn.commit()

def get_rank_info(points):
    """
    Возвращает (название ранга, сколько очков до следующего).
    """
    # Пороги очков: (Порог, Название ТЕКУЩЕГО ранга)
    tiers = [
        (50, "Страж"),
        (150, "Удаль"),
        (350, "Отвага"),
        (700, "Героизм"),
        (1500, "Величие"),
        (float('inf'), "Легенда")
    ]
    
    for threshold, title in tiers:
        if points < threshold:
            needed = int(threshold - points)
            return title, needed
            
    return "Легенда", 0

def update_stat(user_id, stat_type):
    pass 

# ================= ОБЩИЕ ФУНКЦИИ =================

async def log_to_owner(text):
    """Пишет лог в консоль и отправляет его владельцу в ЛС"""
    # 1. Пишем в консоль (как раньше)
    print(f"LOG: {text}")
    
    # 2. Отправляем в ЛС
    try:
        await bot.send_message(OWNER_ID, f"🤖 SYSTEM LOG:\n{text}")
    except Exception as e:
        print(f"⚠️ Не удалось отправить лог в ЛС (проверь OWNER_ID и нажми /start боту): {e}")

async def delete_later(message: types.Message, delay: int):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass

async def check_silence_loop():
    global LAST_MESSAGE_TIME
    while True:
        await asyncio.sleep(300) 
        if (datetime.now() - LAST_MESSAGE_TIME).total_seconds() > 3600:
            fact = random.choice(LORE_FACTS)
            try:
                TARGET_CHAT_ID = CHAT_ID 
                await bot.send_message(TARGET_CHAT_ID, f"📢 Минутка Лора:\n{fact}")
                LAST_MESSAGE_TIME = datetime.now()
            except Exception as e:
                await log_to_owner(f"❌ Ошибка отправки факта: {e}")

def extract_urls(text):
    url_regex = r"(?P<url>https?://[^\s]+)"
    return re.findall(url_regex, text)

def is_link_allowed(text, chat_username):
    urls = extract_urls(text)
    if not urls: return True
    for url in urls:
        is_whitelisted = any(domain in url for domain in ALLOWED_DOMAINS)
        is_telegram = "t.me/" in url or "telegram.me/" in url
        is_self_chat = False
        if is_telegram and chat_username:
            if chat_username in url: is_self_chat = True
        if not is_whitelisted and not is_self_chat:
            return False
    return True

async def verification_timeout(chat_id: int, user_id: int, username: str):
    try:
        await asyncio.sleep(300) 
        await bot.ban_chat_member(chat_id, user_id)
        msg = await bot.send_message(
            chat_id, 
            f"@{username} оказался одержимым Тьмой (БОТ). Изгнан в пустоту."
        )
        asyncio.create_task(delete_later(msg, 15))
    except asyncio.CancelledError:
        pass
    except Exception as e:
        await log_to_owner(f"❌ Ошибка верификации: {e}")
    finally:
        if user_id in PENDING_VERIFICATION:
            del PENDING_VERIFICATION[user_id]

# ================= ХЕНДЛЕРЫ =================

# --- КОМАНДА /STATS (РАНГ ГОРНИЛА) ---
@dp.message(Command("stats"))
async def stats_command(message: types.Message):
    # Если ответили на сообщение — показываем стату того человека
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    user_id = target.id
    name = target.first_name

    # 1. Берем данные из БД
    data = get_user_data(user_id)
    
    wins = data['wins']
    losses = data['losses']
    points = data['points']
    
    # 2. Считаем Винрейт
    total_games = wins + losses
    if total_games > 0:
        winrate = round((wins / total_games) * 100, 1)
    else:
        winrate = 0.0

    # 3. Считаем ранг
    rank_title, points_needed = get_rank_info(points)
    
    if points_needed > 0:
        next_rank_str = f"🔜 До повышения: {points_needed} очков"
    else:
        next_rank_str = "👑 Максимальный ранг"

    d = message.from_user
    du = f"@{d.username}"
    
    text = (
        f"📊 ДОСЬЕ ГОРНИЛА: {du}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🏆 Ранг: {rank_title} ({points} очков)\n"
        f"{next_rank_str}\n"
        f"⚔️ Матчей: {total_games}\n"
        f"✅ Побед: {wins}\n"
        f"❌ Поражений: {losses}\n"
        f"📈 Винрейт: {winrate}%\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Шакс наблюдает за тобой."
    )
    
    msg = await message.reply(text)
    asyncio.create_task(delete_later(msg, 60))

# --- КОМАНДА /HELP ---
@dp.message(Command("help"))
async def help_command(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔧 Гайд по боту", url=BOT_GUIDE)]
    ])
    msg = await message.answer(
        "Made by yagraze & pan1q.\n"
        "📜 Команды:\n"
        "/duel — Вызов на бой (Рейтинговый)\n"
        "/stats — Твоя статистика и ранг\n"
        "/report — Пожаловаться на нарушение\n"
        "/lw — Рулетка (Мут/Удача)\n\n"
        "Узнать больше 👇👇",
        reply_markup=keyboard
    )
    asyncio.create_task(delete_later(msg, 15))
    asyncio.create_task(delete_later(message, 5))

# --- DUEL RPG (100 HP) ---
@dp.message(Command("duel"))
async def duel_command(message: types.Message):
    if not message.reply_to_message:
        msg = await message.reply("⚔️ Чтобы вызвать на дуэль, ответь на сообщение соперника командой /duel.")
        asyncio.create_task(delete_later(msg, 5))
        return

    attacker = message.from_user
    defender = message.reply_to_message.from_user

    if defender.is_bot or defender.id == attacker.id:
        msg = await message.reply("Найди себе достойного противника.")
        asyncio.create_task(delete_later(msg, 5))
        return

    att_name = f"@{attacker.username}" if attacker.username else attacker.first_name
    def_name = f"@{defender.username}" if defender.username else defender.first_name

    buttons = [
        [
            InlineKeyboardButton(text="🔫 Принять вызов", callback_data=f"duel_start|{attacker.id}|{defender.id}"),
            InlineKeyboardButton(text="🏳️ Сбежать", callback_data=f"duel_decline|{attacker.id}|{defender.id}")
        ]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.answer(
        f"🔥 ГОРНИЛО: ПРИВАТНЫЙ МАТЧ!\n\n"
        f"🔴 Претендент: {att_name}\n"
        f"🔵 Цель: {def_name}\n\n"
        f"📜 Правила: 100HP у Стражей,\n"
        f"🎲 Случайный класс (Хант или Варлок).\n"
        f"🔫 - Ханты: Голден Ган + Туз\n"
        f"🔮 - Варлоки: Нова Бомба + Туз\n"
        f"{def_name}, ты принимаешь бой?",
        reply_markup=keyboard
    )

async def update_duel_message(callback: types.CallbackQuery, game_id):
    if game_id not in ACTIVE_DUELS:
        await callback.answer("Игра не найдена (перезагрузка бота?)", show_alert=True)
        try: await callback.message.delete()
        except: pass
        return

    game = ACTIVE_DUELS[game_id]
    game_class = game.get("class", "hunter") # По умолчанию хантер (для старых игр)
    
    def get_hp_bar(hp):
        blocks = int(hp / 10) 
        return "▓" * blocks + "░" * (10 - blocks)

    p1 = game["p1"]
    p2 = game["p2"]
    current_turn_name = p1["name"] if game["turn"] == p1["id"] else p2["name"]

    # Заголовок зависит от класса
    if game_class == "hunter":
        title = "🐍 ДУЭЛЬ НА ХАНТАХ"
    else:
        title = "🔮 ДУЭЛЬ НА ВАРЛОКАХ"

    text = (
        f"⚔️ ДУЭЛЬ: РАУНД ИДЕТ\n\n"
        f"🔴 {p1['name']}: {p1['hp']} HP\n"
        f"[{get_hp_bar(p1['hp'])}]\n\n"
        f"🔵 {p2['name']}: {p2['hp']} HP\n"
        f"[{get_hp_bar(p2['hp'])}]\n\n"
        f"📜 Лог: {game['log']}\n\n"
        f"👉 Сейчас ходит: {current_turn_name}"
    )

    # Кнопки зависят от класса
    if game_class == "hunter":
        buttons = [
            [
                InlineKeyboardButton(text="🔥 GG (12% / kill)", callback_data="duel_gg"),
                InlineKeyboardButton(text="♠️ Ace (50% / 25dmg)", callback_data="duel_ace")
            ]
        ]
    else: # warlock
        buttons = [
            [
                # Общий шанс попадания 40% (15+25)
                InlineKeyboardButton(text="🟣 Nova (20% / 75dmg/kill)", callback_data="duel_nova"),
                InlineKeyboardButton(text="♠️ Ace (50% / 25dmg)", callback_data="duel_ace")
            ]
        ]

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        pass

# --- ОБРАБОТКА ВЫБОРА КЛАССА ---
@dp.callback_query(F.data.startswith("duel_set_"))
async def duel_class_handler(callback: types.CallbackQuery):
    game_id = callback.message.message_id
    
    # Проверка на существование игры
    if game_id not in ACTIVE_DUELS:
        await callback.answer("Игра не найдена.", show_alert=True)
        try: await callback.message.delete()
        except: pass
        return

    game = ACTIVE_DUELS[game_id]
    
    # Проверка: нажимать может только "chooser"
    if callback.from_user.id != game["chooser"]:
        await callback.answer("Не ты выбираешь класс!", show_alert=True)
        return

    # Определяем класс
    choice = callback.data.split("_")[2] # hunter, warlock, random
    
    if choice == "random":
        final_class = random.choice(["hunter", "warlock"])
    else:
        final_class = choice

    # Обновляем данные игры
    game["class"] = final_class
    game["state"] = "fighting" # Переводим в боевой режим
    
    # Текст лога
    class_names = {"hunter": "Хантеров", "warlock": "Варлоков"}
    game["log"] = f"Выбран класс {class_names[final_class]}! Бой начинается!"

    # Запускаем бой
    await update_duel_message(callback, game_id)
    await callback.answer()

@dp.callback_query(F.data.startswith("duel_"))
async def duel_handler(callback: types.CallbackQuery):
    data_parts = callback.data.split("|")
    action = data_parts[0]
    
    if action == "duel_decline":
        defender_id = int(data_parts[2])
        if callback.from_user.id != defender_id:
            await callback.answer("Не лезь, это не твой бой!", show_alert=True)
            return
        await callback.message.edit_text(f"🏳️ Дуэль отменена. Соперник сбежал на орбиту.")
        return

    # --- СТАРТ (ОПРЕДЕЛЕНИЕ ОЧЕРЕДИ И ВЫБОР КЛАССА) ---
    if action == "duel_start":
        attacker_id = int(data_parts[1])
        defender_id = int(data_parts[2])
        if callback.from_user.id != defender_id:
            await callback.answer("Жди решения соперника!", show_alert=True)
            return

        game_id = callback.message.message_id
        
        # Получаем имена
        try:
            att_m = await bot.get_chat_member(callback.message.chat.id, attacker_id)
            def_m = await bot.get_chat_member(callback.message.chat.id, defender_id)
            att_name = f"@{att_m.user.username}" if att_m.user.username else att_m.user.first_name
            def_name = f"@{def_m.user.username}" if def_m.user.username else def_m.user.first_name
        except:
            att_name, def_name = "Игрок 1", "Игрок 2"

        # 1. Кидаем монетку: кто стреляет первым?
        first_shooter_id = random.choice([attacker_id, defender_id])
        
        # 2. Тот, кто НЕ стреляет первым — выбирает класс
        class_chooser_id = defender_id if first_shooter_id == attacker_id else attacker_id
        
        # Имя выбирающего для текста
        chooser_name = def_name if class_chooser_id == defender_id else att_name
        shooter_name = att_name if first_shooter_id == attacker_id else def_name

        # Сохраняем промежуточное состояние
        ACTIVE_DUELS[game_id] = {
            "p1": {"id": attacker_id, "name": att_name, "hp": 100},
            "p2": {"id": defender_id, "name": def_name, "hp": 100},
            "turn": first_shooter_id,     # Кто будет стрелять
            "chooser": class_chooser_id,  # Кто выбирает класс сейчас
            "state": "choosing_class",    # Статус игры
            "log": "🗣 Шакс: Очередь определена! Выбирайте снаряжение."
        }

        # Меню выбора класса
        buttons = [
            [
                InlineKeyboardButton(text="🐍 Хантеры (GG + Ace)", callback_data="duel_set_hunter"),
                InlineKeyboardButton(text="🔮 Варлоки (Nova + Ace)", callback_data="duel_set_warlock")
            ],
            [
                InlineKeyboardButton(text="🎲 Рандом", callback_data="duel_set_random")
            ]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        text = (
            f"⚖️ БАЛАНС СИЛ\n\n"
            f"🔫 Первый ход: {shooter_name}\n"
            f"🗳 Выбор класса: {chooser_name}\n\n"
            f"{chooser_name}, выбирай класс для дуэли!"
        )

        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        return

    # --- ВЫСТРЕЛ ---
    if action in ["duel_gg", "duel_ace", "duel_nova"]:
        game_id = callback.message.message_id
        
        if game_id not in ACTIVE_DUELS:
            await callback.answer("Матч не найден.", show_alert=True)
            try: await callback.message.delete()
            except: pass
            return

        game = ACTIVE_DUELS[game_id]

        if game.get("state") == "choosing_class":
            await callback.answer("Сначала выберите класс!", show_alert=True)
            return
        
        # ПРОВЕРКА КЛАССА (Чит-контроль)
        # Если играем на Хантах, но нажата Нова -> игнор
        if game["class"] == "hunter" and action == "duel_nova":
            await callback.answer("Ты Хантер! У тебя нет Новы.", show_alert=True)
            return
        # Если играем на Варлоках, но нажат ГГ -> игнор
        if game["class"] == "warlock" and action == "duel_gg":
            await callback.answer("Ты Варлок! У тебя нет ГГ.", show_alert=True)
            return

        shooter_id = callback.from_user.id

        if shooter_id != game["turn"]:
            await callback.answer("Сейчас не твой ход!", show_alert=True)
            return

        if shooter_id == game["p1"]["id"]:
            shooter = game["p1"]
            target = game["p2"]
        else:
            shooter = game["p2"]
            target = game["p1"]

        damage = 0
        hit = False
        weapon_name = ""

        # --- ЛОГИКА ОРУЖИЯ ---
        if action == "duel_gg":
            weapon_name = "🔥 Голден Ган"
            if random.randint(1, 100) <= 12: # 12%
                hit = True
                damage = 100
                
        elif action == "duel_ace":
            weapon_name = "♠️ Пиковый Туз"
            if random.randint(1, 100) <= 50: # 50%
                hit = True
                damage = 25
                
        elif action == "duel_nova":
            weapon_name = "🟣 Нова Бомба"
            
            # Кидаем кубик от 1 до 100
            roll = random.randint(1, 100)
            
            # 1-15: Ваншот (100 урона)
            if roll <= 10:
                hit = True
                damage = 100
            # 16-40 (следующие 25%): Урон 70
            elif roll <= 20:
                hit = True
                damage = 75
            # 41-100: Промах
            else:
                hit = False
                damage = 0

        if hit:
            target["hp"] -= damage
            if target["hp"] < 0: target["hp"] = 0
            
            # Разный текст для разного урона Новы
            if action == "duel_nova" and damage == 100:
                log_msg = f"💥 КРИТ! {shooter['name']} кидает Нову и стирает врага в пыль (100 урона)!"
            else:
                log_msg = f"💥 Попадание! {shooter['name']} использует {weapon_name} и сносит {damage} HP!"
        else:
            log_msg = f"💨 Промах! {shooter['name']} промазал с {weapon_name}."

        if target["hp"] <= 0:
            update_duel_stats(shooter['id'], is_winner=True)
            update_duel_stats(target['id'], is_winner=False)
            
            del ACTIVE_DUELS[game_id]
            
            await callback.message.edit_text(
                f"🏆 МАТЧ ЗАВЕРШЕН!\n\n"
                f"{log_msg}\n\n"
                f"💀 {target['name']} повержен. Шакс объявляет нокаут.",
                reply_markup=None
            )
            
            await callback.answer()
            return

        game["turn"] = target["id"]
        game["log"] = log_msg
        
        await update_duel_message(callback, game_id)
        await callback.answer()

# --- РЕПОРТ ---
@dp.message(Command("report"))
async def report_command(message: types.Message):

    if not message.reply_to_message:
        msg = await message.reply("⚠️ Используй команду в ответ на сообщение нарушителя.")
        asyncio.create_task(delete_later(msg, 5))
        return

    reported_msg = message.reply_to_message
    reporter = message.from_user.username or message.from_user.first_name
    violator = reported_msg.from_user.username or reported_msg.from_user.first_name

    if message.chat.username:
        msg_link = f"https://t.me/{message.chat.username}/{reported_msg.message_id}"
    else:
        chat_id_str = str(message.chat.id)
        if chat_id_str.startswith("-100"):
            clean_id = chat_id_str[4:] 
        else:
            clean_id = chat_id_str 
        msg_link = f"https://t.me/c/{clean_id}/{reported_msg.message_id}"

    report_text = (
        f"🚨 СИГНАЛ ТРЕВОГИ (РЕПОРТ)\n"
        f"🕵️‍♂️ Донёс: @{reporter}\n"
        f"💀 Нарушил: @{violator}\n\n"
        f"👉 {msg_link}"
    )

    try:
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=report_text)
        confirm = await message.answer("✅ Жалоба отправлена Авангарду.")
        asyncio.create_task(delete_later(confirm, 5))
        asyncio.create_task(delete_later(message, 1))
        
    except Exception as e:
        await log_to_owner(f"❌ Ошибка репорта: {e}")

# --- MUTE (ADMIN) ---
@dp.message(Command("mute"))
async def admin_mute_command(message: types.Message, command: CommandObject):
    user_status = await bot.get_chat_member(message.chat.id, message.from_user.id)
    if user_status.status not in ["administrator", "creator"]:
        return

    target_user = None
    mute_minutes = 15 

    args = command.args.split() if command.args else []
    for arg in args:
        if arg.isdigit():
            mute_minutes = int(arg)
            break
    
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    elif message.entities:
        for entity in message.entities:
            if entity.type == "text_mention":
                target_user = entity.user
                break
            elif entity.type == "mention":
                pass

    if not target_user:
        msg = await message.answer("⚠️ Чтобы выдать мут, отправь команду в ответ на сообщение нарушителя.\nПример: /mute 30")
        asyncio.create_task(delete_later(msg, 10))
        return

    target_status = await bot.get_chat_member(message.chat.id, target_user.id)
    if target_status.status in ["administrator", "creator"]:
        msg = await message.answer("❌ Я не могу заглушить офицера Авангарда (Админа).")
        asyncio.create_task(delete_later(msg, 15))
        return

    try:
        unmute_time = datetime.now() + timedelta(minutes=mute_minutes)
        await message.chat.restrict(
            user_id=target_user.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=unmute_time
        )

        username = target_user.username or target_user.first_name
        phrase = random.choice(ADMIN_MUTE_PHRASES).format(
            time=mute_minutes
        ).replace("@username", f"@{username}")
        await message.answer(phrase)
        asyncio.create_task(delete_later(message, 5))

    except Exception as e:
        await log_to_owner(f"❌ Ошибка мута: {e}")
        msg = await message.answer(f"Ошибка протокола: {e}")
        asyncio.create_task(delete_later(msg, 10))

# --- UNMUTE (ADMIN) ---
@dp.message(Command("unmute"))
async def admin_unmute_command(message: types.Message):
    user_status = await bot.get_chat_member(message.chat.id, message.from_user.id)
    if user_status.status not in ["administrator", "creator"]:
        return 

    if not message.reply_to_message:
        msg = await message.reply("⚠️ Чтобы снять мут, сделай Reply (Ответить) на сообщение и напиши /unmute")
        asyncio.create_task(delete_later(msg, 10))
        return

    target_user = message.reply_to_message.from_user
    username = target_user.username or target_user.first_name

    try:
        await message.chat.restrict(
            user_id=target_user.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_send_polls=True,
                can_add_web_page_previews=True
            ),
            until_date=datetime.now() 
        )
        text = random.choice(UNMUTE_PHRASES).replace("@username", f"@{username}")
        await message.answer(text)
        asyncio.create_task(delete_later(message, 5))

    except Exception as e:
        print(f"Ошибка размута: {e}")
        await log_to_owner(f"❌ Ошибка размута: {e}")
        msg = await message.answer("Не удалось снять мут. Возможно, я не админ?")
        asyncio.create_task(delete_later(msg, 10))

# --- LASTWORD (ROULETTE) ---
@dp.message(Command("lastword", "lw", "ластворд", "лв"))
async def mute_roulette(message: types.Message):
    bullet = random.randint(1, 4) 
    username = message.from_user.username or message.from_user.first_name

    if bullet == 1:
        user_status = await bot.get_chat_member(message.chat.id, message.from_user.id)
        if user_status.status in ["administrator", "creator"]:
            msg = await message.reply("Выстрел! Прямое попадание, но ты Админ с овершилдом. Живи.")
            return

        try:
            duration_roll = random.randint(1, 5)
            if duration_roll == 5:
                mute_duration = timedelta(minutes=30)
                phrase = random.choice(MUTE_CRITICAL_PHRASES).replace("@username", f"@{username}")
            else:
                mute_duration = timedelta(minutes=15)
                phrase = random.choice(MUTE_SHORT_PHRASES).replace("@username", f"@{username}")

            unmute_time = datetime.now() + mute_duration
            await message.chat.restrict(
                user_id=message.from_user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=unmute_time
            )
            await message.reply(phrase)
            
        except Exception as e:
            await log_to_owner(f"❌ Ошибка рулетки: {e}")
            await message.reply("Хотел выдать мут, но не хватает прав админа! Проверь настройки.")
            print(f"Ошибка мута: {e}")

    else:
        text = random.choice(SAFE_PHRASES)
        msg = await message.reply(f"{text}")
        asyncio.create_task(delete_later(msg, 20))

@dp.message(F.is_automatic_forward)
async def auto_comment_channel_post(message: types.Message):
    # 1. Проверка на альбомы (чтобы не спамить)
    if message.media_group_id:
        if message.media_group_id in PROCESSED_ALBUMS:
            return 
        PROCESSED_ALBUMS.append(message.media_group_id)
        if len(PROCESSED_ALBUMS) > 100:
            PROCESSED_ALBUMS.pop(0)
    
    try:
        await asyncio.sleep(1) # Небольшая задержка перед ответом
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📜 Правила", url=LINK_RULES),
                InlineKeyboardButton(text="💬 Чат", url=LINK_CHAT)
            ]
        ])

        # Текст БЕЗ тегов (чтобы не было уведомления)
        safe_text = (
            "Оскорбления, реклама, спам, размещение ссылок, размещение недостоверной информации, выяснения отношений — Предупреждение/Мут.\n"
            "Повторное несоблюдение правил - БАН.\n\n"
            "По вопросам рекламы/покупки: ...\n"
            "По вопросам касательно бота: ..."
        )

        # Текст С тегами (который появится после редактирования)
        final_text = (
            "Оскорбления, реклама, спам, размещение ссылок, размещение недостоверной информации, выяснения отношений — Предупреждение/Мут.\n"
            "Повторное несоблюдение правил - БАН.\n\n"
            "По вопросам рекламы/покупки: @llRGaming.\n"
            "По вопросам касательно бота: @yaGraze."
        )

        # 1. Отправляем "безопасное" сообщение
        sent_msg = await message.reply(safe_text, reply_markup=keyboard)
        
        # 2. Ждем 0.1
        await asyncio.sleep(0.1)
        
        # 3. Редактируем сообщение, вставляя теги (уведомление не придет)
        await sent_msg.edit_text(final_text, reply_markup=keyboard)
        
        print(f"Оставил (тихий) комментарий к посту: {message.message_id}")

    except Exception as e:
        await log_to_owner(f"❌ Ошибка авто-коммента: {e}")

@dp.message(F.new_chat_members)
async def welcome(message: types.Message):
    for user in message.new_chat_members:
        if user.is_bot: continue

        username = user.username or user.first_name
        
        msg = await message.answer(
            f"Глаза выше, Страж @{username}! \n"
            f"Система безопасности чата активирована. 🛡\n"
            f"Напиши любое сообщение в чат в течение 5 минут, чтобы подтвердить свой Свет.\n"
            f"Иначе ты будешь забанен.\n"
            f"(Если ты будешь допущен - Я отвечу на твое сообщение и сниму таймер)"
        )
        task = asyncio.create_task(verification_timeout(message.chat.id, user.id, username))
        PENDING_VERIFICATION[user.id] = task
        asyncio.create_task(delete_later(msg, 300))

@dp.message()
async def moderate_and_chat(message: types.Message):
    global LAST_MESSAGE_TIME
    LAST_MESSAGE_TIME = datetime.now()
    
    if not message.text or message.from_user.id == bot.id:
        return

    text_lower = message.text.lower()
    username = message.from_user.username or message.from_user.first_name
    chat_username = message.chat.username
    user_id = message.from_user.id

    # --- ПРОВЕРКА НОВИЧКА ---
    if user_id in PENDING_VERIFICATION:
        task = PENDING_VERIFICATION.pop(user_id)
        task.cancel()
        
        username = message.from_user.username or message.from_user.first_name
        success_msg = await message.reply(
            f"Сканирование Света завершено. Допуск получен, Страж @{username}. Веди себя прилично, я всё вижу."
        )
        asyncio.create_task(delete_later(success_msg, 15))
    
    # --- GALREIZ ---
    if message.from_user.username and message.from_user.username.lower() == "galreiz":
        if random.randint(1, 3) == 1:
            try:
                await message.react([ReactionTypeEmoji(emoji="🤡")])
            except:
                await log_to_owner(f"❌ Ошибка реакции галрейз: {e}")
    
    # --- БАН ---
    for word in BAN_WORDS:
        if word in text_lower:
            try:
                await message.delete()
                await message.chat.ban(message.from_user.id)
                msg = await message.answer(f"@{username} улетел в бан. Воздух стал чище.")
                asyncio.create_task(delete_later(msg, 15))
                return
            except:
                await log_to_owner(f"❌ Ошибка бана: {e}")

    # --- УДАЛЕНИЕ ---
    for word in BAD_WORDS:
        if word in text_lower:
            try:
                await message.delete()
                msg = await message.answer(f"@{username}, рот с мылом помой, у тебя скверна изо рта лезет.")
                asyncio.create_task(delete_later(msg, 15))
                return
            except:
                await log_to_owner(f"❌ Ошибка удаления мата: {e}")

    # --- ССЫЛКИ ---
    if not is_link_allowed(message.text, chat_username):
        try:
            await message.delete()
            msg = await message.answer(f"@{username}, ссылки на чужие помойки запрещены. Не засоряй сеть Вексов.")
            asyncio.create_task(delete_later(msg, 15))
            return
        except:
            await log_to_owner(f"❌ Ошибка удаления ссылки: {e}")

    # --- VPN ---
    if "vpn" in text_lower or "впн" in text_lower:
        vpn_msg = random.choice(VPN_PHRASES)
        await message.reply(vpn_msg)
        return 

     # --- ТАПИР ---
    if "тапир" in text_lower or "tapir" in text_lower:
        tapir_msg = random.choice(TAPIR_PHRASES)
        tapir_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔧 Гайд: обход тапира", url=LINK_TAPIR_GUIDE)]
        ])
        await message.reply(tapir_msg, reply_markup=tapir_kb)
        return 
        
    # --- КЛОУН ---
    if message.reply_to_message and "клоун" in text_lower:
        try:
            await message.reply_to_message.react([ReactionTypeEmoji(emoji="🤡")])
        except Exception as e:
            await log_to_owner(f"❌ Ошибка реакции клоун: {e}")

    # --- ДЕРЖИ В КУРСЕ ---
    if message.reply_to_message and "держи в курсе" in text_lower:
        try:
            await message.reply_to_message.reply_sticker(sticker=KEEP_POSTED_STICKER_ID)
        except Exception:
            pass
    
    # --- РЕФАНД ---
    is_refund = any(word in text_lower for word in REFUND_KEYWORDS)
    if is_refund:
        try:
            await message.reply_sticker(sticker="CAACAgIAAxkBAAMWaW-qYjAAAYfnq0GFJwER5Mh-AAG7ywAC1YMAApJ_SEvZaHqj_zTQLzgE")
        except Exception as e:
            await log_to_owner(f"❌ Не могу отправить стикер. Ошибка:\n{e}")
            await message.reply(f"⚠️ Не могу отправить стикер. Ошибка:\n{e}")
        return

    # --- ИИ ---
    bot_info = await bot.get_me()
    is_reply_to_bot = message.reply_to_message and message.reply_to_message.from_user.id == bot.id
    is_mention = f"@{bot_info.username}" in message.text

    if is_reply_to_bot or is_mention:
        clean_text = message.text.replace(f"@{bot_info.username}", "").strip()
        if not clean_text:
            msg = await message.answer("Ну и чё ты меня тегнул? Пообщайся с кем-нибудь другим.")
            asyncio.create_task(delete_later(msg, 5))
            return

        try:
            await bot.send_chat_action(message.chat.id, action="typing")
            
            chat = model.start_chat(history=[
                {"role": "user", "parts": "Веди себя как дерзкий модератор. Твоя инструкция: " + AI_SYSTEM_PROMPT},
                {"role": "model", "parts": "Понял, начальник. Буду жестким и кратким."}
            ])
            
            response = await chat.send_message_async(clean_text)
            await message.reply(response.text)
            
        except Exception as e:
            logging.error(f"Ошибка Gemini: {e}")
            taee_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔧 Гайд по боту", url=BOT_GUIDE)]
            ])
            msg = await message.reply("Made by yagraze & pan1q.\nУзнать больше 👇👇", reply_markup=error_kb)
            asyncio.create_task(delete_later(msg, 5))
            
# ================= ЗАПУСК =================

async def main():
    print("Бот настроен карать.")
    asyncio.create_task(check_silence_loop())
    dp.message.middleware(AntiFloodMiddleware())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
