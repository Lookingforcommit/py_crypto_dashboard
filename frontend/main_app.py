import asyncio
import customtkinter as ctk
from tkinter import StringVar, DoubleVar
from PIL import Image
from typing import Dict, Set, Optional
from frontend.api_keys_management import APIKeysMenu
from backend.market_data_management import WSManager, download_asset_icon
from os import path

APP_NAME = 'PyCryptoDashboard'


def convert_asset_settings_to_str(asset_settings: Dict[str, Optional[int]]) -> Dict[str, str]:
    """
    Converts a dictionary of asset settings to a dictionary of strings for displaying
    :param asset_settings: initial settings dict
    :return: processed settings dict
    """
    ans_dct = {}
    for setting in asset_settings:
        if asset_settings[setting] is not None:
            ans_dct[setting] = str(asset_settings[setting])
        else:
            ans_dct[setting] = 'Max'
    return ans_dct


def convert_asset_settings_to_int(asset_settings: Dict[str, str]) -> Optional[Dict[str, Optional[int]]]:
    """
    Converts a dictionary of asset settings to a dictionary of ints for calculating
    :param asset_settings: initial settings dict
    :return: processed settings dict or None if asset settings are invalid
    """
    ans_dct = {}
    for setting in asset_settings:
        if asset_settings[setting] != 'Max':
            try:
                ans_dct[setting] = int(asset_settings[setting])
            except ValueError:
                return None
            if ans_dct[setting] <= 0:
                return None
        else:
            ans_dct[setting] = None
    return ans_dct


class App(ctk.CTk):
    # TODO: Add functionality to change the valid_assets list
    """
    The main app class which is used for general configuration, application layout and data management
    """

    def __init__(self, valid_assets: Set[str], watchlist_assets: Dict[str, Dict[str, float]],
                 assets_settings: Dict[str, Dict[str, Optional[int]]], api_keys: Dict[str, str], active_api_key: str):
        super().__init__()
        self.title(APP_NAME)
        self.geometry(f'{1100}x{580}')
        self.valid_assets = valid_assets
        self.watchlist_assets = watchlist_assets
        self.assets_settings = assets_settings
        self.api_keys = api_keys  # {name: key}
        self.active_api_key = StringVar(self, active_api_key)  # name
        self.watchlist_frame = WatchlistFrame(self, self.watchlist_assets, self.active_api_key, self.api_keys,
                                              self.assets_settings)
        self.sidebar_frame = SidebarMenu(self, self.valid_assets, self.watchlist_assets, self.api_keys,
                                         self.active_api_key)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.sidebar_frame.grid(row=0, column=0, sticky='nsew')
        self.watchlist_frame.grid(row=0, column=1, sticky='nsew')
        self.ws_manager = WSManager(self, self.api_keys[active_api_key], watchlist_assets, assets_settings)
        self.asyncio_tasks_dct = {}
        self.asyncio_task_group = None

    def add_asset_to_watchlist(self, asset_ticker: str) -> None:
        #  TODO: check if an asset_ticker is valid for subscription
        """
        Adds a new asset to the watchlist and requests market data for it
        :param asset_ticker: asset ticker
        """
        self.watchlist_assets[asset_ticker] = {'open_price': 0, 'price': 0, 'change': 0}
        self.stop_ws()
        self.start_ws()
        self.watchlist_frame.add_asset(asset_ticker)

    def update_watchlist_assets(self, asset_ticker: str) -> None:
        """
        Updates the watchlist assets based on the external websocket data
        :param asset_ticker: asset_ticker of the updated asset
        """
        self.watchlist_frame.update_asset(asset_ticker)

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


