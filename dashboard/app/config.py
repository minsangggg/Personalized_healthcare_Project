from dotenv import load_dotenv
import os

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
DB_CHARSET = os.getenv("DB_CHARSET", "utf8mb4")

print("🔍 [CONFIG LOADED]")
print("HOST:", DB_HOST)
print("PORT:", DB_PORT)
print("USER:", DB_USER)
print("PASS:", DB_PASS)
print("DB:", DB_NAME)
