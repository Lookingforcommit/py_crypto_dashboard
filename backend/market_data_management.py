import websockets
import json
import asyncio
from typing import Dict, Union, Optional
import mysql.connector
from mysql.connector import Error
import frontend.main_app
import datetime


class WSManager:
    """
    The class is used to manage websocket connections and provide real-time market data
    """

    def init(self, app: 'frontend.main_app.App', api_key: str, watchlist_assets: Dict[str, Dict[str, float]],
                 assets_settings: Dict[str, Dict[str, Optional[int]]]):
        self.app = app
        self.api_key = api_key
        self.watchlist_assets = watchlist_assets
        self.assets_settings = assets_settings
        self.active_ws: Optional[websockets.WebSocketClientProtocol] = None
        self.db_connection = None
        self.db_cursor = None

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
                    # Добавление данных в базу данных
                    self.connect_to_db()
                    update_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.insert_to_history_date(asset, price, update_time, change)
                    self.close_db_connection()

    def connect_to_db(self):
        try:
            self.db_connection = mysql.connector.connect(
                host="localhost",
                user="root",
                password="gywMom-4kesca-fewdyj",
                database="crypto_data"
            )
            self.db_cursor = self.db_connection.cursor()
        except Error as e:
            print(f"Error connecting to MySQL: {e}")

    def insert_to_history_date(self, asset_name: str, price: int, update_time: str, change: float):
        if self.db_cursor:
            query = "SELECT * FROM history_date WHERE asset_name = %s ORDER BY update_id DESC LIMIT 1"
            self.db_cursor.execute(query, (asset_name,))
            result = self.db_cursor.fetchone()

            if result:
                # Обновляем существующую запись
                query = "UPDATE history_date SET price = %s, update_time = %s, change = %s WHERE asset_name = %s ORDER BY update_id DESC LIMIT 1"
                values = (price, update_time, change, asset_name)
            else:
                # Вставляем новую запись
                query = "INSERT INTO history_date (asset_name, price, update_time, change) VALUES (%s, %s, %s, %s)"
                values = (asset_name, price, update_time, change)

            try:
                self.db_cursor.execute(query, values)
                self.db_connection.commit()
                print("Record inserted or updated successfully into history_date table")
            except Error as e:
                print(f"Error inserting or updating record: {e}")
            else:
                print("Database cursor is not available.")

            def close_db_connection(self):
                if self.db_connection and self.db_connection.is_connected():
                    self.db_cursor.close()
                    self.db_connection.close()
                    print("MySQL connection is closed")
                else:
                    print("No active database connection to close.")

            @staticmethod
            def calculate_percentage_change(open_price: float, cur_price: float) -> float:
                """
                Calculate the price percentage change since the beginning of the trade day
                :param open_price: open price for the asset
                :param cur_price: current price for the asset
                :return: the price percentage change
                """
                return ((cur_price - open_price) / open_price) * 100

            def stop_active_ws(self) -> None:
                """
                Stop the active websocket connection
                """
                if self.active_ws is not None:
                    asyncio.create_task(self.active_ws.close())
                    self.active_ws = None