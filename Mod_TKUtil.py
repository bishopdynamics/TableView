#!/usr/bin/env python3

# Tk Utility Module
#   Tk utility classes - abstraction layer on top of Tk, to simplify usage

# Created 2022 by James Bishop (james@bishopdynamics.com)

# UI Abstraction Layer
#   these classes provide an abstraction layer on top of the primitives provided by Tk
#   in our system, grid layout is mandatory, and we use 1-indexed col/row numbers
#   Tk has a single object "Treeview" which handles duties for both hierarchical and columnar data
#       our abstractions "TkTableView" and "TkTreeView" simplify usage for each,
#       including helper methods to load a list or dictionary, respectively

import uuid
import random
import json
import tkinter
import tkinter.ttk
import tkinter.filedialog
import traceback
import webbrowser

from typing import Literal

# NOTE padding for x and y are linked, but for now everything is default

DEFAULT_PADDING = 5  # pixels, if you dont provide padding=, then this is the default
DEFAULT_FONT_SMALL = ('Arial', 10)
DEFAULT_FONT = ('Arial', 12)  # used for almost everything by default
DEFAULT_FONT_MEDIUM = ('Arial', 16)
DEFAULT_FONT_LARGE = ('Arial', 24)

# TODO font licensing?

# Debugging: show colored borders around things for debugging
#   choose one or more from DEBUG_ELEMENT_LIST
DEBUG_ELEMENTS = []
DEBUG_ELEMENT_LIST = ['frame', 'label', 'spacer', 'button',
                      'checkbox', 'table', 'tree', 'progressbar', 'combobox', 'textentry']
# colors will be randomly chosen from here
DEBUG_COLORS = ['red', 'yellow', 'blue', 'white', 'pink']

# TODO add method to all ui widgets that we can call to change debug state
#   so that we can trigger changes from within ui (menubar, checks for each)
#   should move frame_wrapper to TkWidget, and add a method to set debug


def sanitize_name(product_name, separator: str = '-'):
    # lowercase, remove ()[]{}/\+ and replace spaces with separator
    new_product_name = product_name.strip().lower().replace('(', '').replace(')', '')
    new_product_name = new_product_name.replace('[', '').replace(']', '')
    new_product_name = new_product_name.replace('{', '').replace('}', '')
    new_product_name = new_product_name.replace(
        '/', '').replace('\\', '').replace('+', '')
    new_product_name = new_product_name.replace(' ', separator)
    return new_product_name


def list_to_dict(input_list: list):
    # turn a list into a dict, with index + 1 as keys
    newdict = {}
    for i in range(0, len(input_list)):
        newdict[i + 1] = input_list[i]
    return newdict

# print a traceback
def print_traceback():
    print(traceback.format_exc())


# open a new browser tab with the given url
def open_browser(url: str):
    webbrowser.open_new_tab(url)


class TkWindow(tkinter.Tk):
    # give the basic window object some helpers

    def __init__(self, title: str = '',
                 width: int = 300, height: int = 300,
                 resizable: bool = True,
                 minwidth: int = 20, minheight: int = 20,
                 maxwidth: int = 65536, maxheight: int = 65536,
                 offset_x: int = 0, offset_y: int = 0):
        super().__init__()
        self.on_close_function = None
        try:
            # calculate a starting point, middle of screen
            self.startpoint_x = (self.winfo_screenwidth() /
                                 2) - (width / 2) + offset_x
            self.startpoint_y = (self.winfo_screenheight() /
                                 2) - (height / 2) + offset_y
            # set the title
            self.title(title)
            # make the window resizable
            self.wm_resizable(resizable, resizable)
            # setup sizing of the main window
            self.geometry('%dx%d+%d+%d' %
                          (width, height, self.startpoint_x, self.startpoint_y))
            self.minsize(width=minwidth, height=minheight)
            self.maxsize(width=maxwidth, height=maxheight)
            # window is a 1x1 grid
            self.rowconfigure(0, weight=1)
            self.columnconfigure(0, weight=1)
            self.protocol("WM_DELETE_WINDOW", self.close)
        except Exception as ex:
            print('Error while initializing Window: %s' % ex)
            print_traceback()

    def close(self):
        # close this window
        self.destroy()


