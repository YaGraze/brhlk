import asyncio
import logging
import re
import os
import random

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ChatMemberStatus
from aiogram.types import LinkPreviewOptions
from datetime import datetime, timedelta
from aiogram.filters import CommandObject, Command
from aiogram.types import ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton, ReactionTypeEmoji
import google.generativeai as genai

# ================= НАСТРОЙКИ =================

BOT_TOKEN = "8400087235:AAFZubO4ijQnZCOjLZ8UulzcthDixzOqSt0"
GOOGLE_API_KEY = "AIzaSyAIYu6GbRS0HtYlgEPLKgm1QuU8PZ15Z2E"

LINK_TAPIR_GUIDE = "https://t.me/destinygoods/9814" 

PENDING_VERIFICATION = {}

# --- ID АДМИНСКОГО ЧАТА (Группы, куда кидать репорты) ---
# Узнать ID можно через бота @getmyid_bot (добавь его в админский чат)
# ID группы всегда начинается с минуса, например -100123456789
ADMIN_CHAT_ID = -1003376406623  # <--- ЗАМЕНИ НА СВОЙ
CHAT_ID = -1002129048580

# --- ФАКТЫ ИЗ ЛОРА (Для тишины) ---
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

# Фразы для админского мута (Destiny 2 style)
ADMIN_MUTE_PHRASES = [
    "Протокол 'Подавление' активирован. @username отправляется в стазис на {time} мин.",
    "Судьи Испытаний Осириса вынесли приговор. @username молчит {time} мин.",
    "Авангард лишил тебя Света на {time} мин. Подумай над поведением, @username.",
    "Шакс недоволен. @username удален с арены на {time} мин.",
    "Приказ командования: режим радиомолчания для @username на {time} мин."
]

# --- НОВЫЕ ФРАЗЫ ПРО ТАПИРА ---
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

    # Фразы для МУТА (Проигрыш)
