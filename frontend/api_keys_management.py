import customtkinter as ctk
from tkinter import StringVar, IntVar
from PIL import Image
from typing import Dict, DefaultDict, Optional
from os import path

import frontend.main_app


class APIKeysMenu(ctk.CTkToplevel):
    """
    A CTkToplevel window that allows the user to manage his API keys
    """
    WINDOW_NAME = 'API keys management'

    def __init__(self, master: 'frontend.main_app.SidebarMenu', app: 'frontend.main_app.App',
                 api_keys: DefaultDict[str, str], active_api_key: StringVar):
        super().__init__(master)
        self.app = app
        self.title(self.WINDOW_NAME)
        self.geometry(f"{1100}x{580}")
        self.sidebar_menu = master
        self.api_keys = api_keys
        self.active_api_key = active_api_key
        self.api_keys_table = APIKeysTable(self, self.app, self.api_keys, self.active_api_key)
        self.new_api_key_frame = NewAPIKeyFrame(self, self.app, self.api_keys_table, self.api_keys)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.new_api_key_frame.grid(row=0, column=0, sticky='ew', padx=10, pady=(10, 0))
        self.api_keys_table.grid(row=1, column=0, sticky='nsew')


class APIKeysTable(ctk.CTkScrollableFrame):
    """
    The frame holds the API keys table and allows to change the active key or delete selected keys
    """

    def __init__(self, master: APIKeysMenu, app: 'frontend.main_app.App', api_keys: DefaultDict[str, str],
                 active_api_key: StringVar):
        super().__init__(master, fg_color='transparent')
        self.app = app
        self.api_keys_menu = master
        self.api_keys = api_keys
        self.active_api_key = active_api_key
        self.api_keys_frames: Dict[str, APIKeyContainer] = {}
        self.radio_var = IntVar(self, value=0)
        self._create_header()
        self.used_rows = 2
        for key_name in self.api_keys:
            if key_name:
                self.add_api_key(key_name)

    def _create_header(self) -> None:
        self.columnconfigure((1, 2), weight=1)
        key_name = ctk.CTkLabel(self, text='Key name', font=('Lucida Console', 14))
        key = ctk.CTkLabel(self, text='Key', font=('Lucida Console', 14))
        key_name.grid(row=1, column=1, sticky='w')
        key.grid(row=1, column=2, sticky='w')

    def add_api_key(self, key_name: str) -> None:
        """
        Add a new api key to the API keys table
        :param key_name: user-assigned api-key name
        """
        if key_name == self.active_api_key.get():
            self.radio_var.set(self.used_rows)
        key = self.api_keys[key_name]
        api_key = APIKeyContainer(self, key_name, key, self.used_rows)
        self.api_keys_frames[key_name] = api_key
        self.used_rows += 1

    def delete_api_key(self, key_name: str) -> None:
        """
        Process the user-triggered API key removal
        :param key_name: user-assigned key name
        """
        self.api_keys.pop(key_name)
        self.api_keys_frames.pop(key_name)
        self.app.delete_api_key(key_name)
        if key_name == self.active_api_key.get():
            self.change_active_api_key('')

    def change_active_api_key(self, new_val: str) -> None:
        self.app.change_active_api_key(new_val)


