import asyncio
import logging
import re
import random
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.enums import ChatMemberStatus
from aiogram.types import LinkPreviewOptions
from aiogram.filters import CommandObject, Command
from aiogram.types import ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton, ReactionTypeEmoji
import google.generativeai as genai

# ================= НАСТРОЙКИ =================

BOT_TOKEN = "8400087235:AAFZubO4ijQnZCOjLZ8UulzcthDixzOqSt0"
GOOGLE_API_KEY = "AIzaSyAIYu6GbRS0HtYlgEPLKgm1QuU8PZ15Z2E"

BOT_GUIDE = "https://telegra.ph/Baraholka-Bot-01-22"
LINK_TAPIR_GUIDE = "https://t.me/destinygoods/9814" 

# Глобальные переменные (RAM)
ACTIVE_DUELS = {}
PENDING_VERIFICATION = {}
PROCESSED_ALBUMS = []
LAST_MESSAGE_TIME = datetime.now()

# --- ID АДМИНСКОГО ЧАТА (Группы, куда кидать репорты) ---
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
    "арбитраж крипты", "мамкин инвестор", "Лучший заработок с доходом",
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

# ================= ИНИЦИАЛИЗАЦИЯ =================

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

# ================= ФУНКЦИИ =================

async def delete_later(message: types.Message, delay: int):
    """Ждет delay секунд и удаляет сообщение"""
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass

async def check_silence_loop():
    """Фоновая задача: проверяет тишину в чате"""
    global LAST_MESSAGE_TIME
    while True:
        await asyncio.sleep(300) 
        
        if (datetime.now() - LAST_MESSAGE_TIME).total_seconds() > 3600:
            fact = random.choice(LORE_FACTS)
            
            try:
                TARGET_CHAT_ID = CHAT_ID 
                await bot.send_message(TARGET_CHAT_ID, f"📢 <b>Минутка Лора:</b>\n{fact}")
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
        print(f"Ошибка верификации: {e}")
    finally:
        if user_id in PENDING_VERIFICATION:
            del PENDING_VERIFICATION[user_id]

# ================= ХЕНДЛЕРЫ =================

# --- КОМАНДА /HELP ---
@dp.message(Command("help"))
async def help_command(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔧 Гайд по боту", url=BOT_GUIDE)]
    ])
    msg = await message.answer(
        "Made by yagraze & pan1q.\nУзнать больше 👇👇",
        reply_markup=keyboard
    )
    asyncio.create_task(delete_later(msg, 15))
    asyncio.create_task(delete_later(message, 5))

# ==========================================
#        НОВАЯ СИСТЕМА ДУЭЛЕЙ (RPG)
# ==========================================