MUTE_SHORT_PHRASES = [
    "ПОДАВЛЕНИЕ! Тебя накрыло стрелой Ночного Охотника. @username молчит 15 минут.",
    "Тьма поглотила твой голос. @username отправляется в стазис-кристалл на 15 минуточек.",
    "Слишком много болтаешь, Страж. Шакс отобрал твою клавиатуру.",
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

# Фразы для ВЫЖИВШИХ (Выигрыш)
SAFE_PHRASES = [
    "Странник избрал тебя. Живи пока.",
    "У тебя что, 100 Здоровья? Пуля отскочила.",
    "ЛВ выстрелил, но призрак успел тебя воскресить. Повезло.",
    "Рандом на твоей стороне, Страж. ЛВ осечку дал.",
    "Ты увернулся, как Хант с перекатом. Заряжаем ЛВ заново?"
]

KEEP_POSTED_STICKER_ID = "CAACAgIAAxkBAAEQSpppcOtmxGDL9gH882Rg8pZrq5eXVAACXZAAAtfYYEiWmZcGWSTJ5TgE"

# Слова для триггера стикера
REFUND_KEYWORDS = ["рефанд", "refund", "refound", "возврат средств", "вернуть деньги"]

VPN_PHRASES = ["Ты имел ввиду КВН? Измени сообщение, эти 3 буквы запрещены в чате."]

# Списки слов и доменов (Те же, что и были)
BAD_WORDS = ["лгбт", "цп", "казино", "цп", "child porn", "cp", "закладки", "мефедрон", 
    "шишки", "гашиш", "купить скорость" "чурка", "хач", "ниггер", "хохол", "кацап", 
    "москаль", "свинособак", "черномаз", "нигга", "nigga", "nigger", "hohol", 
    "магазин 24/7", "hydra", "kraken", "убейся", "выпей яду", "роскомнадзорнись", "мамку ебал", "Путин", "Зеленский", "война", "либераха", "гейропа", "кокс", "фашист"] 
BAN_WORDS = ["заработок в интернете", "быстрый заработок",
    "арбитраж крипты", "мамкин инвестор",
    "раскрутка счета", "Требуется команда из 5 человек для интересного проекта на 2-4 часа. Оплата начинается от 8.000 руб. Пишите в личные сообщения для уточнения деталей."]
ALLOWED_DOMAINS = ["youtube.com", "youtu.be", "google.com", "yandex.ru", "github.com", "x.com", "reddit.com", "t.me", "discord.com", "vk.com", "d2gunsmith.com", "light.gg", "d2foundry.gg", "destinyitemmanager.com", "bungie.net", "d2armorpicker.com"]

# Ссылки для кнопок
LINK_RULES = "https://telegra.ph/Pravila-kanala-i-chata-09-18" # Ссылка на пост с правилами (скопируй в ТГ)
LINK_CHAT = "https://t.me/+Uaa0ALuvIfs1MzYy" # Ссылка на твой чат или предложку

# Настройка Google Gemini
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash') 

# Промпт (Характер)
AI_SYSTEM_PROMPT = (
    "Ты — дерзкий Призрак-модератор чата по Destiny 2. "
    "Твоя задача — подкалывать Стражей (пользователей), используя сленг игры "
    "(ньюлайт, лайт, годролл, мета, вайп, дреджен, баунти, экзот). "
    "Если спрашивают чушь — отвечай в стиле Скитальца (Drifter) или лорда Шакса. "
    "Будь кратким, циничным и остроумным. Обращайся на 'ты', называй их Стражами."
)

# ================= ИНИЦИАЛИЗАЦИЯ =================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ================= ФУНКЦИИ ПРОВЕРКИ (Те же самые) =================

async def check_silence_loop():
    """Фоновая задача: проверяет тишину в чате"""
    global LAST_MESSAGE_TIME
    while True:
        # Проверяем раз в 5 минут
        await asyncio.sleep(300) 
        
        # Если прошло больше 1 часа (3600 секунд) с последнего сообщения
        if (datetime.now() - LAST_MESSAGE_TIME).total_seconds() > 3600:
            # Берем случайный факт
            fact = random.choice(LORE_FACTS)
            
            try:
                # ЗАМЕНИ НА ID ТВОЕГО ОСНОВНОГО ЧАТА (тот же, что и ADMIN_CHAT_ID или другой)
                TARGET_CHAT_ID = CHAT_ID 
                
                await bot.send_message(TARGET_CHAT_ID, f"📢 <b>Минутка Лора:</b>\n{fact}")
                
                # Обновляем время, чтобы не спамить фактами каждую минуту
                LAST_MESSAGE_TIME = datetime.now()
            except Exception as e:
                print(f"Ошибка отправки факта: {e}")

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
    """Ждет 5 минут и банит, если задача не была отменена"""
    try:
        # Ждем 5 минут (300 секунд)
        await asyncio.sleep(300) 
        
        # Если мы здесь, значит таймер не отменили -> БАН
        await bot.ban_chat_member(chat_id, user_id)
        
        # Отправляем сообщение о бане
        msg = await bot.send_message(
            chat_id, 
            f"@{username} оказался одержимым Тьмой (БОТ). Изгнан в пустоту."
        )
        
        # Удаляем сообщение о бане через 15 сек
        await asyncio.sleep(15)
        await msg.delete()
        
    except asyncio.CancelledError:
        # Если задачу отменили (человек написал сообщение), ничего не делаем
        pass
    except Exception as e:
        print(f"Ошибка верификации: {e}")
    finally:
        # Убираем из списка (если он там еще есть)
        if user_id in PENDING_VERIFICATION:
            del PENDING_VERIFICATION[user_id]

# ================= ХЕНДЛЕРЫ =================

# --- 1. ВЫЗОВ НА ДУЭЛЬ (ОТПРАВКА КНОПОК) ---
@dp.message(Command("duel"))
async def duel_command(message: types.Message):
    if not message.reply_to_message:
        msg = await message.reply("⚔️ Чтобы вызвать на дуэль, ответь на сообщение соперника командой /duel.")
        await asyncio.sleep(5)
        await msg.delete()
        return

    attacker = message.from_user
    defender = message.reply_to_message.from_user

    if defender.is_bot or defender.id == attacker.id:
        msg = await message.reply("Найди себе достойного противника.")
        await asyncio.sleep(5)
        await msg.delete()
        return

    # --- ПОЛУЧЕНИЕ ИМЕН (@username) ---
    # Если есть username, берем его, иначе берем имя
    att_name = f"@{attacker.username}" if attacker.username else attacker.first_name
    def_name = f"@{defender.username}" if defender.username else defender.first_name

    buttons = [
        [
            InlineKeyboardButton(text="🔫 Принять вызов", callback_data=f"duel_accept|{attacker.id}|{defender.id}"),
            InlineKeyboardButton(text="🏳️ Сбежать", callback_data=f"duel_decline|{attacker.id}|{defender.id}")
        ]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.answer(
        f"🔥 ГОРНИЛО: ПРИВАТНЫЙ МАТЧ!\n\n"
        f"🛡 Страж №1: {att_name}\n"
        f"🎯 Страж №2: {def_name}\n\n"
        f"{def_name}, ты принимаешь бой? Проигравший вылетает на орбиту (Kick).",
        reply_markup=keyboard
    )

# --- 2. ОБРАБОТКА КНОПОК (ЛОГИКА БОЯ) ---
@dp.callback_query(F.data.startswith("duel_"))
async def duel_callback(callback: types.CallbackQuery):
    data_parts = callback.data.split("|")
    action = data_parts[0]
    attacker_id = int(data_parts[1])
    defender_id = int(data_parts[2])

    if callback.from_user.id != defender_id:
        if callback.from_user.id == attacker_id:
            await callback.answer("Жди решения соперника, че торопишься?", show_alert=True)
        else:
            await callback.answer("Это не твоя разборка, Страж.", show_alert=True)
        return

    # Получаем данные о пользователях заново, чтобы достать username
    try:
        att_member = await bot.get_chat_member(callback.message.chat.id, attacker_id)
        def_member = await bot.get_chat_member(callback.message.chat.id, defender_id)
        
        att_user = att_member.user
        def_user = def_member.user

        # Логика: Если есть юзернейм -> @username. Если нет -> Имя.
        att_name = f"@{att_user.username}" if att_user.username else att_user.first_name
        def_name = f"@{def_user.username}" if def_user.username else def_user.first_name

    except Exception:
        # Если не смогли получить (редкая ошибка), ставим заглушки
        att_name = "Страж №1"
        def_name = "Страж №2"

    # --- ОТКАЗ ---
    if action == "duel_decline":
        await callback.message.edit_text(
            f"🏳️ ДУЭЛЬ ОТМЕНЕНА\n\n"
            f"{def_name} отказался рисковать.\n"
            f"{att_name} убирает оружие.",
            reply_markup=None
        )
        return

    # --- БОЙ ---
    if action == "duel_accept":
        attacker_wins = random.choice([True, False])
        
        if attacker_wins:
            winner_name = att_name
            loser_name = def_name
            loser_id = defender_id
            win_phrase = f"{att_name} делает невероятный флик в голову с Пикового Туза!"
        else:
            winner_name = def_name
            loser_name = att_name
            loser_id = attacker_id
            win_phrase = f"{def_name} Атаковал ультой!"

        result_text = (
            f"⚔️ Все успели сделать ставку?\n\n"
            f"{win_phrase}\n"
            f"💀 {loser_name} разлетается на частицы Света."
        )

        await callback.message.edit_text(result_text, reply_markup=None)

        # КИК
        try:
            loser_check = await bot.get_chat_member(callback.message.chat.id, loser_id)
            if loser_check.status in ["administrator", "creator"]:
                await callback.message.answer(f"{loser_name} проиграл, но Админов кикать нельзя. Коррупция Авангарда!")
            else:
                await bot.ban_chat_member(callback.message.chat.id, loser_id)
                await bot.unban_chat_member(callback.message.chat.id, loser_id)
                await callback.message.answer(f"{loser_name} теряет соединение с чатом... снова Тапир?")
        except Exception as e:
            await callback.message.answer(f"Ошибка кика: {e}")

# --- 2. РЕПОРТ (С ПРАВИЛЬНОЙ ССЫЛКОЙ ДЛЯ ЧАСТНЫХ ЧАТОВ) ---
@dp.message(Command("report"))
async def report_command(message: types.Message):

    if not message.reply_to_message:
        msg = await message.reply("⚠️ Используй команду в ответ на сообщение нарушителя.")
        await asyncio.sleep(5)
        await msg.delete()
        return

    reported_msg = message.reply_to_message
    reporter = message.from_user.username or message.from_user.first_name
    violator = reported_msg.from_user.username or reported_msg.from_user.first_name

    # --- ГЕНЕРАЦИЯ ССЫЛКИ ---
    if message.chat.username:
        # Если у чата есть публичный юзернейм (t.me/chatname)
        msg_link = f"https://t.me/{message.chat.username}/{reported_msg.message_id}"
    else:
        # Если чат частный (Private Supergroup)
        # ID выглядит как -1001234567890. Для ссылки нужно убрать "-100".
        chat_id_str = str(message.chat.id)
        if chat_id_str.startswith("-100"):
            clean_id = chat_id_str[4:] # Отрезаем первые 4 символа (-100)
        else:
            clean_id = chat_id_str # На всякий случай, если ID другой
            
        msg_link = f"https://t.me/c/{clean_id}/{reported_msg.message_id}"

    # Текст отчета
    report_text = (
        f"🚨 СИГНАЛ ТРЕВОГИ (РЕПОРТ)\n"
        f"🕵️‍♂️ Донёс: @{reporter}\n"
        f"💀 Нарушил: @{violator}\n\n"
        f"👉 {msg_link}"
    )

    try:
        # Отправляем только текст с красивой ссылкой
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=report_text)
        
        # Подтверждение юзеру
        confirm = await message.answer("✅ Жалоба отправлена Авангарду.")
        await asyncio.sleep(5)
        await msg.delete()
        
    except Exception as e:
        # Если бот не в админском чате или ID неверен
        print(f"Ошибка репорта: {e}")
        
@dp.message(Command("mute"))
async def admin_mute_command(message: types.Message, command: CommandObject):

    # 2. Проверяем, что пишет АДМИН
    user_status = await bot.get_chat_member(message.chat.id, message.from_user.id)
    if user_status.status not in ["administrator", "creator"]:
        # Если пишет не админ — игнорим или удаляем сразу
        return

    # 3. Ищем, кого мутить и на сколько
    target_user = None
    mute_minutes = 15 # Значение по умолчанию

    # Разбираем аргументы команды (все, что написано после /mute)
    args = command.args.split() if command.args else []

    # --- Поиск времени в аргументах ---
    for arg in args:
        if arg.isdigit():
            mute_minutes = int(arg)
            break
    
    # --- Поиск пользователя ---
    # Вариант А: Команда отправлена ОТВЕТОМ на сообщение (самый надежный)
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    
    # Вариант Б: Пользователь упомянут в команде (@username)
    elif message.entities:
        for entity in message.entities:
            if entity.type == "text_mention":
                # Это если упомянули пользователя без юзернейма (ссылка-имя)
                target_user = entity.user
                break
            elif entity.type == "mention":
                # Это обычный @username. 
                # Увы, бот не всегда может получить ID по тексту, поэтому лучше использовать Reply
                # Но мы попробуем поискать (этот блок сложен без базы данных, поэтому лучше Reply)
                pass

    # Если не нашли кого мутить
    if not target_user:
        msg = await message.answer("⚠️ Чтобы выдать мут, отправь команду в ответ на сообщение нарушителя.\nПример: /mute 30")
        await asyncio.sleep(10)
        await msg.delete()
        return

    # Проверка: Не пытаемся ли замутить другого админа
    target_status = await bot.get_chat_member(message.chat.id, target_user.id)
    if target_status.status in ["administrator", "creator"]:
        msg = await message.answer("❌ Я не могу заглушить офицера Авангарда (Админа).")
        await asyncio.sleep(15)
        await msg.delete()
        return

    # 4. Выдаем МУТ
    try:
        unmute_time = datetime.now() + timedelta(minutes=mute_minutes)
        
        await message.chat.restrict(
            user_id=target_user.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=unmute_time
        )

        # 5. Отправляем красивый ответ
        username = target_user.username or target_user.first_name
        phrase = random.choice(ADMIN_MUTE_PHRASES).format(
            time=mute_minutes
        ).replace("@username", f"@{username}")

        await message.answer(phrase)

    except Exception as e:
        msg = await message.answer(f"Ошибка протокола: {e}")
        await asyncio.sleep(10)
        await msg.delete()

@dp.message(Command("unmute"))
async def admin_unmute_command(message: types.Message):
    # 1. Удаляем сообщение админа через 5 секунд

    # 2. Проверяем права АДМИНА
    user_status = await bot.get_chat_member(message.chat.id, message.from_user.id)
    if user_status.status not in ["administrator", "creator"]:
        return # Просто игнорим, если пишет не админ

    # 3. Проверяем, есть ли Reply
    if not message.reply_to_message:
        msg = await message.reply("⚠️ Чтобы снять мут, сделай Reply (Ответить) на сообщение и напиши /unmute")
        await asyncio.sleep(20)
        await msg.delete()
        return

    target_user = message.reply_to_message.from_user
    username = target_user.username or target_user.first_name

    # 4. Снимаем мут (Возвращаем права)
    try:
        # Разрешаем всё
        await message.chat.restrict(
            user_id=target_user.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_send_polls=True,
                can_add_web_page_previews=True
            ),
            # Важный момент: until_date не нужен, если мы возвращаем права,
            # но для надежности ставим "прямо сейчас", чтобы сбросить таймер
            until_date=datetime.now() 
        )

        # 5. Пишем ответ
        text = random.choice(UNMUTE_PHRASES).replace("@username", f"@{username}")
        await message.answer(text)

    except Exception as e:
        print(f"Ошибка размута: {e}")
        msg = await message.answer("Не удалось снять мут. Возможно, я не админ?")
        await asyncio.sleep(10)
        await msg.delete()

