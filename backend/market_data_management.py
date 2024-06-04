import websockets
import json
import asyncio
from typing import Dict, Union, Optional, List, Tuple
from datetime import datetime
import requests
from os.path import isfile
from PIL import Image
from io import BytesIO

import frontend.main_app
from backend.db_management import DBManager


def download_asset_icon(asset_ticker: str, icon_path: str, api_key: str) -> bool:
    """
    Download the asset icon using the CryptoCompare API
    :param asset_ticker: asset ticker
    :param icon_path: path to save the downloaded icon
    :param api_key: CryptoCompare API key
    """
    url = f'https://data-api.cryptocompare.com/asset/v1/data/by/symbol?asset_symbol={asset_ticker}&api_key={api_key}'
    if not isfile(icon_path):
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise an exception for 4xx or 5xx status codes just in case :)
            asset_data = response.json()
            logo_url = asset_data['Data']['LOGO_URL']
            logo_response = requests.get(logo_url)
            logo_response.raise_for_status()  # Same as comment above
            image = Image.open(BytesIO(logo_response.content), formats=('PNG',))
            image.save(icon_path)
            return True
        except requests.HTTPError:
            return False
    else:
        return True


def insert_to_historical_data(db_manager: DBManager, asset_name: str, price: int, update_time: datetime, change: float):
    """
    Insert a single asset update to the historical data table
    """
    query = "INSERT INTO historical_data (asset_name, update_time, price, `change`) VALUES (%s, %s, %s, %s)"
    values = (asset_name, update_time, price, change)
    db_manager.execute_transaction([query], [values])


def get_historical_data(db_manager: DBManager, asset_name: str, start_date: datetime,
                        end_date: datetime) -> List[Tuple[Union[str, datetime, float]]]:
    """
    Get the historical data for a specific asset within a given date range
    """
    query = "SELECT * FROM historical_data WHERE asset_name = %s AND update_time BETWEEN %s AND %s"
    values = (asset_name, start_date, end_date)
    result = db_manager.execute_transaction([query], [values])
    result = [val[1:] for val in result]
    return result


class WSManager:
    """
    The class is used to manage websocket connections and provide real-time market data
    """

    def __init__(self, app: 'frontend.main_app.App', db_manager: DBManager, api_key: str,
                 watchlist_assets: Dict[str, Dict[str, float]], assets_settings: Dict[str, Dict[str, Optional[int]]]):
        self.app = app
        self.db_manager = db_manager
        self.api_key = api_key
        self.watchlist_assets = watchlist_assets
        self.assets_settings = assets_settings
        self.active_ws: Optional[websockets.WebSocketClientProtocol] = None
        self.db_connection = None
        self.db_cursor = None

    @staticmethod
    def calculate_percentage_change(open_price: float, cur_price: float) -> float:
        """
        Calculate the price percentage change since the beginning of the trade day
        """
        return ((cur_price - open_price) / open_price) * 100

    async def ws_subscribe_to_agg_index(self) -> None:
        """
        Subscribe to the aggregated index channel
        Docs reference: https://min-api.cryptocompare.com/documentation/websockets?key=Channels&cat=AggregateIndex
        """
        url = "wss://streamer.cryptocompare.com/v2?api_key=" + self.api_key
        subs = [f"5~CCCAGG~{asset}~USD" for asset in self.watchlist_assets]
        async for ws in websockets.connect(url):
            self.active_ws = ws
            await ws.send(json.dumps({
                "action": "SubAdd",
                "subs": subs
            }))
            while True:
                try:
                    data = await ws.recv()
                    data = json.loads(data)
                    self.process_ws_agg_idx_update(data)
                except websockets.ConnectionClosed:
                    continue

    def stop_active_ws(self) -> None:
        if self.active_ws is not None:
            asyncio.create_task(self.active_ws.close())
            self.active_ws = None

    def process_ws_agg_idx_update(self, update: Dict[str, Union[str, int, float]]) -> None:
        """
        Process the websocket message data and update the market data
        :param update: ws message
        """
        if 'TYPE' in update and update['TYPE'] == '5':
            if 'FROMSYMBOL' in update and update['FROMSYMBOL'] in self.watchlist_assets:
                asset = update['FROMSYMBOL']
                if 'OPENDAY' in update:
                    self.watchlist_assets[asset]['open_price'] = update['OPENDAY']
                if 'PRICE' in update:
                    price = update['PRICE']
                    open_price = self.watchlist_assets[asset]['open_price']
                    change = self.calculate_percentage_change(open_price, price)
                    self.watchlist_assets[asset]['price'] = price
                    self.watchlist_assets[asset]['change'] = change
                    self.app.update_watchlist_asset(asset)
                    # Inserting data into bd
                    update_time = datetime.now()
                    insert_to_historical_data(self.db_manager, asset, price, update_time, change)
                    