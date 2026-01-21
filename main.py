import asyncio
import logging
import re
import os
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ChatMemberStatus
from aiogram.types import LinkPreviewOptions
from datetime import datetime, timedelta
from aiogram.filters import Command
from aiogram.filters import CommandObject
from aiogram.types import ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton
import google.generativeai as genai

# ================= НАСТРОЙКИ =================

BOT_TOKEN = "8400087235:AAFZubO4ijQnZCOjLZ8UulzcthDixzOqSt0"
GOOGLE_API_KEY = "AIzaSyAIYu6GbRS0HtYlgEPLKgm1QuU8PZ15Z2E"

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
    "Тапир? Это не животное, это диагноз твоему провайдеру. Врубай КВН, клоун.",
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
    "Это был Голд Ган. @username, увидимся через полчаса.",
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

# Слова для триггера стикера
REFUND_KEYWORDS = ["рефанд", "refund", "refound", "возврат средств", "вернуть деньги"]

VPN_PHRASES = ["Ты имел ввиду КВН? Измени сообщение, эти 3 буквы запрещены в чате."]

# Списки слов и доменов (Те же, что и были)
BAD_WORDS = ["лгбт", "цп", "казино", "цп", "child porn", "cp", "закладки", "мефедрон", 
    "шишки", "гашиш", "купить скорость" "чурка", "хач", "ниггер", "хохол", "кацап", 
    "москаль", "свинособак", "черномаз", "нигга", "nigga", "nigger", "hohol", 
    "магазин 24/7", "hydra", "kraken", "убейся", "выпей яду", "роскомнадзорнись", "мамку ебал", "Путин", "Зеленский", "война", "либераха", "гейропа", "кокс", "фашист"] 
BAN_WORDS = ["1win", "vavada", "заработок в интернете", "быстрый заработок", "легкий заработок", "заработок", "быстрая работа", 
    "арбитраж крипты", "мамкин инвестор", "оплата от", "оплата лс",
    "раскрутка счета", "аккаунт с голосами", "Требуется команда из 5 человек для интересного проекта на 2-4 часа. Оплата начинается от 8.000 руб. Пишите в личные сообщения для уточнения деталей."]
ALLOWED_DOMAINS = ["youtube.com", "youtu.be", "google.com", "yandex.ru", "github.com", "x.com", "reddit.com", "t.me"]

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

# ================= ХЕНДЛЕРЫ =================

@dp.message(Command("mute"))
async def admin_mute_command(message: types.Message, command: CommandObject):
    # 1. Удаляем сообщение админа через 5 секунд (запускаем задачу сразу)
    await asyncio.sleep(5)
        await msg.delete()

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
        msg = await message.answer("⚠️ Чтобы выдать мут, отправь команду <b>в ответ</b> на сообщение нарушителя.\nПример: <code>/mute 30</code>")
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
async def welcome_new_member(message: types.Message):
    for user in message.new_chat_members:
        msg = await message.answer(
    f"Глаза выше, Страж! @{user.username or user.first_name}, добро пожаловать в чат."
    f" Веди себя прилично, я всё вижу."

        )

@dp.message()
async def moderate_and_chat(message: types.Message):
    if not message.text or message.from_user.id == bot.id:
        return

    text_lower = message.text.lower()
    username = message.from_user.username or message.from_user.first_name
    chat_username = message.chat.username

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
    # Проверяем, есть ли слово "тапир" или "tapir" в тексте
    if "тапир" in text_lower or "tapir" in text_lower:
        # Выбираем случайную фразу
        tapir_msg = random.choice(TAPIR_PHRASES)
        # Отвечаем на сообщение (не удаляем сообщение пользователя, пусть все видят позор)
        await message.reply(tapir_msg)
        return # Прерываем, чтобы ИИ не отвечал следом

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
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())










