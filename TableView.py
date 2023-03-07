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
import tkinter.filedialog
import tempfile
import random
import os
import sqlite3
import signal

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
        scroll_distance = event.delta * -1
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
            (dataframes, df_names) = load_file(self.parent_window, given_file=filepath)
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

    def queryBar(self, evt=None):
        """Query/filtering dialog"""
        if hasattr(self, 'qframe') and self.qframe is not None:
            return
        self.qframe = CustomQueryDialog(self)  #pylint: disable=attribute-defined-outside-init
        self.qframe.grid(row=self.queryrow,column=0,columnspan=3,sticky='news')
        return


class TableViewApp(tkinter.Frame):
    """ guess load the given dataframe into a table and show it
        https://stackoverflow.com/questions/63531454/import-pandas-table-into-tkinter-project
        https://stackoverflow.com/questions/17355902/tkinter-binding-mousewheel-to-scrollbar
    """
    def __init__(self, root, data):
        super().__init__(root)
        self.parent_window = root
        self.tabs_notebook = tkinter.ttk.Notebook(self)
        for subitem_name, df in data.items():
            tabframe = tkinter.ttk.Frame(self.tabs_notebook)
            # dont use showtoolbar, we are adding our own
            thistable = ScrollableTable(tabframe, showstatusbar=SHOW_STATUSBAR, dataframe=df, window=self.parent_window)
            self.tabs_notebook.add(tabframe, text=subitem_name)
            thistable.show()
        self.tabs_notebook.pack(expand=1, fill='both')


class CustomQueryDialog(tkinter.Frame):
    """Use string query to filter. Will not work with spaces in column
        names, so these would need to be converted first."""

    def __init__(self, table):
        parent = table.parentframe
        tkinter.Frame.__init__(self, parent)
        self.parent = parent
        self.table = table
        self.setup()
        self.filters = []
        return

    def setup(self):

        qf = self
        sfont = "Helvetica 10 bold"
        # tkinter.Label(qf, text='Enter String Query:', font=sfont).pack(side=tkinter.TOP,fill=tkinter.X)
        self.queryvar = tkinter.StringVar()
        e = tkinter.Entry(qf, textvariable=self.queryvar, font="Courier 12 bold")
        e.bind('<Return>', self.query)
        e.pack(fill=tkinter.BOTH,side=tkinter.TOP,expand=1,padx=2,pady=2)
        self.fbar = tkinter.Frame(qf)
        self.fbar.pack(side=tkinter.TOP,fill=tkinter.BOTH,expand=1,padx=2,pady=2)
        f = tkinter.Frame(qf)
        f.pack(side=tkinter.TOP, fill=tkinter.BOTH, padx=2, pady=2)
        addButton(f, 'find', self.query, PDImages.filtering(), 'apply filters', side=tkinter.LEFT)
        addButton(f, 'add manual filter', self.addFilter, PDImages.add(),
                  'add manual filter', side=tkinter.LEFT)
        addButton(f, 'close', self.close, PDImages.cross(), 'close', side=tkinter.LEFT)
        self.applyqueryvar = tkinter.BooleanVar()
        self.applyqueryvar.set(True)
        c = tkinter.Checkbutton(f, text='show filtered only', variable=self.applyqueryvar,
                      command=self.query)
        c.pack(side=tkinter.LEFT,padx=2)
        # addButton(f, 'color rows', self.colorResult, PDImages.color_swatch(), 'color filtered rows', side=tkinter.LEFT)

        self.queryresultvar = tkinter.StringVar()
        l = tkinter.Label(f,textvariable=self.queryresultvar, font=sfont)
        l.pack(side=tkinter.RIGHT)
        return

    def close(self):
        self.destroy()
        self.table.qframe = None
        self.table.showAll()

    def query(self, _evt=None):
        """Do query"""

        table = self.table
        s = self.queryvar.get()
        if table.filtered:
            table.model.df = table.dataframe
        df = table.model.df
        mask = None

        #string query first
        if s!='':
            try:
                mask = df.eval(s)
            except Exception:
                mask = df.eval(s, engine='python')
        #add any filters from widgets
        if len(self.filters)>0:
            mask = self.applyFilter(df, mask)
        if mask is None:
            table.showAll()
            self.queryresultvar.set('')
            return
        #apply the final mask
        self.filtdf = filtdf = df[mask]  #pylint: disable=attribute-defined-outside-init
        self.queryresultvar.set('%s rows found' %len(filtdf))

        if self.applyqueryvar.get() == 1:
            #replace current dataframe but keep a copy!
            table.dataframe = table.model.df.copy()
            table.delete('rowrect')
            table.multiplerowlist = []
            table.model.df = filtdf
            table.filtered = True
        else:
            idx = filtdf.index
            rows = table.multiplerowlist = table.getRowsFromIndex(idx)
            if len(rows)>0:
                table.currentrow = rows[0]

        table.redraw()
        return

    def addFilter(self):
        """Add a filter using widgets"""

        df = self.table.model.df
        fb = CustomFilterBar(self, self.fbar, list(df.columns))
        fb.pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=1, padx=2, pady=2)
        self.filters.append(fb)
        return

    def applyFilter(self, df, mask=None):
        """Apply the widget based filters, returns a boolean mask"""

        if mask is None:
            mask = df.index==df.index

        for f in self.filters:
            col, val, op, b = f.getFilter()
            try:
                val = float(val)
            except Exception:
                pass
            #print (col, val, op, b)
            if op == 'contains':
                m = df[col].str.contains(str(val))
            elif op == 'equals':
                m = df[col]==val
            elif op == 'not equals':
                m = df[col]!=val
            elif op == '>':
                m = df[col]>val
            elif op == '<':
                m = df[col]<val
            elif op == 'is empty':
                m = df[col].isnull()
            elif op == 'not empty':
                m = ~df[col].isnull()
            elif op == 'excludes':
                m = -df[col].str.contains(val)
            elif op == 'starts with':
                m = df[col].str.startswith(val)
            elif op == 'has length':
                m = df[col].str.len()>val
            elif op == 'is number':
                m = df[col].astype('object').str.isnumeric()
            elif op == 'is lowercase':
                m = df[col].astype('object').str.islower()
            elif op == 'is uppercase':
                m = df[col].astype('object').str.isupper()
            else:
                continue
            if b == 'AND':
                mask = mask & m
            elif b == 'OR':
                mask = mask | m
            elif b == 'NOT':
                mask = mask ^ m
        return mask

    def colorResult(self):
        """Color filtered rows in main table"""

        table=self.table
        if not hasattr(self.table,'dataframe') or not hasattr(self, 'filtdf'):
            return
        # TODO no such method getaColor
        clr = self.table.getaColor('#dcf1fc')
        if clr is None:
            return
        _df = table.model.df = table.dataframe
        idx = self.filtdf.index
        rows = table.multiplerowlist = table.getRowsFromIndex(idx)
        table.setRowColors(rows, clr, cols='all')
        return

    def update(self):
        df = self.table.model.df
        cols = list(df.columns)
        for f in self.filters:
            f.update(cols)
        return


