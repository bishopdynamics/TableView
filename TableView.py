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
import tkinter.filedialog
import subprocess
import tempfile
import random
import os

from sys import stdin

from pandastable import Table

# print some extra information if True
DEBUG_MODE = False
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 600

APP_DESCRIPTION = 'TableView - A simple utility for macOS to load csv data from stdin or a file and render a nice interactive tableview to explore it'


class TableViewApp(tkinter.Frame):
    """ super basic pandastable from example
        https://stackoverflow.com/questions/63531454/import-pandas-table-into-tkinter-project
    """
    def __init__(self, parent, filepath):
        super().__init__(parent)
        self.table = Table(self, showtoolbar=True, showstatusbar=True)
        start_time = time.time()
        file_size = get_file_size(filepath)
        if DEBUG_MODE:
            print(f'Reading data from file: {filepath}')
        self.table.importCSV(filepath)
        self.table.show()
        end_time = time.time()
        print(f'Loaded {file_size} in {end_time - start_time} seconds')

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

if __name__ == '__main__':
    # parse args
    parser = argparse.ArgumentParser(description=APP_DESCRIPTION)
    parser.add_argument('file', nargs='?', help='file-with-data.csv')
    args = vars(parser.parse_args())

    window_title = 'TableView'  # default, but we will overwrite this with filename
    # First - figure out if we are loading data from stdin, from file passed as arg, or using a file picker dialog
    #   and then populate input_file_str
    input_data = {}
    input_file_str = ''
    try:
        if not args['file']:
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
                input_file_str = '(from stdin)'
                window_title = 'TableView - (data from stdin)'
                if DEBUG_MODE:
                    print('TableView: loaded data from stdin')
            else:
                # no data in stdin
                # if no --file or -f argument given, and no stdin, then lets try a popup dialog, then re-execute ourselves WITH the --file argument!
                print('no stdin or filename, showing filedialog')
                input_file_str = tkinter.filedialog.askopenfilename(
                    title='Select data-file.csv', filetypes=(("CSV files", "*.csv"),))
                # note: sys.executable only works when it is compiled, because it resolves to the binary
                if input_file_str:
                    # user selected a file
                    if DEBUG_MODE:
                        print('TableView: re-execing with file: %s', input_file_str)
                    new_process = subprocess.Popen([sys.executable, input_file_str])
                    new_process.wait()
                    sys.exit(0)  # we are done here
                else:
                    # user must have hit Cancel, because no file was selected, lets check if we have late stdin
                    b_has_stdin = select.select([sys.stdin, ], [], [], 0.0)[0]  # check again if any data in stdin, late (while dialog was open)
                    if b_has_stdin:
                        # we have data at stdin, lets see if it is empty
                        # copyof_stdin = sys.stdin.copy()
                        csv_reader = csv.reader(stdin)
                        input_data = []
                        for row in csv_reader:
                            if row:
                                input_data.append(row)
                        if not input_data:
                            b_has_stdin = False
                    if b_has_stdin:
                        # we NOW have data at stdin, lets try to load it by re-execing ourself with it
                        if DEBUG_MODE:
                            print('TableView: re-execing with late stdin')
                        subprocess.Popen([sys.executable], stdin=sys.stdin)
                        if DEBUG_MODE:
                            print('TableView: parent process exited.')
                        sys.exit(0)  # we are done here
                    else:
                        # no file selected (must have hit Cancel), and nothing from stdin
                        print('TableView: no input file selected!')
                        sys.exit(0)  # we are done here
            # write input_data to a tempfile, because pandastable is MUCH faster at reading it from the file
            temp_csv = tempfile.mkstemp(prefix='tableview_', suffix='.csv')[1]
            input_file_str = str(temp_csv)
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
            input_file_arg = args['file']
            # normalize to absolute path
            input_file = pathlib.Path(input_file_arg).resolve()
            input_file_str = str(input_file)
            window_title = f'TableView - {input_file_str}'
            if not input_file.is_file():
                raise Exception('File not found!')

        # Finally - show a window with a Table populated from input_file_str
        window_root = tkinter.Tk()
        # put it in the center of the screen
        startpoint_x = (window_root.winfo_screenwidth() / 2) - (WINDOW_WIDTH / 2) + random.randint(1, 10)
        startpoint_y = (window_root.winfo_screenheight() / 2) - (WINDOW_HEIGHT / 2) + random.randint(1, 10)
        window_root.geometry('%dx%d+%d+%d' % (WINDOW_WIDTH, WINDOW_HEIGHT, startpoint_x, startpoint_y))
        window_root.title(window_title)
        app = TableViewApp(window_root, input_file_str)
        app.pack(fill=tkinter.BOTH, expand=1)
        window_root.mainloop()
    except Exception as ex:
        print('something went wrong: %s', ex)
        traceback.print_exc()
        sys.exit()
