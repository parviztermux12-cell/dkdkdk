import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import telebot
from telebot import types

# Конфигурация
TOKEN = '8022987920:AAHtlsRsOuYPDL0ez9oaTys0kd7SBZbvIJc'
ADMIN_ID = 7526512670
ADMIN_USERNAME = '@parvizwp'
GAME_BOT_LINK = 'https://t.me/meow_gamechat_bot'
CHAT_LINK = 'https://t.me/meowchatgame'
CHANNEL_LINK = 'https://t.me/meow_newsbot'

# Инициализация бота
bot = telebot.TeleBot(TOKEN)

# Структуры данных
class TeaUser:
    def __init__(self, user_id: int, username: str, first_name: str):
        self.user_id = user_id
        self.username = username
        self.first_name = first_name
        self.tea_count = 0
        self.last_tea_time = None
        self.blocked = False
        self.block_reason = ""
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'username': self.username,
            'first_name': self.first_name,
            'tea_count': self.tea_count,
            'last_tea_time': self.last_tea_time,
            'blocked': self.blocked,
            'block_reason': self.block_reason
        }
    
    @classmethod
    def from_dict(cls, data):
        user = cls(data['user_id'], data['username'], data['first_name'])
        user.tea_count = data['tea_count']
        user.last_tea_time = data['last_tea_time']
        user.blocked = data.get('blocked', False)
        user.block_reason = data.get('block_reason', "")
        return user

