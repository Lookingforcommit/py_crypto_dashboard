from frontend.main_app import App
from config import API_KEY, DB_HOST, DB_USER, DB_PASSWORD, DB_NAME
import asyncio


if __name__ == "__main__":
    valid_assets = {'BTC', 'ETH', 'LTC', 'XRP', 'BCH', 'ADA', 'DOT', 'LINK', 'XLM', 'USDT'}
    watchlist_assets = {}
    assets_settings = {}
    api_keys = {'Name1': API_KEY}
    active_api_key = 'Name1'
    app = App(valid_assets, api_keys, active_api_key, DB_HOST, DB_USER, DB_PASSWORD, DB_NAME)
    asyncio.run(app.run())
