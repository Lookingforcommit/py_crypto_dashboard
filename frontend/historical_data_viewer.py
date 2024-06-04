import customtkinter as ctk
from tkinter import StringVar
from datetime import datetime
from typing import List, Union, Tuple

import frontend.main_app
from backend.db_management import MIN_DATETIME, MAX_DATETIME

DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'


class HistoricalDataMenu(ctk.CTkToplevel):
    def __init__(self, master: 'frontend.main_app.App', asset_ticker: str):
        super().__init__(master)
        self.app = master
        self.title(f'{asset_ticker} historical data')
        self.geometry(f"{1100}x{580}")
        self.asset_ticker = asset_ticker
        self.historical_data_table = HistoricalDataTable(self, self.app, self.asset_ticker)
        self.search_frame = HistoricalDataSearch(self, self.app, self.historical_data_table, self.asset_ticker)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.search_frame.grid(row=0, column=0, sticky='ew', padx=10, pady=(10, 0))
        self.historical_data_table.grid(row=1, column=0, sticky='nsew')


class HistoricalDataTable(ctk.CTkScrollableFrame):
    def __init__(self, master: HistoricalDataMenu, app: 'frontend.main_app.App', asset_ticker: str):
        super().__init__(master, fg_color='transparent')
        self.app = app
        self.asset_ticker = asset_ticker
        self._create_header()
        self.used_rows = 2

    def _create_header(self) -> None:
        self.columnconfigure((0, 1, 2, 3, 4), weight=1)
        csv_idx = ctk.CTkLabel(self, text='Index', font=('Helvetica', 14))
        asset_ticker = ctk.CTkLabel(self, text='Asset', font=('Helvetica', 14))
        update_time = ctk.CTkLabel(self, text='Update time', font=('Helvetica', 14))
        price = ctk.CTkLabel(self, text='Price', font=('Helvetica', 14))
        change = ctk.CTkLabel(self, text='Change', font=('Helvetica', 14))
        csv_idx.grid(row=1, column=0, sticky='w', padx=(10, 0))
        asset_ticker.grid(row=1, column=1, sticky='w')
        update_time.grid(row=1, column=2, sticky='w')
        price.grid(row=1, column=3, sticky='w')
        change.grid(row=1, column=4, sticky='w')

    def set_rows(self, rows: List[Tuple[Union[str, datetime, float]]]):
        for i in range(len(rows)):
            row = rows[i]
            asset_upd = AssetUpdateContainer(self, i, row[0], row[1], row[2], row[3], self.used_rows + i)
        self.used_rows += len(rows)


class AssetUpdateContainer:
    def __init__(self, master: HistoricalDataTable, csv_idx: int, asset_ticker: str, update_time: datetime,
                 price: float, change: float, row: int):
        self.historical_data_table = master
        self.csv_idx = str(csv_idx)
        self.asset_ticker = asset_ticker
        self.update_time = update_time.strftime(DATETIME_FORMAT)
        self.price = str(price)
        self.change = str(change)
        self.row = row
        self.csv_idx_label = None
        self.asset_ticker_label = None
        self.update_time_label = None
        self.price_label = None
        self.change_label = None
        self.init_frames()

    def init_frames(self) -> None:
        self.csv_idx_label = ctk.CTkLabel(self.historical_data_table, text=self.csv_idx,
                                          font=('Helvetica', 14), anchor='e')
        self.asset_ticker_label = ctk.CTkLabel(self.historical_data_table, text=self.asset_ticker,
                                               font=('Helvetica', 14), anchor='e')
        self.update_time_label = ctk.CTkLabel(self.historical_data_table, text=self.update_time,
                                              font=('Helvetica', 14), anchor='e')
        self.price_label = ctk.CTkLabel(self.historical_data_table, text=self.price,
                                        font=('Helvetica', 14), anchor='e')
        self.change_label = ctk.CTkLabel(self.historical_data_table, text=self.change,
                                         font=('Helvetica', 14), anchor='e')
        self.csv_idx_label.grid(row=self.row, column=0, sticky='w', padx=(10, 0))
        self.asset_ticker_label.grid(row=self.row, column=1, sticky='w')
        self.update_time_label.grid(row=self.row, column=2, sticky='w')
        self.price_label.grid(row=self.row, column=3, sticky='w')
        self.change_label.grid(row=self.row, column=4, sticky='w')


class HistoricalDataSearch(ctk.CTkFrame):
    def __init__(self, master: HistoricalDataMenu, app: 'frontend.main_app.App',
                 historical_data_table: HistoricalDataTable, asset_ticker: str):
        super().__init__(master, fg_color='transparent')
        self.app = app
        self.historical_data_table = historical_data_table
        self.asset_ticker = asset_ticker
        self.start_date_var = StringVar(self, value=str(MIN_DATETIME))
        self.end_date_var = StringVar(self, value=str(MAX_DATETIME))
        self.error_message = StringVar(self, '')
        self.error_label = self.error_label = ctk.CTkLabel(self, text_color="red", textvariable=self.error_message,
                                                           font=('Helvetica', 14), fg_color='transparent')
        self.start_date_entry = ctk.CTkEntry(self, textvariable=self.start_date_var)
        self.end_date_entry = ctk.CTkEntry(self, textvariable=self.end_date_var)
        self.enter_button = ctk.CTkButton(self, text='Find', command=self.validate_query)
        self.columnconfigure((0, 1), weight=1)
        self.start_date_entry.grid(row=0, column=0, sticky='ew')
        self.end_date_entry.grid(row=0, column=1, sticky='ew')
        self.enter_button.grid(row=0, column=2)
        self.error_label.grid(row=1, column=0, sticky='ew', columnspan=2)

    def validate_query(self) -> None:
        try:
            start_datetime = datetime.strptime(self.start_date_var.get(), DATETIME_FORMAT)
            end_datetime = datetime.strptime(self.end_date_var.get(), DATETIME_FORMAT)
            data = self.app.get_historical_data(self.asset_ticker, start_datetime, end_datetime)
            self.historical_data_table.set_rows(data)
        except ValueError:
            valid_format = MAX_DATETIME.strftime(DATETIME_FORMAT)
            self.error_message.set(f'Invalid date format, valid format should be {valid_format}')