# 1. Бан-рулетка (Мут)
@dp.message(Command("lastword", "lw", "ластворд", "лв"))
async def mute_roulette(message: types.Message):
    # 1. Генерируем шанс выстрела (1 к 100)
    bullet = random.randint(1, 4) 
    username = message.from_user.username or message.from_user.first_name

    # --- СЦЕНАРИЙ МУТА (ВЫПАЛО 1) ---
    if bullet == 1:
        # Проверка на админа (их нельзя мутить)
        user_status = await bot.get_chat_member(message.chat.id, message.from_user.id)
        if user_status.status in ["administrator", "creator"]:
            msg = await message.reply("Выстрел! Прямое попадание, но ты Админ с овершилдом. Живи.")
            return

        try:
            # 2. ОПРЕДЕЛЯЕМ ДЛИТЕЛЬНОСТЬ МУТА (РАНДОМ 1 к 5)
            # Генерируем число от 1 до 5
            duration_roll = random.randint(1, 5)
            
            if duration_roll == 5:
                # Шанс 1/5 (20%) -> 30 мин
                mute_duration = timedelta(minutes=30)
                phrase = random.choice(MUTE_CRITICAL_PHRASES).replace("@username", f"@{username}")
            else:
                # Шанс 4/5 (80%) -> 15 МИНУТ
                mute_duration = timedelta(minutes=15)
                phrase = random.choice(MUTE_SHORT_PHRASES).replace("@username", f"@{username}")

            # Применяем ограничения
            unmute_time = datetime.now() + mute_duration
            
            await message.chat.restrict(
                user_id=message.from_user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=unmute_time
            )
            
            # Отправляем сообщение
            await message.reply(phrase)
            
        except Exception as e:
            await message.reply("Хотел выдать мут, но не хватает прав админа! Проверь настройки.")
            print(f"Ошибка мута: {e}")

    # --- СЦЕНАРИЙ ЖИЗНИ (ВЫПАЛО 2-100) ---
    else:
        text = random.choice(SAFE_PHRASES)
        msg = await message.reply(f"{text}")
        await asyncio.sleep(20)
        await msg.delete()

