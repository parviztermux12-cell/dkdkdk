import json
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple  # Добавлен Tuple
import telebot
from telebot import types

# Конфигурация
TOKEN = '8022987920:AAHtlsRsOuYPDL0ez9oaTys0kd7SBZbvIJc'
ADMIN_ID = 7526512670
ADMIN_USERNAME = '@parvizwp'
GAME_BOT_LINK = 'https://t.me/meow_gamechat_bot'
CHAT_LINK = 'https://t.me/meowchatgame'
CHANNEL_LINK = 'https://t.me/meow_newsbot'

# Константы событий
EVENT_NORMAL = "normal"
EVENT_BONUS = "bonus"
EVENT_FAIL = "fail"

# Инициализация бота
bot = telebot.TeleBot(TOKEN)

# ================== BASE DATABASE (tea_data.json) ==================

class TeaUser:
    def __init__(self, user_id: int, username: str, first_name: str):
        self.user_id = user_id
        self.username = username
        self.first_name = first_name
        self.tea_count = 0
        self.last_tea_time = None
        self.blocked = False
        self.block_reason = ""
        self.chats = set()  # Добавлено для совместимости
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'username': self.username,
            'first_name': self.first_name,
            'tea_count': self.tea_count,
            'last_tea_time': self.last_tea_time,
            'blocked': self.blocked,
            'block_reason': self.block_reason,
            'chats': list(self.chats)  # Для совместимости
        }
    
    @classmethod
    def from_dict(cls, data):
        user = cls(data['user_id'], data['username'], data['first_name'])
        user.tea_count = data['tea_count']
        user.last_tea_time = data['last_tea_time']
        user.blocked = data.get('blocked', False)
        user.block_reason = data.get('block_reason', "")
        user.chats = set(data.get('chats', []))  # Для совместимости
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
                
            for user_data in data.get('users', []):
                user = TeaUser.from_dict(user_data)
                self.users[user.user_id] = user
            
            self.chats = set(data.get('chats', []))
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

# ================== EXTRA DATABASE (tea_extra.json) ==================

class UserStats:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.level = 1
        self.exp = 0
        self.streak = 0
        self.last_tea_date = None
        self.daily_count = 0
        self.weekly_count = 0
        self.last_daily_reset = None
        self.last_weekly_reset = None
        self.rewards_received = set()
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'level': self.level,
            'exp': self.exp,
            'streak': self.streak,
            'last_tea_date': self.last_tea_date,
            'daily_count': self.daily_count,
            'weekly_count': self.weekly_count,
            'last_daily_reset': self.last_daily_reset,
            'last_weekly_reset': self.last_weekly_reset,
            'rewards_received': list(self.rewards_received)
        }
    
    @classmethod
    def from_dict(cls, data):
        stats = cls(data['user_id'])
        stats.level = data.get('level', 1)
        stats.exp = data.get('exp', 0)
        stats.streak = data.get('streak', 0)
        stats.last_tea_date = data.get('last_tea_date')
        stats.daily_count = data.get('daily_count', 0)
        stats.weekly_count = data.get('weekly_count', 0)
        stats.last_daily_reset = data.get('last_daily_reset')
        stats.last_weekly_reset = data.get('last_weekly_reset')
        stats.rewards_received = set(data.get('rewards_received', []))
        return stats

class EventData:
    def __init__(self):
        self.tea_hour_active = False
        self.tea_hour_end = None
        self.tea_hour_multiplier = 2
    
    def to_dict(self):
        return {
            'tea_hour_active': self.tea_hour_active,
            'tea_hour_end': self.tea_hour_end,
            'tea_hour_multiplier': self.tea_hour_multiplier
        }
    
    @classmethod
    def from_dict(cls, data):
        event = cls()
        event.tea_hour_active = data.get('tea_hour_active', False)
        event.tea_hour_end = data.get('tea_hour_end')
        event.tea_hour_multiplier = data.get('tea_hour_multiplier', 2)
        return event

