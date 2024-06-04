import customtkinter as ctk
from tkinter import StringVar, DoubleVar
from PIL import Image
from typing import Dict, DefaultDict, Optional, Tuple, Callable
from os import path

import frontend.main_app
from frontend.historical_data_viewer import HistoricalDataMenu
from backend.db_management import MAX_INT
from backend.market_data_management import download_asset_icon


def convert_asset_settings_to_str(asset_settings: Dict[str, Optional[int]]) -> Dict[str, str]:
    """
    Converts a dictionary of asset settings to a dictionary of strings for displaying
    """
    ans_dct = {}
    for setting in asset_settings:
        if asset_settings[setting] != MAX_INT:
            ans_dct[setting] = str(asset_settings[setting])
        else:
            ans_dct[setting] = 'Max'
    return ans_dct


def convert_asset_settings_to_int(asset_settings: Dict[str, str]) -> Optional[Dict[str, Optional[int]]]:
    """
    Converts a dictionary of asset settings to a dictionary of ints for calculating
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
            ans_dct[setting] = MAX_INT
    return ans_dct


class WatchlistFrame(ctk.CTkScrollableFrame):
    """
    The class implements a watchlist frame which is displayed on the main page
    """

    def __init__(self, master: 'frontend.main_app.App', watchlist_assets: Dict[str, Dict[str, float]],
                 active_api_key: StringVar, api_keys: DefaultDict[str, str],
                 assets_settings: Dict[str, Dict[str, Optional[int]]]):
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
        self.columnconfigure((1, 2, 3), weight=1)
        asset = ctk.CTkLabel(self, text='Asset', font=('Helvetica', 14))
        price = ctk.CTkLabel(self, text='Price', font=('Helvetica', 14))
        change = ctk.CTkLabel(self, text='Price change', font=('Helvetica', 14))
        asset.grid(row=0, column=1, sticky='w')
        price.grid(row=0, column=2, sticky='w')
        change.grid(row=0, column=3, sticky='w')

    def add_asset(self, asset_ticker: str) -> None:
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
        """
        asset_frame = self.asset_frames[asset_ticker]
        asset_shown_data = self.shown_data[asset_ticker]
        asset_settings = self.assets_settings[asset_ticker]
        update = self.watchlist_assets[asset_ticker]
        rounded_price = round(update['price'], asset_settings['price_rounding'])
        rounded_change = round(update['change'], asset_settings['change_rounding'])
        if rounded_price != asset_shown_data['price'] or rounded_change != asset_shown_data['change']:
            asset_shown_data['price'] = rounded_price
            asset_shown_data['change'] = rounded_change
            asset_frame.update_data(asset_shown_data)

    def delete_asset(self, asset_ticker: str) -> None:
        """
        Process the user-triggered asset removal
        """
        self.asset_frames.pop(asset_ticker)
        self.shown_data.pop(asset_ticker)
        self.watchlist_assets.pop(asset_ticker)
        self.app.delete_watchlist_asset(asset_ticker)
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
    HISTORICAL_DATA_ICON_BLACK_PATH = f'{RESOURCES_DIR}/historical_data_black.png'
    HISTORICAL_DATA_ICON_WHITE_PATH = f'{RESOURCES_DIR}/historical_data_white.png'
    ASSETS_ICON_PATH = f'{RESOURCES_DIR}/asset_icons'

    def __init__(self, master: WatchlistFrame, app: 'frontend.main_app.App', asset_ticker: str, price: float,
                 change: float, asset_settings: Dict[str, Optional[int]], row: int, api_keys: DefaultDict[str, str],
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
        self.change_label: Optional[ctk.CTkLabel] = None
        self.price_label: Optional[ctk.CTkLabel] = None
        self.asset_ticker_label = None
        self.asset_settings_window: Optional[ctk.CTkToplevel] = None
        self.settings_button: Optional[ctk.CTkButton] = None
        self.historical_data_window: Optional[ctk.CTkToplevel] = None
        self.historical_data_button: Optional[ctk.CTkButton] = None
        self.delete_button: Optional[ctk.CTkButton] = None
        if download_asset_icon(self.asset_ticker, icon_path, api_keys[active_api_key.get()]):
            self.icon_path = icon_path
        else:
            self.icon_path = error_icon_path
        self.init_frames()

    @staticmethod
    def generate_ctk_image(light_image_path: str, dark_image_path: str, size: Tuple[int, int]) -> ctk.CTkImage:
        img = ctk.CTkImage(light_image=Image.open(light_image_path),
                           dark_image=Image.open(dark_image_path),
                           size=size)
        return img

    def generate_button(self, master, light_image_path: str, black_image_path: str, command: Callable, width: int = 30,
                        height: int = 30, text: str = '', fg_color: str = 'transparent',
                        hover_color: str = 'grey') -> ctk.CTkButton:
        image = self.generate_ctk_image(light_image_path, black_image_path, (width, height))
        button = ctk.CTkButton(master, text=text, width=width, height=height, image=image, command=command,
                               fg_color=fg_color, hover_color=hover_color)
        return button

    def init_frames(self) -> None:
        image = self.generate_ctk_image(self.icon_path, self.icon_path, (30, 30))
        self.asset_image = ctk.CTkLabel(self.watchlist_frame, image=image, text='')
        self.asset_ticker_label = ctk.CTkLabel(self.watchlist_frame, text=self.asset_ticker, font=('Helvetica', 14),
                                               anchor='w')
        color = 'red' if self.change_var.get() < 0 else 'LimeGreen'
        self.price_label = ctk.CTkLabel(self.watchlist_frame, textvariable=self.price_var, font=('Helvetica', 14),
                                        text_color=color, anchor='e')
        self.change_label = ctk.CTkLabel(self.watchlist_frame, textvariable=self.change_var, font=('Helvetica', 14),
                                         text_color=color, anchor='e')
        self.settings_button = self.generate_button(self.watchlist_frame, self.SETTINGS_ICON_BLACK_PATH,
                                                    self.SETTINGS_ICON_WHITE_PATH, self.open_settings_window)
        self.historical_data_button = self.generate_button(self.watchlist_frame, self.HISTORICAL_DATA_ICON_BLACK_PATH,
                                                           self.HISTORICAL_DATA_ICON_WHITE_PATH,
                                                           self.open_historical_data)
        self.delete_button = self.generate_button(self.watchlist_frame, self.DELETE_ICON_BLACK_PATH,
                                                  self.DELETE_ICON_WHITE_PATH, self.delete)
        self.asset_image.grid(row=self.row, column=0)
        self.asset_ticker_label.grid(row=self.row, column=1, sticky='w')
        self.price_label.grid(row=self.row, column=2, sticky='w')
        self.change_label.grid(row=self.row, column=3, sticky='w')
        self.settings_button.grid(row=self.row, column=4)
        self.historical_data_button.grid(row=self.row, column=5)
        self.delete_button.grid(row=self.row, column=6)

    def update_data(self, update: Dict[str, float]) -> None:
        """
        Update the asset pricing data and change the textcolor if needed in the UI
        """
        new_price, new_change = update['price'], update['change']
        self.price_var.set(new_price)
        self.change_var.set(new_change)
        cur_color = self.price_label.cget('text_color')
        new_color = 'red' if new_change < 0 else 'LimeGreen'
        if new_color != cur_color:
            self.price_label.configure(text_color=new_color)
            self.change_label.configure(text_color=new_color)

    def delete(self) -> None:
        """
        Delete all the container frames and real-time market data. Triggered by user
        """
        self.asset_image.destroy()
        self.asset_ticker_label.destroy()
        self.price_label.destroy()
        self.change_label.destroy()
        self.historical_data_button.destroy()
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

    def open_historical_data(self):
        """
        Open the HistoricalDataMenu
        """
        if self.historical_data_window is None or not self.historical_data_window.winfo_exists():
            self.historical_data_window = HistoricalDataMenu(self.app, self.asset_ticker)
        self.historical_data_window.deiconify()
        self.app.after(10, lambda: self.historical_data_window.focus_force())


class AssetSettingsWindow(ctk.CTkToplevel):
    """
    A CTkToplevel window that allows the user to change the asset display settings
    """

    def __init__(self, master: 'frontend.main_app.App', asset_ticker: str, asset_settings: Dict[str, int]):
        super().__init__(master)
        self.title(asset_ticker)
        self.geometry('500x120')
        self.app = master
        self.asset_ticker = asset_ticker
        self.asset_settings = asset_settings
        self.shown_asset_settings = convert_asset_settings_to_str(asset_settings)
        self.price_rounding_var = StringVar(self, value=self.shown_asset_settings['price_rounding'])
        self.change_rounding_var = StringVar(self, value=self.shown_asset_settings['change_rounding'])
        self.status_message = StringVar(self, value='')
        self.save_button = None
        self.status_label: Optional[ctk.CTkLabel] = None
        self.change_rounding_entry = None
        self.price_rounding_entry = None
        self.change_rounding_label: Optional[ctk.CTkLabel] = None
        self.price_rounding_label: Optional[ctk.CTkLabel] = None
        self.status_label = None
        self.init_frames()

    def init_frames(self):
        self.price_rounding_label = ctk.CTkLabel(self, text='Price decimal places', font=('Helvetica', 14))
        self.change_rounding_label = ctk.CTkLabel(self, text='Price change decimal places', font=('Helvetica', 14))
        self.price_rounding_entry = ctk.CTkEntry(self, textvariable=self.price_rounding_var, font=('Helvetica', 14))
        self.change_rounding_entry = ctk.CTkEntry(self, textvariable=self.change_rounding_var, font=('Helvetica', 14))
        self.save_button = ctk.CTkButton(self, text='Save', command=self.save_settings)
        self.status_label = ctk.CTkLabel(self, textvariable=self.status_message, font=('Helvetica', 14),
                                         text_color='red')
        self.columnconfigure((0, 1), weight=1)
        self.price_rounding_label.grid(row=0, column=0, sticky='w', padx=(10, 0))
        self.change_rounding_label.grid(row=1, column=0, sticky='w', padx=(10, 0))
        self.price_rounding_entry.grid(row=0, column=1, sticky='w')
        self.change_rounding_entry.grid(row=1, column=1, sticky='w')
        self.save_button.grid(row=2, column=0, columnspan=2, pady=(5, 0))
        self.status_label.grid(row=3, column=0, columnspan=2)

    def save_settings(self):
        new_shown_asset_settings = {
            'price_rounding': self.price_rounding_var.get(),
            'change_rounding': self.change_rounding_var.get()
        }
        new_asset_settings = convert_asset_settings_to_int(new_shown_asset_settings)
        if new_asset_settings is not None:
            for setting in new_asset_settings:
                self.asset_settings[setting] = new_asset_settings[setting]
            self.shown_asset_settings = new_shown_asset_settings
            self.app.update_watchlist_asset_settings(self.asset_ticker)
            self.withdraw()
        else:
            self.status_message.set('Incorrect rounding values')
