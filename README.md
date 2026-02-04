# ☁️ Telegram Cloud Scraper Pro

**Многопользовательское** Streamlit-приложение для парсинга Telegram каналов. Каждый пользователь вводит свои API-ключи в интерфейсе — переменные окружения на сервере не нужны.

---

## 🚀 Инструкция: Как это запустить (От А до Я)

### 1️⃣ Получение "Вечного ключа" (Делаем 1 раз локально)

**Заполните `.env`** (если создали) или просто держите API ID/Hash под рукой.

В терминале Cursor запустите генератор:

```bash
python generate_session.py
```

**Что произойдет:**
1. Введите свои данные (`API_ID` и `API_HASH`)
2. Telegram пришлет код подтверждения в приложение Telegram
3. Введите код подтверждения в терминал
4. Скрипт выдаст длинную строку (набор букв и цифр)

**⚠️ СКОПИРУЙТЕ ЕЁ!** Это ваш пропуск в облако.

---

### 2️⃣ Проверка локально

**Запустите сайт:**

```bash
streamlit run app.py
```

**Проверка:**
1. Откройте браузер (обычно `http://localhost:8501`)
2. В **боковой панели слева** введите свои **API_ID**, **API_HASH** и **TELEGRAM_SESSION** (ключи нигде не сохраняются, только в вашей сессии)
3. Раскройте плашку **"ℹ️ How to get API Keys?"** — там инструкция, как получить ключи
4. Вставьте ссылку на канал в поле "Channel Links"
5. Нажмите **"🚀 Start Scraping"**
6. Если JSON скачался — всё работает ✅

---

### 3️⃣ Заливка на Railway (Cloud)

**Шаг 1: Залейте проект на GitHub**
- Создайте репозиторий на GitHub
- Закоммитьте все файлы (кроме `.env` — он в `.gitignore`)
- Запушьте код

