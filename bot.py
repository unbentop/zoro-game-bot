import requests
import random
import os
from telegram import Update, InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode

# Токен из переменной окружения Render
TOKEN = os.environ.get("BOT_TOKEN")
JSON_URL = "https://zoro-game.store/data/ZObase.json"

# Кеш
games_cache = None

def load_games():
    global games_cache
    if games_cache is not None:
        return games_cache
    try:
        response = requests.get(JSON_URL)
        if response.status_code == 200:
            games_cache = response.json()
            return games_cache
        return []
    except Exception as e:
        print(f"Ошибка загрузки: {e}")
        return []

def fix_url(url):
    if not url or url == "ban" or url == "none":
        return None
    if not url.startswith("http"):
        return f"https://zoro-game.store{url}"
    return url

def find_game_by_id(game_id):
    games = load_games()
    for game in games:
        if str(game.get("id")) == str(game_id):
            return game
    return None

def search_games(query):
    games = load_games()
    results = []
    query_lower = query.lower()
    for game in games:
        title = game.get("title", "").lower()
        if query_lower in title:
            results.append(game)
    return results

def get_games_by_genre(genre):
    games = load_games()
    results = []
    genre_lower = genre.lower()
    for game in games:
        tags = game.get("#", "").lower()
        if genre_lower in tags:
            results.append(game)
    return results

def get_top_games(limit=10):
    games = load_games()
    sorted_games = sorted(
        games,
        key=lambda g: int(g.get("ИКИ", 0)) if str(g.get("ИКИ", "0")).replace("-", "").isdigit() else 0,
        reverse=True
    )
    return sorted_games[:limit]

def get_random_game():
    games = load_games()
    if not games:
        return None
    return random.choice(games)

def build_game_info_text(game):
    title = game.get("title", "Без названия")
    descr = game.get("descr", "Нет описания")
    developer = game.get("DEVELOPER", "Неизвестен")
    year = game.get("year of release", "Неизвестно")
    version = game.get("UPDATES_Vers", "Неизвестно")
    price = game.get("price", "0")

    if str(price) == "0" or price == 0:
        price_text = "Бесплатно"
    elif str(price) == "ban":
        price_text = "🚫 Заблокировано"
    else:
        price_text = f"{price} ₽"

    iki = game.get("ИКИ", 0)
    tags = game.get("#", "—")

    if len(descr) > 800:
        descr = descr[:800] + "..."

    return (
        f"🎮 *{title}*\n\n"
        f"🏷 Жанр: {tags}\n"
        f"📅 Год: {year}\n"
        f"👨‍💻 Разработчик: {developer}\n"
        f"💰 Цена: {price_text}\n"
        f"🔢 Версия: {version}\n"
        f"⭐ ИКИ: {iki}\n\n"
        f"📝 *Описание:*\n{descr}"
    )

def build_game_keyboard(game):
    game_id = game.get("id", "")
    keyboard = []
    site_url = f"https://zoro-game.store/pages/game/game.html?id={game_id}"
    keyboard.append([InlineKeyboardButton("📥 Скачать", url=site_url)])
    row2 = [
        InlineKeyboardButton("📸 Скриншоты", callback_data=f"show_screenshots_{game_id}"),
        InlineKeyboardButton("👨‍💻 Разработчик", callback_data=f"show_developer_{game_id}")
    ]
    keyboard.append(row2)
    return InlineKeyboardMarkup(keyboard)

def build_back_keyboard(game_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Назад", callback_data=f"back_to_game_{game_id}")]
    ])

def build_screenshots_keyboard(game_id, screenshots, current_page):
    total = len(screenshots)
    keyboard = []
    row = []
    if total > 1:
        if current_page > 0:
            row.append(InlineKeyboardButton("◀️", callback_data=f"scr_page_{game_id}_{current_page - 1}"))
        row.append(InlineKeyboardButton(f"{current_page + 1}/{total}", callback_data="noop"))
        if current_page < total - 1:
            row.append(InlineKeyboardButton("▶️", callback_data=f"scr_page_{game_id}_{current_page + 1}"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("⬅️ Назад к игре", callback_data=f"back_to_game_{game_id}")])
    return InlineKeyboardMarkup(keyboard)

# ============ КОМАНДЫ ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Привет! 🎮\n\n"
        "*Команды бота:*\n"
        "/zgsgameid `<id>` — инфо об игре\n"
        "/search `<название>` — поиск по названию\n"
        "/genre `<жанр>` — поиск по жанру\n"
        "/top — топ игр по ИКИ\n"
        "/random — случайная игра\n"
        "/allgames — все игры списком"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

