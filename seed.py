import os
from database import SessionLocal, init_db, Direction, Group, Teacher, GroupTeacher, AdminUser, hash_password
from seed_data import TEACHER_DATA

def get_or_create_direction(db, name):
    obj = db.query(Direction).filter_by(name=name).first()
    if obj: return obj
    obj = Direction(name=name)
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

def get_or_create_group(db, name, direction_id):
    obj = db.query(Group).filter_by(name=name, direction_id=direction_id).first()
    if obj: return obj
    obj = Group(name=name, direction_id=direction_id)
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

def get_or_create_teacher(db, full_name, subject=""):
    obj = db.query(Teacher).filter_by(full_name=full_name).first()
    if obj:
        if subject and obj.subject != subject:
            obj.subject = subject; db.commit()
        return obj
    obj = Teacher(full_name=full_name, subject=subject or "")
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

def ensure_admin(db):
    admin = db.query(AdminUser).first()
    if admin: return admin
    admin = AdminUser(username=os.getenv("ADMIN_USERNAME", "admin"), password_hash=hash_password(os.getenv("ADMIN_PASSWORD", "12345")))
    db.add(admin); db.commit(); db.refresh(admin)
    return admin

def seed_default_data():
    init_db()
    db = SessionLocal()
    try:
        ensure_admin(db)
        for item in TEACHER_DATA:
            teacher = get_or_create_teacher(db, item["full_name"], item.get("subject", ""))
            for a in item.get("assignments", []):
                direction = get_or_create_direction(db, a["direction"])
                for group_name in a.get("groups", []):
                    group = get_or_create_group(db, group_name, direction.id)
                    if not db.query(GroupTeacher).filter_by(group_id=group.id, teacher_id=teacher.id).first():
                        db.add(GroupTeacher(group_id=group.id, teacher_id=teacher.id))
                        db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    seed_default_data()
    print("Seed completed")
