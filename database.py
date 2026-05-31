import os, hashlib, binascii
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime, Boolean, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
    return binascii.hexlify(salt).decode() + "$" + binascii.hexlify(dk).decode()

def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, hash_hex = stored.split("$", 1)
        salt = binascii.unhexlify(salt_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
        return binascii.hexlify(dk).decode() == hash_hex
    except Exception:
        return False

class AdminUser(Base):
    __tablename__ = "admin_users"
    id = Column(Integer, primary_key=True)
    username = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(512), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Direction(Base):
    __tablename__ = "directions"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)

class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    direction_id = Column(Integer, ForeignKey("directions.id"), nullable=False)
    direction = relationship("Direction")
    __table_args__ = (UniqueConstraint("name", "direction_id", name="uq_group_direction"),)

class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True)
    full_name = Column(String(255), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    telegram_id = Column(Integer, nullable=True, unique=True)
    username = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    group = relationship("Group")
    __table_args__ = (UniqueConstraint("full_name", "group_id", name="uq_student_group"),)

class Teacher(Base):
    __tablename__ = "teachers"
    id = Column(Integer, primary_key=True)
    full_name = Column(String(255), nullable=False, unique=True)
    subject = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)

class GroupTeacher(Base):
    __tablename__ = "group_teachers"
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    group = relationship("Group")
    teacher = relationship("Teacher")
    __table_args__ = (UniqueConstraint("group_id", "teacher_id", name="uq_group_teacher"),)

class Rating(Base):
    __tablename__ = "ratings"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    score = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    has_bad_words = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    student = relationship("Student")
    teacher = relationship("Teacher")
    group = relationship("Group")
    __table_args__ = (UniqueConstraint("student_id", "teacher_id", name="uq_student_teacher_rating"),)

def init_db():
    Base.metadata.create_all(bind=engine)
