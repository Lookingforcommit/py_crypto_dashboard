import asyncio
import customtkinter as ctk
from tkinter import StringVar
from typing import Dict, Set

from backend.market_data_management import WSManager
from backend.db_management import DBManager
from frontend.watchlist_management import WatchlistFrame, MAX_INT
from frontend.sidebar_menu import SidebarMenu

APP_NAME = 'PyCryptoDashboard'


class App(ctk.CTk):
    # TODO: Add functionality to change the valid_assets list
    """
    The main app class which is used for general configuration, application layout and data management
    """

    def __init__(self, valid_assets: Set[str], api_keys: Dict[str, str], active_api_key: str,
                 db_host: str, db_user: str, db_password: str, db_name: str):
        super().__init__()
        self.title(APP_NAME)
        self.geometry(f'{1100}x{580}')
        self.db_manager = DBManager(db_host, db_user, db_password, db_name)
        self.valid_assets = valid_assets
        self.watchlist_assets = {}
        self.assets_settings = {}
        self.load_watchlist_assets()
        self.api_keys = api_keys  # {name: key}
        self.active_api_key = StringVar(self, active_api_key)  # name
        self.ws_manager = WSManager(self, self.db_manager, self.api_keys[active_api_key], self.watchlist_assets,
                                    self.assets_settings)
        self.asyncio_tasks_dct = {}
        self.asyncio_task_group = None
        self.watchlist_frame = WatchlistFrame(self, self.watchlist_assets, self.active_api_key, self.api_keys,
                                              self.assets_settings)
        self.sidebar_frame = SidebarMenu(self, self.valid_assets, self.watchlist_assets, self.api_keys,
                                         self.active_api_key)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.sidebar_frame.grid(row=0, column=0, sticky='nsew')
        self.watchlist_frame.grid(row=0, column=1, sticky='nsew')

    def load_watchlist_assets(self):
        query = "SELECT * FROM watchlist_assets"
        values = ()
        res = self.db_manager.execute_transaction([query], [values])
        for row in res:
            self.watchlist_assets[row[0]] = {'open_price': 0, 'price': 0, 'change': 0}
            self.assets_settings[row[0]] = {'price_rounding': row[2], 'change_rounding': row[1]}

    def add_asset_to_watchlist(self, asset_ticker: str) -> None:
        #  TODO: check if an asset_ticker is valid for subscription
        """
        Adds a new asset to the watchlist and requests market data for it
        :param asset_ticker: asset ticker
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
        :param asset_ticker: asset_ticker of the updated asset
        """
        self.watchlist_frame.update_asset(asset_ticker)

    def update_watchlist_asset_settings(self, asset_ticker: str) -> None:
        """
        Updates the watchlist asset settings in the db after a user-triggered change
        :param asset_ticker: asset_ticker of the updated asset
        """
        query = "UPDATE watchlist_assets SET price_decimals = %s, change_decimals = %s WHERE asset_ticker = %s"
        settings = self.assets_settings[asset_ticker]
        values = (settings['price_rounding'], settings['change_rounding'], asset_ticker)
        self.db_manager.execute_transaction([query], [values])

    def delete_watchlist_asset(self, asset_ticker: str) -> None:
        query = "DELETE FROM watchlist_assets WHERE asset_ticker = %s"
        values = (asset_ticker,)
        self.db_manager.execute_transaction([query], [values])

    def change_active_api_key(self) -> None:
        """
        Changes the active api key for websocket manager
        """
        self.stop_ws()
        if self.active_api_key.get():
            self.ws_manager.api_key = self.api_keys[self.active_api_key.get()]
            self.start_ws()

    def stop_ws(self) -> None:
        """
        Stops an active websocket connection
        """
        self.asyncio_tasks_dct['ws_task'].cancel()
        self.ws_manager.stop_active_ws()

    def start_ws(self) -> None:
        """
        Starts a websocket connection
        """
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
            self.start_ws()