class TkWidget(tkinter.BaseWidget, tkinter.Grid):
    # this is the base class of our fancy little tk wrapper library
    #   adds explicit 1-indexed placement in parent grid, and unified default padding
    def __init__(self, parent, parent_col: int, parent_row: int,
                 sticky='', padding: int = DEFAULT_PADDING,
                 ):
        tkinter.Grid.__init__(parent)
        if parent_col == 0:
            return  # skip setting up grid if no cols
        if parent_row == 0:
            return  # skip setting up grid if no rows
        self.grid(column=(parent_col - 1), row=(parent_row - 1),
                  sticky=sticky, padx=padding, pady=padding)


class TkFrame(tkinter.Frame, TkWidget):
    # a frame with extra controls
    #   cols/rows - configure the grid inside this frame
    #   spacecol/spacerow - set a col/row as a spacer which will expand and push away other elements in the col/row.
    #       in this case all other cols/rows will get weight 0, and this spacecol/spacerow will get weight 1
    #       otherwise all cols/rows get weight 1
    #   for auto-resizing to work as expected, you actually need more than one col/row, so in cases where a frame only has 1 of each, we add an extra
    def __init__(self, parent, parent_col: int, parent_row: int,
                 cols: int, rows: int,
                 spacecol: int = 0, spacerow: int = 0,
                 sticky='', padding: int = DEFAULT_PADDING,
                 width: int = None, height: int = None,):
        tkinter.Frame.__init__(self, parent)
        TkWidget.__init__(self, parent, parent_col=parent_col,
                          parent_row=parent_row, sticky=sticky, padding=padding)
        if 'frame' in DEBUG_ELEMENTS:
            border_color = random.choice(DEBUG_COLORS)
            self.config(highlightthickness=1, highlightcolor=border_color,
                        highlightbackground=border_color)
        # configure columns
        if cols > 0:
            if cols == 1:
                # minimum two columns for proper autoresize, so we just toss in an extra with zero weight
                self.columnconfigure(0, weight=1)
                self.columnconfigure(1, weight=0)
            else:
                for c in range(0, (cols - 1)):
                    if spacecol > 0:
                        if c == (spacecol - 1):
                            self.columnconfigure(c, weight=1)
                        else:
                            self.columnconfigure(c, weight=0)
                    else:
                        self.columnconfigure(c, weight=1)
        # configure rows
        if rows > 0:
            if rows == 1:
                # minimum two rows for proper autoresize, so we just toss in an extra with zero weight
                self.rowconfigure(0, weight=1)
                self.rowconfigure(1, weight=0)
            else:
                for r in range(0, (rows - 1)):
                    if spacerow > 0:
                        if r == (spacerow - 1):
                            self.rowconfigure(r, weight=1)
                        else:
                            self.rowconfigure(r, weight=0)
                    else:
                        self.rowconfigure(r, weight=1)
        # setup width/height
        if width:
            self.config(width=width)
        if height:
            self.config(height=height)


class TkLabel(tkinter.Label, TkWidget):
    # basic label, enhanced with word wrapping technology!
    def __init__(self, parent, parent_col: int, parent_row: int,
                 text: str, wraplength: int = None,
                 font: tuple = DEFAULT_FONT,
                 anchor: Literal['nw', 'n', 'ne', 'w',
                                 'center', 'e', 'sw', 's', 'se'] = 'center',
                 justify: Literal['left', 'center', 'right'] = 'center',
                 sticky='', padding: int = DEFAULT_PADDING,
                 width: int = None, height: int = None):
        if wraplength:
            tkinter.Label.__init__(self, parent, text=text, anchor=anchor,
                                   wraplength=wraplength, font=font, justify=justify)
        else:
            tkinter.Label.__init__(
                self, parent, text=text, anchor=anchor, font=font, justify=justify)
        TkWidget.__init__(self, parent, parent_col=parent_col,
                          parent_row=parent_row, sticky=sticky, padding=padding)
        if 'label' in DEBUG_ELEMENTS:
            border_color = random.choice(DEBUG_COLORS)
            self.config(highlightthickness=1, highlightcolor=border_color,
                        highlightbackground=border_color)
        # TODO this might be a way to do dynamic word wrap on labels
        # self.bind('<Configure>', lambda e: self.config(wraplength=self.winfo_width()))
        # setup width/height
        if width:
            self.config(width=width)
        if height:
            self.config(height=height)