async def game_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Укажи ID игры. Например: /zgsgameid 1")
        return
    game_id = context.args[0]
    game = find_game_by_id(game_id)
    if game is None:
        await update.message.reply_text(f"❌ Игра с ID {game_id} не найдена.")
        return
    icon = fix_url(game.get("IconGame", ""))
    caption = build_game_info_text(game)
    keyboard = build_game_keyboard(game)
    if icon:
        try:
            await update.message.reply_photo(photo=icon, caption=caption, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
        except:
            await update.message.reply_text(caption, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    else:
        await update.message.reply_text(caption, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

async def search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Укажи название. Например: /search куб")
        return
    query = " ".join(context.args)
    results = search_games(query)
    if not results:
        await update.message.reply_text(f"🔍 По запросу *{query}* ничего не найдено.", parse_mode=ParseMode.MARKDOWN)
        return
    message = f"🔍 Найдено *{len(results)}* игр:\n\n"
    for game in results[:20]:
        gid = game.get("id", "?")
        title = game.get("title", "Без названия")
        dev = game.get("DEVELOPER", "—")
        message += f"• `{gid}` — *{title}* ({dev})\n"
    if len(results) > 20:
        message += f"\n⚠️ Показано 20 из {len(results)}."
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

async def genre_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        genres = set()
        for g in load_games():
            tags = g.get("#", "")
            if tags:
                for t in tags.split(","):
                    t = t.strip()
                    if t:
                        genres.add(t)
        await update.message.reply_text(
            f"🏷 *Доступные жанры:*\n" + "\n".join(sorted(genres)) + "\n\nИспользуй: /genre `<жанр>`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    genre = " ".join(context.args)
    results = get_games_by_genre(genre)
    if not results:
        await update.message.reply_text(f"🔍 Игры в жанре *{genre}* не найдены.", parse_mode=ParseMode.MARKDOWN)
        return
    message = f"🏷 Жанр *{genre}* — *{len(results)}* игр:\n\n"
    for game in results[:20]:
        gid = game.get("id", "?")
        title = game.get("title", "Без названия")
        message += f"• `{gid}` — *{title}*\n"
    if len(results) > 20:
        message += f"\n⚠️ Показано 20 из {len(results)}."
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

async def top_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top_games = get_top_games(10)
    if not top_games:
        await update.message.reply_text("❌ Нет данных.")
        return
    message = "🏆 *ТОП-10 по ИКИ:*\n\n"
    for i, game in enumerate(top_games, 1):
        title = game.get("title", "Без названия")
        iki = game.get("ИКИ", 0)
        gid = game.get("id", "?")
        message += f"{i}. ⭐{iki} — *{title}* (`/zgsgameid {gid}`)\n"
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

async def random_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    game = get_random_game()
    if game is None:
        await update.message.reply_text("❌ Не удалось загрузить игры.")
        return
    icon = fix_url(game.get("IconGame", ""))
    caption = build_game_info_text(game)
    keyboard = build_game_keyboard(game)
    if icon:
        try:
            await update.message.reply_photo(photo=icon, caption=caption, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
        except:
            await update.message.reply_text(caption, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    else:
        await update.message.reply_text(caption, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

async def allgames_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    games = load_games()
    if not games:
        await update.message.reply_text("❌ Не удалось загрузить список.")
        return
    message = f"📋 *Все игры ({len(games)}):*\n\n"
    for game in games:
        gid = game.get("id", "?")
        title = game.get("title", "Без названия")
        if len(message) > 3800:
            message += "...\n⚠️ Список обрезан."
            break
        message += f"• `{gid}` — *{title}*\n"
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

# ============ КНОПКИ ============

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("show_screenshots_"):
        game_id = data.replace("show_screenshots_", "")
        game = find_game_by_id(game_id)
        if not game:
            return
        screenshots = []
        for i in range(1, 9):
            img_url = fix_url(game.get(f"imag_{i}", ""))
            if img_url:
                screenshots.append(img_url)
        if screenshots:
            caption = f"📸 *Скриншот 1 из {len(screenshots)}*"
            await query.edit_message_media(
                media=InputMediaPhoto(media=screenshots[0], caption=caption, parse_mode=ParseMode.MARKDOWN),
                reply_markup=build_screenshots_keyboard(game_id, screenshots, 0)
            )
        else:
            await query.edit_message_caption(
                caption="📸 *Скриншотов нет*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=build_back_keyboard(game_id)
            )

    elif data.startswith("scr_page_"):
        parts = data.replace("scr_page_", "").split("_")
        game_id = parts[0]
        page = int(parts[1])
        game = find_game_by_id(game_id)
        if not game:
            return
        screenshots = []
        for i in range(1, 9):
            img_url = fix_url(game.get(f"imag_{i}", ""))
            if img_url:
                screenshots.append(img_url)
        caption = f"📸 *Скриншот {page + 1} из {len(screenshots)}*"
        try:
            await query.edit_message_media(
                media=InputMediaPhoto(media=screenshots[page], caption=caption, parse_mode=ParseMode.MARKDOWN),
                reply_markup=build_screenshots_keyboard(game_id, screenshots, page)
            )
        except:
            pass

    elif data.startswith("show_developer_"):
        game_id = data.replace("show_developer_", "")
        game = find_game_by_id(game_id)
        if not game:
            return
        developer = game.get("DEVELOPER", "Неизвестен")
        year = game.get("year of release", "Неизвестно")
        title = game.get("title", "Без названия")
        new_caption = (
            f"🎮 *{title}*\n\n"
            f"👨‍💻 *Разработчик:* {developer}\n"
            f"📅 *Год выпуска:* {year}"
        )
        await query.edit_message_caption(
            caption=new_caption,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=build_back_keyboard(game_id)
        )

    elif data.startswith("back_to_game_"):
        game_id = data.replace("back_to_game_", "")
        game = find_game_by_id(game_id)
        if not game:
            return
        icon = fix_url(game.get("IconGame", ""))
        caption = build_game_info_text(game)
        keyboard = build_game_keyboard(game)
        if icon:
            try:
                await query.edit_message_media(
                    media=InputMediaPhoto(media=icon, caption=caption, parse_mode=ParseMode.MARKDOWN),
                    reply_markup=keyboard
                )
            except:
                await query.edit_message_caption(
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=keyboard
                )
        else:
            await query.edit_message_caption(
                caption=caption,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard
            )

    elif data == "noop":
        pass

# ============ ЗАПУСК ============

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("zgsgameid", game_info))
    app.add_handler(CommandHandler("search", search_cmd))
    app.add_handler(CommandHandler("genre", genre_cmd))
    app.add_handler(CommandHandler("top", top_cmd))
    app.add_handler(CommandHandler("random", random_cmd))
    app.add_handler(CommandHandler("allgames", allgames_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
