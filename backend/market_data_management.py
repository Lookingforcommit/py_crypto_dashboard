import websockets
import json
import asyncio
from typing import Dict, Union, Optional
import frontend.main_app


class WSManager:
    """
    The class is used to manage websocket connections and provide real-time market data
    """
    def __init__(self, app: 'frontend.main_app.App', api_key: str, watchlist_assets: Dict[str, Dict[str, float]]):
        self.app = app
        self.api_key = api_key
        self.watchlist_assets = watchlist_assets
        self.active_ws: Optional[websockets.WebSocketClientProtocol] = None

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
                    self.process_ws_update(data)
                except websockets.ConnectionClosed:
                    continue

    def process_ws_update(self, update: Dict[str, Union[str, int, float]]) -> None:
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
