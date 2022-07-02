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
    def __init__(self, parent, filepath=None):
        super().__init__(parent)
        self.table = Table(self, showtoolbar=True, showstatusbar=True)
        if filepath:
            start_time = time.time()
            this_file_size = get_file_size(filepath)
            if DEBUG_MODE:
                print(f'Reading data from file: {filepath}')
            self.table.importCSV(filepath)
            end_time = time.time()
            print(f'Loaded {this_file_size} in {end_time - start_time} seconds')
        self.table.show()


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
    input_file_str = None
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
                if DEBUG_MODE:
                    print('TableView: loaded data from stdin')
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
                file_size = get_file_size(input_file_str)
                window_title = f'TableView - {file_size} - (stdin)'
                if DEBUG_MODE:
                    print(f'Write .csv took {w_end_time - w_start_time} seconds')
        else:
            input_file_arg = args['file']
            # normalize to absolute path
            input_file = pathlib.Path(input_file_arg).resolve()
            input_file_str = str(input_file)
            if not input_file.is_file():
                raise Exception('File not found!')
            file_size = get_file_size(input_file_str)
            window_title = f'TableView - {file_size} - {input_file_str}'

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
