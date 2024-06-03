from frontend.main_app import App
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME
import asyncio


if __name__ == "__main__":
    valid_assets = {'BTC', 'ETH', 'LTC', 'XRP', 'BCH', 'ADA', 'DOT', 'LINK', 'XLM', 'USDT'}
    app = App(valid_assets, DB_HOST, DB_USER, DB_PASSWORD, DB_NAME)
    asyncio.run(app.run())