class ExtraDatabase:
    def __init__(self):
        self.user_stats: Dict[int, UserStats] = {}
        self.event_data = EventData()
        self.daily_top = {}
        self.weekly_top = {}
        self.load_data()
    
    def load_data(self):
        try:
            with open('tea_extra.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for stats_data in data.get('user_stats', []):
                stats = UserStats.from_dict(stats_data)
                self.user_stats[stats.user_id] = stats
            
            self.event_data = EventData.from_dict(data.get('event_data', {}))
            self.daily_top = data.get('daily_top', {})
            self.weekly_top = data.get('weekly_top', {})
            
        except FileNotFoundError:
            self.save_data()
    
    def save_data(self):
        data = {
            'user_stats': [stats.to_dict() for stats in self.user_stats.values()],
            'event_data': self.event_data.to_dict(),
            'daily_top': self.daily_top,
            'weekly_top': self.weekly_top
        }
        
        with open('tea_extra.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_or_create_stats(self, user_id: int) -> UserStats:
        if user_id not in self.user_stats:
            self.user_stats[user_id] = UserStats(user_id)
            self.save_data()
        return self.user_stats[user_id]
    
    def update_daily_top(self, user_id: int, count: int):
        today = datetime.now().strftime('%Y-%m-%d')
        if today not in self.daily_top:
            self.daily_top[today] = {}
        self.daily_top[today][user_id] = count
        self.save_data()
    
    def update_weekly_top(self, user_id: int, count: int):
        year_week = datetime.now().strftime('%Y-%W')
        if year_week not in self.weekly_top:
            self.weekly_top[year_week] = {}
        self.weekly_top[year_week][user_id] = count
        self.save_data()
    
    def get_daily_top(self, date_str: str = None) -> Dict[int, int]:
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
        return self.daily_top.get(date_str, {})
    
    def get_weekly_top(self, week_str: str = None) -> Dict[int, int]:
        if week_str is None:
            week_str = datetime.now().strftime('%Y-%W')
        return self.weekly_top.get(week_str, {})

# ================== ИНИЦИАЛИЗАЦИЯ БАЗ ==================

db = Database()
extra_db = ExtraDatabase()

# ================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==================

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

def get_level(exp: int) -> Tuple[int, int, int]:
    # Уровень = корень из опыта
    level = int(exp ** 0.5) + 1
    current_level_exp = (level - 1) ** 2
    next_level_exp = level ** 2
    progress = exp - current_level_exp
    total_needed = next_level_exp - current_level_exp
    return level, progress, total_needed

def get_random_event() -> str:
    rand = random.random()
    if rand < 0.1:  # 10% шанс провала
        return EVENT_FAIL
    elif rand < 0.3:  # 20% шанс бонуса
        return EVENT_BONUS
    else:  # 70% шанс обычного
        return EVENT_NORMAL

def is_night_bonus_time() -> bool:
    now = datetime.now()
    hour = now.hour
    return 2 <= hour < 6

def check_and_give_rewards(user: TeaUser, stats: UserStats):
    rewards = []
    
    if user.tea_count >= 200 and '200' not in stats.rewards_received:
        rewards.append(('200 чаёв', '🏆'))
        stats.rewards_received.add('200')
    elif user.tea_count >= 100 and '100' not in stats.rewards_received:
        rewards.append(('100 чаёв', '🎖️'))
        stats.rewards_received.add('100')
    elif user.tea_count >= 50 and '50' not in stats.rewards_received:
        rewards.append(('50 чаёв', '⭐'))
        stats.rewards_received.add('50')
    
    extra_db.save_data()
    return rewards

def reset_daily_weekly_counts(stats: UserStats):
    now = datetime.now()
    today = now.strftime('%Y-%m-%d')
    
    if stats.last_daily_reset != today:
        stats.daily_count = 0
        stats.last_daily_reset = today
    
    year_week = now.strftime('%Y-%W')
    if stats.last_weekly_reset != year_week:
        stats.weekly_count = 0
        stats.last_weekly_reset = year_week

# ================== ОСНОВНЫЕ КОМАНДЫ ==================

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
    
    text = f"{mention}, Привет, это развлекательный чат-бот для ваших групп, где можно пить чай, так же у нас есть другой игровой чат-бот «<a href=\"{GAME_BOT_LINK}\">тык</a>» - нажми чтобы поиграть в нашего второго бота🍵"
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("🗨️ Наш чат", url=CHAT_LINK)
    btn2 = types.InlineKeyboardButton("📢 Наш канал", url=CHANNEL_LINK)
    btn3 = types.InlineKeyboardButton("🍵 Команды бота", callback_data="commands_list")
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
<code>/top_tea</code> - Топы
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

@bot.message_handler(commands=['tea'])
def handle_tea(message):
    db.add_chat(message.chat.id)
    
    user = db.get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )
    
    if user.blocked:
        send_blocked_message(message, user)
        return
    
    now = time.time()
    
    # Проверка кулдауна
    if user.last_tea_time and now - user.last_tea_time < 3600:
        left = int(3600 - (now - user.last_tea_time))
        text = (
            f"⏳ {user.first_name}\n"
            f"☕ Чай можно пить раз в час\n"
            f"🕒 Осталось: {format_time_remaining(left)}"
        )
        bot.reply_to(message, text)
        return
    
    # Получение статистики
    stats = extra_db.get_or_create_stats(user.user_id)
    reset_daily_weekly_counts(stats)
    
    # Определение событий и бонусов
    event = get_random_event()
    tea_to_add = 1
    exp_to_add = 1
    bonus_text = ""
    event_text = ""
    
    # Ночной бонус
    if is_night_bonus_time():
        tea_to_add = 2
        exp_to_add = 2
        bonus_text = "🌙 Ночной бонус x2!\n"
    
    # Чайный час
    if extra_db.event_data.tea_hour_active:
        multiplier = extra_db.event_data.tea_hour_multiplier
        tea_to_add *= multiplier
        exp_to_add *= multiplier
        bonus_text += f"🎉 Чайный час x{multiplier}!\n"
    
    # Случайные события
    if event == EVENT_BONUS:
        tea_to_add *= 2
        exp_to_add *= 2
        event_text = "🎰 Бонус x2!\n"
    elif event == EVENT_FAIL:
        tea_to_add = 0
        exp_to_add = 0
        event_text = "💥 Ой, чай пролился!\n"
    
    # Обновление серии
    today = datetime.now().date()
    last_tea_date = datetime.fromtimestamp(stats.last_tea_date).date() if stats.last_tea_date else None
    
    if last_tea_date:
        days_diff = (today - last_tea_date).days
        if days_diff == 1:
            stats.streak += 1
        elif days_diff > 1:
            stats.streak = 1
        else:
            stats.streak = max(stats.streak, 1)
    else:
        stats.streak = 1
    
    # Обновление данных
    user.tea_count += tea_to_add
    user.last_tea_time = now
    
    stats.exp += exp_to_add
    stats.last_tea_date = now
    stats.daily_count += tea_to_add
    stats.weekly_count += tea_to_add
    
    # Проверка награды
    rewards = check_and_give_rewards(user, stats)
    
    # Сохранение
    db.save_data()
    extra_db.save_data()
    
    # Обновление топов
    extra_db.update_daily_top(user.user_id, stats.daily_count)
    extra_db.update_weekly_top(user.user_id, stats.weekly_count)
    
    # Формирование ответа
    level, progress, total_needed = get_level(stats.exp)
    level_text = f"📊 Уровень: {level} ({progress}/{total_needed} опыта)\n"
    streak_text = f"🔥 Серия: {stats.streak} дней\n" if stats.streak > 1 else ""
    
    reward_text = ""
    if rewards:
        for reward_name, emoji in rewards:
            reward_text += f"{emoji} Получена награда: {reward_name}\n"
    
    text = (
        f"🍵 {user.first_name}\n"
        f"{bonus_text}{event_text}"
        f"{'➖ +0' if tea_to_add == 0 else f'➕ +{tea_to_add}'} чашка чая\n"
        f"📊 Всего: {user.tea_count}\n"
        f"{level_text}{streak_text}"
        f"📈 Сегодня: {stats.daily_count} | Неделя: {stats.weekly_count}\n"
        f"{reward_text}"
    ).strip()
    
    bot.reply_to(message, text)

@bot.message_handler(commands=['my_tea'])
def handle_my_tea(message):
    user = db.get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name
    )
    
    if user.blocked:
        send_blocked_message(message, user)
        return
    
    stats = extra_db.get_or_create_stats(user.user_id)
    reset_daily_weekly_counts(stats)
    
    level, progress, total_needed = get_level(stats.exp)
    
    text = (
        f"🍵 {user.first_name}\n"
        f"📊 Всего чашек: {user.tea_count}\n"
        f"🏆 Уровень: {level} ({progress}/{total_needed} опыта)\n"
        f"🔥 Серия: {stats.streak} дней\n"
        f"📅 Сегодня: {stats.daily_count} | Неделя: {stats.weekly_count}\n"
        f"🎁 Награды: {len(stats.rewards_received)}/3"
    )
    
    bot.reply_to(message, text)