class TkURLLabel(tkinter.Label, TkWidget):
    # just like a label but its blue
    #   and when you click it, it tries to open the url in a browser
    #   and when you hover over it, the cursor changes to a hand
    def __init__(self, parent, parent_col: int, parent_row: int,
                 url: str, wraplength: int = None,
                 font: tuple = DEFAULT_FONT,
                 anchor: Literal['nw', 'n', 'ne', 'w',
                                 'center', 'e', 'sw', 's', 'se'] = 'center',
                 justify: Literal['left', 'center', 'right'] = 'center',
                 sticky='', padding: int = DEFAULT_PADDING,
                 width: int = None, height: int = None):
        if wraplength:
            tkinter.Label.__init__(self, parent, text=url, anchor=anchor, wraplength=wraplength,
                                   font=font, fg='blue', cursor='hand2', justify=justify)
        else:
            tkinter.Label.__init__(self, parent, text=url, anchor=anchor,
                                   font=font, fg='blue', cursor='hand2', justify=justify)
        TkWidget.__init__(self, parent, parent_col=parent_col,
                          parent_row=parent_row, sticky=sticky, padding=padding)
        self.bind('<Button-1>', lambda e: open_browser(url))
        if 'label' in DEBUG_ELEMENTS:
            border_color = random.choice(DEBUG_COLORS)
            self.config(highlightthickness=1, highlightcolor=border_color,
                        highlightbackground=border_color)
        if width:
            self.config(width=width)
        if height:
            self.config(height=height)


class TkButton(tkinter.Button, TkWidget):
    # a basic button, supplemented to make assigning callbacks easier
    def __init__(self, parent, parent_col: int, parent_row: int,
                 text: str,
                 state: Literal['normal', 'disabled', 'readonly'] = 'normal',
                 font: tuple = DEFAULT_FONT,
                 anchor: Literal['nw', 'n', 'ne', 'w',
                                 'center', 'e', 'sw', 's', 'se'] = 'center',
                 justify: Literal['left', 'center', 'right'] = 'center',
                 sticky='', padding: int = DEFAULT_PADDING,
                 ):
        tkinter.Button.__init__(
            self, parent, text=text, state=state, justify=justify, anchor=anchor, font=font)
        TkWidget.__init__(self, parent, parent_col=parent_col,
                          parent_row=parent_row, sticky=sticky, padding=padding)
        self.grid(column=(parent_col - 1), row=(parent_row - 1),
                  sticky=sticky, padx=padding, pady=padding)
        if 'button' in DEBUG_ELEMENTS:
            border_color = random.choice(DEBUG_COLORS)
            self.config(highlightthickness=1, highlightcolor=border_color,
                        highlightbackground=border_color)

    def on_click(self, callback: callable):
        # convenience method to assign callback
        self.config(command=callback)


class TkProgressBar(tkinter.ttk.Progressbar, TkWidget):
    # a basic horizontal progress bar
    #   TODO this can be tweaked to support vertical too!
    def __init__(self, parent, parent_col: int, parent_row: int,
                 value: int,
                 sticky='', padding: int = DEFAULT_PADDING):
        self.frame_wrapper = TkFrame(
            parent, parent_col=parent_col, parent_row=parent_row, cols=1, rows=1, sticky=sticky, padding=padding)
        tkinter.ttk.Progressbar.__init__(
            self, self.frame_wrapper, value=value, orient='horizontal')
        TkWidget.__init__(self, self.frame_wrapper, parent_col=1,
                          parent_row=1, sticky='nsew', padding=0)
        if 'treeview' in DEBUG_ELEMENTS:
            border_color = random.choice(DEBUG_COLORS)
            self.frame_wrapper.config(
                highlightthickness=1, highlightcolor=border_color, highlightbackground=border_color)


class TkCheckbox(tkinter.Checkbutton, TkWidget):
    # Checkbox, toggling a bool value
    #   the Tk Checkbutton is very flexible, extra config is needed to make it behave like a basic boolean checkbox
    def __init__(self, parent, parent_col: int, parent_row: int,
                 text: str, value: bool = False,
                 state: Literal['normal', 'disabled', 'readonly'] = 'normal',
                 font: tuple = DEFAULT_FONT,
                 anchor: Literal['nw', 'n', 'ne', 'w',
                                 'center', 'e', 'sw', 's', 'se'] = 'center',
                 justify: Literal['left', 'center', 'right'] = 'center',
                 sticky='', padding: int = DEFAULT_PADDING,
                 ):
        self.data_variable = tkinter.BooleanVar(parent, value=value)
        tkinter.Checkbutton.__init__(self, parent, onvalue=True, offvalue=False, text=text,
                                     variable=self.data_variable, anchor=anchor, justify=justify, state=state, font=font)
        TkWidget.__init__(self, parent, parent_col=parent_col,
                          parent_row=parent_row, sticky=sticky, padding=padding)
        if 'checkbox' in DEBUG_ELEMENTS:
            border_color = random.choice(DEBUG_COLORS)
            self.config(highlightthickness=1, highlightcolor=border_color,
                        highlightbackground=border_color)

    def on_change(self, callback: callable):
        # add an onchange callback
        self.config(command=callback)

    def get_value(self):
        return self.data_variable.get()

    def set_value(self, value):
        # set the value
        self.data_variable.set(value)


