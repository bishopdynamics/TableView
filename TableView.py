#!/usr/bin/env python3

# TableView

# Created 2022 by James Bishop (james@bishopdynamics.com)
#   NOTE this basically TableView, with a few minor tweaks

import argparse
import pathlib
import traceback
import csv
import time
import select
import sys
import tkinter
import tempfile
import random
import os
import sqlite3

from sys import stdin

import pandas
from pandastable import Table

# print some extra information if True
DEBUG_MODE = False
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 600

APP_DESCRIPTION = 'TableView - A simple utility for macOS to load csv data from stdin or a file and render a nice interactive tableview to explore it'


class TableViewApp(tkinter.Frame):
    """ guess load the given dataframe into a table and show it
        https://stackoverflow.com/questions/63531454/import-pandas-table-into-tkinter-project
        https://stackoverflow.com/questions/17355902/tkinter-binding-mousewheel-to-scrollbar
    """
    def __init__(self, root, dataframes, dataframe_names):
        super().__init__(root)
        self.scroll_threshold_h = 0.08  # handle scroll events only this often
        self.scroll_threshold_v = 0.03  # handle scroll events only this often
        self.scroll_lockout = 0.0  # how much longer to lockout other axis
        self.last_scrolled_h = time.time()
        self.last_scrolled_v = time.time()
        self.tabcontrol = tkinter.ttk.Notebook(self)
        for index, df in enumerate(dataframes):
            tabframe = tkinter.ttk.Frame(self.tabcontrol)
            thistable = Table(tabframe, showtoolbar=True, showstatusbar=True, dataframe=df)
            self.tabcontrol.add(tabframe, text=dataframe_names[index])
            thistable.bind_all("<MouseWheel>", self.on_mousewheel)
            thistable.show()
        self.tabcontrol.pack(expand=1, fill='both')

    def on_mousewheel(self, event):
        # handle mousewheel events and scroll the table
        try:
            right_now = time.time()
            scroll_distance = (event.delta * -1)
            if event.state == 1 and (right_now - self.last_scrolled_h) > self.scroll_threshold_h:
                # horizontal scroll
                # print(f'scrolling horizontal delta: {event.delta}, state: {event.state} x: {event.x}, y: {event.y}')
                self.last_scrolled_h = time.time()
                self.last_scrolled_v = time.time() + self.scroll_lockout
                event.widget.config(xscrollincrement=50)
                event.widget.colheader.config(xscrollincrement=50)
                event.widget.xview_scroll(scroll_distance, "units")
                event.widget.colheader.xview_scroll(scroll_distance, "units")
                event.widget.redrawVisible()
            if event.state == 0 and (right_now - self.last_scrolled_v) > self.scroll_threshold_v:
                # vertical scroll
                # print(f'scrolling vertical delta: {event.delta}, state: {event.state} x: {event.x}, y: {event.y}')
                self.last_scrolled_v = time.time()
                self.last_scrolled_h = time.time() + self.scroll_lockout
                event.widget.config(yscrollincrement=event.widget.rowheight)
                event.widget.rowheader.config(yscrollincrement=event.widget.rowheight)
                event.widget.yview_scroll(scroll_distance, "units")
                event.widget.rowheader.yview_scroll(scroll_distance, "units")
                event.widget.redrawVisible()
            # self.table.currentrow = self.table.currentrow + event.delta  # change selected row
        except Exception:
            pass  # ignore all errors

def get_file_size(file_path, suffix="B"):
    """ Get the size of a given file, as a human-readable string
        https://stackoverflow.com/questions/1094841/get-human-readable-version-of-file-size
    """
    fsize_bytes = os.path.getsize(file_path)
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(fsize_bytes) < 1024.0:
            return f"{fsize_bytes:3.1f}{unit}{suffix}"
        fsize_bytes /= 1024.0
    return f"{fsize_bytes:.1f}Yi{suffix}"

