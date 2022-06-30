#!/usr/bin/env python3

# TableView

# Created 2022 by James Bishop (james@bishopdynamics.com)
#   NOTE this basically TableView, with a few minor tweaks

import argparse
import pathlib
import traceback
import csv
import select
import sys
import tkinter
import tkinter.filedialog
import subprocess

from sys import stdin

from Mod_TKUtil import show_object

input_data = {}
input_file_str = ''
input_file = None

if __name__ == '__main__':
    # parse args
    parser = argparse.ArgumentParser(
        description='TableView - A simple utility for macOS to load csv data from stdin or a file and render a nice interactive tableview to explore it')
    parser.add_argument('file', nargs='?', help='file-with-data.csv')
    args = vars(parser.parse_args())

    # First - figure out what file we are loading data from, and populate "input_data"
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
                        print('TableView: re-execing with late stdin')
                        subprocess.Popen([sys.executable], stdin=sys.stdin)
                        print('TableView: parent process exited.')
                        sys.exit(0)  # we are done here
                    else:
                        # no file selected (must have hit Cancel), and nothing from stdin
                        print('TableView: no input file selected!')
                        sys.exit(0)  # we are done here
        else:
            input_file_str = args['file']
            # normalize to absolute path
            input_file = pathlib.Path(input_file_str).resolve()
            input_file_str = str(input_file)
            print(f'reading data from file: {input_file_str}')
            if not input_file.is_file():
                raise Exception('File not found!')
            # Next - read the file data into a dictionary
            if input_file.is_file():
                with open(input_file_str, 'r', encoding='utf-8') as ifhan:
                    csv_reader = csv.reader(ifhan)
                    input_data = []
                    for row in csv_reader:
                        input_data.append(row)
            else:
                print(f'error: file [{input_file_str}] not found!')
                sys.exit()
    except Exception as ex:
        print('something went wrong: %s', ex)
        traceback.print_exc()
        sys.exit()

    # Finally - show a dialog with a TableView and the data
    try:
        show_object(input_data, input_file_str)
        # print(json.dumps(input_data, indent=4))
    except Exception as ex:
        print('exception: %s', ex)

    print('TableView: Exited.')
