from aiogram import Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import SessionLocal, Direction, Group, Student, Teacher, GroupTeacher, Rating
from bad_words import has_bad_words

class Flow(StatesGroup):
    direction = State()
    group = State()
    student = State()
    comment = State()
    score = State()

def kb(items, prefix, label_func):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=label_func(i), callback_data=f"{prefix}:{i.id}")]
        for i in items
    ])

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Baholashni boshlash", callback_data="start_rating")],
        [InlineKeyboardButton(text="Mening ma'lumotim", callback_data="my_info")],
        [InlineKeyboardButton(text="Qayta tanlash", callback_data="restart_select")]
    ])

def home_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Asosiy menyu", callback_data="home")]])

def score_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=str(i), callback_data=f"score:{i}") for i in range(1, 6)],
        [InlineKeyboardButton(text=str(i), callback_data=f"score:{i}") for i in range(6, 11)],
        [InlineKeyboardButton(text="Bekor qilish", callback_data="home")]
    ])

async def show_directions(target, state, edit=False):
    db = SessionLocal()
    try:
        directions = db.query(Direction).order_by(Direction.name).all()
        await state.set_state(Flow.direction)
        if not directions:
            text = "Hali yo'nalishlar kiritilmagan. Admin bilan bog'laning."
            if edit: await target.message.edit_text(text)
            else: await target.answer(text)
            return
        text = "Yo'nalishingizni tanlang:"
        markup = kb(directions, "direction", lambda d: d.name)
        if edit: await target.message.edit_text(text, reply_markup=markup)
        else: await target.answer(text, reply_markup=markup)
    finally:
        db.close()

async def ask_teacher(target, state):
    data = await state.get_data()
    teacher_ids = data.get("teacher_ids", [])
    idx = data.get("teacher_index", 0)
    if idx >= len(teacher_ids):
        await state.clear()
        text = "Rahmat! Sizga biriktirilgan barcha o'qituvchilar baholandi."
        if hasattr(target, "message"): await target.message.answer(text, reply_markup=main_menu())
        else: await target.answer(text, reply_markup=main_menu())
        return
    db = SessionLocal()
    try:
        teacher = db.query(Teacher).filter_by(id=teacher_ids[idx]).first()
        if not teacher:
            await state.update_data(teacher_index=idx+1)
            await ask_teacher(target, state)
            return
        await state.set_state(Flow.comment)
        text = f"O'qituvchi {idx+1}/{len(teacher_ids)}\\n\\n{teacher.full_name}\\n{teacher.subject or ''}\\n\\nFikringizni yozing. Fikr bo'lmasa '-' yuboring."
        if hasattr(target, "message"): await target.message.answer(text, reply_markup=home_kb())
        else: await target.answer(text, reply_markup=home_kb())
    finally:
        db.close()

async def start_rating_for(target, state, student_id):
    db = SessionLocal()
    try:
        student = db.query(Student).filter_by(id=student_id, is_active=True).first()
        if not student:
            await target.message.answer("O'quvchi topilmadi. /start bosing.")
            await state.clear()
            return
        tids = [x.teacher_id for x in db.query(GroupTeacher).filter_by(group_id=student.group_id).all()]
        teachers = db.query(Teacher).filter(Teacher.id.in_(tids), Teacher.is_active == True).order_by(Teacher.full_name).all() if tids else []
        if not teachers:
            await target.message.answer("Bu guruhga o'qituvchilar biriktirilmagan.")
            await state.clear()
            return
        await state.update_data(student_id=student.id, group_id=student.group_id, teacher_ids=[t.id for t in teachers], teacher_index=0, comment="")
        await ask_teacher(target, state)
    finally:
        db.close()