def load_file(filepath, subitem=None, is_stdin=False):
    dataframes = []
    dataframe_names = []
    if filepath:
        start_time = time.time()
        this_file_size = get_file_size(filepath)
        description = ''
        if DEBUG_MODE:
            print(f'Reading data from file: {filepath}')
        # self.table.importCSV(filepath)
        file_extension = pathlib.Path(filepath).suffix
        if file_extension == '.csv':
            dataframes.append(pandas.read_csv(filepath))
            dataframe_names.append('default')
        elif file_extension == '.tsv':
            dataframes.append(pandas.read_csv(filepath, sep='\t'))
            dataframe_names.append('default')
        elif file_extension in ['.xlsx', '.xls', '.ods']:
            # old xls, new xls, and openoffice ods formats
            xlfile = pandas.ExcelFile(filepath)
            sheet_name = None
            if subitem:
                if DEBUG_MODE:
                    print(f'Requested subitem: {subitem}')
                if subitem in xlfile.sheet_names:
                    sheet_name = subitem
                else:
                    # try using subitem as index into list
                    try:
                        sheet_name = xlfile.sheet_names[int(subitem)]
                    except Exception:
                        print(f'Failed to find sheet: {subitem}')
                        sheet_name = None
            if not sheet_name:
                if len(xlfile.sheet_names) == 1:
                    sheet_name = xlfile.sheet_names[0]
                    if DEBUG_MODE:
                        print(f'Only one sheet: {sheet_name}')
            if not sheet_name:
                # load all sheets
                if DEBUG_MODE:
                    print(f'Reading data from {len(xlfile.sheet_names)} sheets')
                for this_sheet in xlfile.sheet_names:
                    dataframes.append(pandas.read_excel(filepath, sheet_name=this_sheet))
                    dataframe_names.append(this_sheet)
                description = '[all sheets]'
            else:
                if DEBUG_MODE:
                    print(f'Reading data from selected sheet: {sheet_name}')
                dataframes.append(pandas.read_excel(filepath, sheet_name=sheet_name))
                dataframe_names.append(sheet_name)
                description = f'[sheet: {sheet_name}]'
        elif file_extension == '.json':
            # json (an array of arrays, all well formatted)
            dataframes.append(pandas.read_json(filepath))
            dataframe_names.append('default')
        elif file_extension in ['.db', '.sqlite', '.sqlite3']:
            # try to read sqlite db
            if DEBUG_MODE:
                print(f'Treating as sqlite3 database: {file_extension}')
            db_conn = sqlite3.connect(filepath)
            cursor = db_conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables_raw = cursor.fetchall()
            tables_list = []
            for entry in tables_raw:
                tables_list.append(entry[0])
            table_name = None
            if subitem:
                if DEBUG_MODE:
                    print(f'Requested subitem: {subitem}')
                if subitem in tables_list:
                    table_name = subitem
                else:
                    # try using subitem as index into list
                    try:
                        table_name = tables_list[int(subitem)]
                    except Exception:
                        print(f'Failed to find table: {subitem}')
                        table_name = None
            if not table_name:
                if len(tables_list) == 1:
                    # if only one table, just pick that one
                    table_name = tables_list[0]
                    if DEBUG_MODE:
                        print(f'Only one table: {table_name}')
            if not table_name:
                # load all tables
                if DEBUG_MODE:
                    print(f'Reading data from {len(tables_list)} tables')
                for this_table in tables_list:
                    dataframes.append(pandas.read_sql_query(f"SELECT * FROM {this_table};", db_conn))
                    dataframe_names.append(this_table)
                description = '[all tables]'
            else:
                if DEBUG_MODE:
                    print(f'Reading data from selected table: {table_name}')
                dataframes.append(pandas.read_sql_query(f"SELECT * FROM {table_name};", db_conn))
                description = f'[table: {table_name}]'
            db_conn.close()
        else:
            print(f'Unsupported file extension: {file_extension}')
            sys.exit(1)
        end_time = time.time()
        # TODO when loading an xlsx sheet, or sqlite table, the subitem size is less than file size
        #   in title, size is misleading
        print(f'Loaded {this_file_size} in {end_time - start_time} seconds')
        if is_stdin:
            description = f'{this_file_size} - (from stdin)'
        else:
            description = f'{this_file_size} - {filepath} {description}'
    else:
        dataframes.append(pandas.DataFrame())
        dataframe_names.append('default')
        description = '(no data loaded)'
    return (dataframes, dataframe_names, description)

