import os
import logging
import sys
import pypandoc
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
from threading import Timer
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
)

from gpt_score import generate_report, pdf_to_markdown_str, docx_to_markdown  # Импорт функции отчета

load_dotenv()
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Главное меню
MAIN_KEYBOARD = [
    ["📄 Загрузить вакансию"],
    ["📝 Загрузить резюме"],
    ["📊 Получить отчёт по кандидатам"],
    ["📂 Посмотреть файлы"]
]
MARKUP = ReplyKeyboardMarkup(MAIN_KEYBOARD, resize_keyboard=True)

# Контекст пользовательских данных:
# context.user_data['vacancy'] = путь к PDF вакансии
# context.user_data['files'] = список:
#    [{"file_id":..., "file_name":..., "type":..., "file_path":...}, ...]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я помогу подобрать лучшего кандидата.\n"
        "Сначала пришлите вакансию (PDF, DOCX или текстом),\n"
        "затем добавьте резюме кандидатов.\n"
        "Нажмите одну из кнопок ниже:",
        reply_markup=MARKUP
    )

# --- 1) Plain-text вход для вакансии ---
async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("handle_text_input")
    expect = context.user_data.get('expect')
    logger.info(expect)
    if expect == 'vacancy':
        logger.info("handle_text_input - vacancy")
        md = update.message.text.strip()
        context.user_data['vacancy_md'] = md
        await update.message.reply_text("✅ Текст вакансии сохранён.", reply_markup=MARKUP)
        context.user_data['expect'] = None
        return
    return

# --- 2) Общий текст-хендлер для меню ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    ud = context.user_data

    if text == "📄 Загрузить вакансию":
        ud['expect'] = 'vacancy'
        return await update.message.reply_text(
            "📄 Пришлите вакансию PDF, DOCX или текстом.", reply_markup=MARKUP
        )

    if text == "📝 Загрузить резюме":
        ud['expect'] = 'resume'
        return await update.message.reply_text(
            "📝 Пришлите PDF резюме.", reply_markup=MARKUP
        )

    if text == "📂 Посмотреть файлы":
        vacancy_exists = 'vacancy_md' in ud
        files = ud.get('files', [])
        if not vacancy_exists and not files:
            await update.message.reply_text("У вас ещё нет загруженных данных.", reply_markup=MARKUP)
            return

        # Показываем кнопку для текста вакансии, если он есть
        if vacancy_exists:
            lines = ud['vacancy_md'].splitlines()
            snippet = "\n".join(lines[:3])
            await update.message.reply_text(f"✏️ Описание вакансии :\n{snippet}...", reply_markup=MARKUP)

        # Показываем загруженные резюме
        resume_items = [(i,f) for i,f in enumerate(files) if f.get('type')=='resume']
        if resume_items:
            kb_res = []
            for i,f in resume_items:
                kb_res.append([
                    InlineKeyboardButton(f"📝 {f['file_name']}", callback_data=f"SHOW|{i}"),
                    InlineKeyboardButton("🗑️", callback_data=f"DEL|{i}")
                ])
            await update.message.reply_text("Резюме:", reply_markup=InlineKeyboardMarkup(kb_res))

        await update.message.reply_text("Что дальше?", reply_markup=MARKUP)
        return

    if text == "📊 Получить отчёт по кандидатам":
        ud = context.user_data
        # Предпочитаем vacancy_md, иначе vacancy_pdf
        vacancy_md = ud.get('vacancy_md')
        if not vacancy_md:
            await update.message.reply_text("Сначала введите описание вакансии!", reply_markup=MARKUP)
            return

        resume_paths = [f['file_path'] for f in ud.get('files', []) if f.get('type')=='resume']
        if not resume_paths:
            await update.message.reply_text("Нет загруженных резюме.", reply_markup=MARKUP)
            return

        await update.message.reply_text("🔎 Анализирую…", reply_markup=MARKUP)
        mai_weights = {
            "jobPreferences":0.10,
            "experience":0.25,
            "education":0.15, 
            "courses":0.10,
            "skills":0.20,  
            "languages":0.10,
            "additional":0.10
        }
        # generate_report пока принимает PDF вакансии, но можно адаптировать
        
        report = generate_report(
            vacancy_md=vacancy_md,
            resume_pdfs=resume_paths,
            mai_weights=mai_weights,
            alpha=0.5
        )

        lines = ["🔍 Рейтинг резюме:"]

        for item in report:
            name = item["name"]
            pct  = item["score"] * 100
            issues = item.get("ontologyIssues", [])
            
            if not issues:
                # нет нарушений онтологии
                mark = "✅"
                note = ""
            else:
                # есть нарушения, выводим warning и кратко их описываем
                mark = "⚠️"
                note = f" (Предупреждение: {', '.join(issues)})"
            
            lines.append(f"{mark} {name}: {pct:.1f}%{note}")

        return await update.message.reply_text("\n".join(lines), reply_markup=MARKUP)


    # всё остальное
    await update.message.reply_text("Не понял команду.", reply_markup=MARKUP)