class Database:
    def __init__(self):
        self.users: Dict[int, TeaUser] = {}
        self.chats = set()
        self.broadcast_message = None
        self.broadcast_in_progress = False
        self.load_data()
    
    def load_data(self):
        try:
            with open('tea_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Загрузка пользователей
            for user_data in data.get('users', []):
                user = TeaUser.from_dict(user_data)
                self.users[user.user_id] = user
            
            # Загрузка чатов
            self.chats = set(data.get('chats', []))
            
            # Загрузка рассылки
            self.broadcast_message = data.get('broadcast_message')
            self.broadcast_in_progress = data.get('broadcast_in_progress', False)
            
        except FileNotFoundError:
            self.save_data()
    
    def save_data(self):
        data = {
            'users': [user.to_dict() for user in self.users.values()],
            'chats': list(self.chats),
            'broadcast_message': self.broadcast_message,
            'broadcast_in_progress': self.broadcast_in_progress
        }
        
        with open('tea_data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_or_create_user(self, user_id: int, username: str, first_name: str) -> TeaUser:
        if user_id not in self.users:
            self.users[user_id] = TeaUser(user_id, username, first_name)
            self.save_data()
        return self.users[user_id]
    
    def add_chat(self, chat_id: int):
        if chat_id not in self.chats:
            self.chats.add(chat_id)
            self.save_data()
    
    def get_top_users(self, limit: int = 20) -> List[TeaUser]:
        sorted_users = sorted(self.users.values(), 
                            key=lambda u: u.tea_count, 
                            reverse=True)
        return sorted_users[:limit]
    
    def get_top_chat_users(self, chat_users: List[int], limit: int = 20) -> List[TeaUser]:
        chat_user_objects = [self.users.get(user_id) for user_id in chat_users 
                           if user_id in self.users]
        chat_user_objects = [u for u in chat_user_objects if u is not None]
        sorted_users = sorted(chat_user_objects, 
                            key=lambda u: u.tea_count, 
                            reverse=True)
        return sorted_users[:limit]

# Инициализация базы данных
db = Database()

# Вспомогательные функции
def get_user_mention(user_id: int, username: str, first_name: str) -> str:
    if username:
        return f'<a href="https://t.me/{username}">{first_name}</a>'
    return f'<a href="tg://user?id={user_id}">{first_name}</a>'

def format_time_remaining(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    if hours > 0:
        return f"{hours}ч {minutes}м"
    elif minutes > 0:
        return f"{minutes}м {seconds}с"
    else:
        return f"{seconds}с"

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

def get_chat_users(chat_id: int) -> List[int]:
    try:
        chat_members = []
        # Получаем информацию о чате
        chat = bot.get_chat(chat_id)
        
        # Получаем администраторов чата
        admins = bot.get_chat_administrators(chat_id)
        
        # Добавляем всех администраторов
        for admin in admins:
            if admin.user.id not in chat_members:
                chat_members.append(admin.user.id)
        
        # Это упрощенный подход. В реальности нужно использовать get_chat_member_count
        # и get_chat_member для получения всех пользователей
        return chat_members
        
    except Exception as e:
        print(f"Error getting chat users: {e}")
        return []

# Обработчики команд
@bot.message_handler(commands=['start'])
def handle_start(message):
    db.add_chat(message.chat.id)
    
    user = db.get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )
    
    if user.blocked:
        send_blocked_message(message, user)
        return
    
    mention = get_user_mention(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )
    
    text = f"{mention}, Привет, это развлекательный чат - бот для ваших групп, где можно пить чай, так же у нас есть другой игровой чат бот «<a href=\"{GAME_BOT_LINK}\">тык</a>» - нажми чтобы поиграть в нашего второго бота🍵"
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("🗨️ Наш чат", url=CHAT_LINK)
    btn2 = types.InlineKeyboardButton("📢 Наш канал", url=CHANNEL_LINK)
    btn3 = types.InlineKeyboardButton("🍵Команды бота", callback_data="commands_list")
    keyboard.add(btn1, btn2)
    keyboard.add(btn3)
    
    bot.send_message(
        message.chat.id,
        text,
        parse_mode='HTML',
        disable_web_page_preview=True,
        reply_markup=keyboard
    )

@bot.message_handler(commands=['help'])
def handle_help(message):
    db.add_chat(message.chat.id)
    
    user = db.get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )
    
    if user.blocked:
        send_blocked_message(message, user)
        return
    
    help_text = """
<code>/start</code> - Запустить бота
<code>/tea</code> - Выпить чашку чая
<code>/my_tea</code> - Моя статистика
<code>/top_tea</code> - Топ 20
<code>/help</code> - Помощь по командам

<b>РП команды (только ответом на сообщения):</b>
"попить чай" - Выпить чай вместе
"налить чай" - Налить чай другому
"украсть чай" - Украсть чей-то чай
"""
    
    bot.send_message(
        message.chat.id,
        help_text,
        parse_mode='HTML'
    )

# ================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==================

def get_user_mention(user_id: int, username: str, first_name: str) -> str:
    return f"@{username}" if username else first_name


def format_time_remaining(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}ч {m}м"
    if m > 0:
        return f"{m}м {s}с"
    return f"{s}с"


# ================== DATABASE FIX ==================

class Database(Database):

    def get_top_users(self, limit: int = 20):
        users = [u for u in self.users.values() if u.tea_count > 0]
        users.sort(key=lambda u: u.tea_count, reverse=True)
        return users[:limit]

    def get_top_chat_users(self, chat_id: int, limit: int = 20):
        users = [
            u for u in self.users.values()
            if u.tea_count > 0 and chat_id in getattr(u, "chats", set())
        ]
        users.sort(key=lambda u: u.tea_count, reverse=True)
        return users[:limit]


# ================== ДОБАВЛЯЕМ УЧЁТ ЧАТОВ У ЮЗЕРА ==================

class TeaUser(TeaUser):
    def __init__(self, user_id, username, first_name):
        super().__init__(user_id, username, first_name)
        self.chats = set()

    def to_dict(self):
        data = super().to_dict()
        data["chats"] = list(self.chats)
        return data

    @classmethod
    def from_dict(cls, data):
        user = cls(data["user_id"], data["username"], data["first_name"])
        user.tea_count = data["tea_count"]
        user.last_tea_time = data["last_tea_time"]
        user.blocked = data.get("blocked", False)
        user.block_reason = data.get("block_reason", "")
        user.chats = set(data.get("chats", []))
        return user


@bot.message_handler(commands=['tea'])
def handle_tea(message):
    db.add_chat(message.chat.id)

    user = db.get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )

    # 🔧 фикс для старых пользователей
    if not hasattr(user, "chats"):
        user.chats = set()

    user.chats.add(message.chat.id)

    if user.blocked:
        send_blocked_message(message, user)
        return

    now = time.time()

    if user.last_tea_time and now - user.last_tea_time < 3600:
        left = int(3600 - (now - user.last_tea_time))
        text = (
            f"⏳ {get_user_mention(user.user_id, user.username, user.first_name)}\n"
            f"☕ Чай можно пить раз в час\n"
            f"🕒 Осталось: {format_time_remaining(left)}"
        )
        bot.send_message(message.chat.id, text)
        return

    user.tea_count += 1
    user.last_tea_time = now
    db.save_data()

    text = (
        f"🍵 {get_user_mention(user.user_id, user.username, user.first_name)}\n"
        f"➕ +1 чашка чая\n"
        f"📊 Всего: {user.tea_count}"
    )
    bot.send_message(message.chat.id, text)


