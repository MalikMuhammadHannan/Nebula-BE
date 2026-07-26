from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    echo=True
)


sessionLocal = sessionmaker(
    autoflush=False,
    autocommit=False,
    bind=engine
)

def get_db ():
    db = sessionLocal()
    try:
        yield db
        
    finally:
        db.close()
        