from fastapi import FastAPI
from sqlalchemy import text

from app.database.session import engine


app = FastAPI()


@app.get("/")
def test_db():
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT 1")
            )
            return {
                "database":"connected",
                "result":result.fetchone()[0]
            }

    except Exception as e:

        return {
            "error":str(e)
        }