PROCESSED_ALBUMS = []
@dp.message(F.is_automatic_forward)
async def auto_comment_channel_post(message: types.Message):
    if message.media_group_id:
        # Если этот альбом уже есть в списке — значит мы уже ответили на первое фото
        if message.media_group_id in PROCESSED_ALBUMS:
            return # Просто игнорируем и выходим из функции
        
        # Если нет, добавляем ID в список
        PROCESSED_ALBUMS.append(message.media_group_id)
        
        # Чистим список, чтобы не забивать память (храним последние 100 альбомов)
        if len(PROCESSED_ALBUMS) > 100:
            PROCESSED_ALBUMS.pop(0)
    try:
        # Небольшая задержка, чтобы выглядело естественнее (2-5 секунд)
        await asyncio.sleep(1)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📜 Правила", url=LINK_RULES),
                InlineKeyboardButton(text="💬 Чат", url=LINK_CHAT)
            ]
        ])
        # Отвечаем на пост (это и будет комментарием)
        await message.reply(f"Оскорбления, реклама, спам, размещение ссылок, размещение недостоверной информации, выяснения отношений — Предупреждение/Мут.\nПовторное несоблюдение правил - БАН.\n\nПо вопросам рекламы/покупки: @llRGaming.\nПо вопросам касательно бота: @yaGraze.", reply_markup=keyboard)
        print(f"Оставил комментарий к посту: {message.message_id}")
    except Exception as e:
        print(f"Не удалось оставить комментарий: {e}")