@bot.message_handler(commands=['top_tea'])
def handle_top_tea(message):
    # Создаем инлайн-меню с тремя вариантами топов
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("🏆 Общий топ", callback_data="top_global"),
        types.InlineKeyboardButton("📅 Топ дня", callback_data="top_daily"),
        types.InlineKeyboardButton("📆 Топ недели", callback_data="top_weekly")
    )
    
    text = "Выберите тип топа:"
    bot.send_message(message.chat.id, text, reply_markup=keyboard)

# ================== ОБРАБОТКА CALLBACK-ЗАПРОСОВ ==================

@bot.callback_query_handler(func=lambda call: call.data.startswith('top_'))
def handle_top_callback(call):
    if call.data == "top_global":
        show_global_top(call)
    elif call.data == "top_daily":
        show_daily_top(call)
    elif call.data == "top_weekly":
        show_weekly_top(call)
    elif call.data == "back_to_top_menu":
        back_to_top_menu(call)

def show_global_top(call):
    top_users = db.get_top_users(20)
    
    if not top_users:
        text = "😴 Пока никто не пил чай"
    else:
        text = "🏆 ОБЩИЙ ТОП 20\n\n"
        for i, user in enumerate(top_users, 1):
            text += f"{i}. {get_user_mention(user.user_id, user.username, user.first_name)} — 🍵 {user.tea_count}\n"
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("📅 Топ дня", callback_data="top_daily"),
        types.InlineKeyboardButton("📆 Топ недели", callback_data="top_weekly"),
        types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_top_menu")
    )
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard
    )

