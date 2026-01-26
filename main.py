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
from openai import AsyncOpenAI

# ================= НАСТРОЙКИ =================

BOT_TOKEN = "8400087235:AAEE7FqXyq-94oGao_rA8-Ed4YtazrrMugs"
OPENAI_API_KEY = "sk-VceymhbQITrkT8qoYFshaQ" 

BOT_GUIDE = "https://telegra.ph/Baraholka-Bot-01-22"
LINK_TAPIR_GUIDE = "https://t.me/destinygoods/9814" 

OWNER_ID = 832840031

# Глобальные переменные
PENDING_VERIFICATION = {}
ACTIVE_DUELS = {}   
USER_STATS = {} # Загружается из файла
PROCESSED_ALBUMS = []
LAST_MESSAGE_TIME = datetime.now()
AI_COOLDOWN_TIME = datetime.now()
TOURNAMENT_ACTIVE = False
TOURNAMENT_MAX_PLAYERS = 0
TOURNAMENT_PLAYERS = [] # Список ID участников
TOURNAMENT_USERNAMES = [] # Список ников для красоты

ADMIN_CHAT_ID = -1003376406623 
CHAT_ID = -1002129048580

# --- СПИСКИ И ФРАЗЫ ---
LORE_FACTS = [
    "Небольшой факт: всеми любимый в эпизоде ереси 'Губитель королев' был в первой части Destiny, но была плазменкой на особых патронах.",
    "Интересный факт: Майя Сундареш, ныне известная как Дирижёр, перерождалась целых два раза! Сначала она умерла на Неомуне, попытавшись связаться с вуалью, затем её разум был перемещен в экзо-тело 'Лакшми-2', но и в этой оболочке она умерла в ходе нападения вексов на башню.",
    "Забавный факт: бродяги на Неомуне живут 10-15 лет, такой короткий срок жизни обусловлен тем, что у них установлено много имплантов.",
    "Наблюдательный факт: в некоторых строениях тьмы можно обнаружить летающие лампы, которые поразительно схожи с логотип Марафона.",
    "Ностальгический факт: одно из самых первых упоминаний Destiny в играх Bungiе было в Halo, на плакате с планетой Земля и в самом низу картинки Луны, которая сильно была похожа на Странника, а также цитата: 'судьба (Destiny) ждёт'.",
    "Печальный факт: в Destiny 1 у варлока были такие же наручи, как у титана или охотника, но в Destiny 2 их уже обрезали до перчаток.",
    "Грустный факт: многие могли не заметить, но Буря и Натиск связаны не только механикой, но и лорами. У обоих оружий в кратком описании написано, для кого они. Буря для Сигрун от Виктора, а Натиск для Виктора от Сигрун. Они были парой, но их разделила судьба. Виктор был в криосне на борту 'Исхода', а Сигрун опоздала на этот корабль и не могла больше погрузиться в криосон.",
    "Свидетельский факт: мороки это бывшие известные нам враги. Адъютант и ткач это псионы, а панцирь – эликсни. Также смотритель это эксперимент - слияние эликсни/презренного и червя.",
    "Праксический факт: Онор Махал упомянулась ещё до дополнений отступников и обители теней. Упоминается в сезоне скитальца, и про неё даже есть целая книжка: 'Варлок Онор'",
    "Незаметный факт: При использовании благосклонности фортуны у охотника, если смотреть в третьем лице, можно заметить змей вокруг ног, которые меняют цвет в зависимости от шейдера."
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

BAN_WORDS = ["заработок в интернете", "быстрый заработок", "лучший заработок", "с доходом от", "без вложений", "работа для студентов", "доход от", "нужны люди для работы",
    "арбитраж крипты", "мамкин инвестор",
    "раскрутка счета", "Требуется команда из 5 человек для интересного проекта на 2-4 часа. Оплата начинается от 8.000 руб. Пишите в личные сообщения для уточнения деталей."]

ALLOWED_DOMAINS = ["youtube.com", "youtu.be", "google.com", "yandex.ru", "github.com", "x.com", "reddit.com", "t.me", "discord.com", "vk.com", "d2gunsmith.com", "light.gg", "d2foundry.gg", "destinyitemmanager.com", "bungie.net", "d2armorpicker.com"]

LINK_RULES = "https://telegra.ph/Pravila-kanala-i-chata-09-18" 
LINK_CHAT = "https://t.me/+Uaa0ALuvIfs1MzYy" 

AI_SYSTEM_PROMPT = (
    "Ты — интеллектуальный ИИ-ассистент, специализирующийся на игре Destiny 2. По умолчанию интерпретируй ЛЮБОЙ вопрос в контексте Destiny 2, если явно не указано иное. НЕ используй форматирование текста Телеграмм в своих сообщениях для жирности текста и прочего (ПО ТИПУ **жирность** НЕ ИСПОЛЬЗУЙ), ПИШИ ОБЫЧНЫМ ТЕКСТОМ ВСЕГДА, также НЕ ПИШИ в своих ответах «[2]» подобное, выглядит как указание источников, убирай это из своих ответов."
    "КОНТЕКСТ И АКТУАЛЬНОСТЬ: Если вопрос касается Destiny 2 (лора, билдов, экзотиков, рейдов, патчей, меты, активностей и т.д.), используй самые актуальные знания, Старайся опираться на свежую информацию: текущий сезон, патчи, баланс, мету, Если данные могут быть устаревшими — явно укажи это, Используй официальные названия на русском языке (если они существуют), а также общепринятый англоязычный сленг сообщества."
    "ПРИМЕР: «Испытания Осириса (Trials)», «Ночная миссия: ГМ (Grandmaster Nightfall)», «Сияние (Radiant)», «Ослабление (Weaken)», «Перегрузка (Overload)», Используй термины так, как это делают игроки."
    "СТИЛЬ И ПОВЕДЕНИЕ: Пиши как опытный Страж, а не как справочник, Используй сленг комьюнити, но не перегибай, Не будь формальным без причины, Не объясняй очевидные для игроков вещи, если пользователь не новичок, Если вопрос задан кратко — отвечай кратко."
    "ДЛИНА ОТВЕТА: По умолчанию отвечай коротко: 2–4 предложения, Развёрнутые объяснения, билды и разборы давай ТОЛЬКО по прямой просьбе пользователя, "
    "МЫШЛЕНИЕ И ЛОГИКА: Всегда сначала определяй, что именно хочет пользователь: совет, факт, мнение, мету, лор. Если вопрос неоднозначен — задай один точный уточняющий вопрос, Не выдумывай механики и не додумывай лор, Если есть несколько вариантов (например, билды или экзотики) — укажи лучший и альтернативы."
    "КОД И ТЕХНИКА (если вдруг требуется): Отвечай корректно и по делу, Не уходи в оффтоп, не используй форматирование текста Телеграмм в своих сообщениях для жирности текста и прочего, пиши обычным текстом всегда, также не пиши в своих ответах «[2]» подобное, выглядит как указание источников, убирай это из своих ответов."
    "ГЛАВНОЕ: Твоя задача — быть актуальным, умным и полезным Destiny 2 ассистентом, Лучше дать короткий, точный и актуальный ответ, чем длинный и устаревший."
)

client = AsyncOpenAI(
    api_key=OPENAI_API_KEY, 
    base_url="https://api.artemox.com/v1"
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

# ================= БАЗА ДАННЫХ (SQLite + WAL) =================

# 1. Определяем пути
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "database.db")

# 2. Создаем папку data
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# 3. Подключаемся
conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 4. Включаем WAL (надежность)
cursor.execute("PRAGMA journal_mode=WAL;")
cursor.execute("PRAGMA synchronous=NORMAL;")
conn.commit()

# Создаем таблицу ТОЛЬКО для Дуэлей
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
    try:
        cursor.execute('SELECT wins, losses, points FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        else:
            return {'wins': 0, 'losses': 0, 'points': 0}
    except Exception as e:
        print(f"Ошибка БД (get): {e}")
        return {'wins': 0, 'losses': 0, 'points': 0}

def update_duel_stats(user_id, is_winner):
    """Обновляет очки после дуэли"""
    try:
        cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
        
        if is_winner:
            # Победа: +1 победа, +25 очков
            cursor.execute('UPDATE users SET wins = wins + 1, points = points + 25 WHERE user_id = ?', (user_id,))
        else:
            # Поражение: +1 луз, -10 очков (но не ниже 0)
            cursor.execute('UPDATE users SET losses = losses + 1, points = MAX(0, points - 10) WHERE user_id = ?', (user_id,))
        
        conn.commit()
    except Exception as e:
        print(f"Ошибка БД (get): {e}")

def update_stat(user_id, stat_type):
    """
    Эта функция нужна, чтобы старый код модерации не выдавал ошибку.
    Но в БД мы ничего не пишем.
    """
    pass 

def get_rank_info(points):
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

# --- ЗАПУСК ТУРНИРА (АДМИН) ---
@dp.message(Command("startcup"))
async def start_cup_command(message: types.Message, command: CommandObject):
    # 1. Проверка прав (только ты)
    if message.from_user.id != OWNER_ID:
        return # Игнорим остальных

    # 2. Проверка аргумента (число участников)
    args = command.args
    if not args or not args.isdigit():
        await message.reply("Укажи количество участников. Пример: `/startcup 8`")
        return

    count = int(args)
    
    # 3. Активируем турнир
    global TOURNAMENT_ACTIVE, TOURNAMENT_MAX_PLAYERS, TOURNAMENT_PLAYERS, TOURNAMENT_USERNAMES
    TOURNAMENT_ACTIVE = True
    TOURNAMENT_MAX_PLAYERS = count
    TOURNAMENT_PLAYERS = []
    TOURNAMENT_USERNAMES = []

    await message.answer(
        f"🏆 РЕГИСТРАЦИЯ НА ТУРНИР ОТКРЫТА!\n\n"
        f"Нужно стражей: {count}\n"
        f"Чтобы участвовать, напиши команду: /cup."
    )

# --- РЕГИСТРАЦИЯ (/cup) ---
@dp.message(Command("cup"))
async def join_cup_command(message: types.Message):
    global TOURNAMENT_ACTIVE, TOURNAMENT_PLAYERS, TOURNAMENT_USERNAMES

    # 1. Если турнира нет
    if not TOURNAMENT_ACTIVE:
        msg = await message.reply("Сейчас не ведется набор в турнир.")
        asyncio.create_task(delete_later(msg, 5))
        asyncio.create_task(delete_later(message, 5))
        return

    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name

    # 2. Если уже записался
    if user_id in TOURNAMENT_PLAYERS:
        msg = await message.reply("Ты уже в списке, Страж.")
        asyncio.create_task(delete_later(msg, 5))
        return

    # 3. Добавляем участника
    TOURNAMENT_PLAYERS.append(user_id)
    TOURNAMENT_USERNAMES.append(username)
    
    current_count = len(TOURNAMENT_PLAYERS)
    needed = TOURNAMENT_MAX_PLAYERS

    # 4. Проверяем, набрались ли люди
    if current_count < needed:
        await message.answer(f"✅ {username} записан! ({current_count}/{needed})")
    else:
        # ВСЕ НАБРАЛИСЬ -> ЗАКРЫВАЕМ НАБОР
        TOURNAMENT_ACTIVE = False
        
        # --- ЖЕРЕБЬЕВКА ---
        # Перемешиваем список ников
        random.shuffle(TOURNAMENT_USERNAMES)
        
        # Разбиваем на пары
        pairs_text = ""
        pair_num = 1
        
        # Идем шагом по 2 (0, 2, 4...)
        for i in range(0, len(TOURNAMENT_USERNAMES), 2):
            p1 = TOURNAMENT_USERNAMES[i]
            # Проверяем, есть ли пара (на случай нечетного числа)
            if i + 1 < len(TOURNAMENT_USERNAMES):
                p2 = TOURNAMENT_USERNAMES[i+1]
                pairs_text += f"⚔️ Пара {pair_num}: {p1} vs {p2}\n"
            else:
                # Если кто-то остался без пары
                pairs_text += f"⚠ Без пары: {p1}.\n"
            pair_num += 1

        await message.answer(
            f"🚫 НАБОР ЗАКРЫТ! Стартовая сетка сформирована.\n\n"
            f"{pairs_text}\n\n"
            f"Ждите инструкций от организатора!"
        )

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
        f"━━━━━━━━━━━━━━━━━\n"
        f"🏆 Ранг: {rank_title} ({points} очков)\n"
        f"{next_rank_str}\n"
        f"⚔️ Матчей: {total_games}\n"
        f"✅ Побед: {wins}\n"
        f"❌ Поражений: {losses}\n"
        f"📈 Винрейт: {winrate}%\n"
        f"━━━━━━━━━━━━━━━━━\n"
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
        f"🔴 Страж №1: {att_name}\n"
        f"🔵 Страж №2: {def_name}\n\n"
        f"📜 Сетапы классов:\n"
        f"🔫 - Ханты: Голден Ган + Туз\n"
        f"🔮 - Варлоки: Нова Бомба + Туз\n"
        f"☄️ - Титаны: Тандеркраш + Туз\n\n"
        f"{def_name}, ты принимаешь бой?",
        reply_markup=keyboard
    )

async def update_duel_message(callback: types.CallbackQuery, game_id):
    if game_id not in ACTIVE_DUELS:
        try: await callback.message.edit_reply_markup(reply_markup=None)
        except: pass
        return

    game = ACTIVE_DUELS[game_id]
    
    def get_hp_bar(hp):
        blocks = int(hp / 10) 
        return "▓" * blocks + "░" * (10 - blocks)

    p1 = game["p1"]
    p2 = game["p2"]
    
    # Определяем, кто сейчас ходит (объект игрока)
    current_player = p1 if game["turn"] == p1["id"] else p2
    current_class = current_player["class"]
    current_name = current_player["name"]

    # Формируем заголовок (показываем классы игроков)
    ru_cl = {"hunter": "🐍", "warlock": "🔮", "titan": "🛡"}
    ru_classes = {"hunter": "Хантер 🐍", "warlock": "Варлок 🔮", "titan": "Титан 🛡"}
    title = f"{ru_classes[p1['class']]} vs {ru_classes[p2['class']]}"

    # Статус полета Титана
    flying_status = ""
    if game.get("pending_crash"):
        flying_status = "\n⚡ ВРАГ В ВОЗДУХЕ! СБЕЙ ЕГО!"

    text = (
        f"⚔️ {title}\n\n"
        f"🔴 {p1['name']}:{p1['hp']} HP\n"
        f"[{get_hp_bar(p1['hp'])}]\n\n"
        f"🔵 {p2['name']}: {p2['hp']} HP\n"
        f"[{get_hp_bar(p2['hp'])}]\n\n"
        f"📜 Лог: {game['log']}\n"
        f"{flying_status}\n\n"
        f"👉 Ход: {current_name} [{ru_cl[current_class]}]"
    )

    # ГЕНЕРИРУЕМ КНОПКИ ДЛЯ ТОГО, ЧЕЙ СЕЙЧАС ХОД
    buttons = []
    
    if current_class == "hunter":
        buttons = [
            [InlineKeyboardButton(text="🔥 GG (12% / kill)", callback_data="duel_gg"),
             InlineKeyboardButton(text="♠️ Ace (55% / 25dmg)", callback_data="duel_ace")]
        ]
    elif current_class == "warlock":
        buttons = [
            [InlineKeyboardButton(text="🟣 Nova (14% / 75dmg/kill)", callback_data="duel_nova"),
             InlineKeyboardButton(text="♠️ Ace (55% / 25dmg)", callback_data="duel_ace")]
        ]
    elif current_class == "titan":
        # Если титан уже летит, кнопку полета блокировать не обязательно (мы блочим в логике),
        # но можно визуально убрать. Оставим пока как есть.
        buttons = [
            [InlineKeyboardButton(text="⚡ Crash (22% / Delay)", callback_data="duel_crash"),
             InlineKeyboardButton(text="♠️ Ace (55% / 25dmg)", callback_data="duel_ace")]
        ]

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        pass

# --- ОБРАБОТКА ВЫБОРА КЛАССА (ДЛЯ ДВОИХ) ---
@dp.callback_query(F.data.startswith("duel_pick_"))
async def duel_class_handler(callback: types.CallbackQuery):
    game_id = callback.message.message_id
    
    if game_id not in ACTIVE_DUELS:
        await callback.answer("Матч устарел.", show_alert=True)
        try: await callback.message.edit_text("🚫 Матч аннулирован. (Кажется, тапир?...)", reply_markup=None)
        except: pass
        return

    game = ACTIVE_DUELS[game_id]
    user_id = callback.from_user.id
    choice = callback.data.split("_")[2]

    # Определяем, кто нажал (Игрок 1 или Игрок 2)
    player = None
    if user_id == game["p1"]["id"]:
        player = "p1"
    elif user_id == game["p2"]["id"]:
        player = "p2"
    else:
        await callback.answer("Ты не участвуешь в дуэли!", show_alert=True)
        return

    # Если уже выбрал - ругаем
    if game[player]["class"] is not None:
        await callback.answer("Ты уже выбрал класс!", show_alert=True)
        return

    # Записываем выбор
    real_choice = choice
    if choice == "random":
        real_choice = random.choice(["hunter", "warlock", "titan"])
    
    game[player]["class"] = real_choice
    
    # Обновляем текст (показываем галочки)
    p1_status = "✅ Готов" if game["p1"]["class"] else "Ожидание..."
    p2_status = "✅ Готов" if game["p2"]["class"] else "Ожидание..."
    
    # Если ОБА выбрали — начинаем бой
    if game["p1"]["class"] and game["p2"]["class"]:
        game["state"] = "fighting"
        # Рандомно выбираем, кто первый
        game["turn"] = random.choice([game["p1"]["id"], game["p2"]["id"]])
        
        # Красивые названия для лога
        ru_classes = {"hunter": "Хантер", "warlock": "Варлок", "titan": "Титан"}
        c1 = ru_classes[game["p1"]["class"]]
        c2 = ru_classes[game["p2"]["class"]]
        
        game["log"] = f"⚔️ {c1} vs {c2}! Бой начинается!"
        await update_duel_message(callback, game_id)
    else:
        # Иначе просто обновляем сообщение
        text = (
            f"🗳 ВЫБОР КЛАССОВ\n\n"
            f"👤 {game['p1']['name']}: {p1_status}\n"
            f"👤 {game['p2']['name']}: {p2_status}\n\n"
            f"Ждем второго игрока..."
        )
        # Клавиатуру оставляем ту же
        current_kb = callback.message.reply_markup
        try: await callback.message.edit_text(text, reply_markup=current_kb)
        except: pass
        
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

    # --- СТАРТ (ПЕРЕХОД К ВЫБОРУ КЛАССОВ) ---
    if action == "duel_start":
        attacker_id = int(data_parts[1])
        defender_id = int(data_parts[2])
        if callback.from_user.id != defender_id:
            await callback.answer("Жди решения соперника!", show_alert=True)
            return

        game_id = callback.message.message_id
        
        try:
            att_m = await bot.get_chat_member(callback.message.chat.id, attacker_id)
            def_m = await bot.get_chat_member(callback.message.chat.id, defender_id)
            att_name = f"@{att_m.user.username}" if att_m.user.username else att_m.user.first_name
            def_name = f"@{def_m.user.username}" if def_m.user.username else def_m.user.first_name
        except:
            att_name, def_name = "Игрок 1", "Игрок 2"

        # Инициализируем игру, но ХП пока не важны, главное ID и имена
        ACTIVE_DUELS[game_id] = {
            "p1": {"id": attacker_id, "name": att_name, "hp": 100, "class": None}, # Класс пока пустой
            "p2": {"id": defender_id, "name": def_name, "hp": 100, "class": None},
            "state": "choosing_classes",
            "log": "Ожидание выбора классов..."
        }

        # Меню выбора для ОБОИХ
        buttons = [
            [
                InlineKeyboardButton(text="🐍 Хантер", callback_data="duel_pick_hunter"),
                InlineKeyboardButton(text="🔮 Варлок", callback_data="duel_pick_warlock"),
                InlineKeyboardButton(text="🛡 Титан", callback_data="duel_pick_titan")
            ],
            [InlineKeyboardButton(text="🎲 Рандом", callback_data="duel_pick_random")]
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        text = (
            f"🗳 ВЫБОР КЛАССОВ\n\n"
            f"👤 {att_name}: Ожидание...\n"
            f"👤 {def_name}: Ожидание...\n\n"
            f"Каждый выбирает сам за себя!"
        )

        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        return
    
    # --- ВЫСТРЕЛ ---
    if action in ["duel_gg", "duel_ace", "duel_nova", "duel_crash"]:
        game_id = callback.message.message_id
        
        if game_id not in ACTIVE_DUELS:
            await callback.answer("Матч устарел.", show_alert=True)
            try: await callback.message.edit_text("🚫 Матч аннулирован. (Кажется... Тапир?", reply_markup=None)
            except: pass
            return

        game = ACTIVE_DUELS[game_id]
        
        if game.get("state") != "fighting":
            await callback.answer("Бой еще не начался!", show_alert=True)
            return

        # Запрет на встречный полет (Титан)
        if game.get("pending_crash") and action == "duel_crash":
            await callback.answer("Противник в воздухе! Стреляй!", show_alert=True)
            return

        shooter_id = callback.from_user.id

        if shooter_id != game["turn"]:
            await callback.answer("Сейчас не твой ход!", show_alert=True)
            return

        # Определяем участников
        if shooter_id == game["p1"]["id"]:
            shooter = game["p1"]
            target = game["p2"]
        else:
            shooter = game["p2"]
            target = game["p1"]

        # ПРОВЕРКА КЛАССА ИГРОКА
        my_class = shooter["class"]
        
        if my_class == "hunter" and action not in ["duel_gg", "duel_ace"]:
            await callback.answer("Это не твое оружие!", show_alert=True); return
            
        if my_class == "warlock" and action not in ["duel_nova", "duel_ace"]:
            await callback.answer("Это не твое оружие!", show_alert=True); return
            
        if my_class == "titan" and action not in ["duel_crash", "duel_ace"]:
            await callback.answer("Это не твое оружие!", show_alert=True); return
       
        if game.get("pending_crash") and action == "duel_crash":
            await callback.answer("Противник в воздухе! Сбей его, а не улетай сам!", show_alert=True)
            return
        
        shooter_id = callback.from_user.id

        if shooter_id != game["turn"]:
            await callback.answer("Сейчас не твой ход!", show_alert=True)
            return

        # Определяем участников
        if shooter_id == game["p1"]["id"]:
            shooter = game["p1"]
            target = game["p2"]
        else:
            shooter = game["p2"]
            target = game["p1"]

        # === ЛОГИКА ТИТАНА (ЗАПУСК) ===
        if action == "duel_crash":
            game["pending_crash"] = shooter_id # Кто летит
            game["crash_turns"] = 2            # Сколько ходов у врага
            game["turn"] = target["id"]        # Передаем ход врагу
            
            game["log"] = f"⚡ ГРОМ! {shooter['name']} взмывает в воздух! У {target['name']} есть 2 выстрела!"
            
            await update_duel_message(callback, game_id)
            await callback.answer()
            return

        # === ЛОГИКА ОБЫЧНОЙ СТРЕЛЬБЫ ===
        damage = 0
        hit = False
        weapon_name = ""

        if action == "duel_gg":
            weapon_name = "🔥 Голден Ган"
            if random.randint(1, 100) <= 9: hit = True; damage = 100
        elif action == "duel_ace":
            weapon_name = "♠️ Пиковый Туз"
            if random.randint(1, 100) <= 55: hit = True; damage = 25
        elif action == "duel_nova":
            weapon_name = "🟣 Нова Бомба"
            roll = random.randint(1, 100)
            if roll <= 5: hit = True; damage = 100
            elif roll <= 14: hit = True; damage = 75
            else: hit = False; damage = 0

        # Наносим урон
        log_msg = ""
        if hit:
            target["hp"] -= damage
            if target["hp"] < 0: target["hp"] = 0
            if damage >= 100:
                log_msg = f"💥 КРИТ! {shooter['name']} уничтожает врага с {weapon_name}!"
            else:
                log_msg = f"💥 {shooter['name']} попадает с {weapon_name} (-{damage} HP)!"
        else:
            log_msg = f"💨 {shooter['name']} промазал с {weapon_name}."

        # Проверка: Умер ли враг от выстрела?
        if target["hp"] <= 0:
            update_duel_stats(shooter['id'], is_winner=True)
            update_duel_stats(target['id'], is_winner=False)
            del ACTIVE_DUELS[game_id]
            await callback.message.edit_text(f"🏆 ПОБЕДА!\n\n{log_msg}\n\n💀 {target['name']} повержен.", reply_markup=None)
            await callback.answer()
            return

        # === ЛОГИКА ПОЛЕТА / ПРИЗЕМЛЕНИЯ ===
        # Проверяем, летит ли кто-то (pending_crash - ID Титана)
        flying_titan_id = game.get("pending_crash")
        
        if flying_titan_id:
            # Если стрелял тот, кто НЕ летит (то есть враг, пытающийся сбить)
            if shooter_id != flying_titan_id:
                # Уменьшаем счетчик ходов
                game["crash_turns"] -= 1
                turns_left = game["crash_turns"]
                
                if turns_left > 0:
                    # Если ходы еще есть — враг стреляет снова
                    game["log"] = f"{log_msg}\n⏳ Титан все еще в воздухе! Еще 1 выстрел!"
                    game["turn"] = shooter_id # Ход остается у стрелка
                else:
                    # Ходы кончились — Титан приземляется!
                    titan_id = flying_titan_id
                    # Определяем объект Титана (кто из них p1/p2)
                    titan = game["p1"] if game["p1"]["id"] == titan_id else game["p2"]
                    enemy = game["p1"] if game["p1"]["id"] != titan_id else game["p2"]
                    
                    game["pending_crash"] = None # Сброс полета
                    
                    # Шанс 22%
                    if random.randint(1, 100) <= 22:
                        enemy["hp"] = 0
                        
                        update_duel_stats(titan['id'], True)
                        update_duel_stats(enemy['id'], False)
                        del ACTIVE_DUELS[game_id]
                        
                        final_msg = f"🏆 ПОБЕДА!\n\n{log_msg}\n\n⚡ БУУМ! {titan['name']} размазал соперника! (-100 HP)"
                        await callback.message.edit_text(final_msg, reply_markup=None)
                        await callback.answer()
                        return
                    else:
                        game["log"] = f"{log_msg}\n\n💨 {titan['name']} промахивается ультой и врезается в Dredgen Sere!"
                        game["turn"] = titan_id # Ход переходит Титану (он приземлился)

        else:
            # Если никто не летит — просто передаем ход
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
            except Exception as e:
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
            except Exception as e:
                await log_to_owner(f"❌ Ошибка бана: {e}")

    # --- УДАЛЕНИЕ ---
    for word in BAD_WORDS:
        if word in text_lower:
            try:
                await message.delete()
                msg = await message.answer(f"@{username}, рот с мылом помой, у тебя скверна изо рта лезет.")
                asyncio.create_task(delete_later(msg, 15))
                return
            except Exception as e:
                await log_to_owner(f"❌ Ошибка удаления мата: {e}")

    # --- ССЫЛКИ ---
    if not is_link_allowed(message.text, chat_username):
        try:
            await message.delete()
            msg = await message.answer(f"@{username}, ссылки на чужие помойки запрещены. Не засоряй сеть Вексов.")
            asyncio.create_task(delete_later(msg, 15))
            return
        except Exception as e:
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

    # --- ИИ (ТОЛЬКО ПО ТЕГУ + КУЛДАУН) ---
    bot_info = await bot.get_me()
    
    # Проверяем, есть ли тег бота в сообщении
    is_mention = f"@{bot_info.username}" in message.text

    # Реагируем ТОЛЬКО если есть тег (реплаи игнорируем)
    if is_mention:
        clean_text = message.text.replace(f"@{bot_info.username}", "").strip()
        
        if not clean_text:
            msg = await message.answer("Чего звал? Пиши вопрос сразу.")
            asyncio.create_task(delete_later(msg, 5))
            return

        # ПРОВЕРКА КУЛДАУНА
        global AI_COOLDOWN_TIME
        now = datetime.now()
        
        if now < AI_COOLDOWN_TIME:
            time_left = AI_COOLDOWN_TIME - now
            minutes_left = int(time_left.total_seconds() // 60) + 1
            
            msg = await message.reply(
                f"Я сейчас занят, лайт поднимаю в портале. "
                f"Обратись ко мне через {minutes_left} мин, когда курить пойду."
            )
            asyncio.create_task(delete_later(msg, 5))
            return

        # ЗАПРОС К ИИ
        try:
            await bot.send_chat_action(message.chat.id, action="typing")
            
            response = await client.chat.completions.create(
                model="sonar",
                messages=[
                    {"role": "system", "content": AI_SYSTEM_PROMPT},
                    {"role": "user", "content": clean_text}
                ],
                temperature=0.8,
                max_tokens=200
            )
            
            ai_reply = response.choices[0].message.content
            await message.reply(ai_reply)
            
            # Ставим КД 10 минут
            AI_COOLDOWN_TIME = datetime.now() + timedelta(minutes=5)
            
        except Exception as e:
            await log_to_owner(f"❌ Ошибка ИИ: {e}")
            # Если ошибка — не отвечаем пользователю, чтобы не спамить
            
# ================= ЗАПУСК =================

async def main():
    print("Бот настроен карать.")
    asyncio.create_task(check_silence_loop())
    dp.message.middleware(AntiFloodMiddleware())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())