class TkSpacer(tkinter.Frame, TkWidget):
    # put this inside a spacer row/column
    #   exists mostly for visualization in debugging
    def __init__(self, parent, parent_col: int, parent_row: int):
        tkinter.Frame.__init__(self, parent)
        TkWidget.__init__(self, parent, parent_col=parent_col,
                          parent_row=parent_row, sticky='nsew')
        if 'spacer' in DEBUG_ELEMENTS:
            border_color = random.choice(DEBUG_COLORS)
            self.config(highlightthickness=1, highlightcolor=border_color,
                        highlightbackground=border_color)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)


class TkSeparator(tkinter.ttk.Separator, TkWidget):
    # a basic, horizontal or vertical line, used as a separator
    def __init__(self, parent, parent_col: int, parent_row: int,
                 orientation: Literal['horizontal', 'vertical'],
                 sticky='', padding: int = DEFAULT_PADDING):
        tkinter.ttk.Separator.__init__(self, parent, orient=orientation)
        TkWidget.__init__(self, parent, parent_col=parent_col,
                          parent_row=parent_row, sticky=sticky, padding=padding)


class TkTableView(tkinter.ttk.Treeview, TkWidget):
    # Supplement Tk Treeview to behave like a tableview, with methods for loading data
    #   also wrapped in a TkFrame so that we can optionally add scrollbars
    def __init__(self, parent, parent_col: int, parent_row: int,
                 column_headings: list[str], column_widths: list[int], value: list = None,
                 scrollbar_horizontal: bool = False, scrollbar_vertical: bool = False,
                 sticky='', padding: int = DEFAULT_PADDING):
        # need to wrap everything in a frame so we can add scrollbars
        self.frame_wrapper = TkFrame(parent, parent_col=parent_col, parent_row=parent_row,
                                     cols=2, rows=2, spacecol=1, spacerow=1, sticky=sticky, padding=padding)
        tkinter.ttk.Treeview.__init__(self, self.frame_wrapper)

        if scrollbar_vertical:
            self.scrollbar_vertical = tkinter.Scrollbar(
                self.frame_wrapper, orient='vertical', command=self.yview)
            self.scrollbar_vertical.grid(column=1, row=0, sticky='ns')
            self.config(yscrollcommand=self.scrollbar_vertical.set)

        if scrollbar_horizontal:
            self.scrollbar_horizontal = tkinter.Scrollbar(
                self.frame_wrapper, orient='horizontal', command=self.xview)
            self.scrollbar_horizontal.grid(column=0, row=1, sticky='ew')
            self.config(xscrollcommand=self.scrollbar_horizontal.set)

        TkWidget.__init__(self, self.frame_wrapper, parent_col=1,
                          parent_row=1, sticky='nsew', padding=0)
        # pack table and scrollbars into frame_wrapper

        # border for frame_wrapper if debug
        if 'table' in DEBUG_ELEMENTS:
            border_color = random.choice(DEBUG_COLORS)
            self.frame_wrapper.config(
                highlightthickness=1, highlightcolor=border_color, highlightbackground=border_color)
        self.column_headings = column_headings
        self.column_ids = []
        try:
            for entry in self.column_headings:
                # sanitize headings and use them as column ids
                col_id = sanitize_name(entry, separator='_')
                self.column_ids.append(col_id)
            self.config(columns=self.column_ids)
            # '#0' is the root object, because this is a "tree", and it occupies its own column
            self.column('#0', width=0, stretch=False)
            self.heading('#0', anchor='center', text='')
            # iterate over column definitions
            for col_num in range(0, len(self.column_ids)):
                column_id = self.column_ids[col_num]
                self.column(column_id, width=column_widths[col_num])
                self.heading(column_id, anchor='center',
                             text=self.column_headings[col_num], command=lambda _col=column_id: self.treeview_sort_column(_col, False))
            if value is not None:
                self.load_list(value)
        except Exception as ex:
            print('Error initializing TableView: %s' % ex)
            print_traceback()

    def get_wrapper(self):
        # need to get wrapper to use it
        return self.frame_wrapper

    def clear_data(self):
        # clear all existing entries
        for item in self.get_children():  # delete all items in the treeview
            try:
                self.delete(item)
            except Exception as ex:
                print(
                    'Warning: failed to delete an item in TkTableView.clear_data(): %s' % ex)
                continue

    def load_list(self, input_list: list, reverse_rows: bool = False):
        # load a list of rows into this table
        #   reverse_rows allows the top -> down ordering of the input data to be reversed,
        #       so the bottom row of data is the top row of the table
        try:
            if reverse_rows:
                list_in_order = input_list.copy()
                list_in_order.reverse()
            else:
                list_in_order = input_list
            # clear the table
            self.clear_data()
            # now repopulate it
            for index, entry in enumerate(list_in_order):
                self.insert('', index=index, values=entry)
        except Exception as ex:
            print('Error loading list into TableView: %s' % ex)
            print_traceback()

    def clear_selection(self):
        # clear any selected rows
        if len(self.selection()) > 0:
            for i in self.selection():
                self.selection_remove(i)

    def get_row_from_id(self, row_identifier, use_headers=False):
        # using result of .identify_row(event.y) or .selection(), return dict of data in that row
        row_values = self.item(row_identifier)['values']
        row_dict = {}
        for i in range(0, (len(row_values))):
            value = row_values[i]
            if use_headers:
                # use headers as keys
                key = self.column_headings[i]
            else:
                # use the column_ids we generated from headers
                key = self.column_ids[i]
            row_dict[key] = value
        return row_dict

    def get_selection(self, use_headers=False):
        # returns the contents of selected rows
        #   each row is a dictionary, with column_id as key (sanitized header names)
        #   if use_headers=True, then use header name as key
        selection = self.selection()
        sel_vals = []
        for sel in selection:
            row_dict = self.get_row_from_id(sel, use_headers=use_headers)
            sel_vals.append(row_dict)
        return sel_vals

    def on_change(self, callback: callable):
        # called when selection changes
        self.bind('<ButtonRelease-1>', callback)

    def on_right_click(self, callback: callable):
        # called when right-click on item
        self.bind('<Button-2>', callback)

    def treeview_sort_column(self, col, reverse):
        self.clear_selection()
        data_list = [(self.set(k, col), k) for k in self.get_children('')]
        data_list.sort(reverse=reverse)
        # rearrange items in sorted positions
        for index, (_val, k) in enumerate(data_list):
            self.move(k, '', index)
        # reverse sort next time
        self.heading(
            col, command=lambda: self.treeview_sort_column(col, not reverse))