def show_daily_top(call):
    daily_top = extra_db.get_daily_top()
    
    if not daily_top:
        text = "📅 Сегодня ещё никто не пил чай"
    else:
        # Сортируем по убыванию
        sorted_items = sorted(daily_top.items(), key=lambda x: x[1], reverse=True)[:20]
        
        text = "📅 ТОП ДНЯ\n\n"
        for i, (user_id, count) in enumerate(sorted_items, 1):
            user = db.users.get(user_id)
            if user:
                text += f"{i}. {get_user_mention(user.user_id, user.username, user.first_name)} — 🍵 {count}\n"
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("🏆 Общий топ", callback_data="top_global"),
        types.InlineKeyboardButton("📆 Топ недели", callback_data="top_weekly"),
        types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_top_menu")
    )
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard
    )

def show_weekly_top(call):
    weekly_top = extra_db.get_weekly_top()
    
    if not weekly_top:
        text = "📆 На этой неделе ещё никто не пил чай"
    else:
        # Сортируем по убыванию
        sorted_items = sorted(weekly_top.items(), key=lambda x: x[1], reverse=True)[:20]
        
        text = "📆 ТОП НЕДЕЛИ\n\n"
        for i, (user_id, count) in enumerate(sorted_items, 1):
            user = db.users.get(user_id)
            if user:
                text += f"{i}. {get_user_mention(user.user_id, user.username, user.first_name)} — 🍵 {count}\n"
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("🏆 Общий топ", callback_data="top_global"),
        types.InlineKeyboardButton("📅 Топ дня", callback_data="top_daily"),
        types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_top_menu")
    )
    
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard
    )

