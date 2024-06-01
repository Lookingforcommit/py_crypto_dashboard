import customtkinter as ctk
from tkinter import StringVar
from typing import Dict, Set, Optional

import frontend.main_app
from frontend.api_keys_management import APIKeysMenu


class NewAssetWindow(ctk.CTkToplevel):
    """
    A CTkToplevel window that allows the user to add an asset to the watchlist
    """
    WINDOW_NAME = 'Add asset'

    def __init__(self, master: 'frontend.main_app.App', valid_assets: Set[str],
                 watchlist_assets: Dict[str, Dict[str, float]]):
        super().__init__(master)
        self.title(self.WINDOW_NAME)
        self.valid_assets = valid_assets
        self.watchlist_assets = watchlist_assets
        self.app = master
        self.geometry('500x150')
        self.grid_columnconfigure(0, weight=1)
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

    def __init__(self, master: 'frontend.main_app.App', valid_assets: Set[str],
                 watchlist_assets: Dict[str, Dict[str, float]], api_keys: Dict[str, str], active_api_key: StringVar):
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
        logo_label = ctk.CTkLabel(self, text=frontend.main_app.APP_NAME, font=ctk.CTkFont(size=20, weight='bold'))
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
