import json
import logging
import requests
import time
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from modules.send import receive_link  # Імпорт функції receive_link з send.py

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

# API токен Monobank
MONOBANK_API_TOKEN = "uSdOxQuJ1_mmahr8Ke7ImZNp2H8WRJvRpAnjCM36-JDI"
ACCOUNT_ID = "cEeQ-klTV5tseZmWL1j-Y7BP-Po4OeY"  # ID рахунку "На товарку"

# Токен для другого бота
NOTIFICATION_BOT_TOKEN = "7990285286:AAHwOfV_aOH_42TZrmJTVN9JIIsGtayAGFI"
NOTIFICATION_CHAT_ID = "-4501440341"  # ID чату для сповіщень

# Файл для збереження користувачів
USERS_FILE = 'users.json'

# Завантаження користувачів з файлу
def load_users():
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# Збереження користувачів у файл
def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

# Функція для отримання максимальної кількості сайтів за тарифом
def get_max_sites_by_tariff(tariff):
    tariffs = {
        'Звичайний': 1,
        'Про': 3,
        'Бізнес': 10,
    }
    return tariffs.get(tariff, 1)

# Генерація унікальної суми для поповнення (долари -> гривні)
def generate_payment_amount(dollar_amount):
    exchange_rate = 41
    base_amount = dollar_amount * exchange_rate
    unique_cents = round(time.time() % 1, 2)  # Унікальні копійки
    return round(base_amount + unique_cents, 2)