def back_to_top_menu(call):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("🏆 Общий топ", callback_data="top_global"),
        types.InlineKeyboardButton("📅 Топ дня", callback_data="top_daily"),
        types.InlineKeyboardButton("📆 Топ недели", callback_data="top_weekly")
    )
    
    text = "Выберите тип топа:"
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data == "commands_list")
def show_commands_list(call):
    commands_text = """
<b>🍵 Команды бота:</b>

<code>/start</code> - Запустить бота
<code>/tea</code> - Выпить чашку чая (1 раз в час)
<code>/my_tea</code> - Посмотреть свою статистику
<code>/top_tea</code> - Посмотреть топы
<code>/help</code> - Помощь по командам

<b>РП команды (только ответом на сообщение):</b>
"попить чай" - Выпить чай вместе с другим пользователем
"налить чай" - Налить чай другому пользователю
"украсть чай" - Украсть чей-то любимый чай
"""
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start"))
    
    bot.edit_message_text(
        commands_text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data == "back_to_start")
def back_to_start(call):
    mention = get_user_mention(
        call.from_user.id,
        call.from_user.username,
        call.from_user.first_name
    )
    
    text = f"{mention}, Привет, это развлекательный чат-бот для ваших групп, где можно пить чай, так же у нас есть другой игровой чат-бот «<a href=\"{GAME_BOT_LINK}\">тык</a>» - нажми чтобы поиграть в нашего второго бота🍵"
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("🗨️ Наш чат", url=CHAT_LINK)
    btn2 = types.InlineKeyboardButton("📢 Наш канал", url=CHANNEL_LINK)
    btn3 = types.InlineKeyboardButton("🍵 Команды бота", callback_data="commands_list")
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

# ================== АДМИНСКИЕ КОМАНДЫ ==================

@bot.message_handler(commands=['admin'])
def handle_admin(message):
    if not is_admin(message.from_user.id):
        return
    
    total_users = len(db.users)
    total_groups = len(db.chats)
    
    text = f"""<b>Меню admin's</b>
• Всего пользователей - {total_users}
• Всего групп где находится бот - {total_groups}
• Чайный час: {"АКТИВЕН" if extra_db.event_data.tea_hour_active else "не активен"}"""
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("Рассылка", callback_data="broadcast"),
        types.InlineKeyboardButton("Чайный час", callback_data="tea_hour_toggle")
    )
    
    bot.send_message(
        message.chat.id,
        text,
        parse_mode='HTML',
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data == "tea_hour_toggle")
def toggle_tea_hour(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "Только для админов!")
        return
    
    event_data = extra_db.event_data
    
    if event_data.tea_hour_active:
        event_data.tea_hour_active = False
        event_data.tea_hour_end = None
        text = "Чайный час завершён!"
    else:
        event_data.tea_hour_active = True
        event_data.tea_hour_end = time.time() + 3600  # 1 час
        text = "Чайный час активирован на 1 час! x2 бонус!"
    
    extra_db.save_data()
    bot.answer_callback_query(call.id, text)
    
    # Обновляем админское меню
    handle_admin(call.message)

# ================== РП КОМАНДЫ (БЕЗ ИЗМЕНЕНИЙ) ==================

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
    
    if not message.text or not message.reply_to_message:
        return
    
    text = message.text.lower().strip()
    
    # Админ-команды
    if text.startswith("заблокировать"):
        handle_block_command(message)
        return
    
    if text.startswith("разблокировать"):
        handle_unblock_command(message)
        return
    
    # РП команды
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

# ================== РАССЫЛКА (БЕЗ ИЗМЕНЕНИЙ) ==================

@bot.callback_query_handler(func=lambda call: call.data == "broadcast")
def start_broadcast(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "Только для админов!")
        return
    
    text = "Киньте текст для рассылки"
    bot.send_message(call.message.chat.id, text)
    
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
        
        bot.message_handler(func=lambda m: False)(receive_broadcast_text)

@bot.callback_query_handler(func=lambda call: call.data == "start_broadcast")
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

@bot.callback_query_handler(func=lambda call: call.data == "cancel_broadcast")
def cancel_broadcast(call):
    db.broadcast_message = None
    db.broadcast_in_progress = False
    db.save_data()
    
    bot.edit_message_text(
        "Рассылка отменена",
        call.message.chat.id,
        call.message.message_id
    )

# ================== ЗАПУСК БОТА ==================

if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling()