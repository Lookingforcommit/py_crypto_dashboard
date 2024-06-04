import asyncio
import customtkinter as ctk
from tkinter import StringVar
from typing import List, Union
from collections import defaultdict
from datetime import datetime

from backend.market_data_management import WSManager, get_historical_data, get_valid_assets
from backend.db_management import DBManager, MAX_INT
from frontend.watchlist_management import WatchlistFrame
from frontend.sidebar_menu import SidebarMenu

APP_NAME = 'PyCryptoDashboard'


class App(ctk.CTk):
    # TODO: Add functionality to change the valid_assets list
    """
    The main app class which is used for general configuration, application layout and data management
    """

    def __init__(self, db_host: str, db_user: str, db_password: str, db_name: str):
        super().__init__()
        self.title(APP_NAME)
        self.geometry(f'{1100}x{580}')
        self.protocol('WM_DELETE_WINDOW', self.on_close)
        self.valid_assets = get_valid_assets()
        self.watchlist_assets = {}
        self.assets_settings = {}
        self.api_keys = defaultdict()  # {name: key}
        self.api_keys.setdefault('')
        self.active_api_key = StringVar(self, '')  # name
        self.asyncio_tasks_dct = {}
        self.asyncio_task_group = None
        self.db_manager = DBManager(db_host, db_user, db_password, db_name)
        self.load_watchlist_assets()
        self.load_api_keys()
        self.ws_manager = WSManager(self, self.db_manager, self.api_keys[self.active_api_key.get()],
                                    self.watchlist_assets, self.assets_settings)
        self.watchlist_frame = None
        self.sidebar_frame = None
        self.init_frames()

    def init_frames(self):
        self.watchlist_frame = WatchlistFrame(self, self.watchlist_assets, self.active_api_key, self.api_keys,
                                              self.assets_settings)
        self.sidebar_frame = SidebarMenu(self, self.valid_assets, self.watchlist_assets, self.api_keys,
                                         self.active_api_key)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self.sidebar_frame.grid(row=0, column=0, sticky='nsew')
        self.watchlist_frame.grid(row=0, column=1, sticky='nsew')

    def load_watchlist_assets(self) -> None:
        """
        Load watchlist assets from the database
        """
        query = "SELECT * FROM watchlist_assets"
        values = ()
        res = self.db_manager.execute_transaction([query], [values])
        for row in res:
            self.watchlist_assets[row[0]] = {'open_price': 0, 'price': 0, 'change': 0}
            self.assets_settings[row[0]] = {'price_rounding': row[2], 'change_rounding': row[1]}

    def add_asset_to_watchlist(self, asset_ticker: str) -> None:
        """
        Adds a new asset to the watchlist and requests market data for it
        """
        query = "INSERT INTO watchlist_assets (price_decimals, change_decimals, asset_ticker) VALUES (%s, %s, %s)"
        values = (MAX_INT, MAX_INT, asset_ticker)
        self.db_manager.execute_transaction([query], [values])
        self.watchlist_assets[asset_ticker] = {'open_price': 0, 'price': 0, 'change': 0}
        self.assets_settings[asset_ticker] = {'price_rounding': MAX_INT, 'change_rounding': MAX_INT}
        self.stop_ws()
        self.start_ws()
        self.watchlist_frame.add_asset(asset_ticker)

    def update_watchlist_asset(self, asset_ticker: str) -> None:
        """
        Updates the watchlist assets based on the external websocket data
        """
        self.watchlist_frame.update_asset(asset_ticker)

    def update_watchlist_asset_settings(self, asset_ticker: str) -> None:
        """
        Updates the watchlist asset settings in the db after a user-triggered change
        """
        query = "UPDATE watchlist_assets SET price_decimals = %s, change_decimals = %s WHERE asset_ticker = %s"
        settings = self.assets_settings[asset_ticker]
        values = (settings['price_rounding'], settings['change_rounding'], asset_ticker)
        self.db_manager.execute_transaction([query], [values])

    def delete_watchlist_asset(self, asset_ticker: str) -> None:
        """
        Deletes a watchlist asset from the db after a user-triggered removal
        """
        query = "DELETE FROM watchlist_assets WHERE asset_ticker = %s"
        values = (asset_ticker,)
        self.db_manager.execute_transaction([query], [values])

    def load_api_keys(self) -> None:
        """
        Load API keys from the db
        """
        query = "SELECT * FROM api_keys"
        values = ()
        res = self.db_manager.execute_transaction([query], [values])
        for row in res:
            self.api_keys[row[0]] = row[1]
            if row[2]:
                self.active_api_key.set(row[0])

    def add_api_key(self, api_key: str) -> None:
        """
        Adds a new API key to the db
        """
        query = "INSERT INTO api_keys (name, `key`) VALUES (%s, %s)"
        values = (api_key, self.api_keys[api_key])
        self.db_manager.execute_transaction([query], [values])

    def change_active_api_key(self, new_val: str) -> None:
        """
        Changes the active api key for websocket manager and updates it in the db
        """
        upd_query = "UPDATE api_keys SET active = %s WHERE name = %s"
        values1 = (False, self.active_api_key.get())
        values2 = (True, new_val)
        self.db_manager.execute_transaction([upd_query, upd_query], [values1, values2])
        self.active_api_key.set(new_val)
        self.stop_ws()
        if self.active_api_key.get():
            self.ws_manager.api_key = self.api_keys[self.active_api_key.get()]
            self.start_ws()

    def delete_api_key(self, api_key: str) -> None:
        """
        Deletes an API key from the db after a user-triggered removal
        """
        query = "DELETE FROM api_keys WHERE name = %s"
        values = (api_key,)
        self.db_manager.execute_transaction([query], [values])

    def get_historical_data(self, asset_ticker: str, start_date: datetime,
                            end_date: datetime) -> List[List[Union[str, datetime, float]]]:
        res = get_historical_data(self.db_manager, asset_ticker, start_date, end_date)
        return res

    def stop_ws(self) -> None:
        if 'ws_task' in self.asyncio_tasks_dct:
            self.asyncio_tasks_dct['ws_task'].cancel()
            self.ws_manager.stop_active_ws()

    def start_ws(self) -> None:
        ws_task = self.asyncio_task_group.create_task(self.ws_manager.ws_subscribe_to_agg_index())
        self.asyncio_tasks_dct['ws_task'] = ws_task

    async def update_ui(self) -> None:
        """
        UI update function which substitutes the App.mainloop functionality
        """
        while True:
            self.update()
            await asyncio.sleep(0.01)

    async def run(self) -> None:
        """
        Program entrypoint, runs both the UI and ws subscription
        """
        async with asyncio.TaskGroup() as tg:
            self.asyncio_task_group = tg
            ui_task = tg.create_task(self.update_ui())
            self.asyncio_tasks_dct['ui_task'] = ui_task
            if self.active_api_key.get():
                self.start_ws()

    def on_close(self) -> None:
        self.stop_ws()
        self.asyncio_tasks_dct['ui_task'].cancel()
        self.quit()
