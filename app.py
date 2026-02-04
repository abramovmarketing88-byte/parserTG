"""
Telegram Cloud Scraper Pro — многопользовательское приложение.
Премиальный SaaS-дизайн: карточки, вкладки, индикаторы статуса, валидация, экспорт.
"""
import streamlit as st
import asyncio
import json
import io
import re
from datetime import datetime
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError, SessionPasswordNeededError
import pandas as pd

# ——— Настройка страницы ———
st.set_page_config(
    page_title="Telegram Cloud Scraper Pro",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="expanded"
)


def inject_custom_css():
    """Внедряет кастомный CSS для премиального SaaS-стиля."""
    st.markdown(
        """
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            /* Базовый фон и шрифт */
            .stApp, [data-testid="stAppViewContainer"] {
                background-color: #F0F2F6 !important;
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
            }
            /* Сайдбар — тёмно-синий */
            section[data-testid="stSidebar"] > div {
                background: linear-gradient(180deg, #0E1117 0%, #1a1d24 100%) !important;
            }
            section[data-testid="stSidebar"] .stMarkdown, section[data-testid="stSidebar"] label {
                color: #e4e6eb !important;
            }
            section[data-testid="stSidebar"] .stCaption {
                color: #b0b3b8 !important;
            }
            /* Карточки на главной */
            .card {
                background: white;
                border-radius: 20px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.06);
                padding: 1.5rem;
                margin-bottom: 1.25rem;
            }
            /* Заголовки в карточках */
            .card h3 { font-family: 'Inter', sans-serif; font-weight: 600; color: #1c1e21; margin-top: 0; }
            /* Индикатор статуса в сайдбаре */
            .status-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 8px; vertical-align: middle; }
            .status-dot.inactive { background: #e74c3c; box-shadow: 0 0 0 2px rgba(231,76,60,0.3); }
            .status-dot.active { background: #27ae60; box-shadow: 0 0 0 2px rgba(39,174,96,0.4); animation: pulse-green 1.5s ease-in-out infinite; }
            @keyframes pulse-green { 0%, 100% { opacity: 1; box-shadow: 0 0 0 2px rgba(39,174,96,0.4); } 50% { opacity: 0.85; box-shadow: 0 0 0 6px rgba(39,174,96,0.2); } }
            /* Главная кнопка — градиент Telegram Blue */
            .stButton > button[kind="primary"] {
                background: linear-gradient(135deg, #2481cc 0%, #41a7f5 100%) !important;
                color: white !important;
                border: none !important;
                border-radius: 12px !important;
                font-weight: 600 !important;
                padding: 0.6rem 1.2rem !important;
                box-shadow: 0 4px 14px rgba(36,129,204,0.4) !important;
                transition: transform 0.2s, box-shadow 0.2s !important;
            }
            .stButton > button[kind="primary"]:hover {
                transform: scale(1.02) !important;
                box-shadow: 0 6px 20px rgba(36,129,204,0.5) !important;
            }
            /* Заголовок страницы */
            h1 { font-family: 'Inter', sans-serif !important; color: #1c1e21 !important; }
            .main-caption { color: #65676b !important; font-family: 'Inter', sans-serif !important; }
            /* Поле с ошибкой валидации */
            .input-invalid { border: 1px solid #e74c3c !important; border-radius: 8px !important; }
        </style>
        """,
        unsafe_allow_html=True
    )


inject_custom_css()

# ——— Session state ———
if "telegram_session_string" not in st.session_state:
    st.session_state.telegram_session_string = ""
if "phone_login_pending" not in st.session_state:
    st.session_state.phone_login_pending = None
if "scrape_results" not in st.session_state:
    st.session_state.scrape_results = None
if "scrape_log_lines" not in st.session_state:
    st.session_state.scrape_log_lines = []
if "last_export_format" not in st.session_state:
    st.session_state.last_export_format = "JSON"

# ——— Валидация ссылок на каналы ———
def is_valid_channel_link(line: str) -> bool:
    """Проверяет, похожа ли строка на ссылку/username канала."""
    s = line.strip()
    if not s:
        return False
    # @channel, t.me/channel, https://t.me/channel, или просто username (латиница/цифры/подчёркивание)
    if s.startswith("@"):
        return len(s) > 1 and re.match(r"^@[a-zA-Z0-9_]{5,}$", s)
    if "t.me/" in s:
        return True
    if re.match(r"^[a-zA-Z0-9_]{5,32}$", s):
        return True
    return False


