"""
Telegram Cloud Scraper Pro — многопользовательское приложение.
Вход: по номеру телефона (код из Telegram) или вставка готовой сессии.
"""
import streamlit as st
import asyncio
import json
from datetime import datetime
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError, SessionPasswordNeededError

# Настройка страницы
st.set_page_config(
    page_title="Telegram Cloud Scraper Pro",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Состояние для входа по телефону
if "telegram_session_string" not in st.session_state:
    st.session_state.telegram_session_string = ""
if "phone_login_pending" not in st.session_state:
    st.session_state.phone_login_pending = None  # {"session": str, "phone": str, "phone_code_hash": str}

# Сайдбар: API-ключи и два способа входа
with st.sidebar:
    st.header("🔑 Ваши API-ключи")
    st.caption("API_ID и API_HASH с my.telegram.org. Сессию можно получить прямо здесь по телефону.")
    
    api_id_input = st.text_input(
        "API_ID",
        placeholder="12345678",
        help="Число с my.telegram.org"
    )
    api_hash_input = st.text_input(
        "API_HASH",
        placeholder="abcdef1234567890...",
        type="password",
        help="Строка с my.telegram.org"
    )
    
    api_ok = api_id_input.strip() and api_hash_input.strip()
    
    st.markdown("---")
    st.subheader("📱 Вход в Telegram")
    
    session_input = ""  # по умолчанию; перезапишется полем во вкладке «Вставить сессию»
    login_tab, session_tab = st.tabs(["По номеру телефона", "Вставить сессию"])
    
    with login_tab:
        if st.session_state.telegram_session_string:
            st.success("✅ Вы уже вошли по телефону. Сессия активна в этой вкладке.")
            if st.button("Выйти и войти снова"):
                st.session_state.telegram_session_string = ""
                st.session_state.phone_login_pending = None
                st.rerun()
        else:
            phone = st.text_input("Номер телефона", placeholder="+79001234567", key="phone")
            pending = st.session_state.phone_login_pending
            
            if pending is None:
                if st.button("📤 Отправить код в Telegram") and api_ok and phone.strip():
                    async def do_send_code():
                        client = TelegramClient(StringSession(), int(api_id_input.strip()), api_hash_input.strip())
                        await client.connect()
                        sent = await client.send_code_request(phone.strip())
                        s = client.session.save()
                        await client.disconnect()
                        return s, sent.phone_code_hash
                    try:
                        session_str, phone_code_hash = asyncio.run(do_send_code())
                        st.session_state.phone_login_pending = {
                            "session": session_str,
                            "phone": phone.strip(),
                            "phone_code_hash": phone_code_hash,
                        }
                        st.success("Код отправлен в Telegram. Введите его ниже.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ошибка: {e}")
            else:
                # Если включена двухфакторная защита — запрашиваем пароль
                needs_password = pending.get("needs_password")
                if needs_password:
                    st.info("🔐 Включена двухфакторная защита. Введите пароль облачного пароля Telegram.")
                    password_2fa = st.text_input("Пароль (2FA)", type="password", placeholder="Пароль облачного пароля", key="password_2fa")
                    if st.button("Войти с паролем") and password_2fa:
                        async def do_sign_in_password():
                            client = TelegramClient(StringSession(pending["session"]), int(api_id_input.strip()), api_hash_input.strip())
                            await client.connect()
                            await client.sign_in(password=password_2fa)
                            s = client.session.save()
                            await client.disconnect()
                            return s
                        try:
                            session_str = asyncio.run(do_sign_in_password())
                            st.session_state.telegram_session_string = session_str
                            st.session_state.phone_login_pending = None
                            st.success("Вход выполнен. Можно скрапить.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Ошибка: {e}")
                else:
                    code = st.text_input("Код из Telegram", placeholder="12345", key="code")
                    if st.button("Войти") and code.strip():
                        async def do_sign_in():
                            client = TelegramClient(StringSession(pending["session"]), int(api_id_input.strip()), api_hash_input.strip())
                            await client.connect()
                            try:
                                await client.sign_in(
                                    pending["phone"],
                                    code.strip(),
                                    phone_code_hash=pending["phone_code_hash"],
                                )
                                s = client.session.save()
                                await client.disconnect()
                                return ("ok", s)
                            except SessionPasswordNeededError:
                                # Код принят, но нужен пароль 2FA — сохраняем сессию и просим пароль
                                s = client.session.save()
                                await client.disconnect()
                                return ("need_password", s)
                        try:
                            status, session_str = asyncio.run(do_sign_in())
                            if status == "need_password":
                                st.session_state.phone_login_pending = {
                                    **pending,
                                    "session": session_str,
                                    "needs_password": True,
                                }
                                st.success("Код принят. Введите пароль облачного пароля (2FA) выше.")
                                st.rerun()
                            else:
                                st.session_state.telegram_session_string = session_str
                                st.session_state.phone_login_pending = None
                                st.success("Вход выполнен. Можно скрапить.")
                                st.rerun()
                        except Exception as e:
                            st.error(f"Ошибка: {e}")
    
    with session_tab:
        session_input = st.text_area(
            "TELEGRAM_SESSION (опционально)",
            placeholder="Если уже есть строка сессии — вставьте сюда",
            height=80,
            help="Или получите сессию через «По номеру телефона»"
        )
    
    # Итоговая сессия: из входа по телефону или из вставленной строки
    effective_session = st.session_state.telegram_session_string or session_input.strip()
    credentials_ok = api_ok and bool(effective_session)
    
    if credentials_ok:
        try:
            _ = int(api_id_input.strip())
            st.success("✅ Готово к скрапингу")
        except ValueError:
            st.error("API_ID должен быть числом")
            credentials_ok = False
    else:
        st.info("👆 Введите API_ID, API_HASH и войдите по телефону или вставьте сессию")

# Заголовок
st.title("☁️ Telegram Cloud Scraper Pro")
st.caption("Многопользовательский скрапер — войдите по телефону или вставьте сессию")
st.markdown("---")

# Expander с инструкцией по получению API ключей
with st.expander("ℹ️ How to get API Keys?", expanded=False):
    st.markdown("""
    **Шаг 1.** Зайдите на [my.telegram.org](https://my.telegram.org), войдите по номеру телефона.
    
    **Шаг 2.** Нажмите **«API development tools»**.
    
    **Шаг 3.** Заполните форму (любые данные):
       - **App title:** `Scraper`
       - **Short name:** `scraper`
    
    **Шаг 4.** Скопируйте **App api_id** и **App api_hash** в поля слева.
    
    **Шаг 5.** Вкладка **«По номеру телефона»**: введите свой номер → «Отправить код» → введите код из Telegram → «Войти».  
    Сессия создастся сама, вставлять TELEGRAM_SESSION вручную не нужно.
    
    ⚠️ **Ключи никому не передавайте.**
    """)

st.markdown("---")

# UI элементы
st.subheader("📋 Channel Links")
channel_links_text = st.text_area(
    "Enter channel links (one per line):",
    placeholder="""@channel1
@channel2
https://t.me/channel3
channel4""",
    height=150,
    help="You can use @username, t.me/username, or just username format"
)

st.subheader("⚙️ Настройка выгрузки")
scrape_mode = st.radio(
    "Что выгружать:",
    options=["by_count", "by_date", "from_start", "by_words"],
    format_func=lambda x: {
        "by_count": "По количеству сообщений (последние N)",
        "by_date": "По дате (с указанной даты до сейчас)",
        "from_start": "С самого начала истории канала",
        "by_words": "По количеству слов (последние N слов)"
    }[x],
    horizontal=False,
    help="Режим ограничения выгрузки"
)

message_limit = 1000
from_date_value = None
word_limit_value = 100_000

if scrape_mode == "by_count":
    message_limit = st.number_input(
        "Количество последних сообщений:",
        min_value=1,
        max_value=50_000_000,
        value=1000,
        step=10000,
        help="Сколько последних сообщений забрать (для больших каналов можно ставить миллионы)"
    )
elif scrape_mode == "by_date":
    from_date_value = st.date_input(
        "С какой даты выгружать (включительно):",
        value=None,
        help="Сообщения начиная с этой даты до текущего момента"
    )
    if from_date_value:
        message_limit = 20_000_000
    else:
        st.info("Выберите дату")
elif scrape_mode == "from_start":
    message_limit = st.number_input(
        "Максимум сообщений с канала:",
        min_value=1000,
        max_value=50_000_000,
        value=100_000,
        step=10000,
        help="С начала истории до лимита (для каналов с миллионами сообщений)"
    )
elif scrape_mode == "by_words":
    word_limit_value = st.number_input(
        "Последних слов (примерно):",
        min_value=1000,
        max_value=50_000_000,
        value=100_000,
        step=10000,
        help="Собирать сообщения, пока не наберётся столько слов в тексте"
    )
    message_limit = 20_000_000

start_button = st.button("🚀 Start Scraping", type="primary", use_container_width=True)

# Функция для определения типа медиа
def get_media_type(message):
    """Определяет тип медиа в сообщении."""
    if message.photo:
        return "photo"
    elif message.video:
        return "video"
    elif message.voice:
        return "voice"
    elif message.document:
        return "document"
    elif message.audio:
        return "audio"
    elif message.sticker:
        return "sticker"
    elif message.gif:
        return "gif"
    elif message.poll:
        return "poll"
    else:
        return "none"

# Функция для парсинга реакций
def parse_reactions(message):
    """Парсит реакции из сообщения."""
    reactions = []
    if message.reactions:
        try:
            # Проверяем наличие results
            if hasattr(message.reactions, 'results') and message.reactions.results:
                for reaction in message.reactions.results:
                    try:
                        if reaction.reaction:
                            # Пытаемся получить emoji разными способами
                            emoji = None
                            if hasattr(reaction.reaction, 'emoticon'):
                                emoji = reaction.reaction.emoticon
                            elif hasattr(reaction.reaction, 'emoticon'):
                                emoji = str(reaction.reaction.emoticon)
                            else:
                                emoji = str(reaction.reaction)
                            
                            count = reaction.count if hasattr(reaction, 'count') else 0
                            
                            if emoji:
                                reactions.append({
                                    "emoji": emoji,
                                    "count": count
                                })
                    except Exception:
                        continue
        except Exception:
            pass
    return reactions

# Функция для построения публичной ссылки
def build_message_url(channel_username, message_id):
    """Строит публичную ссылку на сообщение."""
    username = channel_username.lstrip('@')
    return f"https://t.me/{username}/{message_id}"

# Основная функция скрапинга
def normalize_channel_link(link):
    """Убирает префикс ссылки, оставляет только username канала. lstrip() не использовать — он удаляет символы из набора, а не подстроку."""
    link = link.strip()
    if link.startswith("https://t.me/"):
        link = link[len("https://t.me/"):]
    elif link.startswith("http://t.me/"):
        link = link[len("http://t.me/"):]
    elif link.startswith("t.me/"):
        link = link[len("t.me/"):]
    if link.startswith("@"):
        link = link[1:]
    return link.strip()


async def scrape_channel(client, channel_link, options):
    """Скрапит один канал. options: mode, message_limit, from_date (date or None), word_limit."""
    try:
        channel_link = normalize_channel_link(channel_link)
        entity = await client.get_entity(channel_link)
        channel_username = entity.username if hasattr(entity, 'username') else channel_link
        
        mode = options.get("mode", "by_count")
        message_limit = options.get("message_limit", 1000)
        from_date = options.get("from_date")  # datetime.date or None
        word_limit = options.get("word_limit", 100_000)
        
        messages_data = []
        total_words = 0
        stop_reason = None
        
        async for message in client.iter_messages(entity, limit=message_limit):
            try:
                message_date = message.date if message.date else None
                
                # Режим «по дате»: останавливаемся, когда дошли до сообщений старше from_date
                if mode == "by_date" and from_date and message_date:
                    msg_date = message_date.date() if hasattr(message_date, "date") else message_date
                    if msg_date < from_date:
                        stop_reason = "date"
                        break
                
                # Режим «по словам»: считаем слова и останавливаемся при достижении лимита
                text = message.text or ""
                if mode == "by_words":
                    total_words += len(text.split())
                    if total_words >= word_limit:
                        stop_reason = "words"
                
                date_iso = message_date.isoformat() if message_date else None
                date_unixtime = int(message_date.timestamp()) if message_date else None
                
                message_data = {
                    "id": message.id,
                    "date": date_iso,
                    "date_unixtime": date_unixtime,
                    "text": text,
                    "views": message.views if hasattr(message, 'views') else None,
                    "forwards": message.forwards if hasattr(message, 'forwards') else None,
                    "media_type": get_media_type(message),
                    "reactions": parse_reactions(message),
                    "reply_to_msg_id": message.reply_to_msg_id if hasattr(message, 'reply_to_msg_id') else None,
                    "url": build_message_url(channel_username, message.id)
                }
                messages_data.append(message_data)
                
                if mode == "by_words" and stop_reason == "words":
                    break
            except FloodWaitError as e:
                st.warning(f"⏳ Rate limit: waiting {e.seconds} seconds...")
                await asyncio.sleep(e.seconds)
                continue
            except Exception as e:
                st.warning(f"⚠️ Skipping message {message.id}: {str(e)}")
                continue
        
        return {
            "channel": channel_link,
            "channel_id": entity.id,
            "channel_title": entity.title if hasattr(entity, 'title') else None,
            "messages": messages_data,
            "total_messages": len(messages_data),
            "total_words": total_words if mode == "by_words" else None,
            "stop_reason": stop_reason
        }
        
    except FloodWaitError as e:
        st.error(f"⏳ FloodWaitError: Need to wait {e.seconds} seconds for channel {channel_link}")
        await asyncio.sleep(e.seconds)
        return None
    except Exception as e:
        st.error(f"❌ Error scraping {channel_link}: {str(e)}")
        return None

# Асинхронная функция для скрапинга (клиент создаётся из ключей пользователя)
async def run_scraping(api_id, api_hash, session_string, links, options, progress_bar, status_text):
    """Запускает процесс скрапинга всех каналов. options: mode, message_limit, from_date, word_limit."""
    all_results = []
    client = None
    
    try:
        api_id = int(api_id.strip())
        client = TelegramClient(
            StringSession(session_string.strip()),
            api_id,
            api_hash.strip()
        )
        await client.connect()
        if not await client.is_user_authorized():
            st.error("❌ Сессия не авторизована. Проверьте TELEGRAM_SESSION (запустите generate_session.py заново).")
            return None
        
        for idx, link in enumerate(links):
            status_text.text(f"🔄 Scraping {idx + 1}/{len(links)}: {link}")
            progress_bar.progress((idx) / len(links))
            
            result = await scrape_channel(client, link, options)
            
            if result:
                all_results.append(result)
                st.success(f"✅ Scraped {result['total_messages']} messages from {link}")
        
        progress_bar.progress(1.0)
        status_text.text(f"✅ Completed! Scraped {len(all_results)} channel(s)")
        
        return all_results
        
    except ValueError:
        st.error("❌ API_ID должен быть числом.")
        return None
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return None
    finally:
        if client:
            await client.disconnect()

# Обработка нажатия кнопки
if start_button:
    if not credentials_ok:
        st.warning("⚠️ Сначала введите свои API-ключи в боковой панели (слева).")
    elif not channel_links_text.strip():
        st.warning("⚠️ Please enter at least one channel link!")
    else:
        # Парсим ссылки
        links = [line.strip() for line in channel_links_text.strip().split('\n') if line.strip()]
        
        if not links:
            st.warning("⚠️ No valid channel links found!")
        else:
            if scrape_mode == "by_date" and not from_date_value:
                st.warning("⚠️ Выберите дату «с какой выгружать».")
            else:
                st.info(f"📊 Found {len(links)} channel(s) to scrape")
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                options = {
                    "mode": scrape_mode,
                    "message_limit": message_limit,
                    "from_date": from_date_value,
                    "word_limit": word_limit_value,
                }
                
                all_results = asyncio.run(run_scraping(
                    api_id_input,
                    api_hash_input,
                    effective_session,
                    links,
                    options,
                    progress_bar,
                    status_text
                ))
            
            if all_results:
                # Формируем финальный JSON
                final_result = {
                    "scraped_at": datetime.now().isoformat(),
                    "total_channels": len(all_results),
                    "total_messages": sum(r['total_messages'] for r in all_results),
                    "channels": all_results
                }
                
                # Конвертируем в JSON строку
                json_string = json.dumps(final_result, ensure_ascii=False, indent=2)
                
                # Показываем результаты
                st.subheader("📊 Results")
                st.json(final_result)
                
                # Кнопка скачивания
                st.download_button(
                    label="📥 Download result.json",
                    data=json_string,
                    file_name=f"telegram_scrape_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True
                )

# Футер
st.markdown("---")
st.markdown("**Telegram Cloud Scraper Pro** - Powered by Streamlit & Telethon")