class CustomFilterBar(tkinter.Frame):
    """Class providing filter widgets"""

    operators = ['contains','excludes','equals','not equals','>','<','is empty','not empty',
                 'starts with','ends with','has length','is number','is lowercase','is uppercase']
    booleanops = ['AND','OR','NOT']

    def __init__(self, parent, parentframe, cols):
        tkinter.Frame.__init__(self, parentframe)
        self.parent = parent
        self.filtercol = tkinter.StringVar()
        _initial = cols[0]
        self.filtercolmenu = tkinter.ttk.Combobox(self,
                textvariable = self.filtercol,
                values = cols,
                #initialitem = initial,
                width = 14)
        self.filtercolmenu.grid(row=0,column=1,sticky='news',padx=2,pady=2)
        self.operator = tkinter.StringVar()
        #self.operator.set('equals')
        operatormenu = tkinter.ttk.Combobox(self,
                textvariable = self.operator,
                values = self.operators,
                width = 10)
        operatormenu.grid(row=0,column=2,sticky='news',padx=2,pady=2)
        self.filtercolvalue=tkinter.StringVar()
        valsbox = tkinter.Entry(self,textvariable=self.filtercolvalue,width=26)
        valsbox.grid(row=0,column=3,sticky='news',padx=2,pady=2)
        valsbox.bind_all("<Return>", self.parent.query)
        self.booleanop = tkinter.StringVar()
        self.booleanop.set('AND')
        booleanopmenu = tkinter.ttk.Combobox(self,
                textvariable = self.booleanop,
                values = self.booleanops,
                width = 6)
        booleanopmenu.grid(row=0,column=0,sticky='news',padx=2,pady=2)
        #disable the boolean operator if it's the first filter
        # if self.index == 0:
        #    booleanopmenu.component('menubutton').configure(state=DISABLED)
        img = PDImages.cross()
        cb = tkinter.Button(self,text='-', image=img, command=self.close)
        cb.image = img
        cb.grid(row=0,column=5,sticky='news',padx=2,pady=2)
        return

    def close(self):
        """Destroy and remove from parent"""

        self.parent.filters.remove(self)
        self.destroy()
        return

    def getFilter(self):
        """Get filter values for this instance"""

        col = self.filtercol.get()
        val = self.filtercolvalue.get()
        op = self.operator.get()
        booleanop = self.booleanop.get()
        return col, val, op, booleanop

    def update(self, cols):  #pylint: disable=arguments-differ
        self.filtercolmenu['values'] = cols
        return


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
        # img = PDImages.open_proj()
        # addButton(self, 'Load Secondary', self.parentapp.load_secondary_table, img, 'load secondary table from file')
        img = PDImages.plot()
        addButton(self, 'Plot', self.parentapp.plotSelected, img, 'plot selected')
        # img = PDImages.transpose()
        # addButton(self, 'Transpose', self.parentapp.transpose, img, 'transpose')
        img = PDImages.copy()
        addButton(self, 'Copy', self.parentapp.copyTable, img, 'copy to clipboard')
        # img = PDImages.paste()
        # addButton(self, 'Paste', self.parentapp.pasteTable, img, 'paste table')
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