class TkTreeView(tkinter.ttk.Treeview, TkWidget):
    # Supplement Tk Treeview with methods for loading data, expand all, collapse all
    #   display an arbitrary dictionary (of values that can convert to str)
    def __init__(self, parent, parent_col: int, parent_row: int, value: dict = None, sticky='', padding: int = DEFAULT_PADDING, show_units: bool = False, sort_keys: bool = True):
        self.frame_wrapper = TkFrame(
            parent, parent_col=parent_col, parent_row=parent_row, cols=1, rows=1, sticky=sticky, padding=padding)
        tkinter.ttk.Treeview.__init__(self, self.frame_wrapper)
        TkWidget.__init__(self, self.frame_wrapper, parent_col=1,
                          parent_row=1, sticky='nsew', padding=0)
        if 'treeview' in DEBUG_ELEMENTS:
            border_color = random.choice(DEBUG_COLORS)
            self.frame_wrapper.config(
                highlightthickness=1, highlightcolor=border_color, highlightbackground=border_color)
        self.tree_nodes = []  # track all nodes of the tree in a flat list, for iterating
        # copy of current data loaded into tree will be stored here for convenvient retrieval
        self.tree_data = {}
        # show units in nodes with children, such a: [2 keys]
        self.show_units = show_units
        self.sort_keys = sort_keys  # wether to sort dict keys
        column_widths = [100, 300, 0]
        column_headings = ['Key', 'Value', '']
        column_ids = ['#0', 'key', 'value']
        self.config(columns=['key', 'value'])  # column ids (other than '#0')
        for col_num in range(0, len(column_ids)):
            column_id = column_ids[col_num]
            self.heading(column_id, anchor='w', text=column_headings[col_num])
            self.column(column_id, width=column_widths[col_num])
        if value is not None:
            self.load_dict(value)

    def insert_tree_node(self, node_data, parent: str = ''):
        # insert a node to the tree, as a child of the given parent
        #   this method is used recursively
        #   if data is a dict, we recursively process its keys and add nodes for them
        #   if data is a set, we turn it into a list
        #   if data is a list, we recursively process its entries and add nodes for them
        #   if data is a multiline string, we recursively process each line as if they were entries in a list
        #   NOTE: this method was lass blessed as "perfect" on Apr 27, 2022, 2:06pm PST. dont touch it
        if isinstance(node_data, type(set())):
            # turn set into list
            node_data = sorted(node_data)
        if isinstance(node_data, dict) and self.sort_keys:
            # sort dictionary keys
            node_data = dict(sorted(node_data.items()))
        for key in node_data:
            uid = str(uuid.uuid4())
            self.tree_nodes.append(uid)
            # print('traversing key: %s' % key)
            value = node_data[key]
            if isinstance(value, type(set())):
                # turn any values of type set into list
                value = sorted(value)
            if isinstance(value, dict):
                if self.show_units:
                    key_name = '%s [dict] (%d keys)' % (key, len(value.keys()))
                else:
                    key_name = '%s (%d)' % (key, len(value.keys()))
                self.insert(parent, 'end', uid, text=key_name)
                self.insert_tree_node(value, uid)
            elif isinstance(value, list):
                if len(value) == 0:
                    # turn empty lists into (empty)
                    if self.show_units:
                        self.insert(parent, 'end', uid, text=key +
                                    ' [list] (0 items):', values=['(empty)'])
                    else:
                        self.insert(parent, 'end', uid, text=key +
                                    ' (0):', values=['(empty)'])
                else:
                    list_as_dict = list_to_dict(value)
                    if self.show_units:
                        self.insert(parent, 'end', uid, text=key +
                                    ' [list] (%d items):' % len(list_as_dict))
                    else:
                        self.insert(parent, 'end', uid, text=key +
                                    ' (%d):' % len(list_as_dict))
                    self.insert_tree_node(list_as_dict, uid)
            else:
                try:
                    if value is None:
                        # if value is empty, replace it with string 'None' to give something in the UI
                        value = 'None'
                    else:
                        if isinstance(value, str):
                            if len(value.splitlines()) > 1:
                                # this multiline string will look ugly in the treeview
                                #   lets turn it into an array of lines
                                value_as_lines = value.splitlines()
                                # we ended up with a list of lines, lets treat it like a list
                                if self.show_units:
                                    self.insert(
                                        parent, 'end', uid, text=key + ' [text] (%d lines): ' % len(value_as_lines))
                                else:
                                    self.insert(
                                        parent, 'end', uid, text=key + ' (%d): ' % len(value_as_lines))
                                self.insert_tree_node(
                                    list_to_dict(value_as_lines), uid)
                                continue  # otherwise tree.insert below will create a duplicate entry
                        else:
                            value = str(value)
                    # hopefully now we have a string, lets add it
                    # below, remember values needs to be an array in this context
                    self.insert(parent, 'end', uid, text=key, values=[value])
                except Exception as ex:
                    print('failed to insert value for key: %s, error: %s' %
                          (str(key), ex))
                    continue

    def load_dict(self, input_dict: dict):
        # load a dictionary into the treeview
        try:
            self.clear_data()  # first clear out existing data
            # now populate it
            if input_dict is None:
                input_dict = {
                    'data': 'no data'
                }
            self.insert_tree_node(input_dict)
            self.tree_data = input_dict.copy()
        except Exception as ex:
            print('Error loading dict into TreeView: %s' % ex)
            print_traceback()

    def get_data(self):
        # helper method to get currently loaded data
        return self.tree_data

    def clear_data(self):
        # clear data from treeview
        self.tree_nodes = []  # clear our nodes list
        self.tree_data = {}  # clear stored copy of loaded data
        for item in self.get_children():  # delete all items in the treeview
            self.delete(item)

    def expand(self):
        # expand all items of treeview
        for item in self.tree_nodes:
            self.item(item, open=True)

    def collapse(self):
        # collapse all items of treeview
        for item in self.tree_nodes:
            self.item(item, open=False)