# ================== /my_tea ==================

@bot.message_handler(commands=['my_tea'])
def handle_my_tea(message):
    user = db.get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )

    text = (
        f"🍵 {get_user_mention(user.user_id, user.username, user.first_name)}\n"
        f"📊 Ты выпил чашек: {user.tea_count}"
    )
    bot.send_message(message.chat.id, text)


# ================== /top_tea ==================

@bot.message_handler(commands=['top_tea'])
def handle_top_tea(message):
    top = db.get_top_users(20)

    if not top:
        bot.send_message(message.chat.id, "😴 Пока никто не пил чай")
        return

    text = "🏆 ТОП 20 ПО ЧАЮ\n\n"
    for i, u in enumerate(top, 1):
        text += f"{i}. {get_user_mention(u.user_id, u.username, u.first_name)} — 🍵 {u.tea_count}\n"

    # Отправляем сообщение без кнопки
    bot.send_message(message.chat.id, text)

# ================== CALLBACK: TOP ЧАТА ==================

@bot.callback_query_handler(func=lambda c: c.data.startswith("chat_top:"))
def show_chat_top(call):
    chat_id = int(call.data.split(":")[1])
    top = db.get_top_chat_users(chat_id, 20)

    if not top:
        bot.answer_callback_query(call.id, "В этом чате ещё никто не пил чай ☕")
        return

    text = "🏠 ТОП ЧАТА\n\n"
    for i, u in enumerate(top, 1):
        text += f"{i}. {get_user_mention(u.user_id, u.username, u.first_name)} — 🍵 {u.tea_count}\n"

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(
        "🌍 Общий топ",
        callback_data="back_global_top"
    ))

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda c: c.data == "back_global_top")
def back_global_top(call):
    top = db.get_top_users(20)

    if not top:
        bot.answer_callback_query(call.id, "☕ Пока нет данных")
        return

    text = "🏆 ТОП 20 ПО ЧАЮ\n\n"
    for i, u in enumerate(top, 1):
        text += f"{i}. {get_user_mention(u.user_id, u.username, u.first_name)} — 🍵 {u.tea_count}\n"

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(
        "🏠 Топ этого чата",
        callback_data=f"chat_top:{call.message.chat.id}"
    ))

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )

    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data.startswith("chat_top:"))
def show_chat_top(call):
    chat_id = int(call.data.split(":")[1])
    top = db.get_top_chat_users(chat_id, 20)

    if not top:
        bot.answer_callback_query(call.id, "☕ В этом чате ещё никто не пил чай")
        return

    text = "🏠 ТОП ЭТОГО ЧАТА\n\n"
    for i, u in enumerate(top, 1):
        text += f"{i}. {get_user_mention(u.user_id, u.username, u.first_name)} — 🍵 {u.tea_count}\n"

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton(
        "⬅️ Назад",
        callback_data="back_global_top"
    ))

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )

    bot.answer_callback_query(call.id)

# ================== ОБРАБОТКА ТЕКСТА И РП КОМАНД ==================