@dp.message(F.new_chat_members)
async def welcome(message: types.Message):
    for user in message.new_chat_members:
        # Игнорируем ботов
        if user.is_bot: continue

        username = user.username or user.first_name
        
        # 1. Отправляем предупреждение
        msg = await message.answer(
            f"Глаза выше, Страж @{username}! \n"
            f"Система безопасности чата активирована. 🛡\n"
            f"Напиши любое сообщение в чат в течение 5 минут, чтобы подтвердить свой Свет.\n"
            f"Иначе ты будешь забанен."
        )
        
        # 2. Запускаем таймер на бан
        task = asyncio.create_task(verification_timeout(message.chat.id, user.id, username))
        
        # 3. Сохраняем задачу, чтобы потом её можно было отменить
        PENDING_VERIFICATION[user.id] = task
        
        # Удаляем приветствие через 5 минут (чтобы не висело вечно, если человека забанят)
        await asyncio.sleep(300)
        await msg.delete()

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

# --- ПРОВЕРКА НОВИЧКА (ВЕРИФИКАЦИЯ) ---
    if user_id in PENDING_VERIFICATION:
        # 1. Достаем таймер и отменяем его (бан отменяется)
        task = PENDING_VERIFICATION.pop(user_id)
        task.cancel()
        
        # 2. Пишем об успехе
        username = message.from_user.username or message.from_user.first_name
        success_msg = await message.reply(
            f"Сканирование Света завершено. Допуск получен, Страж @{username}. Веди себя прилично, я всё вижу."
        )
        
        # 3. Удаляем сообщение об успехе через 15 секунд
        asyncio.create_task(delete_later(success_msg, 15))
    