def validate_channel_links(text: str) -> tuple[list[str], list[str]]:
    """Возвращает (валидные ссылки, невалидные строки)."""
    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
    valid, invalid = [], []
    for line in lines:
        if is_valid_channel_link(line):
            valid.append(line.strip())
        else:
            invalid.append(line)
    return valid, invalid


# ——— Сайдбар: API-ключи и вход ———
with st.sidebar:
    st.markdown(
        "<div style='padding:0.5rem 0; border-bottom: 1px solid #3a3b3c; margin-bottom: 1rem;'>"
        "<span style='font-family: Inter; font-size: 1.1rem; font-weight: 600;'>🔑 API-ключи</span>"
        "</div>",
        unsafe_allow_html=True
    )
    st.caption("API_ID и API_HASH с my.telegram.org. Сессию можно получить по телефону.")

    api_id_input = st.text_input("API_ID", placeholder="12345678", help="Число с my.telegram.org")
    api_hash_input = st.text_input("API_HASH", placeholder="abcdef...", type="password", help="Строка с my.telegram.org")
    api_ok = api_id_input.strip() and api_hash_input.strip()

    with st.expander("ℹ️ Как получить API Keys?", expanded=False):
        st.markdown("""
        **Шаг 1.** Зайдите на [my.telegram.org](https://my.telegram.org), войдите по номеру телефона.  
        **Шаг 2.** Нажмите **«API development tools»**.  
        **Шаг 3.** Заполните форму (App title: `Scraper`, Short name: `scraper`).  
        **Шаг 4.** Скопируйте **api_id** и **api_hash** в поля выше.  
        **Шаг 5.** Вкладка «По номеру телефона»: введите номер → «Отправить код» → введите код из Telegram → «Войти».  
        ⚠️ **Ключи никому не передавайте.**
        """)

    st.markdown("---")
    st.markdown("<span style='font-weight: 600;'>📱 Вход в Telegram</span>", unsafe_allow_html=True)
    session_input_sidebar = ""
    login_tab, session_tab = st.tabs(["По номеру телефона", "Вставить сессию"])

    with login_tab:
        if st.session_state.telegram_session_string:
            st.success("✅ Сессия активна в этой вкладке.")
            # Сохранить сессию для следующего раза (по второму слайду)
            with st.expander("💾 Сохранить сессию", expanded=False):
                st.caption("Скопируйте строку ниже или скачайте файл. Потом вкладка «Вставить сессию» — не нужно вводить код снова.")
                session_to_save = st.session_state.telegram_session_string
                st.text_area("Строка сессии (скопируйте)", value=session_to_save, height=80, disabled=True, key="session_display")
                st.download_button(
                    label="📥 Скачать сессию в файл",
                    data=session_to_save,
                    file_name="telegram_session.txt",
                    mime="text/plain",
                    key="dl_session",
                )
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
                        st.success("Код отправлен. Введите его ниже.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Ошибка: {e}")
            else:
                needs_password = pending.get("needs_password")
                if needs_password:
                    st.info("🔐 Введите пароль облачного пароля (2FA).")
                    password_2fa = st.text_input("Пароль (2FA)", type="password", placeholder="Пароль", key="password_2fa")
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
                            st.success("Вход выполнен.")
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
                                st.success("Код принят. Введите пароль 2FA выше.")
                                st.rerun()
                            else:
                                st.session_state.telegram_session_string = session_str
                                st.session_state.phone_login_pending = None
                                st.success("Вход выполнен.")
                                st.rerun()
                        except Exception as e:
                            st.error(f"Ошибка: {e}")

    with session_tab:
        st.caption("Сохранили сессию после входа по телефону? Вставьте сюда — не нужно вводить код снова.")
        session_input_sidebar = st.text_area(
            "TELEGRAM_SESSION (опционально)",
            placeholder="Вставьте строку сессии из файла или из блока «Сохранить сессию»",
            height=80,
            help="Или войдите через вкладку «По номеру телефона»",
        )

    # Индикатор статуса: после вкладок, когда известна и вставленная сессия
    effective_session_sidebar = st.session_state.telegram_session_string or (session_input_sidebar.strip() if session_input_sidebar else "")
    st.markdown(
        "<div style='display: flex; align-items: center; margin-top: 0.5rem;'>"
        "<span class='status-dot " + ("active" if effective_session_sidebar else "inactive") + "'></span>"
        "<span style='font-size: 0.9rem;'>" + ("Сессия активна" if effective_session_sidebar else "Не в сети") + "</span>"
        "</div>",
        unsafe_allow_html=True
    )

