import customtkinter as ctk
from typing import List, Union
from tkinter import StringVar
from datetime import datetime
import csv

import frontend.main_app
from backend.db_management import MIN_DATETIME, MAX_DATETIME

DATETIME_FORMAT = '%Y-%m-%d_%H:%M:%S'


class HistoricalDataMenu(ctk.CTkToplevel):
    """
    A CTkToplevel window that allows the user to view saved historical data
    """

    def __init__(self, master: 'frontend.main_app.App', asset_ticker: str):
        super().__init__(master)
        self.app = master
        self.title(f'{asset_ticker} historical data')
        self.geometry(f"{600}x{160}")
        self.asset_ticker = asset_ticker
        self.search_frame = HistoricalDataSearch(self, self.app, self.asset_ticker)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.search_frame.grid(row=0, column=0, sticky='ew', padx=10, pady=(10, 0))


class HistoricalDataSearch(ctk.CTkFrame):
    """
    The class allows user to specify what asset historical data he wants to load
    """
    CSV_HEADER = ['Asset', 'Update_time', 'Price', 'Change']

    def __init__(self, master: HistoricalDataMenu, app: 'frontend.main_app.App', asset_ticker: str):
        super().__init__(master, fg_color='transparent')
        self.app = app
        self.asset_ticker = asset_ticker
        self.start_date_var = StringVar(self, value=MIN_DATETIME.strftime(DATETIME_FORMAT))
        self.end_date_var = StringVar(self, value=MAX_DATETIME.strftime(DATETIME_FORMAT))
        self.output_filename_var = StringVar(self, value='output.csv')
        self.status_message = StringVar(self, '')
        self.columnconfigure((0, 1, 2, 3), weight=1)
        self.status_label = None
        self.start_date_entry = None
        self.end_date_entry = None
        self.output_filename_entry = None
        self.enter_button = None
        self._create_header()
        self.init_frames()

    def _create_header(self) -> None:
        asset = ctk.CTkLabel(self, text='Start date', font=('Helvetica', 14))
        price = ctk.CTkLabel(self, text='End date', font=('Helvetica', 14))
        change = ctk.CTkLabel(self, text='Output filename', font=('Helvetica', 14))
        asset.grid(row=0, column=0, sticky='w')
        price.grid(row=0, column=1, sticky='w')
        change.grid(row=0, column=2, sticky='w')

    def init_frames(self) -> None:
        self.status_label = ctk.CTkLabel(self, textvariable=self.status_message,
                                         font=('Helvetica', 14), fg_color='transparent')
        self.start_date_entry = ctk.CTkEntry(self, textvariable=self.start_date_var)
        self.end_date_entry = ctk.CTkEntry(self, textvariable=self.end_date_var)
        self.output_filename_entry = ctk.CTkEntry(self, textvariable=self.output_filename_var)
        self.enter_button = ctk.CTkButton(self, text='Save', command=self.validate_query)
        self.start_date_entry.grid(row=1, column=0, sticky='ew')
        self.end_date_entry.grid(row=1, column=1, sticky='ew')
        self.output_filename_entry.grid(row=1, column=2, sticky='ew')
        self.enter_button.grid(row=1, column=3, sticky='ew')
        self.status_label.grid(row=2, column=0, sticky='ew', columnspan=4)

    def save_history_data_to_csv(self, output_filename: str, data: List[List[Union[str, datetime, float]]]):
        """
        Saves an extracted list of historical data to a csv file
        """
        for row in data:
            row[1] = row[1].strftime(DATETIME_FORMAT)
        with open(output_filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(self.CSV_HEADER)
            writer.writerows(data)

    def validate_query(self) -> None:
        """
        Check if the query is correct and load the requested data
        """
        try:
            start_datetime = datetime.strptime(self.start_date_var.get(), DATETIME_FORMAT)
            end_datetime = datetime.strptime(self.end_date_var.get(), DATETIME_FORMAT)
            data = self.app.get_historical_data(self.asset_ticker, start_datetime, end_datetime)
            try:
                self.save_history_data_to_csv(self.output_filename_var.get(), data)
                self.status_label.configure(text_color='LimeGreen')
                self.status_message.set(f'Data successfully saved to {self.output_filename_var.get()}')
            except PermissionError:
                self.status_label.configure(text_color='red')
                self.status_message.set(f'Permission denied writing to {self.output_filename_var.get()}')
        except ValueError:
            valid_format = MAX_DATETIME.strftime(DATETIME_FORMAT)
            self.status_label.configure(text_color='red')
            self.status_message.set(f'Invalid date format, valid format is {valid_format}')
