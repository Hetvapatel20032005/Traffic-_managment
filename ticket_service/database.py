from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 🔥 100% CORRECTED SUPABASE URL 🔥
# (Brackets hata diye hain aur '@' ko '%40' kar diya hai URL encode karne ke liye)
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:Nisarg%407112%40@db.bauirzjgerxiafnfhmyu.supabase.co:5432/postgres"

# Supabase (PostgreSQL) ke liye engine setup
engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency: API jab bhi call hogi, yeh function database connection dega aur fir close kar dega
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()