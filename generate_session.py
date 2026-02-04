"""
Генератор сессии для Telegram API.
Создает String Session для постоянного использования.
"""
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession


async def generate_session_async():
    """Генерирует строку сессии для постоянного использования."""
    print("=" * 60)
    print("Генератор сессии Telegram")
    print("=" * 60)
    print()

    # Запрашиваем API_ID и API_HASH у пользователя
    api_id = input("Введите ваш API_ID: ").strip()
    api_hash = input("Введите ваш API_HASH: ").strip()

    if not api_id or not api_hash:
        print("\n❌ Ошибка: API_ID и API_HASH обязательны!")
        print("Получите их на https://my.telegram.org/apps")
        return

    try:
        api_id = int(api_id)
    except ValueError:
        print("\n❌ Ошибка: API_ID должен быть числом!")
        return

    print("\n🔐 Подключение к Telegram...")
    print("📱 Вам нужно будет авторизоваться через Telegram")
    print("   (введите код из Telegram, если потребуется)")
    print()

    client = TelegramClient(StringSession(), api_id, api_hash)

    try:
        await client.start()
        session_string = client.session.save()

        print("\n" + "=" * 60)
        print("✅ Сессия успешно создана!")
        print("=" * 60)
        print()
        print("ВАША СТРОКА СЕССИИ:")
        print("-" * 60)
        print(session_string)
        print("-" * 60)
        print()
        print("⚠️  ВНИМАНИЕ: СКОПИРУЙТЕ ЭТУ СТРОКУ!")
        print("⚠️  Она понадобится вам для поля TELEGRAM_SESSION в веб-форме")
        print("⚠️  Храните её в безопасности и не делитесь ею!")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ Ошибка при создании сессии: {e}")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(generate_session_async())