**Шаг 2: Создайте проект в Railway**
1. Зайдите на [railway.app](https://railway.app)
2. Создайте аккаунт (можно через GitHub)
3. Нажмите **"New Project"**
4. Выберите **"Deploy from GitHub repo"**
5. Выберите ваш репозиторий

**Шаг 3: Переменные окружения не нужны**
- Приложение **многопользовательское**: каждый пользователь вводит свои **API_ID**, **API_HASH** и **TELEGRAM_SESSION** прямо в веб-интерфейсе (в боковой панели).
- На Railway **не нужно** добавлять эти переменные — просто деплойте проект.

**Шаг 4: Дождитесь деплоя**
- Railway сам запустит сайт
- Обычно это занимает 1-2 минуты
- Статус деплоя виден в логах

**Готово! 🎉**

По ссылке Railway могут заходить **любые пользователи**. Каждый один раз получает свои ключи (шаг 1️⃣), затем вводит их в боковую панель и скрапит каналы. Ключи не хранятся на сервере.

**Преимущества многопользовательского режима:**
- ✅ Один деплой — много пользователей
- ✅ API вводит каждый сам, ключи не нужны на Railway
- ✅ Доступ по ссылке с любого устройства
- ✅ Сессия Telegram (TELEGRAM_SESSION) вводится один раз и действует долго

---

## 📋 Deployment Guide (English)

### 1. Local Setup

#### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

#### Step 2: Get API Credentials

1. Go to [my.telegram.org](https://my.telegram.org) and log in with your phone number
2. Click **"API development tools"**
3. Fill in the form:
   - **App title:** `Scraper`
   - **Short name:** `scraper`
   - Other fields can be filled with dummy data
4. Copy your **App api_id** and **App api_hash**

#### Step 3: Generate Session String

Run the session generator script:

```bash
python generate_session.py
```

**Follow the prompts:**
1. Enter your `API_ID` when prompted
2. Enter your `API_HASH` when prompted
3. You'll receive a code in Telegram - enter it when prompted
4. **IMPORTANT:** Copy the generated session string that appears in the console

The session string will look something like:
```
1BVtsOHwBu5...
```

**⚠️ Save this string securely!** You'll need it for the `TELEGRAM_SESSION` environment variable.

#### Step 4: Test Locally (Optional)

Run the app locally:

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`. Enter your **API_ID**, **API_HASH**, and **TELEGRAM_SESSION** in the sidebar — they are not stored on the server.

---

### 2. Railway Deployment

#### Step 1: Connect GitHub Repository

1. Create an account on [Railway](https://railway.app) if you haven't already
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Authorize Railway to access your GitHub account
5. Select your repository containing this project

#### Step 2: No Environment Variables Needed

This app is **multi-user**: each user enters their own **API_ID**, **API_HASH**, and **TELEGRAM_SESSION** in the web interface (sidebar). You do **not** need to add these variables in Railway — just deploy. Railway will set `PORT` automatically.

#### Step 3: Deploy

1. Railway will automatically detect the `Procfile` and start deploying
2. Wait for the deployment to complete (usually 1-2 minutes)
3. Your app will be live at the Railway-provided URL

#### Step 4: Access Your App

- Click on your service in Railway dashboard
- Click **"Settings"** → **"Generate Domain"** to get a public URL
- Or use the default Railway domain

---

## 🔐 How It Works: Multi-User & 24/7

**Multi-user:** Each visitor enters their own API keys in the sidebar. Keys are not stored on the server. **Key advantage:** Once a user has generated their session string with `generate_session.py`, they can use the app **24/7 without re-entering the phone code**.

### Why This Works:

1. **Session String = Permanent Authentication**
   - The `TELEGRAM_SESSION` string contains your authenticated session
   - It's like a "permanent login token" that doesn't expire
   - No need to re-authenticate with phone codes

2. **Railway Keeps It Running**
   - Railway runs your app continuously
   - The session string is stored securely in environment variables
   - Your app stays authenticated as long as Railway is running

3. **No Manual Intervention Required**
   - Once deployed, the app works autonomously
   - You can scrape channels anytime via the web interface
   - No need to be near your phone or enter codes

**⚠️ Important Notes:**
- Keep your `TELEGRAM_SESSION` string secure - treat it like a password
- If you lose the session string, you'll need to regenerate it
- The session string is tied to your Telegram account

---

## 📝 Features

- ✅ **Mass Channel Scraping** - Scrape multiple channels at once
- ✅ **Telegram Export Format** - Data exported in standard Telegram format
- ✅ **Rich Message Data** - Includes views, forwards, reactions, media type
- ✅ **Public Message URLs** - Direct links to each message
- ✅ **JSON Export** - Download results as JSON file
- ✅ **Modern UI** - Clean Streamlit interface
- ✅ **24/7 Operation** - Runs continuously on Railway

## 🔧 Technologies

- **Streamlit** - Web framework for Python apps
- **Telethon** - Telegram API client library
- **Railway** - Cloud deployment platform

## 📁 Project Structure

```
railway-scraper/
├── .env                  # (Don't commit!) Local environment variables
├── .gitignore            # Excludes .env and *.session files
├── requirements.txt      # Python dependencies
├── generate_session.py   # Session string generator
├── app.py                # Main Streamlit application
├── Procfile              # Railway deployment command
└── README.md             # This file
```

## ⚠️ Security Notes

- **NEVER commit `.env` file** - It's already in `.gitignore`
- **NEVER commit `*.session` files** - They're also in `.gitignore`
- **Keep `TELEGRAM_SESSION` secure** - Don't share it publicly
- **Don't expose API keys** - Use Railway environment variables

## 🐛 Troubleshooting

### "Client is not authorized"
- Regenerate your session string using `generate_session.py`
- Make sure `TELEGRAM_SESSION` is correctly set in Railway

### "Missing API Keys"
- Verify all three environment variables are set in Railway
- Check for typos in variable names (case-sensitive)

### App won't start on Railway
- Check Railway logs for error messages
- Verify `Procfile` exists and is correct
- Ensure `requirements.txt` has all dependencies

---

**Made with ❤️ for Telegram scraping**