class WatchlistFrame(ctk.CTkScrollableFrame):
    """
    The class implements a watchlist frame which is displayed on the main page
    """

    def __init__(self, master: App, watchlist_assets: Dict[str, Dict[str, float]], active_api_key: StringVar,
                 api_keys: Dict[str, str], assets_settings: Dict[str, Dict[str, Optional[int]]]):
        super().__init__(master, fg_color='transparent')
        self.app = master
        self.assets_settings = assets_settings
        self.watchlist_assets = watchlist_assets
        self.active_api_key = active_api_key
        self.api_keys = api_keys
        self.asset_frames: Dict[str, AssetContainer] = {}
        self.shown_data = {}
        self._create_header()
        self.used_rows = 1
        for asset_ticker in self.watchlist_assets:
            self.add_asset(asset_ticker)

    def _create_header(self) -> None:
        """
        Create a header for the watchlist table
        """
        self.grid_columnconfigure((1, 2, 3), weight=1)
        asset = ctk.CTkLabel(self, text='Asset', font=('Helvetica', 14))
        price = ctk.CTkLabel(self, text='Price', font=('Helvetica', 14))
        change = ctk.CTkLabel(self, text='Price change', font=('Helvetica', 14))
        asset.grid(row=0, column=1, sticky='w')
        price.grid(row=0, column=2, sticky='w')
        change.grid(row=0, column=3, sticky='w')

    def add_asset(self, asset_ticker: str) -> None:
        """
        Add an asset to the watchlist table
        :param asset_ticker: asset ticker
        """
        self.shown_data[asset_ticker] = {}
        self.shown_data[asset_ticker]['price'] = self.watchlist_assets[asset_ticker]['price']
        self.shown_data[asset_ticker]['change'] = self.watchlist_assets[asset_ticker]['change']
        data = self.shown_data[asset_ticker]
        price, change = data['price'], data['change']
        asset = AssetContainer(self, self.app, asset_ticker, price, change, self.assets_settings[asset_ticker],
                               self.used_rows, self.api_keys, self.active_api_key)
        self.asset_frames[asset_ticker] = asset
        self.used_rows += 1

    def update_asset(self, asset_ticker: str) -> None:
        """
        Process the asset data update and display it in the interface
        :param asset_ticker: asset ticker
        """
        asset_frame = self.asset_frames[asset_ticker]
        asset_shown_data = self.shown_data[asset_ticker]
        asset_settings = self.assets_settings[asset_ticker]
        update = self.watchlist_assets[asset_ticker]
        if asset_settings['price_rounding'] is None:
            rounded_price = update['price']
        else:
            rounded_price = round(update['price'], asset_settings['price_rounding'])
        if asset_settings['change_rounding'] is None:
            rounded_change = update['change']
        else:
            rounded_change = round(update['change'], asset_settings['change_rounding'])
        if rounded_price != asset_shown_data['price'] or rounded_change != asset_shown_data['change']:
            asset_shown_data['price'] = rounded_price
            asset_shown_data['change'] = rounded_change
            asset_frame.update_data(asset_shown_data)

    def delete_asset(self, asset_ticker: str) -> None:
        """
        Process the user-triggered asset removal
        :param asset_ticker: asset ticker
        """
        self.asset_frames.pop(asset_ticker)
        self.shown_data.pop(asset_ticker)
        self.watchlist_assets.pop(asset_ticker)
        self.app.stop_ws()
        self.app.start_ws()