@bot.message_handler(func=lambda message: True)
def handle_text_messages(message):
    db.add_chat(message.chat.id)

    user = db.get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )

    if user.blocked:
        send_blocked_message(message, user)
        return

    if not message.text:
        return

    text = message.text.lower().strip()

    # Админ-команды
    if text.startswith("заблокировать"):
        handle_block_command(message)
        return

    if text.startswith("разблокировать"):
        handle_unblock_command(message)
        return

    # РП команды — только ответом
    if message.reply_to_message:
        handle_rp_command(message)


def handle_rp_command(message):
    text = message.text.lower().strip()

    sender = db.get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )

    if sender.blocked:
        return

    receiver_user = message.reply_to_message.from_user
    receiver = db.get_or_create_user(
        receiver_user.id,
        receiver_user.username,
        receiver_user.first_name
    )

    if receiver.blocked:
        return

    sender_mention = get_user_mention(
        sender.user_id,
        sender.username,
        sender.first_name
    )

    receiver_mention = get_user_mention(
        receiver.user_id,
        receiver.username,
        receiver.first_name
    )

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🍵 Наш чат", url=CHAT_LINK))

    if text == "попить чай":
        response = (
            f"🍵 {sender_mention} и {receiver_mention}\n"
            f"☕ Мирно попили чай вместе"
        )
        bot.send_message(message.chat.id, response, reply_markup=keyboard)

    elif text == "налить чай":
        response = (
            f"🫖 {sender_mention}\n"
            f"➡️ Налил горячий чай для {receiver_mention}"
        )
        bot.send_message(message.chat.id, response, reply_markup=keyboard)

    elif text == "украсть чай":
        response = (
            f"😈 {sender_mention}\n"
            f"🥃 Подло украл чай у {receiver_mention}"
        )
        bot.send_message(message.chat.id, response, reply_markup=keyboard)


# ================== БЛОКИРОВКА ==================

def handle_block_command(message):
    if not is_admin(message.from_user.id):
        return

    args = message.text.split()
    reason = ""
    target_id = None

    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        reason = " ".join(args[1:])

    else:
        try:
            target_id = int(args[1])
            reason = " ".join(args[2:])
        except:
            return

    if target_id not in db.users:
        try:
            info = bot.get_chat(target_id)
            db.get_or_create_user(target_id, info.username, info.first_name)
        except:
            bot.send_message(message.chat.id, "❌ Пользователь не найден")
            return

    user = db.users[target_id]
    user.blocked = True
    user.block_reason = reason
    db.save_data()

    admin_mention = get_user_mention(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )

    user_mention = get_user_mention(
        user.user_id,
        user.username,
        user.first_name
    )

    bot.send_message(
        message.chat.id,
        f"🚫 {admin_mention}\n"
        f"Пользователь {user_mention} заблокирован\n"
        f"📄 Причина: {reason or 'не указана'}"
    )


# ================== РАЗБЛОКИРОВКА ==================

def handle_unblock_command(message):
    if not is_admin(message.from_user.id):
        return

    args = message.text.split()
    target_id = None

    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
    else:
        try:
            target_id = int(args[1])
        except:
            return

    if target_id not in db.users:
        return

    user = db.users[target_id]
    user.blocked = False
    user.block_reason = ""
    db.save_data()

    admin_mention = get_user_mention(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )

    user_mention = get_user_mention(
        user.user_id,
        user.username,
        user.first_name
    )

    bot.send_message(
        message.chat.id,
        f"✅ {admin_mention}\n"
        f"Пользователь {user_mention} разблокирован"
    )

# Админские команды
@bot.message_handler(commands=['admin'])
def handle_admin(message):
    if not is_admin(message.from_user.id):
        return
    
    total_users = len(db.users)
    total_groups = len(db.chats)
    
    text = f"""<b>Меню admin's</b>
• Всего пользователей - {total_users}
• Всего групп где находится бот - {total_groups}"""
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(
        "Рассылка", 
        callback_data="broadcast"
    ))
    
    bot.send_message(
        message.chat.id,
        text,
        parse_mode='HTML',
        reply_markup=keyboard
    )