class TkCombobox(tkinter.ttk.Combobox, TkWidget):
    # combobox
    def __init__(self, parent, parent_col: int, parent_row: int,
                 state: str = 'readonly',
                 font: tuple = DEFAULT_FONT, options: list[tuple[int, str]] = None,
                 justify: Literal['left', 'center', 'right'] = 'center',
                 sticky='', padding: int = DEFAULT_PADDING):
        self.combobox_values = {}  # stores values, indexed by display string
        self.combobox_textvariable = None
        self.on_change_callback = None
        # wrap in a frame so we can highlight for debugging
        self.frame_wrapper = TkFrame(
            parent, parent_col=parent_col, parent_row=parent_row, cols=1, rows=1, sticky=sticky, padding=padding)
        tkinter.ttk.Combobox.__init__(
            self, self.frame_wrapper, state=state, justify=justify, font=font)
        TkWidget.__init__(self, self.frame_wrapper, parent_col=1,
                          parent_row=1, sticky='nsew', padding=0)
        self.bind('<<ComboboxSelected>>', self.combobox_changed)
        if 'combobox' in DEBUG_ELEMENTS:
            border_color = random.choice(DEBUG_COLORS)
            self.frame_wrapper.config(
                highlightthickness=1, highlightcolor=border_color, highlightbackground=border_color)
        if options:
            # if options provided, populate with first one selected
            self.populate(options, 0)

    def on_change(self, callback: callable):
        # assign an on_change callback
        self.on_change_callback = callback

    def set_value(self, value: int):
        # set the selected value
        self.current(value)

    def get_value(self):
        # values of the combobox are the display string, so we need to translate that back to value
        selected_item_display = self.get()
        selected_item_value = self.combobox_values[selected_item_display]
        return selected_item_value

    def combobox_changed(self, _event):
        # onchange callback
        selected_item_value = self.get_value()
        self.on_change_callback(selected_item_value)

    def populate(self, options: list[tuple[int, str]], selected: int = 0):
        # populate using list of tuples (value, display)
        for (value, display) in options:
            self.combobox_values[display] = value
        values = list(self.combobox_values.keys())
        self.combobox_textvariable = tkinter.StringVar()
        self.config(textvariable=self.combobox_textvariable)
        self.config(values=values)
        self.current(selected)


