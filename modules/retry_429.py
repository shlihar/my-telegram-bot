import aiohttp
import asyncio
import random
import logging

from retry_429 import handle_429  # Імпорт обробника 429 помилок

from aiohttp_socks import ProxyConnector
from modules.names import names, phones

# Налаштування логування
logger = logging.getLogger(__name__)

# Проксі дані
PROXY = 'socks5://Uj8pHTcd:LFFKzhza@connect-uasocks.net:1080'

# Функція для повторної спроби відправки форми у випадку помилки 429
async def retry_send_form(session, url, form_data, headers, i, delay, retry_count=3):
    for attempt in range(retry_count):
        try:
            await asyncio.sleep(delay)  # Затримка перед запитом
            async with session.post(url, data=form_data, headers=headers) as form_response:
                if form_response.status == 200:
                    logger.info(f"Форма {i+1} успішно відправлена після {attempt+1} спроб!")
                    return True
                elif form_response.status == 429:
                    logger.warning(f"Форма {i+1}: Занадто багато запитів (429), спроба {attempt+1}")
                    await asyncio.sleep(5)  # Затримка перед наступною спробою
                else:
                    logger.error(f"Форма {i+1}: Не вдалося відправити. Статус-код: {form_response.status}")
                    return False
        except aiohttp.ClientError as e:
            logger.error(f"Помилка при відправці форми {i+1}: {e}")
        except Exception as ex:
            logger.error(f"Невідома помилка при відправці форми {i+1}: {ex}")
    return False

Функція для обробки помилок статусу
async def send_form_with_retry(session, url, form_data, headers, i, delay):
    try:
        await send_form(session, url, form_data, headers, i, delay)
    except Exception as e:
        if '429' in str(e):
            logger.warning(f"Виклик повторної обробки для форми {i+1} через помилку 429.")
            await handle_429(url, form_data, headers)
        else:
            logger.error(f"Помилка при відправці форми {i+1}: {e}")
# Основна функція для обробки помилок
async def handle_429(link, form_data, headers):
    connector = ProxyConnector.from_url(PROXY)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [(link, form_data)]
        for i, (url, data) in enumerate(tasks):
            success = await retry_send_form(session, url, data, headers, i, delay=2)
            if not success:
                logger.error(f"Форма {i+1} не була відправлена навіть після кількох спроб.")