# --- 1. ВЫЗОВ НА ДУЭЛЬ ---
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

    # Кнопки принятия вызова
    buttons = [
        [
            InlineKeyboardButton(text="🔫 Принять вызов", callback_data=f"duel_start|{attacker.id}|{defender.id}"),
            InlineKeyboardButton(text="🏳️ Сбежать", callback_data=f"duel_decline|{attacker.id}|{defender.id}")
        ]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.answer(
        f"🔥 <b>ГОРНИЛО: ПРИВАТНЫЙ МАТЧ!</b>\n\n"
        f"🔴 <b>Претендент:</b> {att_name}\n"
        f"🔵 <b>Цель:</b> {def_name}\n\n"
        f"<i>Правила: 100 HP. Пошаговый бой. Проигравший вылетает из чата.</i>\n"
        f"🔥 <b>GG:</b> 12% шанс (Ваншот)\n"
        f"♠️ <b>Ace:</b> 50% шанс (-34 HP)\n"
        f"{def_name}, ты принимаешь бой?",
        reply_markup=keyboard
    )

# --- ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ ОБНОВЛЕНИЯ ЭКРАНА БОЯ ---
async def update_duel_message(callback: types.CallbackQuery, game_id):
    if game_id not in ACTIVE_DUELS:
        await callback.answer("Игра не найдена (бот перезагружен)", show_alert=True)
        try: await callback.message.delete()
        except: pass
        return

    game = ACTIVE_DUELS[game_id]
    
    def get_hp_bar(hp):
        blocks = int(hp / 10) 
        return "▓" * blocks + "░" * (10 - blocks)

    p1 = game["p1"]
    p2 = game["p2"]
    
    current_turn_name = p1["name"] if game["turn"] == p1["id"] else p2["name"]

    text = (
        f"⚔️ <b>ДУЭЛЬ: РАУНД ИДЕТ</b>\n\n"
        f"🔴 <b>{p1['name']}</b>: {p1['hp']} HP\n"
        f"[{get_hp_bar(p1['hp'])}]\n\n"
        f"🔵 <b>{p2['name']}</b>: {p2['hp']} HP\n"
        f"[{get_hp_bar(p2['hp'])}]\n\n"
        f"📜 <i>Лог: {game['log']}</i>\n\n"
        f"👉 <b>Сейчас ходит:</b> {current_turn_name}"
    )

    buttons = [
        [
            InlineKeyboardButton(text="🔥 GG (12% / Kill)", callback_data="duel_gg"),
            InlineKeyboardButton(text="♠️ Ace (50% / -34HP)", callback_data="duel_ace")
        ]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        pass

# --- 2. ЛОГИКА БОЯ (ОБРАБОТЧИК КНОПОК) ---
@dp.callback_query(F.data.startswith("duel_"))
async def duel_handler(callback: types.CallbackQuery):
    data_parts = callback.data.split("|")
    action = data_parts[0]
    
    # --- ОТКАЗ ОТ ДУЭЛИ ---
    if action == "duel_decline":
        defender_id = int(data_parts[2])
        if callback.from_user.id != defender_id:
            await callback.answer("Не лезь, это не твой бой!", show_alert=True)
            return
            
        msg = await callback.message.edit_text(f"🏳️ Дуэль отменена. Соперник улетел на орбиту.")
        asyncio.create_task(delete_later(msg, 30))
        return

    # --- НАЧАЛО БОЯ ---
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
            att_name, def_name = "Страж №1", "Страж №2"

        # Кто ходит первым? (Рандом)
        current_turn = random.choice([attacker_id, defender_id])

        ACTIVE_DUELS[game_id] = {
            "p1": {"id": attacker_id, "name": att_name, "hp": 100},
            "p2": {"id": defender_id, "name": def_name, "hp": 100},
            "turn": current_turn,
            "log": "🗣 Шакс: Матч начался! Покажите, на что вы способны!"
        }

        await update_duel_message(callback, game_id)
        await callback.answer() # ОБЯЗАТЕЛЬНО!
        return

    # --- ВЫСТРЕЛ (ХОД ИГРОКА) ---
    if action in ["duel_gg", "duel_ace"]:
        game_id = callback.message.message_id
        
        # Если игра не найдена
        if game_id not in ACTIVE_DUELS:
            msg = await callback.answer("Матч не найден (Бот был перезагружен).", show_alert=True)
            try: await callback.message.delete()
            except: pass
            return

        game = ACTIVE_DUELS[game_id]
        shooter_id = callback.from_user.id

        # Проверка: чей ход?
        if shooter_id != game["turn"]:
            await callback.answer("Сейчас не твой ход!", show_alert=True)
            return

        # Определяем, кто стрелок, кто жертва
        if shooter_id == game["p1"]["id"]:
            shooter = game["p1"]
            target = game["p2"]
        else:
            shooter = game["p2"]
            target = game["p1"]

        # Логика оружия
        damage = 0
        hit = False
        weapon_name = ""

        if action == "duel_gg":
            weapon_name = "🔥 Голден Ган"
            if random.randint(1, 100) <= 12: # 12%
                hit = True
                damage = 100
        elif action == "duel_ace":
            weapon_name = "♠️ Пиковый Туз"
            if random.randint(1, 100) <= 50: # 50%
                hit = True
                damage = 34

        # Обработка попадания
        if hit:
            target["hp"] -= damage
            if target["hp"] < 0: target["hp"] = 0
            log_msg = f"💥 <b>Попадание!</b> {shooter['name']} использует {weapon_name} и сносит {damage} HP!"
        else:
            log_msg = f"💨 <b>Промах!</b> {shooter['name']} промазал с {weapon_name}."

        # Проверка на победу
        if target["hp"] <= 0:
            del ACTIVE_DUELS[game_id]
            
            await callback.message.edit_text(
                f"🏆 <b>МАТЧ ЗАВЕРШЕН!</b>\n\n"
                f"{log_msg}\n\n"
                f"💀 {target['name']} повержен и отправляется на орбиту (Kicked).",
                reply_markup=None
            )
            
            # Кик проигравшего
            try:
                loser_status = await bot.get_chat_member(callback.message.chat.id, target['id'])
                if loser_status.status in ["administrator", "creator"]:
                    msg = await callback.message.answer(f"{target['name']} проиграл, но Админов кикать нельзя.")
                    asyncio.create_task(delete_later(msg, 15))
                else:
                    await bot.ban_chat_member(callback.message.chat.id, target['id'])
                    await bot.unban_chat_member(callback.message.chat.id, target['id'])
            except Exception as e:
                print(f"Ошибка кика: {e}")
            
            await callback.answer() # ОБЯЗАТЕЛЬНО!
            return

        # Если никто не умер — следующий ход
        game["turn"] = target["id"]
        game["log"] = log_msg
        
        await update_duel_message(callback, game_id)
        await callback.answer() # ОБЯЗАТЕЛЬНО!

# --- 2. РЕПОРТ (С ПРАВИЛЬНОЙ ССЫЛКОЙ ДЛЯ ЧАСТНЫХ ЧАТОВ) ---
@dp.message(Command("report"))
async def report_command(message: types.Message):

    if not message.reply_to_message:
        msg = await message.reply("⚠️ Используй команду в ответ на сообщение нарушителя.")
        asyncio.create_task(delete_later(msg, 5))
        return

    reported_msg = message.reply_to_message
    reporter = message.from_user.username or message.from_user.first_name
    violator = reported_msg.from_user.username or reported_msg.from_user.first_name

    # --- ГЕНЕРАЦИЯ ССЫЛКИ ---
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
        print(f"Ошибка репорта: {e}")
        
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

    except Exception as e:
        msg = await message.answer(f"Ошибка протокола: {e}")
        asyncio.create_task(delete_later(msg, 10))

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

    except Exception as e:
        print(f"Ошибка размута: {e}")
        msg = await message.answer("Не удалось снять мут. Возможно, я не админ?")
        asyncio.create_task(delete_later(msg, 10))

# 1. Бан-рулетка (Мут)
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
            await message.reply("Хотел выдать мут, но не хватает прав админа! Проверь настройки.")
            print(f"Ошибка мута: {e}")

    else:
        text = random.choice(SAFE_PHRASES)
        msg = await message.reply(f"{text}")
        asyncio.create_task(delete_later(msg, 20))

PROCESSED_ALBUMS = []
@dp.message(F.is_automatic_forward)
async def auto_comment_channel_post(message: types.Message):
    if message.media_group_id:
        if message.media_group_id in PROCESSED_ALBUMS:
            return
        PROCESSED_ALBUMS.append(message.media_group_id)
        if len(PROCESSED_ALBUMS) > 100:
            PROCESSED_ALBUMS.pop(0)
    try:
        await asyncio.sleep(1)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📜 Правила", url=LINK_RULES),
                InlineKeyboardButton(text="💬 Чат", url=LINK_CHAT)
            ]
        ])
        await message.reply(f"Оскорбления, реклама, спам, размещение ссылок, размещение недостоверной информации, выяснения отношений — Предупреждение/Мут.\nПовторное несоблюдение правил - БАН.\n\nПо вопросам рекламы/покупки: @llRGaming.\nПо вопросам касательно бота: @yaGraze.", reply_markup=keyboard)
        print(f"Оставил комментарий к посту: {message.message_id}")
    except Exception as e:
        print(f"Не удалось оставить комментарий: {e}")

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

    if user_id in PENDING_VERIFICATION:
        task = PENDING_VERIFICATION.pop(user_id)
        task.cancel()
        
        username = message.from_user.username or message.from_user.first_name
        success_msg = await message.reply(
            f"Сканирование Света завершено. Допуск получен, Страж @{username}. Веди себя прилично, я всё вижу."
        )
        asyncio.create_task(delete_later(success_msg, 15))
    
    if message.from_user.username and message.from_user.username.lower() == "galreiz":
        if random.randint(1, 3) == 1:
            try:
                await message.react([ReactionTypeEmoji(emoji="🤡")])
            except:
                pass 
    
    for word in BAN_WORDS:
        if word in text_lower:
            try:
                await message.delete()
                await message.chat.ban(message.from_user.id)
                msg = await message.answer(f"@{username} улетел в бан. Воздух стал чище.")
                asyncio.create_task(delete_later(msg, 15))
                return
            except: pass

    for word in BAD_WORDS:
        if word in text_lower:
            try:
                await message.delete()
                msg = await message.answer(f"@{username}, рот с мылом помой, у тебя скверна изо рта лезет.")
                asyncio.create_task(delete_later(msg, 15))
                return
            except: pass

    if not is_link_allowed(message.text, chat_username):
        try:
            await message.delete()
            msg = await message.answer(f"@{username}, ссылки на чужие помойки запрещены. Не засоряй сеть Вексов.")
            asyncio.create_task(delete_later(msg, 15))
            return
        except: pass

    if "vpn" in text_lower or "впн" in text_lower:
        vpn_msg = random.choice(VPN_PHRASES)
        await message.reply(vpn_msg)
        return

    if "тапир" in text_lower or "tapir" in text_lower:
        tapir_msg = random.choice(TAPIR_PHRASES)
        tapir_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔧 Гайд: обход тапира", url=LINK_TAPIR_GUIDE)]
        ])
        await message.reply(tapir_msg, reply_markup=tapir_kb)
        return 
        
    if message.reply_to_message and "клоун" in text_lower:
        try:
            await message.reply_to_message.react([ReactionTypeEmoji(emoji="🤡")])
        except Exception as e:
            print(f"Не удалось поставить реакцию: {e}")

    if message.reply_to_message and "держи в курсе" in text_lower:
        try:
            await message.reply_to_message.reply_sticker(sticker=KEEP_POSTED_STICKER_ID)
        except Exception:
            pass
    
    is_refund = any(word in text_lower for word in REFUND_KEYWORDS)
    if is_refund:
        try:
            await message.reply_sticker(sticker="CAACAgIAAxkBAAMWaW-qYjAAAYfnq0GFJwER5Mh-AAG7ywAC1YMAApJ_SEvZaHqj_zTQLzgE")
        except Exception as e:
            await message.reply(f"⚠️ Не могу отправить стикер. Ошибка:\n{e}")
        return

    bot_info = await bot.get_me()
    is_reply_to_bot = message.reply_to_message and message.reply_to_message.from_user.id == bot.id
    is_mention = f"@{bot_info.username}" in message.text

    if is_reply_to_bot or is_mention:
        clean_text = message.text.replace(f"@{bot_info.username}", "").strip()
        if not clean_text:
            msg = await message.answer("Ну и чё ты меня тегнул? Я не люблю общаться.")
            asyncio.create_task(delete_later(msg, 15))
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
            error_kb = InlineKeyboardMarkup(inline_keyboard=[
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
