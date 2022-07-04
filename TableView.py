#!/usr/bin/env python3

# TableView

# Created 2022 by James Bishop (james@bishopdynamics.com)
#   pandas and pandastable do almost all the work here, including most of the UI
#   pandastable can take any pandas dataframe, and pandas can load a wide variety of file formats into dataframe+

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
from pandastable import images as PDImages
from pandastable.dialogs import addButton

# print some extra information if True
DEBUG_MODE = False
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 600

POP_OUT_CHILD = False

SHOW_STATUSBAR = True

APP_NAME = 'TableView'
APP_DESCRIPTION = f'{APP_NAME} - A simple utility for macOS to load csv data from stdin or a file and render a nice interactive tableview to explore it'


class ScrollableTable(Table):
    """ Custom table with scrolling and a custom toolbar """
    xscrollincrement = 10  # distance in pixels on x axis to scroll per increment
    secondarysize = 400  # when opening a secondary table, make window this much taller

    def __init__(self, parent=None, model=None, dataframe=None, width=None, height=None, rows=20, cols=5, showtoolbar=False, showstatusbar=False, editable=True, enable_menus=True, window=None, **kwargs):
        super().__init__(parent, model, dataframe, width, height, rows, cols, showtoolbar, showstatusbar, editable, enable_menus, **kwargs)
        self.toolbar = CustomToolBar(parent, self)
        self.toolbar.grid(row=0,column=3,rowspan=2,sticky='news')
        self.parent_window = window

    def mouse_wheel(self, event):
        # handle mousewheel events and scroll the table
        #   TODO we have to do things different on windows: https://github.com/dmnfarrell/pandastable/blob/39bb317ec3abbeca7b013fc99fa40d0111f7b3df/pandastable/core.py#L219
        if DEBUG_MODE:
            print(f'scroll delta: {event.delta}, state: {event.state} x: {event.x}, y: {event.y}')
        scroll_distance = (event.delta * -1)
        if event.state == 0:
            # vertical scroll
            self.config(yscrollincrement=event.widget.rowheight)
            self.rowheader.config(yscrollincrement=event.widget.rowheight)
            self.yview_scroll(scroll_distance, "units")
            self.rowheader.yview_scroll(scroll_distance, "units")
            self.redrawVisible()
        elif event.state == 1:
            # horizontal scroll
            self.config(xscrollincrement=self.xscrollincrement)
            self.colheader.config(xscrollincrement=self.xscrollincrement)
            self.xview_scroll(scroll_distance, "units")
            self.colheader.xview_scroll(scroll_distance, "units")
            self.redrawVisible()

    def createChildTable(self, df, title=None, index=False, out=False):
        """Add the child table, using our custom toolbar"""

        self.closeChildTable()
        if out:
            win = tkinter.Toplevel()
            x,y,w,h = self.getGeometry(self.master)
            win.geometry('+%s+%s' %(int(x+w/2),int(y+h/2)))
            if title:
                win.title(title)
        else:
            win = tkinter.Frame(self.parentframe)
            win.grid(row=self.childrow,column=0,columnspan=2,sticky='news')
        self.childframe = win # pylint: disable=attribute-defined-outside-init
        newtable = self.__class__(win, dataframe=df, showtoolbar=0, showstatusbar=1)
        newtable.parenttable = self # pylint: disable=attribute-defined-outside-init
        newtable.parent_window = self.parent_window
        newtable.adjustColumnWidths()
        newtable.show()
        toolbar = CustomChildToolBar(win, newtable)
        toolbar.grid(row=0,column=3,rowspan=2,sticky='news')
        self.child = newtable
        if hasattr(self, 'pf'):
            newtable.pf = self.pf # pylint: disable=attribute-defined-outside-init
        if index:
            newtable.showIndex()
        return

    def remove(self):
        """Close child table frame"""
        if DEBUG_MODE:
            print('removing child table')
        if hasattr(self, 'parenttable'):
            self.parenttable.child.destroy()
            self.parenttable.child = None
            self.parenttable.plotted = 'main'
        self.parentframe.destroy()
        return

    def load_secondary_table(self):
        print('loading secondary table')
        filepath = prompt_for_file()
        if filepath:
            (dataframes, df_names, _desc) = load_file(filepath)
            selected_index = 0  # default to first
            if len(df_names) > 1:
                selected_subitem = prompt_for_option(self.parent_window, 'Choose', 'Choose one:', df_names)
                print(f'selected item: {selected_subitem}')
                for (index, value) in enumerate(df_names):
                    if value == selected_subitem:
                        selected_index = index
                        break
            if DEBUG_MODE:
                print('creating child table...')
            self.createChildTable(dataframes[selected_index], title=df_names[selected_index], out=POP_OUT_CHILD)


class TableViewApp(tkinter.Frame):
    """ guess load the given dataframe into a table and show it
        https://stackoverflow.com/questions/63531454/import-pandas-table-into-tkinter-project
        https://stackoverflow.com/questions/17355902/tkinter-binding-mousewheel-to-scrollbar
    """
    def __init__(self, root, dataframes, dataframe_names):
        super().__init__(root)
        self.parent_window = root
        self.tabs_notebook = tkinter.ttk.Notebook(self)
        for index, df in enumerate(dataframes):
            tabframe = tkinter.ttk.Frame(self.tabs_notebook)
            # dont use showtoolbar, we are adding our own
            thistable = ScrollableTable(tabframe, showstatusbar=SHOW_STATUSBAR, dataframe=df, window=self.parent_window)
            self.tabs_notebook.add(tabframe, text=dataframe_names[index])
            thistable.show()
        self.tabs_notebook.pack(expand=1, fill='both')


class CustomToolBar(tkinter.Frame):
    """Uses the parent instance to provide the functions"""
    # NOTE this is just copied from pandastable.Table and modified to remove some buttons
    def __init__(self, parent=None, parentapp=None):
        tkinter.Frame.__init__(self, parent, width=600, height=40)
        self.parentframe = parent
        self.parentapp = parentapp
        img = PDImages.open_proj()
        addButton(self, 'Load Secondary', self.parentapp.load_secondary_table, img, 'load secondary table from file')
        img = PDImages.copy()
        addButton(self, 'Copy', self.parentapp.copyTable, img, 'copy table to clipboard')
        img = PDImages.paste()
        addButton(self, 'Paste', self.parentapp.pasteTable, img, 'paste table')
        img = PDImages.plot()
        addButton(self, 'Plot', self.parentapp.plotSelected, img, 'plot selected')
        img = PDImages.aggregate()
        addButton(self, 'Aggregate', self.parentapp.aggregate, img, 'aggregate')
        img = PDImages.pivot()
        addButton(self, 'Pivot', self.parentapp.pivot, img, 'pivot')
        img = PDImages.melt()
        addButton(self, 'Melt', self.parentapp.melt, img, 'melt')
        img = PDImages.merge()
        addButton(self, 'Merge', self.parentapp.doCombine, img, 'merge, concat or join')
        img = PDImages.table_multiple()
        addButton(self, 'Table from selection', self.parentapp.tableFromSelection, img, 'secondary table from selection')
        img = PDImages.filtering()
        addButton(self, 'Query', self.parentapp.queryBar, img, 'filter table')
        img = PDImages.calculate()
        addButton(self, 'Evaluate function', self.parentapp.evalBar, img, 'calculate')
        img = PDImages.fit()
        addButton(self, 'Stats models', self.parentapp.statsViewer, img, 'model fitting')
        img = PDImages.table_delete()
        addButton(self, 'Clear', self.parentapp.clearTable, img, 'clear table')
        return


class CustomChildToolBar(tkinter.Frame):
    """Smaller toolbar for child table"""
    def __init__(self, parent=None, parentapp=None):
        tkinter.Frame.__init__(self, parent, width=600, height=40)
        self.parentframe = parent
        self.parentapp = parentapp
        img = PDImages.plot()
        addButton(self, 'Plot', self.parentapp.plotSelected, img, 'plot selected')
        img = PDImages.transpose()
        addButton(self, 'Transpose', self.parentapp.transpose, img, 'transpose')
        img = PDImages.copy()
        addButton(self, 'Copy', self.parentapp.copyTable, img, 'copy to clipboard')
        img = PDImages.paste()
        addButton(self, 'Paste', self.parentapp.pasteTable, img, 'paste table')
        img = PDImages.table_delete()
        addButton(self, 'Clear', self.parentapp.clearTable, img, 'clear table')
        img = PDImages.cross()
        addButton(self, 'Close', self.parentapp.remove, img, 'close')
        return


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
            # old xls, new xlsx, and openoffice ods formats
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
                dataframe_names.append(table_name)
                description = f'[table: {table_name}]'
            db_conn.close()
        else:
            print(f'Unsupported file extension: {file_extension}')
            sys.exit(1)
        end_time = time.time()
        print(f'Loaded {this_file_size} in {end_time - start_time} seconds')
        if is_stdin:
            description = f'{this_file_size} - (from stdin)'
        else:
            description = f'{this_file_size} - {filepath} {description}'
    else:
        dataframes.append(pandas.DataFrame())
        dataframe_names.append('No Data')
        description = '(no data loaded)'
    return (dataframes, dataframe_names, description)

def prompt_for_option(root, title, prompt, options=None):
    # ask the user to choose one of the given options, then return the selected option
    if DEBUG_MODE:
        print(f'prompting user to pick one of {len(options)} options')
    prompt_width = 300
    prompt_height = (25 * len(options)) + 50
    dialog = tkinter.Toplevel(root)
    dialog.title(title)
    start_x = (dialog.winfo_screenwidth() / 2) - (prompt_width / 2) + random.randint(1, 10)
    start_y = (dialog.winfo_screenheight() / 2) - (prompt_height / 2) + random.randint(1, 10)
    dialog.geometry('%dx%d+%d+%d' % (prompt_width, prompt_height, start_x, start_y))
    tkinter.Label(dialog, text=prompt).pack()
    v = tkinter.IntVar()
    for i, option in enumerate(options):
        tkinter.Radiobutton(dialog, text=option, variable=v, value=i).pack(anchor='w')
    tkinter.Button(dialog, text='Submit', command=dialog.destroy).pack()
    dialog.grab_set()
    dialog.wait_window()
    print('prompt loop exited')
    if len(options) == 0:
        return  # if no options provided, dont try to return any
    return options[v.get()]

def prompt_for_file():
    # prompt to select a supported file
    if DEBUG_MODE:
        print('prompting for a file')
    filepath = tkinter.filedialog.askopenfilename(title='Select a file', filetypes=(
                ("CSV files", "*.csv"),
                ("TSV files", "*.tsv"),
                ("Excel files", "*.xls"),
                ("Excel files", "*.xlsx"),
                ("OpenOffice files", "*.ods"),
                ("Sqlite3 databases", "*.db"),
                ("Sqlite3 databases", "*.sqlite"),
                ("Sqlite3 databases", "*.sqlite3"),
                ))
    if DEBUG_MODE:
        print(f'user selected file: {filepath}')
    return filepath

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
    # figure out from arguments and stdin, what data to load
    #   for stdin, write it to a temp file first
    #   returns a tuple: (filepath, b_from_stdin)
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
                print('Loaded data from stdin')
            # write input_data to a tempfile, because pandastable is MUCH faster at reading it from the file
            temp_csv = tempfile.mkstemp(prefix='tableview_', suffix='.csv')[1]
            input_file_path = str(temp_csv)
            if DEBUG_MODE:
                print(f'Writing data from stdin to tempfile: {input_file_str}')
            w_start_time = time.time()
            with open(temp_csv, 'w', encoding='utf-8') as tcsv:
                writer = csv.writer(tcsv)
                writer.writerows(input_data)
            w_end_time = time.time()
            if DEBUG_MODE:
                print(f'Write .csv took {w_end_time - w_start_time} seconds')
        else:
            # no stdin, prompt to select file
            # if the user clicks Cancel, or closes the dialog, input_file_path = None, and will exit
            print('no stdin or filename, showing filedialog')
            input_file_path = prompt_for_file()
            if input_file_path is None:
                sys.exit()
    else:
        input_file_arg = arguments['file']
        # normalize to absolute path
        input_file = pathlib.Path(input_file_arg).resolve()
        input_file_path = str(input_file)
        if not input_file.is_file():
            raise Exception('File not found!')
    return (input_file_path, b_has_stdin)


# Execution starts here

if __name__ == '__main__':
    # parse args
    parser = argparse.ArgumentParser(description=APP_DESCRIPTION)
    parser.add_argument('file', nargs='?', help='file-with-data.csv')
    parser.add_argument('subitem', nargs='?', help='which sheet or table, by name or index')
    args = vars(parser.parse_args())
    try:
        # First - figure out if we are loading data from stdin, or from file passed as arg
        #   if needed, write stdin data to a tempfile first
        (input_file_str, from_stdin) = get_input_file_str(args)
        # Next - load the file into a dataframe, and generate a description
        #   we get back a list of dataframes, a list of corresponding names, and a string f'{size} - {filepath}
        (input_dataframes, input_dataframe_names, input_desc) = load_file(input_file_str, args['subitem'], from_stdin)
        # Finally - show a table populated with the dataframe
        new_window_title = f'{APP_NAME} - {input_desc}'
        show_table(input_dataframes, input_dataframe_names, new_window_title)
    except Exception as ex:
        print('Error: %s' % ex)
        if DEBUG_MODE:
            traceback.print_exc()
        sys.exit()
