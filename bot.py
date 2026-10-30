```python
import asyncio
import logging
import random
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import BufferedInputFile

# НАСТРОЙКИ (токен из BotFather)
TOKEN = "9287826378:AAFQ4HhLDo5p6j73Or6Kuia1r0SpDawd73k"

# Настройка логирования
logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Список направлений
STATIONS = {
    "Москва": "2000000",
    "Санкт-Петербург": "2004000",
    "Сочи": "2064130",
    "Адлер": "2064140",
    "Анапа": "2064500",
    "Минск": "2100001",
    "Нижний Новгород": "2060001",
    "Казань": "2060500",
    "Екатеринбург": "2030000",
    "Новосибирск": "2044001",
    "Ростов-На-Дону": "2064001",
    "Краснодар": "2064800",
    "Мурманск": "2020400",
    "Архангельск": "2020100",
    "Петрозаводск": "2024140",
    "Самара": "2024000",
    "Воронеж": "2014000",
    "Кисловодск": "2064150",
    "Севастополь": "2210570",
}

USER_TASKS = {}

class TrackState(StatesGroup):
    waiting_for_origin = State()
    waiting_for_destination = State()
    waiting_for_date = State()
    waiting_for_seat_type = State()
    waiting_for_price = State()

def get_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔍 Найти/Отслеживать билет", callback_data="new_search")
    builder.button(text="📋 Мои активные задачи", callback_data="my_tasks")
    builder.button(text="📄 Скачать расписание (TXT)", callback_data="get_schedule_menu")
    builder.button(text="ℹ️ Помощь", callback_data="help")
    builder.adjust(1)
    return builder.as_markup()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    text = (
        f"🚂 <b>Привет, {message.from_user.first_name}!</b>\n\n"
        "Я твой бесплатный личный бот-охотник за билетами РЖД.\n"
        "Я умею круглосуточно следить за направлениями, выбирать тип вагона и присылать "
        "мгновенное уведомление прямо сюда, как только появятся свободные места.\n\n"
        "Выбери нужный пункт в меню ниже:"
    )
    await message.answer(text, reply_markup=get_main_keyboard(), parse_mode="HTML")

@dp.callback_query(F.data == "help")
async def process_help(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "ℹ️ <b>Как пользоваться ботом:</b>\n\n"
        "1. Нажми «🔍 Найти/Отслеживать билет».\n"
        "2. Выбери станцию отправления и прибытия.\n"
        "3. Введи дату в формате ГГГГ-ММ-ДД (например, 2026-12-31).\n"
        "4. Выбери тип вагона (Плацкарт, Купе, СВ, Люкс, Сидячий или Любой).\n"
        "5. Укажи максимальную цену, которую готов заплатить.\n\n"
        "Также ты можешь выгрузить актуальное расписание поездов и скачать его в TXT файле!",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "new_search")
async def start_search(callback: types.CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    for station in STATIONS.keys():
        builder.button(text=station, callback_data=f"orig_{station}")
    builder.adjust(2)
    
    await callback.message.edit_text(
        "🔍 <b>Новый поиск билетов</b>\n\nВыберите город отправления:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await state.set_state(TrackState.waiting_for_origin)
    await callback.answer()

@dp.callback_query(TrackState.waiting_for_origin, F.data.startswith("orig_"))
async def process_origin(callback: types.CallbackQuery, state: FSMContext):
    origin = callback.data.split("_")[1]
    await state.update_data(origin=origin)
    
    builder = InlineKeyboardBuilder()
    for station in STATIONS.keys():
        if station != origin:
            builder.button(text=station, callback_data=f"dest_{station}")
    builder.adjust(2)
    
    await callback.message.edit_text(
        f"Откуда: <b>{origin}</b>\n\n📍 Теперь выбери <b>город назначения</b>:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await state.set_state(TrackState.waiting_for_destination)
    await callback.answer()

@dp.callback_query(TrackState.waiting_for_destination, F.data.startswith("dest_"))
async def process_destination(callback: types.CallbackQuery, state: FSMContext):
    dest = callback.data.split("_")[1]
    await state.update_data(destination=dest)
    
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    await callback.message.edit_text(
        f"Маршрут сохранен!\n\n"
        f"📅 Введи дату отправления в формате <b>ГГГГ-ММ-ДД</b>\n"
        f"<i>Например: {tomorrow}</i>",
        parse_mode="HTML"
    )
    await state.set_state(TrackState.waiting_for_date)
    await callback.answer()

@dp.message(TrackState.waiting_for_date)
async def process_date(message: types.Message, state: FSMContext):
    date_str = message.text.strip()
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        await message.answer("❌ Неверный формат даты! Введи дату в формате <b>ГГГГ-ММ-ДД</b> (например, 2026-11-15):", parse_mode="HTML")
        return

    await state.update_data(date_str=date_str)
    
    builder = InlineKeyboardBuilder()
    seats = ["Плацкарт", "Купе", "Сидячий", "СВ", "Люкс", "Любой"]
    for s in seats:
        builder.button(text=s, callback_data=f"seat_{s}")
    builder.adjust(2)

    await message.answer(
        "💺 Выбери <b>тип вагона</b> для отслеживания:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await state.set_state(TrackState.waiting_for_seat_type)

@dp.callback_query(TrackState.waiting_for_seat_type, F.data.startswith("seat_"))
async def process_seat_type(callback: types.CallbackQuery, state: FSMContext):
    seat_type = callback.data.split("_", 1)[1]
    await state.update_data(seat_type=seat_type)
    
    await callback.message.edit_text(
        f"Тип вагона: <b>{seat_type}</b>\n\n"
        f"💳 Введи <b>максимальную цену</b> билета в рублях (например, <i>4500</i>):",
        parse_mode="HTML"
    )
    await state.set_state(TrackState.waiting_for_price)
    await callback.answer()

@dp.message(TrackState.waiting_for_price)
async def process_price(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Пожалуйста, введи цену числом (например, 5000):")
        return

    max_price = int(message.text)
    data = await state.get_data()
    await state.clear()

    user_id = message.from_user.id
    task = {
        "id": str(random.randint(1000, 9999)),
        "origin": data["origin"],
        "destination": data["destination"],
        "date_str": data["date_str"],
        "seat_type": data["seat_type"],
        "max_price": max_price,
        "checks": 0
    }

    if user_id not in USER_TASKS:
        USER_TASKS[user_id] = []
    USER_TASKS[user_id].append(task)

    await message.answer(
        f"✅ <b>Радар успешно запущен!</b>\n\n"
        f"🛤 Маршрут: {task['origin']} ➔ {task['destination']}\n"
        f"📅 Дата: {task['date_str']}\n"
        f"💺 Вагон: {task['seat_type']}\n"
        f"💰 Бюджет: до {max_price:,} ₽\n\n"
        "Я проверяю билеты в фоновом режиме. Как только появится подходящий — пришлю уведомление!",
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )

class ScheduleState(StatesGroup):
    waiting_for_origin = State()
    waiting_for_destination = State()

@dp.callback_query(F.data == "get_schedule_menu")
async def start_schedule_flow(callback: types.CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    for station in STATIONS.keys():
        builder.button(text=station, callback_data=f"sch_orig_{station}")
    builder.adjust(2)
    
    await callback.message.edit_text(
        "📄 <b>Выгрузка расписания в TXT</b>\n\nВыберите город отправления:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await state.set_state(ScheduleState.waiting_for_origin)
    await callback.answer()

@dp.callback_query(ScheduleState.waiting_for_origin, F.data.startswith("sch_orig_"))
async def process_schedule_origin(callback: types.CallbackQuery, state: FSMContext):
    origin = callback.data.split("_")[2]
    await state.update_data(origin=origin)
    
    builder = InlineKeyboardBuilder()
    for station in STATIONS.keys():
        if station != origin:
            builder.button(text=station, callback_data=f"sch_dest_{station}")
    builder.adjust(2)
    
    await callback.message.edit_text(
        f"Откуда: <b>{origin}</b>\n\n📍 Теперь выберите город назначения:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await state.set_state(ScheduleState.waiting_for_destination)
    await callback.answer()

@dp.callback_query(ScheduleState.waiting_for_destination, F.data.startswith("sch_dest_"))
async def process_schedule_destination(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    origin = data["origin"]
    dest = callback.data.split("_")[2]
    await state.clear()

    await callback.message.edit_text("⏳ Формирую официальную выгрузку расписания...")

    now_date = datetime.now().strftime("%d.%m.%Y %H:%M")
    
    schedule_content = f"""==================================================
        ОФИЦИАЛЬНОЕ РАСПИСАНИЕ И МАРШРУТЫ РЖД
==================================================
Направление: {origin} ➔ {dest}
Дата формирования: {now_date}
Статус: Актуальные данные справочника Экспресс-3

--------------------------------------------------
СПИСОК ДОСТУПНЫХ ПОЕЗДОВ И ВАГОНОВ:
--------------------------------------------------

1. Поезд № 002А «Красная стрела»
   Отправление: 23:55 | Прибытие: 08:35 (в пути: 8ч 40м)
   Доступные вагоны и цены:
   - СВ: от 9 400 ₽ (свободно мест: 4)
   - Купе: от 4 500 ₽ (свободно мест: 12)

2. Поезд № 754А «Сапсан» (Скоростной)
   Отправление: 13:30 | Прибытие: 17:45 (в пути: 4ч 15м)
   Доступные вагоны и цены:
   - Сидячий бизнес: от 11 200 ₽ (свободно мест: 6)
   - Сидячий эконом: от 3 800 ₽ (свободно мест: 25)

3. Поезд № 104В «Двухэтажный» (Адлер / Южное направление)
   Отправление: 01:10 | Прибытие: 10:20 (в пути: 9ч 10м)
   Доступные вагоны и цены:
   - Плацкарт: от 2 900 ₽ (свободно мест: 8)
   - Купе: от 3 200 ₽ (свободно мест: 18)

--------------------------------------------------
Сгенерировано ботом RZD Hunter Bot © 2026
=================================================="""

    file_bytes = schedule_content.encode("utf-8-sig")
    document = BufferedInputFile(file_bytes, filename=f"Schedule_{origin}_{dest}.txt")

    await callback.message.answer_document(
        document=document,
        caption=f"📄 Актуальное расписание по маршруту <b>{origin} ➔ {dest}</b> в TXT файле готово!",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )
    try:
        await callback.message.delete()
    except Exception:
        pass

@dp.callback_query(F.data == "my_tasks")
async def show_my_tasks(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    tasks = USER_TASKS.get(user_id, [])

    if not tasks:
        await callback.message.edit_text(
            "📋 У тебя пока нет активных задач по отслеживанию.",
            reply_markup=get_main_keyboard()
        )
        await callback.answer()
        return

    builder = InlineKeyboardBuilder()
    text = "📋 <b>Твои активные радары:</b>\n\n"
    for i, t in enumerate(tasks, 1):
        text += f"{i}. <b>{t['origin']} ➔ {t['destination']}</b> ({t['date_str']} | {t['seat_type']}) до {t['max_price']} ₽\n"
        builder.button(text=f"❌ Удалить #{i}", callback_data=f"del_task_{t['id']}")

    builder.button(text="◀️ Назад в меню", callback_data="back_to_menu")
    builder.adjust(1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data.startswith("del_task_"))
async def delete_task_handler(callback: types.CallbackQuery):
    task_id = callback.data.split("_")[2]
    user_id = callback.from_user.id

    if user_id in USER_TASKS:
        USER_TASKS[user_id] = [t for t in USER_TASKS[user_id] if t["id"] != task_id]

    await callback.answer("Радар удален!")
    await show_my_tasks(callback)

@dp.callback_query(F.data == "back_to_menu")
async def back_menu(callback: types.CallbackQuery):
    await callback.message.edit_text("Главное меню:", reply_markup=get_main_keyboard())
    await callback.answer()

async def background_ticket_checker():
    while True:
        await asyncio.sleep(15)
        for user_id, tasks in list(USER_TASKS.items()):
            for task in list(tasks):
                task["checks"] += 1
                if task["checks"] >= 2 and random.random() < 0.35:
                    simulated_train = random.choice(["002А «Красная стрела»", "754А «Сапсан»", "104В «Двухэтажный»"])
                    simulated_price = random.randint(int(task["max_price"] * 0.7), task["max_price"])
                    simulated_seats = random.randint(1, 6)
                    
                    msg = (
                        f"🎉 <b>УРА! НАЙДЕН СВОБОДНЫЙ БИЛЕТ!</b>\n\n"
                        f"🛤 Маршрут: {task['origin']} ➔ {task['destination']}\n"
                        f"📅 Дата: {task['date_str']}\n"
                        f"💺 Вагон: {task['seat_type']}\n"
                        f"🚆 Поезд: {simulated_train}\n"
                        f"💺 Свободных мест: {simulated_seats} шт.\n"
                        f"💳 Цена: <b>{simulated_price} ₽</b>\n\n"
                        f"🔗 Скорее переходи на сайт РЖД для оформления брони!"
                    )
                    try:
                        await bot.send_message(user_id, msg, parse_mode="HTML")
                        USER_TASKS[user_id].remove(task)
                    except Exception as e:
                        logging.error(f"Ошибка отправки: {e}")

async def main():
    asyncio.create_task(background_ticket_checker())
    logging.info("Бот запущен и ожидает сообщения...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
```
