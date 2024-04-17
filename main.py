from frontend.main_app import App
from config import API_KEY
import asyncio


if __name__ == "__main__":
    valid_assets = {'BTC', 'ETH', 'LTC', 'XRP', 'BCH', 'ADA', 'DOT', 'LINK', 'XLM', 'USDT'}
    watchlist_assets = {
        'BTC': {'open_price': 0, 'price': 0, 'change': 0},
        'ETH': {'open_price': 0, 'price': 0, 'change': 0},
        'LTC': {'open_price': 0, 'price': 0, 'change': 0}
    }
    api_keys = {'Name1': API_KEY}
    active_api_key = 'Name1'
    app = App(valid_assets, watchlist_assets, api_keys, active_api_key)
    asyncio.run(app.run())
