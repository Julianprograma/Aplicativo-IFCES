import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")

    # MySQL via PyMySQL if env vars are provided, otherwise SQLite (instance folder)
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = os.getenv("DB_PORT", "3306")

    mysql_url = None
    if DB_NAME and DB_USER is not None:
        mysql_url = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD or ''}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

    SQLITE_PATH = BASE_DIR / "instance" / "app.db"
    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)

    SQLALCHEMY_DATABASE_URI = mysql_url or f"sqlite:///{SQLITE_PATH.as_posix()}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class TestConfig(Config):
    TESTING = True