class AssetContainer:
    """
    The class acts as a container for the asset row
    """
    RESOURCES_DIR = path.join(path.dirname(__file__), 'resources')
    DELETE_ICON_BLACK_PATH = f'{RESOURCES_DIR}/delete_icon_black.png'
    DELETE_ICON_WHITE_PATH = f'{RESOURCES_DIR}/delete_icon_white.png'
    SETTINGS_ICON_BLACK_PATH = f'{RESOURCES_DIR}/asset_settings_icon_black.png'
    SETTINGS_ICON_WHITE_PATH = f'{RESOURCES_DIR}/asset_settings_icon_white.png'
    ASSETS_ICON_PATH = f'{RESOURCES_DIR}/asset_icons'

    def __init__(self, master: WatchlistFrame, app: App, asset_ticker: str, price: float, change: float,
                 asset_settings: Dict[str, Optional[int]], row: int, api_keys: Dict[str, str],
                 active_api_key: StringVar):
        self.watchlist_frame = master
        self.app = app
        self.asset_ticker = asset_ticker
        self.asset_settings = asset_settings
        icon_path = f'{self.ASSETS_ICON_PATH}/{asset_ticker}.png'
        error_icon_path = f'{self.ASSETS_ICON_PATH}/error_icon.png'
        self.price_var = DoubleVar(master, price)
        self.change_var = DoubleVar(master, change)
        self.row = row
        self.asset_image = None
        self.delete_button = None
        self.change_label: Optional[ctk.CTkLabel] = None
        self.price_label: Optional[ctk.CTkLabel] = None
        self.asset_ticker_label = None
        self.asset_settings_window: Optional[ctk.CTkLabel] = None
        self.settings_button = None
        if download_asset_icon(self.asset_ticker, icon_path, api_keys[active_api_key.get()]):
            self.icon_path = icon_path
        else:
            self.icon_path = error_icon_path
        self.init_frames()

    def init_frames(self) -> None:
        """
        Initialize the frames and place them in the watchlist frame
        """
        image = ctk.CTkImage(light_image=Image.open(self.icon_path),
                             dark_image=Image.open(self.icon_path),
                             size=(30, 30))
        self.asset_image = ctk.CTkLabel(self.watchlist_frame, image=image, text='')
        self.asset_ticker_label = ctk.CTkLabel(self.watchlist_frame, text=self.asset_ticker, font=('Helvetica', 14),
                                               anchor='w')
        color = 'red' if self.change_var.get() < 0 else 'LimeGreen'
        self.price_label = ctk.CTkLabel(self.watchlist_frame, textvariable=self.price_var, font=('Helvetica', 14),
                                        text_color=color, anchor='e')
        self.change_label = ctk.CTkLabel(self.watchlist_frame, textvariable=self.change_var, font=('Helvetica', 14),
                                         text_color=color, anchor='e')
        settings_image = ctk.CTkImage(light_image=Image.open(self.SETTINGS_ICON_BLACK_PATH),
                                      dark_image=Image.open(self.SETTINGS_ICON_WHITE_PATH),
                                      size=(30, 30))
        self.settings_button = ctk.CTkButton(self.watchlist_frame, text='', width=30, height=30, image=settings_image,
                                             command=self.open_settings_window, fg_color='transparent',
                                             hover_color='grey')
        delete_image = ctk.CTkImage(light_image=Image.open(self.DELETE_ICON_BLACK_PATH),
                                    dark_image=Image.open(self.DELETE_ICON_WHITE_PATH),
                                    size=(30, 30))
        self.delete_button = ctk.CTkButton(self.watchlist_frame, text='', width=30, height=30, image=delete_image,
                                           command=self.delete, fg_color='transparent', hover_color='grey')
        self.asset_image.grid(row=self.row, column=0)
        self.asset_ticker_label.grid(row=self.row, column=1, sticky='w')
        self.price_label.grid(row=self.row, column=2, sticky='w')
        self.change_label.grid(row=self.row, column=3, sticky='w')
        self.settings_button.grid(row=self.row, column=4)
        self.delete_button.grid(row=self.row, column=5)

    def update_data(self, update: Dict[str, float]) -> None:
        """
        Update the asset pricing data and change the textcolor if needed in the UI
        :param update: dict containing new pricing data
        """
        new_price, new_change = update['price'], update['change']
        self.price_var.set(new_price)
        self.change_var.set(new_change)
        color = 'red' if new_change < 0 else 'LimeGreen'
        self.price_label.configure(text_color=color)
        self.change_label.configure(text_color=color)

    def delete(self) -> None:
        """
        Delete all the container frames and real-time market data. Triggered by user
        """
        self.asset_image.destroy()
        self.asset_ticker_label.destroy()
        self.price_label.destroy()
        self.change_label.destroy()
        self.delete_button.destroy()
        if self.asset_settings_window:
            self.asset_settings_window.destroy()
        self.settings_button.destroy()
        self.watchlist_frame.delete_asset(self.asset_ticker)

    def open_settings_window(self):
        """
        Open the AssetSettingsWindow
        """
        if self.asset_settings_window is None or not self.asset_settings_window.winfo_exists():
            self.asset_settings_window = AssetSettingsWindow(self.app, self.asset_ticker, self.asset_settings)
        self.asset_settings_window.deiconify()
        self.app.after(10, lambda: self.asset_settings_window.focus_force())