class TkTextEntry(tkinter.Entry, TkWidget):
    # tricked out text entry widget
    #   sensitive = shows * instead of what you type
    def __init__(self, parent, parent_col: int, parent_row: int,
                 text: str = '', state: Literal['normal', 'disabled', 'readonly'] = 'normal',
                 sensitive: bool = False,
                 font: tuple = DEFAULT_FONT,
                 justify: Literal['left', 'center', 'right'] = 'center',
                 sticky='', padding: int = DEFAULT_PADDING):
        self.data_variable = tkinter.StringVar(parent, value=text)
        tkinter.Entry.__init__(
            self, parent, textvariable=self.data_variable, state=state, justify=justify, font=font)
        TkWidget.__init__(self, parent, parent_col=parent_col,
                          parent_row=parent_row, sticky=sticky, padding=padding)
        if sensitive:
            self.config(show='*')
        if 'textentry' in DEBUG_ELEMENTS:
            border_color = random.choice(DEBUG_COLORS)
            self.config(highlightthickness=1, highlightcolor=border_color,
                        highlightbackground=border_color)

    def get_value(self):
        # retrieve current value of the text field
        value = self.data_variable.get()
        return value

    def set_value(self, value):
        # set the value
        self.data_variable.set(value)


class TkBasicDialogText(TkWindow):
    # create a basic dialog with some text and an ok button
    #   provide url, and it will be below the text, blue and clickable
    def __init__(self, title: str, text: str, button_text: str = 'Close', url: str = None,
                 resizable: bool = False, width: int = 200, height: int = 200, minwidth: int = 200, minheight: int = 200):
        super().__init__(title=title, width=width, height=height,
                         minwidth=minwidth, minheight=minheight, resizable=resizable)
        root_frame = TkFrame(self, parent_col=1, parent_row=1,
                             cols=1, rows=2, spacerow=1, sticky='nsew')
        TkLabel(root_frame, parent_col=1, parent_row=1, text=text, anchor='center',
                sticky='nsew', wraplength=(width - (DEFAULT_PADDING * 8)), justify='left')
        if url:
            TkURLLabel(root_frame, parent_col=1, parent_row=2, url=url)
        button_ok = TkButton(root_frame, parent_col=1,
                             parent_row=3, text=button_text, sticky='ew')
        button_ok.config(command=self.close)