# --- ПЕРСОНАЛЬНЫЙ КЛОУН ДЛЯ @galreiz (Шанс 1 к 3) ---
    if message.from_user.username and message.from_user.username.lower() == "galreiz":
        # Кидаем кубик: 1, 2 или 3.
        # Если выпадает 1 — ставим клоуна. Если 2 или 3 — не ставим.
        if random.randint(1, 3) == 1:
            try:
                await message.react([ReactionTypeEmoji(emoji="🤡")])
            except:
                pass 
    
    # --- БАН ---
    for word in BAN_WORDS:
        if word in text_lower:
            try:
                await message.delete()
                await message.chat.ban(message.from_user.id)
                msg = await message.answer(f"@{username} улетел в бан. Воздух стал чище.")
                await asyncio.sleep(15)
                await msg.delete()
                return
            except: pass

    # --- УДАЛЕНИЕ ---
    for word in BAD_WORDS:
        if word in text_lower:
            try:
                await message.delete()
                msg = await message.answer(f"@{username}, рот с мылом помой, у тебя скверна изо рта лезет.")
                await asyncio.sleep(15)
                await msg.delete()
                return
            except: pass

    # --- ССЫЛКИ ---
    if not is_link_allowed(message.text, chat_username):
        try:
            await message.delete()
            msg = await message.answer(f"@{username}, ссылки на чужие помойки запрещены. Не засоряй сеть Вексов.")
            await asyncio.sleep(15)
            await msg.delete()
            return
        except: pass

    # --- ПАСХАЛКА: vpn ---
    # Проверяем, есть ли слово vpn в тексте
    if "vpn" in text_lower or "впн" in text_lower:
        # Выбираем случайную фразу
        vpn_msg = random.choice(VPN_PHRASES)
        # Отвечаем на сообщение (не удаляем сообщение пользователя, пусть все видят позор)
        await message.reply(vpn_msg)
        return # Прерываем, чтобы ИИ не отвечал следом

     # --- ПАСХАЛКА: ТАПИР (TAPIR) ---
    if "тапир" in text_lower or "tapir" in text_lower:
        # Выбираем фразу
        tapir_msg = random.choice(TAPIR_PHRASES)
        
        # Создаем кнопку
        tapir_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔧 Гайд: обход тапира", url=LINK_TAPIR_GUIDE)]
        ])
        
        # Отправляем ответ с кнопкой
        await message.reply(tapir_msg, reply_markup=tapir_kb)
        return 
        
        # --- РЕАКЦИЯ "КЛОУН" (🤡) ---
    # Если написали "клоун" в ответ на чье-то сообщение
    if message.reply_to_message and "клоун" in text_lower:
        try:
            # Ставим реакцию на ТО сообщение, на которое ответили
            await message.reply_to_message.react([ReactionTypeEmoji(emoji="🤡")])
        except Exception as e:
            # Ошибки могут быть, если сообщение слишком старое или у бота нет прав
            print(f"Не удалось поставить реакцию: {e}")

        # --- РЕАКЦИЯ "ДЕРЖИ В КУРСЕ" ---
    # Если ответили фразой "держи в курсе"
    if message.reply_to_message and "держи в курсе" in text_lower:
        try:
            # Бот отправляет стикер в ответ на ИСХОДНОЕ сообщение (которое троллят)
            await message.reply_to_message.reply_sticker(sticker=KEEP_POSTED_STICKER_ID)
        except Exception:
            pass
    
    # --- РЕАКЦИЯ НА "РЕФАНД" (СТИКЕР) ---
    # Проверяем, есть ли ключевые слова в тексте
    is_refund = any(word in text_lower for word in REFUND_KEYWORDS)
    if is_refund:
        try:
            # Отправляем стикер ответом
            await message.reply_sticker(sticker="CAACAgIAAxkBAAMWaW-qYjAAAYfnq0GFJwER5Mh-AAG7ywAC1YMAApJ_SEvZaHqj_zTQLzgE")
        except Exception as e:
            # Бот напишет в чат, что пошло не так
            await message.reply(f"⚠️ Не могу отправить стикер. Ошибка:\n{e}")
        return

    # --- ИИ ОТВЕТЫ (GEMINI) ---
    bot_info = await bot.get_me()
    is_reply_to_bot = message.reply_to_message and message.reply_to_message.from_user.id == bot.id
    is_mention = f"@{bot_info.username}" in message.text

    if is_reply_to_bot or is_mention:
        clean_text = message.text.replace(f"@{bot_info.username}", "").strip()
        if not clean_text:
            msg = await message.answer("Ну и чё ты меня тегнул? Я не люблю общаться.")
            await asyncio.sleep(15)
            await msg.delete()
            return

        try:
            await bot.send_chat_action(message.chat.id, action="typing")
            
            # Формируем чат с историей, чтобы задать характер
            chat = model.start_chat(history=[
                {"role": "user", "parts": "Веди себя как дерзкий модератор. Твоя инструкция: " + AI_SYSTEM_PROMPT},
                {"role": "model", "parts": "Понял, начальник. Буду жестким и кратким."}
            ])
            
            # Отправляем сообщение пользователя
            response = await chat.send_message_async(clean_text)
            
            # Отправляем ответ в телеграм
            await message.reply(response.text)
            
        except Exception as e:
            logging.error(f"Ошибка Gemini: {e}")
            msg = await message.reply("Пообщайся с кем-нибудь другим, по вопросам: yagraze & pan1q.")
            await asyncio.sleep(15)
            await msg.delete()
# ================= ЗАПУСК =================

async def main():
    print("Бот настроен карать.")
    asyncio.create_task(check_silence_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

