class AssetSettingsWindow(ctk.CTkToplevel):
    """
    A CTkToplevel window that allows the user to change the asset display settings
    """
    def __init__(self, master: App, asset_ticker: str, asset_settings: Dict[str, int]):
        super().__init__(master)
        self.title(asset_ticker)
        self.geometry('500x120')
        self.app = master
        self.asset_ticker = asset_ticker
        self.asset_settings = asset_settings
        self.shown_asset_settings = convert_asset_settings_to_str(asset_settings)
        self.price_rounding_var = StringVar(self, value=self.shown_asset_settings['price_rounding'])
        self.change_rounding_var = StringVar(self, value=self.shown_asset_settings['change_rounding'])
        self.error_message = StringVar(self, value='')
        self.save_button = None
        self.error_label = None
        self.change_rounding_entry = None
        self.price_rounding_entry = None
        self.change_rounding_label = None
        self.price_rounding_label = None
        self.error_label = None
        self.init_frames()

    def init_frames(self):
        """
        Initialize the frames and place them in the settings frame
        """
        self.price_rounding_label = ctk.CTkLabel(self, text='Price decimal places', font=('Helvetica', 14))
        self.change_rounding_label = ctk.CTkLabel(self, text='Price change decimal places',
                                                  font=('Helvetica', 14))
        self.price_rounding_entry = ctk.CTkEntry(self, textvariable=self.price_rounding_var, font=('Helvetica', 14))
        self.change_rounding_entry = ctk.CTkEntry(self, textvariable=self.change_rounding_var, font=('Helvetica', 14))
        self.save_button = ctk.CTkButton(self, text='Save', command=self.save_settings)
        self.error_label = ctk.CTkLabel(self, text_color='red', textvariable=self.error_message, font=('Helvetica', 14))
        self.columnconfigure((0, 1), weight=1)
        self.price_rounding_label.grid(row=0, column=0, sticky='w', padx=(10, 0))
        self.change_rounding_label.grid(row=1, column=0, sticky='w', padx=(10, 0))
        self.price_rounding_entry.grid(row=0, column=1, sticky='w')
        self.change_rounding_entry.grid(row=1, column=1, sticky='w')
        self.save_button.grid(row=2, column=0, columnspan=2, pady=(5, 0))
        self.error_label.grid(row=3, column=0, columnspan=2)

    def save_settings(self):
        """
        Validate and save new asset settings
        """
        new_shown_asset_settings = {
            'price_rounding': self.price_rounding_var.get(),
            'change_rounding': self.change_rounding_var.get()
        }
        new_asset_settings = convert_asset_settings_to_int(new_shown_asset_settings)
        if new_asset_settings is not None:
            self.error_message.set('')
            for setting in new_asset_settings:
                self.asset_settings[setting] = new_asset_settings[setting]
            self.shown_asset_settings = new_shown_asset_settings
            self.withdraw()
        else:
            self.error_message.set('Incorrect decimal places value')