def read_file(filepath):
    # read a file and return its data, as a dictionary of named Dataframes
    #   checks file extension to assign a decoder
    print(f'Reading data from file: {filepath}')
    filepath_absolute = pathlib.Path(filepath).resolve()
    file_data = None
    if filepath_absolute.is_file():
        if filepath_absolute.suffix in ['.csv', '.tsv', '.xlsx', '.xls', '.ods', '.db', '.sqlite', '.sqlite3']:
            # lets try decoding this with pandas
            # first try to read into dataframe
            dataframes = []  # store dataframes
            dataframe_names = []  # store dataframe names
            if filepath_absolute.suffix == '.csv':
                attempt_data = None
                try:
                    attempt_data = pandas.read_csv(filepath_absolute, encoding='utf-8')
                except UnicodeDecodeError:
                    print('re-trying with latin/cp1252/ISO-8859-1 encoding')
                    attempt_data = pandas.read_csv(filepath_absolute, encoding='latin')
                dataframes.append(attempt_data)
                dataframe_names.append('default')
            elif filepath_absolute.suffix == '.tsv':
                attempt_data = None
                try:
                    attempt_data = pandas.read_csv(filepath_absolute, sep='\t', encoding='utf-8')
                except UnicodeDecodeError:
                    print('re-trying with latin/cp1252/ISO-8859-1 encoding')
                    attempt_data = pandas.read_csv(filepath_absolute, sep='\t', encoding='latin')
                dataframes.append(attempt_data)
                dataframe_names.append('default')
            elif filepath_absolute.suffix in ['.xlsx', '.xls', '.ods']:
                # old xls, new xlsx, and openoffice ods formats
                xlfile = pandas.ExcelFile(filepath_absolute)
                # load all sheets
                if DEBUG_MODE:
                    print(f'Reading data from {len(xlfile.sheet_names)} sheets')
                for this_sheet in xlfile.sheet_names:
                    dataframes.append(pandas.read_excel(filepath_absolute, sheet_name=this_sheet))
                    dataframe_names.append(this_sheet)
            elif filepath_absolute.suffix in ['.db', '.sqlite', '.sqlite3']:
                # try to read sqlite db
                if DEBUG_MODE:
                    print(f'Treating as sqlite3 database: {filepath_absolute.suffix}')
                db_conn = sqlite3.connect(filepath_absolute)
                cursor = db_conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables_raw = cursor.fetchall()
                tables_list = []
                for entry in tables_raw:
                    tables_list.append(entry[0])
                # load all tables
                if DEBUG_MODE:
                    print(f'Reading data from {len(tables_list)} tables')
                for this_table in tables_list:
                    dataframes.append(pandas.read_sql_query(f"SELECT * FROM {this_table};", db_conn))
                    dataframe_names.append(this_table)
                db_conn.close()
            # now turn our lists into a single dictionary
            file_data = {}
            for (index, df_name) in enumerate(dataframe_names):
                file_data[df_name] = dataframes[index]
        else:
            raise Exception(f'Unsupported file extension: {filepath_absolute.suffix}')
    else:
        raise FileNotFoundError
    return file_data