# Обработка команды блокировки
def handle_block_command(message):
    if not is_admin(message.from_user.id):
        return
    
    args = message.text.split()
    
    if len(args) < 2:
        return
    
    target_id = None
    reason = ""
    
    # Проверяем если команда отправлена ответом на сообщение
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
        reason = ' '.join(args[1:])
    else:
        # Пытаемся получить ID из текста
        try:
            target_id = int(args[1])
            reason = ' '.join(args[2:]) if len(args) > 2 else ""
        except ValueError:
            return
    
    if target_id:
        if target_id in db.users:
            user = db.users[target_id]
            user.blocked = True
            user.block_reason = reason
            db.save_data()
            
            admin_mention = get_user_mention(
                message.from_user.id,
                message.from_user.username,
                message.from_user.first_name
            )
            
            user_mention = get_user_mention(
                user.user_id,
                user.username,
                user.first_name
            )
            
            response = f"{admin_mention}, вы заблокировали пользователя {user_mention} по причине: {reason}"
            bot.send_message(message.chat.id, response, parse_mode='HTML')

# Обработка команды разблокировки
def handle_unblock_command(message):
    if not is_admin(message.from_user.id):
        return
    
    args = message.text.split()
    
    if len(args) < 2:
        return
    
    target_id = None
    
    # Проверяем если команда отправлена ответом на сообщение
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
    else:
        # Пытаемся получить ID из текста
        try:
            target_id = int(args[1])
        except ValueError:
            return
    
    if target_id and target_id in db.users:
        user = db.users[target_id]
        user.blocked = False
        user.block_reason = ""
        db.save_data()
        
        admin_mention = get_user_mention(
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name
        )
        
        user_mention = get_user_mention(
            user.user_id,
            user.username,
            user.first_name
        )
        
        response = f"{admin_mention}, вы разблокировали пользователя {user_mention}"
        bot.send_message(message.chat.id, response, parse_mode='HTML')

# Функция для отправки сообщения заблокированному пользователю
def send_blocked_message(message, user):
    mention = get_user_mention(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )
    
    text = f"❗{mention}, вы были заблокированы администратором по причине: {user.block_reason}. Обратитесь к администратору в личные сообщения чтобы снять бан."
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(
        "🍵 Написать", 
        url=f"https://t.me/{ADMIN_USERNAME.replace('@', '')}"
    ))
    
    bot.send_message(
        message.chat.id,
        text,
        parse_mode='HTML',
        reply_markup=keyboard
    )

# Обработка callback-запросов
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user = db.get_or_create_user(
        call.from_user.id,
        call.from_user.username,
        call.from_user.first_name
    )
    
    if user.blocked:
        bot.answer_callback_query(call.id, "Вы заблокированы!")
        return
    
    if call.data == "commands_list":
        show_commands_list(call)
    elif call.data == "back_to_start":
        back_to_start(call)
    elif call.data.startswith("chat_top:"):
        show_chat_top(call)
    elif call.data == "back_to_global_top":
        back_to_global_top(call)
    elif call.data == "broadcast":
        start_broadcast(call)
    elif call.data == "start_broadcast":
        confirm_broadcast(call)
    elif call.data == "cancel_broadcast":
        cancel_broadcast(call)

def show_commands_list(call):
    commands_text = """
<b>🍵 Команды бота:</b>

<code>/start</code> - Запустить бота
<code>/tea</code> - Выпить чашку чая (1 раз в час)
<code>/my_tea</code> - Посмотреть свою статистику
<code>/top_tea</code> - Посмотреть топ 20 пользователей
<code>/help</code> - Помощь по командам

<b>РП команды (только ответом на сообщение):</b>
"попить чай" - Выпить чай вместе с другим пользователем
"налить чай" - Налить чай другому пользователю
"украсть чай" - Украсть чей-то любимый чай
"""
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(
        "Назад", 
        callback_data="back_to_start"
    ))
    
    bot.edit_message_text(
        commands_text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=keyboard
    )

