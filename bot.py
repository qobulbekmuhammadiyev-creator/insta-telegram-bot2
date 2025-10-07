import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi! Iltimos, .env faylga yoki Railway Variables bo‘limiga qo‘shing.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
DB_PATH = "contracts.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_number INTEGER,
            full_name TEXT,
            bank_name TEXT,
            created_at TEXT
        );
        """)
        await db.commit()

async def create_contract(full_name: str, bank_name: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("BEGIN IMMEDIATE;")
        cursor = await db.execute("SELECT MAX(contract_number) FROM contracts;")
        row = await cursor.fetchone()
        last = row[0] if row and row[0] is not None else 4139
        next_num = last + 1
        now = datetime.utcnow().isoformat()
        await db.execute(
            "INSERT INTO contracts (contract_number, full_name, bank_name, created_at) VALUES (?, ?, ?, ?);",
            (next_num, full_name, bank_name, now)
        )
        await db.commit()
        return next_num

async def search_contract(query: str):
    async with aiosqlite.connect(DB_PATH) as db:
        if query.isdigit():
            cursor = await db.execute("SELECT * FROM contracts WHERE contract_number = ?;", (int(query),))
        else:
            cursor = await db.execute("SELECT * FROM contracts WHERE full_name LIKE ?;", (f"%{query}%",))
        return await cursor.fetchall()

class Form(StatesGroup):
    full_name = State()
    bank_name = State()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Assalomu alaykum! 👋\n"
        "Bu bot shartnomalarga ketma-ket raqam beradi.\n\n"
        "Buyruqlar:\n"
        "/new - Yangi shartnoma yaratish\n"
        "/search - Qidirish (F.I.Sh yoki raqam bo‘yicha)\n"
        "/list - Oxirgi 5 ta shartnomani ko‘rish"
    )

@dp.message(Command("new"))
async def cmd_new(message: types.Message, state: FSMContext):
    await message.answer("Iltimos, F.I.Sh kiriting:")
    await state.set_state(Form.full_name)

@dp.message(Form.full_name)
async def get_full_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await message.answer("Endi bank nomini kiriting:")
    await state.set_state(Form.bank_name)

@dp.message(Form.bank_name)
async def get_bank_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    full_name = data["full_name"]
    bank_name = message.text
    num = await create_contract(full_name, bank_name)
    await message.answer(f"✅ Shartnoma yaratildi!\n\nRaqam: {num}\n👤 F.I.Sh: {full_name}\n🏦 Bank: {bank_name}")
    await state.clear()

@dp.message(Command("search"))
async def cmd_search(message: types.Message):
    await message.answer("Qidirish uchun F.I.Sh yoki shartnoma raqamini kiriting:")

@dp.message(lambda m: not m.text.startswith("/"))
async def handle_search(message: types.Message):
    query = message.text.strip()
    results = await search_contract(query)
    if not results:
        await message.answer("Hech narsa topilmadi 😕")
        return
    text = ""
    for r in results:
        text += f"📄 Raqam: {r[1]}\n👤 F.I.Sh: {r[2]}\n🏦 Bank: {r[3]}\n🕒 Sana: {r[4][:10]}\n\n"
    await message.answer(text)

@dp.message(Command("list"))
async def cmd_list(message: types.Message):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT * FROM contracts ORDER BY id DESC LIMIT 5;")
        rows = await cursor.fetchall()
    if not rows:
        await message.answer("Hozircha hech qanday shartnoma yo‘q.")
        return
    text = "🗂 Oxirgi 5 ta shartnoma:\n\n"
    for r in rows:
        text += f"{r[1]} — {r[2]} ({r[3]})\n"
    await message.answer(text)

async def main():
    print("✅ Bot ishga tushdi...")
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
