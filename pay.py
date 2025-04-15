import requests

# Ваш токен Monobank API
MONOBANK_API_TOKEN = "uSdOxQuJ1_mmahr8Ke7ImZNp2H8WRJvRpAnjCM36-JDI"

def get_account_info():
    url = "https://api.monobank.ua/personal/client-info"
    headers = {
        "X-Token": MONOBANK_API_TOKEN
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()  # Інформація про рахунок
    else:
        print("Помилка при отриманні інформації про клієнта:", response.status_code)
        return None

# Отримання інформації про рахунок
account_info = get_account_info()
if account_info:
    print(account_info)