def check_transactions(amount, from_time, to_time):
    url = f"https://api.monobank.ua/personal/statement/{ACCOUNT_ID}/{from_time}/{to_time}"
    headers = {
        "X-Token": MONOBANK_API_TOKEN
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        transactions = response.json()
        for tx in transactions:
            if tx['amount'] == amount * 100:  # Сума в копійках
                return True
    return False

# Функція для поповнення балансу
async def top_up_balance(user_id, context):
    users = load_users()
    
    # Переконуємося, що користувач існує
    if str(user_id) not in users:
        users[str(user_id)] = {
            'tariff': 'Звичайний',
            'sites': [],
            'domens': [],
            'expected_amount': 0,
            'available_sites': 0  # Додаємо поле для доступних сайтів
        }
        save_users(users)

    user_data = users[str(user_id)]
    
    # Отримуємо актуальний тариф користувача
    tariff = user_data.get('tariff', 'Звичайний')

    logger.info(f"Поточний тариф користувача {user_id}: {tariff}.")  # Логування тарифу

    # Вартість тарифів у доларах
    tariffs_cost = {
        'Звичайний': 10,
        'Про': 30,
        'Бізнес': 100
    }

    # Визначаємо вартість тарифу у гривнях
    dollar_amount = tariffs_cost.get(tariff, 10)
    amount_uah = generate_payment_amount(dollar_amount)

    # Відправляємо користувачу суму для поповнення і реквізити
    await context.bot.send_message(
        chat_id=user_id,
        text=f"Ваш тариф: {tariff}. Для поповнення рахунку вам необхідно поповнити {amount_uah} грн. "
             f"Надішліть цю суму на 5375411222893203"
    )

    # Зберігаємо необхідну суму для перевірки
    users[str(user_id)]['expected_amount'] = amount_uah
    save_users(users)

    # Додаємо кнопку "Підтвердити оплату"
    keyboard = [[InlineKeyboardButton("Підтвердити оплату", callback_data='check_payment')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(user_id, "Після поповнення натисніть 'Підтвердити оплату' для перевірки платежу.", reply_markup=reply_markup)

# Відправка меню користувачу
async def send_user_menu(user_id, context):
    users = load_users()  # Завантажити користувачів тут
    user_data = users.get(str(user_id), {})
    tariff = user_data.get('tariff', 'Звичайний')  # Отримуємо правильний тариф

    # Отримуємо максимальну кількість сайтів за тарифом
    max_sites = get_max_sites_by_tariff(tariff)
    active_sites = len(user_data.get('sites', []))  # Кількість активних сайтів
    available_sites = user_data.get('available_sites', 0)  # Отримуємо кількість доступних сайтів

    # Якщо доступні сайти менші за 0, ставимо 0
    if available_sites < 0:
        available_sites = 0

    # Кнопки для основного меню
    keyboard = [
        [InlineKeyboardButton("Додати сайт", callback_data='add_site')],
        [InlineKeyboardButton("Додати домен", callback_data='add_domen')],
        [InlineKeyboardButton("Оплатити тариф", callback_data='choose_tariff')],
      
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Відправляємо повідомлення з меню
    await context.bot.send_message(
        chat_id=user_id,
        text=f'🆔 Ваш ID користувача: {user_id}\n\n'
             f'👨‍💻 Ваш тариф: {tariff}\n'
             f'✅ Активних сайтів: {active_sites}\n'
             f'#️⃣ Доступних для запуску сайтів: {available_sites}\n'
             f'🔗 Активних доменів: {len(user_data.get("domens", []))}\n',
        reply_markup=reply_markup
    )

# Функція для відправлення сповіщення в чат
async def send_notification_to_chat(context, message):
    notification_bot = Application.builder().token(NOTIFICATION_BOT_TOKEN).build()
    await notification_bot.bot.send_message(chat_id=NOTIFICATION_CHAT_ID, text=message)

# Перевірка, чи надійшли кошти після натискання "Підтвердити оплату"
async def check_payment_status_button(query: Update, context) -> None:
    user_id = query.from_user.id
    users = load_users()
    user_data = users.get(str(user_id), {})
    expected_amount = user_data.get('expected_amount', 0)  # Використовуємо збережену суму

    if expected_amount > 0:
        # Перевіряємо транзакції за останні 10 хвилин
        current_time = int(time.time())
        ten_minutes_ago = current_time - 600  # 10 хвилин тому

        if check_transactions(expected_amount, ten_minutes_ago, current_time):
            await query.message.reply_text(f"Платіж на суму {expected_amount} грн отримано. Ваш тариф активовано!")

            # Оновлюємо статус тарифу
            new_tariff = user_data.get('new_tariff')
            max_sites = get_max_sites_by_tariff(new_tariff)
            user_data['available_sites'] = max_sites  # Встановлюємо нову кількість доступних сайтів
            user_data['tariff'] = new_tariff  # Зберігаємо новий тариф
            save_users(users)

            # Показуємо оновлене меню з статусом акаунту
            await send_user_menu(user_id, context)
        else:
            # Повідомлення про те, що платіж не отримано
            await query.message.reply_text(
                f"Платіж на суму {expected_amount} грн не знайдено. "
                f"Будь ласка, перевірте реквізити."
            )

            # Додаємо кнопку "Підтвердити оплату" для повторної перевірки
            keyboard = [[InlineKeyboardButton("Підтвердити оплату", callback_data='check_payment')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(user_id, "Спробуйте ще раз натиснувши 'Підтвердити оплату'.", reply_markup=reply_markup)
    else:
        await query.message.reply_text("Немає очікуваного поповнення.")

# Клавіатура для кнопок "Меню" та "Підтримка" під основною клавіатурою
async def send_persistent_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = ReplyKeyboardMarkup(
        [['🏠 Меню', '💬 Підтримка']],
        resize_keyboard=True  # Зменшення розміру клавіатури
    )
    persistent_message = await update.message.reply_text("Оберіть опцію:", reply_markup=keyboard)
    context.user_data['persistent_message_id'] = persistent_message.message_id


# Обробка вибору тарифу
async def button(update: Update, context) -> None:
    query = update.callback_query
    user_id = query.from_user.id  # Правильний ID користувача
    users = load_users()

    await query.message.delete()

    if query.data == 'top_up_balance':
        await top_up_balance(user_id, context)  # Передаємо user_id
    elif query.data == 'check_payment':
        await check_payment_status_button(query, context)
    elif query.data == 'add_site':
        message = await query.message.reply_text("Додайте ваш сайт:")
        context.user_data['site_message_id'] = message.message_id
    elif query.data == 'add_domen':
        # Відправлення реквізитів на оплату домену
        dollar_amount = 100
        amount_uah = generate_payment_amount(dollar_amount)

        await query.message.reply_text(
            f"Для додавання домену, будь ласка, поповніть баланс на суму {amount_uah}, "
          
            f"Надішліть цю суму на 5375411222893203."
        )

        # Додаємо кнопку "Підтвердити оплату"
        keyboard = [[InlineKeyboardButton("Підтвердити оплату", callback_data='check_payment_domen')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(user_id, "Після поповнення натисніть 'Підтвердити оплату' для перевірки платежу.", reply_markup=reply_markup)

    elif query.data == 'choose_tariff':
        keyboard = [
            [InlineKeyboardButton("Звичайний - 1 сайт/7 днів (10$)", callback_data='tariff_normal')],
            [InlineKeyboardButton("Про - 3 сайти/14 днів (30$)", callback_data='tariff_pro')],
            [InlineKeyboardButton("Бізнес - 10 сайтів/30 днів (100$)", callback_data='tariff_business')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text('Оберіть тариф:', reply_markup=reply_markup)
    elif query.data.startswith('tariff_'):
        new_tariff = query.data.split('_')[1]
        tariffs = {
            'normal': 'Звичайний',
            'pro': 'Про',
            'business': 'Бізнес',
        }
        selected_tariff = tariffs.get(new_tariff, 'Звичайний')

        # Вартість тарифів у доларах
        tariffs_cost = {
            'Звичайний': 10,
            'Про': 30,
            'Бізнес': 100
        }

        dollar_amount = tariffs_cost.get(selected_tariff, 10)
        amount_uah = generate_payment_amount(dollar_amount)

        # Зберігаємо новий тариф і суму в даних користувача
        user_data = users.get(str(user_id), {})
        user_data['new_tariff'] = selected_tariff  # Зберігаємо новий тариф
        user_data['expected_amount'] = amount_uah  # Зберігаємо очікувану суму для перевірки
        users[str(user_id)] = user_data
        save_users(users)

        # Відправляємо інформацію про обраний тариф та реквізити
        await query.message.reply_text(
            f"Ви обрали тариф: {selected_tariff}. Для активації, будь ласка, поповніть баланс на суму {amount_uah} грн. "
          
            f"Надішліть цю суму на 5375411222893203."
        )

        # Додаємо кнопку "Підтвердити оплату"
        keyboard = [[InlineKeyboardButton("Підтвердити оплату", callback_data='check_payment')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(user_id, "Після поповнення натисніть 'Підтвердити оплату' для перевірки платежу.", reply_markup=reply_markup)

# Обробка введених повідомлень
async def handle_message(update: Update, context) -> None:
    text = update.message.text
    user_id = update.message.from_user.id
    users = load_users()

    if text == '🏠 Меню':
        await send_user_menu(user_id, context)
    elif text == '💬 Підтримка':
        await update.message.reply_text("Зверніться до нашої підтримки: @suport_2208")
    elif 'http://' in text or 'https://' in text:  # Перевірка наявності URL
        user_data = users.get(str(user_id), {})
        
        max_sites = get_max_sites_by_tariff(user_data.get('tariff', 'Звичайний'))
        active_sites = len(user_data.get('sites', []))

        # Перевірка доступних сайтів
        available_sites = user_data.get('available_sites', 0)  # Отримуємо кількість доступних сайтів

        if active_sites < available_sites:  # Якщо користувач може ще додати сайт
            await receive_link(update, context)  # Викликаємо функцію receive_link, яка вже є в send.py

            # Оновлення даних користувача
            user_data['sites'].append(text)  # Додаємо сайт
            user_data['available_sites'] = available_sites - 1  # Оновлюємо кількість доступних сайтів

            # Зберігаємо оновлені дані в users.json
            users[str(user_id)] = user_data
            save_users(users)

            # Відправляємо сповіщення в чат про додавання сайту
            await send_notification_to_chat(context, f"Користувач {user_id} додав сайт: {text}")

        else:
            await update.message.reply_text(f"Ви досягли ліміту додавання сайтів за вашим тарифом ({max_sites} сайти).")
        
        # Відправляємо оновлене меню
        await send_user_menu(user_id, context)

    else:
        user_data = users.get(str(user_id), {})
        if 'domens' not in user_data:
            user_data['domens'] = []
        user_data['domens'].append(text)  # Додаємо домен в масив 'domens'
        users[str(user_id)] = user_data
        save_users(users)

        # Відправляємо сповіщення в чат про додавання домену
        await send_notification_to_chat(context, f"Користувач {user_id} додав домен: {text}")

        await update.message.reply_text("Дякую! Спам активовано!")
        await send_user_menu(user_id, context)  # Відправляємо оновлене меню

# Запуск бота
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    users = load_users()
    if str(user_id) not in users:
        users[str(user_id)] = {
            'tariff': 'Звичайний',
            'sites': [],
            'domens': [],
            'expected_amount': 0,
            'available_sites': 1  # Додаємо 1 доступний сайт для запуску
        }
        save_users(users)
        
        # Повідомлення для нового користувача
        await update.message.reply_text(
            "Вітаємо! У вас є 1 доступний сайт для тесту. Ми відправлятимемо спам протягом 5 хвилин."
        )
        await send_notification_to_chat(context, f"Новий користувач: {user_id} отримав 1 доступний сайт для тесту.")

    await send_user_menu(user_id, context)  # Передаємо user_id замість update
    await send_persistent_keyboard(update, context)  # Показуємо кнопки меню та підтримки

# Головна функція
def main():
    application = Application.builder().token("7362910993:AAFxDBixzl1DOl9msPK4jjvaL1ASifrfvPQ").build()

    # Обробка команд та повідомлень
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))  # Використання handle_message

    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()