class TkRadioButtonGroup(tkinter.Frame, TkWidget):
    # a collection of radiobuttons
    #   options is a list of tuples (value, display)
    def __init__(self, parent, parent_col: int, parent_row: int, options: list[tuple[int, str]], orientation: Literal['horizontal', 'vertical'] = 'horizontal'):
        tkinter.Frame.__init__(self, parent)
        TkWidget.__init__(self, parent, parent_col=parent_col,
                          parent_row=parent_row, sticky='nsew')
        if 'radiobutton' in DEBUG_ELEMENTS:
            border_color = random.choice(DEBUG_COLORS)
            self.config(highlightthickness=1, highlightcolor=border_color,
                        highlightbackground=border_color)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        # container frame for radiobuttons
        button_frame = tkinter.Frame(self)
        button_frame.grid(column=0, row=0)
        self.radiobuttons = []  # track all our radiobuttons here
        self.variable = tkinter.IntVar()
        self.callback = None
        index = 0
        if orientation == 'horizontal':
            button_frame.rowconfigure(0, weight=1)
        else:
            button_frame.columnconfigure(0, weight=1)
        # create buttons
        for (value, display) in options:
            radio_button = tkinter.Radiobutton(
                button_frame, text=display, value=value, variable=self.variable, command=self._on_change)
            self.radiobuttons.append(radio_button)
            if orientation == 'horizontal':
                button_frame.columnconfigure(index, weight=1)
                radio_button.grid(column=index, row=0)
            else:
                button_frame.rowconfigure(index, weight=1)
                radio_button.grid(column=0, row=index)
            index += 1

    def get_value(self):
        return self.variable.get()

    def set_value(self, value: int):
        self.variable.set(value)

    def on_click(self, callback: callable):
        self.callback = callback

    def _on_change(self, _event=None):
        if self.callback:
            self.callback(self.get_value())


def show_object(this_object, object_name):
    # show a dialog with tableview populated by this object, used for debugging
    #   TODO this is blocking, so causes execution to stop wherever this was called
    DialogTableview('TableView', summary='File: %s' % object_name, width=800,
                    height=500, resizable=True, focus_force=True, data=this_object)


class DialogTableview(object):
    # Generic Tableview Dialog
    #   if you provide data, it will be loaded into the tableview immediately
    def __init__(self, name: str, data: dict = None, summary: str = None, description: str = None,
                 height: int = 400, width: int = 300, resizable=False, focus_force=False):
        super().__init__()
        self.name = name
        self.data = data
        self.focus_force = focus_force
        self.tableview_result = None
        try:
            self.window = TkWindow(name, width=width, height=height, minwidth=200, minheight=300, resizable=resizable)
            # this is the overall window, the container of all containers
            frame_root = TkFrame(self.window, parent_col=1, parent_row=1, cols=1, rows=4, spacerow=2, sticky='nsew')
            frame_root.rowconfigure(0, weight=0)
            frame_root.rowconfigure(1, weight=1)
            frame_top_section = TkFrame(
                frame_root, parent_col=1, parent_row=1, cols=1, rows=3, sticky='ewn')
            if summary:
                TkLabel(frame_top_section, parent_col=1, parent_row=1,text=summary, font=DEFAULT_FONT_LARGE, sticky='ew')
            if description:
                TkLabel(frame_top_section, parent_col=1, parent_row=2, text=description,font=DEFAULT_FONT_MEDIUM, sticky='ew', wraplength=(width - 10))
            # need to split headings from data
            headings = self.data[0]
            col_widths = []
            for _ent in headings:
                col_widths.append('100')  # default every col width to 100
            self.tableview_result = TkTableView(
                frame_root, parent_col=1, parent_row=2, sticky='nsew',
                column_headings=headings, column_widths=col_widths, scrollbar_horizontal=True, scrollbar_vertical=True)
        except Exception as ex:
            print('exception while building ui: %s' % ex)
            print_traceback()
        # schedule setup_backend to run within the loop
        self.window.after(100, self.setup_backend)
        self.window.mainloop()

    @staticmethod
    def log_msg(message):
        # what to do with messages?
        print('TableView: %s' % message)

    def setup_backend(self):
        # setup any backend stuffs
        if self.focus_force:
            self.window.focus_force()
        if self.data is not None:
            self.log_msg('Rendering table...')
            self.tableview_result.load_list(self.data[1:])  # trim headings from data
            self.log_msg('Done rendering table.')

    def cleanup(self):
        # cleanup any connections
        self.window.destroy()