effective_session = st.session_state.telegram_session_string or (session_input_sidebar.strip() if session_input_sidebar else "")

credentials_ok = api_ok and bool(effective_session)
if credentials_ok:
    try:
        int(api_id_input.strip())
    except ValueError:
        credentials_ok = False

# ——— Главная область: заголовок и вкладки ———
st.markdown("<h1 style='font-family: Inter; margin-bottom: 0.25rem;'>☁️ Telegram Cloud Scraper Pro</h1>", unsafe_allow_html=True)
st.caption("Многопользовательский скрапер — премиум-интерфейс и экспорт в JSON, CSV, Excel")
st.markdown("---")

tab_config, tab_results = st.tabs(["📋 Конфигурация", "📊 Результаты и Анализ"])

# ——— Вкладка «Конфигурация» ———
# По первому слайду: сверху формат выгрузки, кнопка старта и инструкция — визуально понятно
with tab_config:
    st.markdown("<div class='card'><h3>Формат выгрузки</h3></div>", unsafe_allow_html=True)
    export_format = st.radio(
        "Формат выгрузки:",
        options=["JSON", "CSV", "Excel"],
        horizontal=True,
        key="export_format",
    )
    st.session_state.last_export_format = export_format

    start_button = st.button("🚀 Start Scraping", type="primary", use_container_width=True)

    st.markdown("<div class='card'><h3>📋 Ссылки на каналы</h3></div>", unsafe_allow_html=True)
    channel_links_text = st.text_area(
        "Введите ссылки (по одной на строку):",
        placeholder="@channel1\nhttps://t.me/channel2\nchannel3",
        height=140,
        help="Формат: @username, t.me/username или просто username",
        key="channel_links",
    )

    valid_links, invalid_links = validate_channel_links(channel_links_text)
    if invalid_links and channel_links_text.strip():
        st.warning(f"⚠️ Некорректные строки (будут пропущены): {', '.join(invalid_links[:5])}{'…' if len(invalid_links) > 5 else ''}")

    st.markdown("<div class='card'><h3>⚙️ Настройка выгрузки</h3></div>", unsafe_allow_html=True)
    scrape_mode = st.radio(
        "Что выгружать:",
        options=["by_count", "by_date", "from_start", "by_words"],
        format_func=lambda x: {
            "by_count": "По количеству сообщений (последние N)",
            "by_date": "По дате (с указанной даты до сейчас)",
            "from_start": "С самого начала истории канала",
            "by_words": "По количеству слов (последние N слов)",
        }[x],
        horizontal=False,
    )

    message_limit = 1000
    from_date_value = None
    word_limit_value = 100_000

    if scrape_mode == "by_count":
        message_limit = st.number_input("Количество последних сообщений:", min_value=1, max_value=50_000_000, value=1000, step=10000)
    elif scrape_mode == "by_date":
        from_date_value = st.date_input("С какой даты выгружать (включительно):", value=None)
        if from_date_value:
            message_limit = 20_000_000
        else:
            st.info("Выберите дату")
    elif scrape_mode == "from_start":
        message_limit = st.number_input("Максимум сообщений с канала:", min_value=1000, max_value=50_000_000, value=100_000, step=10000)
    elif scrape_mode == "by_words":
        word_limit_value = st.number_input("Последних слов (примерно):", min_value=1000, max_value=50_000_000, value=100_000, step=10000)
        message_limit = 20_000_000

    # Место под прогресс и лог
    progress_placeholder = st.empty()
    log_placeholder = st.empty()

    if start_button:
        if not credentials_ok:
            st.warning("⚠️ Введите API-ключи и войдите в Telegram в боковой панели.")
        elif not valid_links:
            st.warning("⚠️ Введите хотя бы одну корректную ссылку на канал.")
        elif scrape_mode == "by_date" and not from_date_value:
            st.warning("⚠️ Выберите дату «с какой выгружать».")
        else:
            st.session_state.scrape_log_lines = []
            progress_bar = progress_placeholder.progress(0)
            status_text = log_placeholder.empty()

            def log_line(msg: str):
                st.session_state.scrape_log_lines.append(msg)
                status_text.text(msg)

            options = {
                "mode": scrape_mode,
                "message_limit": message_limit,
                "from_date": from_date_value,
                "word_limit": word_limit_value,
            }

            with st.spinner("Собираем сообщения..."):
                async def run_scraping_async():
                    return await run_scraping(
                        api_id_input,
                        api_hash_input,
                        effective_session,
                        valid_links,
                        options,
                        progress_bar,
                        log_line,
                    )

                all_results = asyncio.run(run_scraping_async())

            if all_results:
                st.session_state.scrape_results = all_results
                progress_placeholder.progress(1.0)
                log_placeholder.markdown("\n".join(f"`{line}`" for line in st.session_state.scrape_log_lines[-15:]))
                st.success(f"✅ Готово! Собрано {sum(r['total_messages'] for r in all_results)} сообщений. Перейдите на вкладку «Результаты и Анализ».")
                st.rerun()