def prompt_for_option(title, prompt, options=None):
    # ask the user to choose one of the given options, then return the selected option
    prompt_width = 300
    prompt_height = (25 * len(options)) + 50
    root = tkinter.Tk()
    root.title(title)
    start_x = (root.winfo_screenwidth() / 2) - (prompt_width / 2) + random.randint(1, 10)
    start_y = (root.winfo_screenheight() / 2) - (prompt_height / 2) + random.randint(1, 10)
    root.geometry('%dx%d+%d+%d' % (prompt_width, prompt_height, start_x, start_y))
    tkinter.Label(root, text=prompt).pack()
    v = tkinter.IntVar()
    for i, option in enumerate(options):
        tkinter.Radiobutton(root, text=option, variable=v, value=i).pack(anchor='w')
    tkinter.Button(text='Submit', command=root.destroy).pack()
    root.mainloop()
    if len(options) == 0:
        return  # if no options provided, dont try to return any
    return options[v.get()]

def notify(message):
    # show a message
    prompt_for_option('Notice', message, [])

def show_table(data, data_names, title):
    """ show a window with table for the given dataframe
    """
    window_root = tkinter.Tk()
    # put it in the center of the screen
    startpoint_x = (window_root.winfo_screenwidth() / 2) - (WINDOW_WIDTH / 2) + random.randint(1, 10)
    startpoint_y = (window_root.winfo_screenheight() / 2) - (WINDOW_HEIGHT / 2) + random.randint(1, 10)
    window_root.geometry('%dx%d+%d+%d' % (WINDOW_WIDTH, WINDOW_HEIGHT, startpoint_x, startpoint_y))
    window_root.title(title)
    app = TableViewApp(window_root, data, data_names)
    app.pack(fill=tkinter.BOTH, expand=1)
    window_root.mainloop()

def get_input_file_str(arguments):
    b_has_stdin = False
    input_file_path = None
    input_data = []
    if not arguments['file']:
        b_has_stdin = select.select([sys.stdin, ], [], [], 0.0)[0]  # check if any data in stdin
        if b_has_stdin:
            # we have data at stdin, lets see if it is empty
            csv_reader = csv.reader(stdin)
            input_data = []
            for row in csv_reader:
                if row:
                    input_data.append(row)
            if not input_data:
                b_has_stdin = False
        if b_has_stdin:
            if DEBUG_MODE:
                print('TableView: loaded data from stdin')
            # write input_data to a tempfile, because pandastable is MUCH faster at reading it from the file
            temp_csv = tempfile.mkstemp(prefix='tableview_', suffix='.csv')[1]
            input_file_path = str(temp_csv)
            if DEBUG_MODE:
                print('Writing data from stdin to tempfile: %s' % input_file_str)
            w_start_time = time.time()
            with open(temp_csv, 'w', encoding='utf-8') as tcsv:
                writer = csv.writer(tcsv)
                writer.writerows(input_data)
            w_end_time = time.time()
            if DEBUG_MODE:
                print(f'Write .csv took {w_end_time - w_start_time} seconds')
    else:
        input_file_arg = arguments['file']
        # normalize to absolute path
        input_file = pathlib.Path(input_file_arg).resolve()
        input_file_path = str(input_file)
        if not input_file.is_file():
            raise Exception('File not found!')
    return (input_file_path, b_has_stdin)

if __name__ == '__main__':
    # parse args
    parser = argparse.ArgumentParser(description=APP_DESCRIPTION)
    parser.add_argument('file', nargs='?', help='file-with-data.csv')
    parser.add_argument('subitem', nargs='?', help='which sheet or table')
    args = vars(parser.parse_args())
    window_title = 'TableView'  # default, but we will overwrite this with filename
    try:
        # First - figure out if we are loading data from stdin, or from file passed as arg
        #   if needed, write stdin data to a tempfile first
        (input_file_str, from_stdin) = get_input_file_str(args)
        # Next - load the file into a dataframe, and generate a description
        # TODO this tuple return is ugly, refactor this
        (input_dataframes, input_dataframe_names, input_desc) = load_file(input_file_str, args['subitem'], from_stdin)
        # Finally - show a table populated with the dataframe
        window_title = f'TableView - {input_desc}'
        show_table(input_dataframes, input_dataframe_names, window_title)
    except Exception as ex:
        print('something went wrong: %s', ex)
        traceback.print_exc()
        sys.exit()