def back_to_start(call):
    mention = get_user_mention(
        call.from_user.id,
        call.from_user.username,
        call.from_user.first_name
    )
    
    text = f"{mention}, Привет, это развлекательный чат - бот для ваших групп, где можно пить чай, так же у нас есть другой игровой чат бот «<a href=\"{GAME_BOT_LINK}\">тык</a>» - нажми чтобы поиграть в нашего второго бота🍵"
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("🗨️ Наш чат", url=CHAT_LINK)
    btn2 = types.InlineKeyboardButton("📢 Наш канал", url=CHANNEL_LINK)
    btn3 = types.InlineKeyboardButton("🍵Команды бота", callback_data="commands_list")
    keyboard.add(btn1, btn2)
    keyboard.add(btn3)
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        disable_web_page_preview=True,
        reply_markup=keyboard
    )

def show_chat_top(call):
    chat_id = int(call.data.split(":")[1])
    chat_users = get_chat_users(chat_id)
    top_users = db.get_top_chat_users(chat_users, 20)
    
    text = "<b>🏆 Топ чата:</b>\n\n"
    for i, top_user in enumerate(top_users, 1):
        mention = get_user_mention(
            top_user.user_id,
            top_user.username,
            top_user.first_name
        )
        text += f"{i}. {mention} - 🧉выпито чашек ({top_user.tea_count})\n"
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(
        "Назад", 
        callback_data="back_to_global_top"
    ))
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=keyboard
    )

def back_to_global_top(call):
    top_users = db.get_top_users(20)
    
    text = "<b>🏆 Топ 20:</b>\n\n"
    for i, top_user in enumerate(top_users, 1):
        mention = get_user_mention(
            top_user.user_id,
            top_user.username,
            top_user.first_name
        )
        text += f"{i}. {mention} - 🧉выпито чашек ({top_user.tea_count})\n"
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(
        "Топ чата", 
        callback_data=f"chat_top:{call.message.chat.id}"
    ))
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=keyboard
    )

def start_broadcast(call):
    text = "Киньте текст для рассылки"
    bot.send_message(call.message.chat.id, text)
    
    # Регистрируем следующий хендлер для получения текста рассылки
    @bot.message_handler(func=lambda m: m.chat.id == call.message.chat.id and m.from_user.id == ADMIN_ID)
    def receive_broadcast_text(message):
        db.broadcast_message = message.text
        db.save_data()
        
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            types.InlineKeyboardButton("Начать", callback_data="start_broadcast"),
            types.InlineKeyboardButton("Отмена", callback_data="cancel_broadcast")
        )
        
        preview_text = f"<b>Текст рассылки:</b>\n\n{message.text}"
        bot.send_message(
            message.chat.id,
            preview_text,
            parse_mode='HTML',
            reply_markup=keyboard
        )
        
        # Удаляем хендлер после использования
        bot.message_handler(func=lambda m: False)(receive_broadcast_text)

def confirm_broadcast(call):
    if not db.broadcast_message:
        bot.answer_callback_query(call.id, "Нет текста для рассылки!")
        return
    
    db.broadcast_in_progress = True
    db.save_data()
    
    bot.edit_message_text(
        "Рассылка начата!",
        call.message.chat.id,
        call.message.message_id
    )
    
    # Отправляем рассылку
    sent = 0
    failed = 0
    
    for chat_id in db.chats:
        try:
            bot.send_message(chat_id, db.broadcast_message, parse_mode='HTML')
            sent += 1
        except Exception as e:
            failed += 1
            print(f"Failed to send to {chat_id}: {e}")
    
    db.broadcast_in_progress = False
    db.broadcast_message = None
    db.save_data()
    
    bot.send_message(
        call.message.chat.id,
        f"Рассылка завершена!\nОтправлено: {sent}\nНе удалось отправить: {failed}"
    )

def cancel_broadcast(call):
    db.broadcast_message = None
    db.broadcast_in_progress = False
    db.save_data()
    
    bot.edit_message_text(
        "Рассылка отменена",
        call.message.chat.id,
        call.message.message_id
    )

# Запуск бота
if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling()