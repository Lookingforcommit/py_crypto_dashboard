from frontend.main_app import App
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME
import asyncio


if __name__ == "__main__":
    app = App(DB_HOST, DB_USER, DB_PASSWORD, DB_NAME)
    asyncio.run(app.run())