# ——— Вкладка «Результаты и Анализ» ———
with tab_results:
    res = st.session_state.scrape_results
    if res is None:
        st.info("Здесь появится предпросмотр после запуска скрапинга на вкладке «Конфигурация».")
    else:
        st.markdown("<div class='card'><h3>📊 Предпросмотр данных</h3></div>", unsafe_allow_html=True)
        # Собираем первые 10 сообщений из всех каналов для таблицы
        rows = []
        for ch in res:
            for msg in (ch.get("messages") or [])[:10]:
                rows.append({
                    "Канал": ch.get("channel_title") or ch.get("channel", ""),
                    "ID сообщения": msg.get("id"),
                    "Дата": msg.get("date", "")[:19] if msg.get("date") else "",
                    "Текст": (msg.get("text") or "")[:120] + ("…" if len((msg.get("text") or "")) > 120 else ""),
                    "Просмотры": msg.get("views"),
                    "Пересылки": msg.get("forwards"),
                    "Медиа": msg.get("media_type", "none"),
                    "Ссылка": msg.get("url", ""),
                })
        if rows:
            df_preview = pd.DataFrame(rows)
            st.dataframe(df_preview, use_container_width=True, height=320)
        else:
            st.caption("Нет сообщений для предпросмотра.")

        st.markdown("<div class='card'><h3>📥 Скачать выгрузку</h3></div>", unsafe_allow_html=True)
        final_result = {
            "scraped_at": datetime.now().isoformat(),
            "total_channels": len(res),
            "total_messages": sum(r["total_messages"] for r in res),
            "channels": res,
        }
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        flat_rows = []
        for ch in res:
            for msg in (ch.get("messages") or []):
                flat_rows.append({
                    "channel": ch.get("channel", ""),
                    "channel_title": ch.get("channel_title", ""),
                    "message_id": msg.get("id"),
                    "date": msg.get("date"),
                    "text": msg.get("text") or "",
                    "views": msg.get("views"),
                    "forwards": msg.get("forwards"),
                    "media_type": msg.get("media_type", ""),
                    "url": msg.get("url", ""),
                })
        df_export = pd.DataFrame(flat_rows)

        col1, col2, col3 = st.columns(3)
        with col1:
            json_string = json.dumps(final_result, ensure_ascii=False, indent=2)
            st.download_button(
                label="📥 JSON",
                data=json_string,
                file_name=f"telegram_scrape_{ts}.json",
                mime="application/json",
                use_container_width=True,
                key="dl_json",
            )
        with col2:
            buf_csv = io.StringIO()
            df_export.to_csv(buf_csv, index=False, encoding="utf-8-sig")
            st.download_button(
                label="📥 CSV",
                data=buf_csv.getvalue(),
                file_name=f"telegram_scrape_{ts}.csv",
                mime="text/csv",
                use_container_width=True,
                key="dl_csv",
            )
        with col3:
            buf_xlsx = io.BytesIO()
            with pd.ExcelWriter(buf_xlsx, engine="openpyxl") as w:
                df_export.to_excel(w, index=False, sheet_name="Messages")
            st.download_button(
                label="📥 Excel",
                data=buf_xlsx.getvalue(),
                file_name=f"telegram_scrape_{ts}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="dl_excel",
            )

