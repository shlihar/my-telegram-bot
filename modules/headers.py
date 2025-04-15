import random

# Список можливих значень для User-Agent
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/85.0.4183.121 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.1 Safari/605.1.15',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15A372 Safari/604.1',
    'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:47.0) Gecko/20100101 Firefox/47.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'
]

# Список можливих значень для Referer
REFERERS = [
    'https://www.google.com',
    'https://www.bing.com',
    'https://www.facebook.com',
    'https://example.com',
    'https://twitter.com'
]

# Список можливих значень для Origin
ORIGINS = [
    'https://example.com',
    'https://randomsite.com',
    'https://testwebsite.org'
]

# Функція для генерації випадкових заголовків
def generate_random_headers(link):
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Referer': random.choice(REFERERS),
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': random.choice(ORIGINS),
        'X-Requested-With': 'XMLHttpRequest'
    }