# --- Групповой summary для резюме ---
def send_group_summary(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    g = job.context
    ud = context.dispatcher.user_data[g['user_id']]
    files = ud.get('files', [])
    group_files = [
        f['file_name'] for f in files
        if f.get('media_group_id')==g['group_id']
    ]
    if group_files:
        context.bot.send_message(
            chat_id=g['chat_id'],
            text="✅ Резюме сохранены: " + ", ".join(group_files),
            reply_markup=MARKUP
        )
    ud['media_groups'].pop(g['group_id'], None)

# --- Документ (PDF / DOCX) & медиа-группа резюме ---
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    expect = (context.user_data.get('expect') or '').lower()
    msg = update.message
    doc = msg.document

    context.user_data.setdefault('files', [])
    context.user_data.setdefault('media_groups', {})

    os.makedirs("downloads", exist_ok=True)
    fp = os.path.join("downloads", f"{msg.from_user.id}_{doc.file_name}")
    
    file = await context.bot.get_file(doc.file_id)
    await file.download_to_drive(fp)

    entry = {
        "file_id": doc.file_id,
        "file_name": doc.file_name,
        "type": expect,
        "file_path": fp,
        "media_group_id": msg.media_group_id
    }
    context.user_data['files'].append(entry)

    # вакансия
    if expect=='vacancy':
        ext = doc.file_name.lower().rsplit(".",1)[-1]
        if ext=="pdf":
            md = pdf_to_markdown_str(fp)
            context.user_data['vacancy_md']=md
            await update.message.reply_text("✅ PDF вакансии сохранён.", reply_markup=MARKUP)
        elif ext in ("doc","docx"):
            md = docx_to_markdown(fp)
            context.user_data['vacancy_md']=md
            await update.message.reply_text("✅ DOCX вакансии сохранён и конвертирован.", reply_markup=MARKUP)
        else:
            await update.message.reply_text("❌ Неподдерживаемый формат.", reply_markup=MARKUP)
        context.user_data['expect']=None
        return

    # резюме
    if expect=='resume':
        gid = msg.media_group_id
        if gid:
            context.user_data['media_groups'].setdefault(gid, []).append(entry)
            await update.message.reply_text("✅ Резюме сохранено.", reply_markup=MARKUP)
        else:
            await update.message.reply_text("✅ Резюме сохранено.", reply_markup=MARKUP)
            context.user_data['expect']=None
        return

    # всё остальное
    await update.message.reply_text("Сначала нажмите нужную кнопку.", reply_markup=MARKUP)
    context.user_data['expect']=None

# --- Показать / Удалить файл ---
async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    action, idx = query.data.split("|")
    idx = int(idx)
    files = context.user_data.get('files', [])
    if action=="SHOW" and 0<=idx<len(files):
        f=files[idx]
        await context.bot.send_document(query.message.chat.id, f['file_id'], filename=f['file_name'])
    if action=="DEL" and 0<=idx<len(files):
        rem=files.pop(idx)
        try: os.remove(rem['file_path'])
        except: pass
        await context.bot.send_message(query.message.chat.id, f"🗑️ Удалён {rem['file_name']}")
    await query.answer()

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.Regex(r'^(📄|📝|📊|📂)'), handle_text_input), group=0)
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.Regex(r'^(📄|📝|📊|📂)'), handle_text))
    app.add_handler(CallbackQueryHandler(callback_query_handler, pattern=r'^(SHOW|DEL)\|\d+$'))

    app.run_polling()
    logger.info("Bot started")

if __name__=="__main__":
    main()