# ——— Вспомогательные функции (парсинг, скрапинг) ———
def get_media_type(message):
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
    return "none"


def parse_reactions(message):
    reactions = []
    if message.reactions and hasattr(message.reactions, "results") and message.reactions.results:
        for reaction in message.reactions.results:
            try:
                if reaction.reaction:
                    emoji = getattr(reaction.reaction, "emoticon", None) or str(reaction.reaction)
                    count = getattr(reaction, "count", 0) or 0
                    if emoji:
                        reactions.append({"emoji": emoji, "count": count})
            except Exception:
                continue
    return reactions


def build_message_url(channel_username: str, message_id: int) -> str:
    username = channel_username.lstrip("@")
    return f"https://t.me/{username}/{message_id}"


def normalize_channel_link(link: str) -> str:
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
    try:
        channel_link = normalize_channel_link(channel_link)
        entity = await client.get_entity(channel_link)
        channel_username = entity.username if hasattr(entity, "username") else channel_link
        mode = options.get("mode", "by_count")
        message_limit = options.get("message_limit", 1000)
        from_date = options.get("from_date")
        word_limit = options.get("word_limit", 100_000)
        messages_data = []
        total_words = 0
        stop_reason = None

        async for message in client.iter_messages(entity, limit=message_limit):
            try:
                message_date = message.date
                if mode == "by_date" and from_date and message_date:
                    msg_date = message_date.date() if hasattr(message_date, "date") else message_date
                    if msg_date < from_date:
                        stop_reason = "date"
                        break
                text = message.text or ""
                if mode == "by_words":
                    total_words += len(text.split())
                    if total_words >= word_limit:
                        stop_reason = "words"
                date_iso = message_date.isoformat() if message_date else None
                date_unixtime = int(message_date.timestamp()) if message_date else None
                messages_data.append({
                    "id": message.id,
                    "date": date_iso,
                    "date_unixtime": date_unixtime,
                    "text": text,
                    "views": getattr(message, "views", None),
                    "forwards": getattr(message, "forwards", None),
                    "media_type": get_media_type(message),
                    "reactions": parse_reactions(message),
                    "reply_to_msg_id": getattr(message, "reply_to_msg_id", None),
                    "url": build_message_url(channel_username, message.id),
                })
                if mode == "by_words" and stop_reason == "words":
                    break
            except FloodWaitError as e:
                await asyncio.sleep(e.seconds)
                continue
            except Exception:
                continue

        return {
            "channel": channel_link,
            "channel_id": entity.id,
            "channel_title": getattr(entity, "title", None),
            "messages": messages_data,
            "total_messages": len(messages_data),
            "total_words": total_words if mode == "by_words" else None,
            "stop_reason": stop_reason,
        }
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds)
        return None
    except Exception:
        return None


async def run_scraping(api_id, api_hash, session_string, links, options, progress_bar, log_callback):
    all_results = []
    client = None
    try:
        api_id = int(api_id.strip())
        client = TelegramClient(
            StringSession(session_string.strip()),
            api_id,
            api_hash.strip(),
        )
        await client.connect()
        if not await client.is_user_authorized():
            log_callback("❌ Сессия не авторизована.")
            return None
        for idx, link in enumerate(links):
            log_callback(f"🔄 Обработка {idx + 1}/{len(links)}: {link}")
            progress_bar.progress((idx) / len(links))
            result = await scrape_channel(client, link, options)
            if result:
                all_results.append(result)
                log_callback(f"✅ {result['total_messages']} сообщений: {link}")
        progress_bar.progress(1.0)
        log_callback(f"✅ Готово. Каналов: {len(all_results)}.")
        return all_results
    except ValueError:
        log_callback("❌ API_ID должен быть числом.")
        return None
    except Exception as e:
        log_callback(f"❌ Ошибка: {e}")
        return None
    finally:
        if client:
            await client.disconnect()


st.markdown("---")
st.caption("**Telegram Cloud Scraper Pro** — Streamlit & Telethon")
