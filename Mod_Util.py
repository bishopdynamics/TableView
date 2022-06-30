#!/usr/bin/env python3

# Utility Module
#   General utility functions

# Created 2022 by James Bishop (james@bishopdynamics.com)

import os
import traceback
import datetime
import json
import pathlib


# read VERSION and commit_id to create a version string
def get_version(commit_id_file, version_file):
    with open(commit_id_file) as cf:
        commit_id = cf.read().splitlines()[0]
    with open(version_file) as vf:
        version = vf.read().splitlines()[0]
    version_string = '%s-%s' % (version.strip(), commit_id.strip())
    return version_string


# find the base folder
def get_basedir():
    basedir = pathlib.Path(os.path.dirname(__file__))
    return basedir


# print an object as a nice indented json string
def print_obj(this_object):
    print(json.dumps(this_object, indent=4))


# get a string timestamp in our standard format
def get_timestamp():
    timestamp_format = '%Y-%m-%d_%H%M%S%z'
    now_dto = datetime.datetime.now().astimezone()
    now_string = now_dto.strftime(timestamp_format)
    return now_string


# turn a worksheet from an xlsx workbook into a dictionary, with column names used for keys
def ws_to_dict(worksheet):
    #   first row is presumed to be column names
    #   first column is used as key within dict, so you have a dict of dicts
    newdict = {}
    rowindex = 0
    column_names = []
    for row in worksheet.iter_rows():
        if rowindex == 0:
            # first row is column names
            for cell in row:
                if cell.value is None:
                    break
                column_names.append(str(cell.value))
        else:
            if row[0].value is None:
                # consider any blank row to be the end
                break
            # create entry in dict
            newdict[row[0].value] = {}
            for i, colname in enumerate(column_names):
                newdict[row[0].value][colname] = str(row[i].value)
        rowindex += 1
    return newdict


# trim characters that commonly get in the way when comparing strings
def sanitize_string(product_name):
    # remove leading and trailing whitespace
    # remove leading and trailing commas
    return product_name.strip().strip(',')


# print a traceback for debugging
def print_traceback():
    print(traceback.format_exc())


def list_to_dict(input_list: list):
    # turn a list into a dict, with index s key
    newdict = {}
    for i in range(0, len(input_list)):
        newdict[i] = input_list[i]
    return newdict

# transform the product_name into what is used for g2 track product urls
#   TODO rename this, it is also for basic table ids


def product_name_to_urlname(product_name, separator: str = '-'):
    # lowercase, remove ()[]{}/\+ and replace spaces with separator
    #   for G2 product name urls, separator is "-"
    new_product_name = product_name.strip().lower().replace('(', '').replace(')', '')
    new_product_name = new_product_name.replace('[', '').replace(']', '')
    new_product_name = new_product_name.replace('{', '').replace('}', '')
    new_product_name = new_product_name.replace(
        '/', '').replace('\\', '').replace('+', '')
    new_product_name = new_product_name.replace(' ', separator)
    return new_product_name


# print a traceback for debugging
def print_traceback():
    print(traceback.format_exc())


# open a new browser tab with the given url
def open_browser(url: str):
    webbrowser.open_new_tab(url)