class APIKeyContainer:
    """
    The class acts as a container for the API key row
    """
    RESOURCES_DIR = path.join(path.dirname(__file__), 'resources')
    DELETE_ICON_BLACK_PATH = f'{RESOURCES_DIR}/delete_icon_black.png'
    DELETE_ICON_WHITE_PATH = f'{RESOURCES_DIR}/delete_icon_white.png'
    EYE_ICON_WHITE_PATH = f'{RESOURCES_DIR}/eye_icon_white.png'
    EYE_ICON_BLACK_PATH = f'{RESOURCES_DIR}/eye_icon_black.png'

    def __init__(self, master: APIKeysTable, key_name: str, key: str, row: int):
        self.api_keys_table = master
        self.key_name = key_name
        self.key = key
        self.key_var = StringVar(self.api_keys_table, '*' * len(key))
        self.row = row
        self.delete_button = None
        self.key_name_label: Optional[ctk.CTkLabel] = None
        self.key_label: Optional[ctk.CTkLabel] = None
        self.select_radiobutton = None
        self.show_private_button = None
        self.init_frames()

    def init_frames(self) -> None:
        self.key_name_label = ctk.CTkLabel(self.api_keys_table, text=self.key_name, font=('Lucida Console', 14),
                                           anchor='e')
        self.key_label = ctk.CTkLabel(self.api_keys_table, textvariable=self.key_var, font=('Lucida Console', 14),
                                      anchor='e')
        delete_image = ctk.CTkImage(light_image=Image.open(self.DELETE_ICON_BLACK_PATH),
                                    dark_image=Image.open(self.DELETE_ICON_WHITE_PATH),
                                    size=(30, 30))
        show_key_image = ctk.CTkImage(light_image=Image.open(self.EYE_ICON_BLACK_PATH),
                                      dark_image=Image.open(self.EYE_ICON_WHITE_PATH),
                                      size=(30, 30))
        self.delete_button = ctk.CTkButton(self.api_keys_table, text='', width=30, height=30, image=delete_image,
                                           command=self.delete, fg_color='transparent', hover_color='grey')
        self.show_private_button = ctk.CTkButton(self.api_keys_table, text='', width=30, height=30,
                                                 image=show_key_image, command=self.show_key, fg_color='transparent',
                                                 hover_color='grey')
        self.select_radiobutton = ctk.CTkRadioButton(self.api_keys_table, command=self.select_key, value=self.row,
                                                     variable=self.api_keys_table.radio_var, text='')
        self.select_radiobutton.grid(row=self.row, column=0)
        self.key_name_label.grid(row=self.row, column=1, sticky='w')
        self.key_label.grid(row=self.row, column=2, sticky='w')
        self.show_private_button.grid(row=self.row, column=3)
        self.delete_button.grid(row=self.row, column=4)

    def select_key(self) -> None:
        """
        Select the key as an active API key. Triggered by user
        """
        self.api_keys_table.change_active_api_key(self.key_name)

    def show_key(self) -> None:
        """
        Show the API key in the UI. Triggered by user
        """
        self.key_var.set(self.key)

    def delete(self) -> None:
        """
        Delete all the container frames and corresponding API key. Triggered by user
        """
        self.select_radiobutton.destroy()
        self.key_name_label.destroy()
        self.key_label.destroy()
        self.delete_button.destroy()
        self.show_private_button.destroy()
        self.api_keys_table.delete_api_key(self.key_name)


class NewAPIKeyFrame(ctk.CTkFrame):
    """
    The class allows user to add an API key
    """

    def __init__(self, master: APIKeysMenu, app: 'frontend.main_app.App', api_keys_table: APIKeysTable,
                 api_keys: DefaultDict[str, str]):
        super().__init__(master, fg_color='transparent')
        self.app = app
        self.api_keys_table = api_keys_table
        self.api_keys = api_keys
        self.key_name_var = StringVar(self, value='Key name')
        self.key_var = StringVar(self, value='Key')
        self.status_message = StringVar(self, '')
        self.status_label = ctk.CTkLabel(self, textvariable=self.status_message, font=('Lucida Console', 14),
                                         fg_color='transparent')
        self.key_name_entry = ctk.CTkEntry(self, textvariable=self.key_name_var)
        self.key_entry = ctk.CTkEntry(self, textvariable=self.key_var)
        self.enter_button = ctk.CTkButton(self, text='Add', command=self.validate_key)
        self.columnconfigure((0, 1), weight=1)
        self.key_name_entry.grid(row=0, column=0, sticky='ew')
        self.key_entry.grid(row=0, column=1, sticky='ew')
        self.enter_button.grid(row=0, column=2)
        self.status_label.grid(row=1, column=0, sticky='ew', columnspan=2)

    def validate_key(self) -> None:
        """
        Check if the API key is correct and add it to the api_keys dictionary
        """
        if self.key_name_var.get() in self.api_keys or self.key_var.get() in self.api_keys.values():
            self.status_message.set('The API key is already present in the table')
            self.status_label.configure(text_color='red')
        else:
            self.api_keys[self.key_name_var.get()] = self.key_var.get()
            self.api_keys_table.add_api_key(self.key_name_var.get())
            self.app.add_api_key(self.key_name_var.get())
            self.status_message.set('API key added')
            self.status_label.configure(text_color='LimeGreen')