def register_handlers(dp: Dispatcher):
    @dp.message(CommandStart())
    async def start(message: Message, state: FSMContext):
        await state.clear()
        db = SessionLocal()
        try:
            student = db.query(Student).filter_by(telegram_id=message.from_user.id, is_active=True).first()
            if student:
                await message.answer(f"Assalomu alaykum, {student.full_name}!\\nYo'nalish: {student.group.direction.name}\\nGuruh: {student.group.name}", reply_markup=main_menu())
            else:
                await show_directions(message, state)
        finally:
            db.close()

    @dp.callback_query(F.data == "restart_select")
    async def restart_select(call: CallbackQuery, state: FSMContext):
        await state.clear()
        await show_directions(call, state, edit=True)

    @dp.callback_query(F.data == "home")
    async def home(call: CallbackQuery, state: FSMContext):
        await state.clear()
        await call.message.answer("Asosiy menyu:", reply_markup=main_menu())

    @dp.callback_query(F.data == "my_info")
    async def my_info(call: CallbackQuery):
        db = SessionLocal()
        try:
            student = db.query(Student).filter_by(telegram_id=call.from_user.id, is_active=True).first()
            if not student:
                await call.message.answer("Siz hali o'quvchi sifatida tanlanmagansiz. /start bosing.")
                return
            await call.message.answer(f"F.I.Sh: {student.full_name}\\nYo'nalish: {student.group.direction.name}\\nGuruh: {student.group.name}")
        finally:
            db.close()

    @dp.callback_query(F.data == "start_rating")
    async def start_rating(call: CallbackQuery, state: FSMContext):
        db = SessionLocal()
        try:
            student = db.query(Student).filter_by(telegram_id=call.from_user.id, is_active=True).first()
            if not student:
                await call.message.answer("Avval o'zingizni ro'yxatdan tanlang. /start bosing.")
                return
            await start_rating_for(call, state, student.id)
        finally:
            db.close()

    @dp.callback_query(F.data.startswith("direction:"))
    async def choose_direction(call: CallbackQuery, state: FSMContext):
        direction_id = int(call.data.split(":")[1])
        await state.update_data(direction_id=direction_id)
        db = SessionLocal()
        try:
            groups = db.query(Group).filter_by(direction_id=direction_id).order_by(Group.name).all()
            if not groups:
                await call.message.edit_text("Bu yo'nalishda guruh yo'q.", reply_markup=home_kb())
                return
            await state.set_state(Flow.group)
            await call.message.edit_text("Guruhingizni tanlang:", reply_markup=kb(groups, "group", lambda g: g.name))
        finally:
            db.close()

    @dp.callback_query(F.data.startswith("group:"))
    async def choose_group(call: CallbackQuery, state: FSMContext):
        group_id = int(call.data.split(":")[1])
        await state.update_data(group_id=group_id)
        db = SessionLocal()
        try:
            students = db.query(Student).filter_by(group_id=group_id, is_active=True).order_by(Student.full_name).all()
            if not students:
                await call.message.edit_text("Bu guruhda o'quvchilar kiritilmagan.", reply_markup=home_kb())
                return
            await state.set_state(Flow.student)
            await call.message.edit_text("Ro'yxatdan o'zingizni tanlang:", reply_markup=kb(students, "student", lambda s: s.full_name))
        finally:
            db.close()

    @dp.callback_query(F.data.startswith("student:"))
    async def choose_student(call: CallbackQuery, state: FSMContext):
        student_id = int(call.data.split(":")[1])
        db = SessionLocal()
        try:
            student = db.query(Student).filter_by(id=student_id, is_active=True).first()
            if not student:
                await call.message.answer("O'quvchi topilmadi.")
                return
            if student.telegram_id and student.telegram_id != call.from_user.id:
                await call.message.answer("Bu o'quvchi boshqa Telegram akkauntga biriktirilgan. Admin bilan bog'laning.")
                return
            student.telegram_id = call.from_user.id
            student.username = call.from_user.username
            db.commit()
            await call.message.edit_text(f"Siz tanlandingiz:\\n{student.full_name}\\n{student.group.direction.name} / {student.group.name}")
            await start_rating_for(call, state, student.id)
        finally:
            db.close()

    @dp.message(Flow.comment)
    async def get_comment(message: Message, state: FSMContext):
        comment = message.text.strip()
        if comment == "-": comment = ""
        await state.update_data(comment=comment)
        await state.set_state(Flow.score)
        await message.answer("1 dan 10 gacha ball qo'ying:", reply_markup=score_kb())

    @dp.callback_query(F.data.startswith("score:"))
    async def save_score(call: CallbackQuery, state: FSMContext):
        score = int(call.data.split(":")[1])
        data = await state.get_data()
        teacher_ids = data.get("teacher_ids", [])
        idx = data.get("teacher_index", 0)
        if idx >= len(teacher_ids):
            await state.clear()
            await call.message.answer("Baholash yakunlangan.")
            return
        teacher_id = teacher_ids[idx]
        db = SessionLocal()
        try:
            rating = db.query(Rating).filter_by(student_id=data["student_id"], teacher_id=teacher_id).first()
            if rating:
                rating.score = score
                rating.comment = data.get("comment", "")
                rating.has_bad_words = has_bad_words(rating.comment)
            else:
                rating = Rating(student_id=data["student_id"], teacher_id=teacher_id, group_id=data["group_id"], score=score, comment=data.get("comment",""), has_bad_words=has_bad_words(data.get("comment","")))
                db.add(rating)
            db.commit()
            await call.message.answer(f"Saqlandi: {score}/10")
            await state.update_data(teacher_index=idx+1, comment="")
            await ask_teacher(call, state)
        finally:
            db.close()