def load_file(wroot, arguments=None, given_file=None):
    # load, from arguments or given_file, a file into a tableview
    filepath = None
    is_stdin = False
    subitem = None
    file_data = {}
    start_time = time.time()
    if given_file:
        filepath = given_file
    if not filepath:
        # figure out where data is coming from, writing to a tempfile if needed
        (filepath, is_stdin) = get_input_data(args)
    if arguments:
        subitem = arguments['subitem']
    if filepath:
        this_file_size = get_file_size(filepath)
        description = ''
        if DEBUG_MODE:
            print(f'Reading data from file: {filepath}')
        file_data = read_file(filepath)
        file_extension = pathlib.Path(filepath).suffix
        if file_extension in ['.xlsx', '.xls', '.ods', '.db', '.sqlite', '.sqlite3']:
            # some formats have sub-items, like xlsx->sheet or sqlite->table
            subitem_name = None
            subitem_index = None
            if subitem:
                if DEBUG_MODE:
                    print(f'Requested subitem: {subitem}')
                if subitem in file_data:
                    # subitem is the name
                    subitem_name = subitem
                    subitem_index = list(file_data.keys()).index(subitem_name)
                else:
                    # try using subitem as index
                    print(f'No subitem named: {subitem}, trying as index')
                    try:
                        file_data_keys = list(file_data.keys())
                        subitem_index = int(subitem)
                        subitem_name = file_data_keys[subitem_index]
                    except Exception:
                        print(f'Failed to find subitem: {subitem}, will load all subitems')
                        subitem_name = None
                        subitem_index = None
            if subitem_name is not None:
                # only return the named sheet
                print(f'filtering for subitem {subitem_index}: {subitem_name}')
                new_data = {}
                new_data[subitem_name] = file_data[subitem_name]
                file_data = new_data
                description = f'[subitem {subitem_index} : {subitem_name}]'
            else:
                description = '[all subitems]'
        if is_stdin:
            description = f'{this_file_size} - (from stdin)'
        else:
            description = f'{this_file_size} - {filepath} {description}'
        end_time = time.time()
        print(f'Loaded {this_file_size} in {end_time - start_time} seconds')
    else:
        file_data = {}
        file_data['default'] = pandas.DataFrame()
        description = '(no data loaded)'
    if given_file:
        return file_data
    else:
        wroot.title(f'{APP_NAME} - {description}')
        app = TableViewApp(wroot, file_data)
        app.pack(fill=tkinter.BOTH, expand=1)

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
    try:
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
    except Exception as exa:
        print(f'Error: {exa}')
    if DEBUG_MODE:
        print(f'user selected file: {filepath}')
    return filepath

def notify(message):
    # show a message
    prompt_for_option('Notice', message, [])

def get_input_data(arguments):
    # figure out from arguments and stdin, what data to load
    #   for stdin, write it to a temp file first
    #   returns a tuple: (filepath, b_from_stdin)
    b_has_stdin = False
    input_file_path = None
    input_data = []
    if not arguments['file']:
        try:
            b_has_stdin = select.select([sys.stdin, ], [], [], 0.0)[0]  # check if any data in stdin
        except Exception:
            b_has_stdin = False
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
            if DEBUG_MODE:
                print(f'Writing data from stdin to tempfile: {temp_csv}')
            w_start_time = time.time()
            with open(temp_csv, 'w', encoding='utf-8') as tcsv:
                writer = csv.writer(tcsv)
                writer.writerows(input_data)
            input_file_path = str(temp_csv)
            w_end_time = time.time()
            if DEBUG_MODE:
                print(f'Wrote temp .csv in {w_end_time - w_start_time} seconds')
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

def signal_handler(signum, _frame):
    # handle a signal like segfault
    print(f'caught signal {signum}')
    traceback.print_exc()
    sys.exit()

# Execution starts here

if __name__ == '__main__':
    # parse args
    parser = argparse.ArgumentParser(description=APP_DESCRIPTION)
    parser.add_argument('file', nargs='?', help='file-with-data.csv')
    parser.add_argument('subitem', nargs='?', help='which sheet or table, by name or index')
    args = vars(parser.parse_args())
    try:
        signal.signal(signal.SIGSEGV, signal_handler)
        window_root = tkinter.Tk()
        # put it in the center of the screen
        startpoint_x = (window_root.winfo_screenwidth() / 2) - (WINDOW_WIDTH / 2) + random.randint(1, 10)
        startpoint_y = (window_root.winfo_screenheight() / 2) - (WINDOW_HEIGHT / 2) + random.randint(1, 10)
        window_root.geometry('%dx%d+%d+%d' % (WINDOW_WIDTH, WINDOW_HEIGHT, startpoint_x, startpoint_y))
        load_file(window_root, args)
        window_root.mainloop()
    except Exception as ex:
        print('Error: %s' % ex)
        if DEBUG_MODE:
            traceback.print_exc()
        sys.exit()