class NewAssetWindow(ctk.CTkToplevel):
    """
    A CTkToplevel window that allows the user to add an asset to the watchlist
    """
    WINDOW_NAME = 'Add asset'

    def __init__(self, master: App, valid_assets: Set[str], watchlist_assets: Dict[str, Dict[str, float]]):
        super().__init__(master)
        self.title(self.WINDOW_NAME)
        self.valid_assets = valid_assets
        self.watchlist_assets = watchlist_assets
        self.app = master
        self.geometry('500x150')
        self.grid_columnconfigure((0), weight=1)
        self.error_message = StringVar(self, value='')
        self.new_asset = StringVar(self, value='BTC')
        self.error_label = ctk.CTkLabel(self, text_color='red', textvariable=self.error_message, font=('Helvetica', 14))
        self.entry = ctk.CTkEntry(self, textvariable=self.new_asset, font=('Helvetica', 14))
        self.validation_button = ctk.CTkButton(self, text='Add', command=self.validate_asset)
        self.entry.grid(row=0, column=0, sticky='ew')
        self.validation_button.grid(row=0, column=1)
        self.error_label.grid(row=1, column=0, sticky='ew')

    def validate_asset(self):
        """
        Validate asset and add it to the watchlist
        """
        new_asset = self.new_asset.get()
        if new_asset in self.watchlist_assets:
            self.error_message.set('The asset is already present in the watchlist')
        elif new_asset not in self.valid_assets:
            self.error_message.set('Incorrect asset ticker')
        else:
            self.app.add_asset_to_watchlist(new_asset)
            self.error_message.set('')


class SidebarMenu(ctk.CTkFrame):
    """
    The class implements a sidebar menu which contains UI settings, watchlist editing functionality, API keys settings
    """

    def __init__(self, master: App, valid_assets: Set[str], watchlist_assets: Dict[str, Dict[str, float]],
                 api_keys: Dict[str, str], active_api_key: StringVar):
        super().__init__(master, width=140, corner_radius=0)
        self.app = master
        self.valid_assets = valid_assets
        self.watchlist_assets = watchlist_assets
        self.api_keys = api_keys
        self.active_api_key = active_api_key
        self.new_asset_window: Optional[NewAssetWindow] = None
        self.api_keys_window: Optional[APIKeysMenu] = None
        self.init_frames()

    def init_frames(self) -> None:
        """
        Initialize the frames and place them in the sidebar menu
        """
        logo_label = ctk.CTkLabel(self, text=APP_NAME, font=ctk.CTkFont(size=20, weight='bold'))
        new_asset_button = ctk.CTkButton(self, height=40, text='Add asset', command=self.open_new_asset_menu)
        appearance_mode_label = ctk.CTkLabel(self, text='Theme settings:')
        default_theme = StringVar(self, 'System')
        appearance_mode_optionmenu = ctk.CTkOptionMenu(self, values=['System', 'Light', 'Dark'],
                                                       command=self.change_appearance_mode, variable=default_theme)
        api_keys_label = ctk.CTkLabel(self, text='API keys settings:')
        api_keys_button = ctk.CTkButton(self, textvariable=self.active_api_key, command=self.open_api_keys_menu)
        self.rowconfigure(2, weight=1)
        logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        new_asset_button.grid(row=1, column=0, padx=20)
        api_keys_label.grid(row=3, column=0)
        api_keys_button.grid(row=4, column=0)
        appearance_mode_label.grid(row=5, column=0)
        appearance_mode_optionmenu.grid(row=6, column=0)

    @staticmethod
    def change_appearance_mode(new_appearance_mode: str) -> None:
        """
        Change the app theme
        :param new_appearance_mode: new theme
        """
        ctk.set_appearance_mode(new_appearance_mode)

    def open_new_asset_menu(self) -> None:
        """
        Create and focus a NewAssetWindow
        """
        # noinspection PyTypeChecker
        if self.new_asset_window is None or not self.new_asset_window.winfo_exists():
            self.new_asset_window = NewAssetWindow(self.app, self.valid_assets, self.watchlist_assets)
        self.new_asset_window.deiconify()
        self.after(10, lambda: self.new_asset_window.focus_force())

    def open_api_keys_menu(self) -> None:
        """
        Create and focus an APIKeysMenu window
        """
        if self.api_keys_window is None or not self.api_keys_window.winfo_exists():
            self.api_keys_window = APIKeysMenu(self, self.app, self.api_keys, self.active_api_key)
        self.api_keys_window.deiconify()
        self.after(10, lambda: self.api_keys_window.focus_force())
