import websockets
import json
import asyncio
from typing import Dict, Union, Optional
import frontend.main_app
import requests
import os


class WSManager:
    """
    The class is used to manage websocket connections and provide real-time market data
    """
    def __init__(self, app: 'frontend.main_app.App', api_key: str, watchlist_assets: Dict[str, Dict[str, float]],
                 assets_settings: Dict[str, Dict[str, Optional[int]]]):
        self.app = app
        self.api_key = api_key
        self.watchlist_assets = watchlist_assets
        self.assets_settings = assets_settings
        self.active_ws: Optional[websockets.WebSocketClientProtocol] = None

    async def validate_api_key(self) -> bool:
        """
        Validate the Cryptocompare API key
        :return: True if valid, False otherwise
        Docs reference: https://min-api.cryptocompare.com/documentation/websockets?key=Channels&cat=Trade
        """
        url = "wss://streamer.cryptocompare.com/v2?api_key=" + self.api_key
        async with websockets.connect(url) as ws:
            self.active_ws = ws
            while True:
                message = await ws.recv()
                data = json.loads(message)
                if 'MESSAGE' in data:
                    if data['MESSAGE'] == "STREAMERWELCOME":
                        await self.close_connection()
                        return True
                    else:
                        await self.close_connection()
                        return False

    async def ws_subscribe_to_agg_index(self) -> None:
        """
        Subscribe to the aggregated index channel\n
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
                self.app.update_watchlist_assets(asset)

    def stop_active_ws(self) -> None:
        """
        Stop the active websocket connection
        """
        if self.active_ws is not None:
            asyncio.create_task(self.active_ws.close())
            self.active_ws = None

    @staticmethod
    def calculate_percentage_change(open_price, cur_price) -> float:
        """
        Calculate the price percentage change since the beginning of the trade day
        :param open_price: open price for the asset
        :param cur_price: current price for the asset
        :return: the price percentage change
        """
        return ((cur_price - open_price) / open_price) * 100
    
    def download_asset_icon(asset: str, icon_path: str) -> None:
        """
        Download the asset icon and save it to the specified path
        If the download fails, download the 404 error icon instead.
        :param asset: Asset ticker
        :param icon_path: Path to save the icon
        """
        ASSETS_ICON_PATH = AssetContainer.ASSETS_ICON_PATH 
        """
        Вроде так указывать путь, но я так до конца и не понял
        Я импортнул из main_app всё, чтобы разобраться, но чет не попёрло
        Анлак ищу ошибки
        """
        if not os.path.exists(ASSETS_ICON_PATH):#эта часть сделана на прикол
            os.makedirs(ASSETS_ICON_PATH)#и эта тоже. ниже вроде норм код
        
        icon_url = f"https://cryptocompare.com/media/{asset.lower()}/64.png"
        error_icon_url = "https://via.placeholder.com/64?text=404"
        response = requests.get(icon_url)
        if response.status_code == 200:
            with open(icon_path, 'wb') as f:
                f.write(response.content)
        else:
            # Download the error icon if the asset icon is not available
            response = requests.get(error_icon_url)
            if response.status_code == 200:
                with open(icon_path, 'wb') as f:
                    f.write(response.content)