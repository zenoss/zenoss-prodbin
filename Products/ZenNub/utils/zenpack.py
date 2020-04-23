##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

# Provide access to zenpack data without the need for zodb.

import os
import pkg_resources
from pkg_resources import Requirement


def zenpack_names():
    for pkg in pkg_resources.iter_entry_points('zenoss.zenpacks'):
        yield pkg.module_name

def zenpack_directory(zenpack_name, in_module=True):
    file_name = '.'
    if in_module:
        file_name = zenpack_name.replace('.', '/') + "/" + file_name

    return os.path.normpath(pkg_resources.resource_filename(Requirement(zenpack_name), file_name))

def zenpack_has_file(zenpack_name, file_name, in_module=True):
    if in_module:
        file_name = zenpack_name.replace('.', '/') + "/" + file_name
    if pkg_resources.resource_isdir(Requirement(zenpack_name), file_name):
        return False
    return pkg_resources.resource_exists(Requirement(zenpack_name), file_name)

def zenpack_has_directory(zenpack_name, file_name, in_module=True):
    if in_module:
        file_name = zenpack_name.replace('.', '/') + "/" + file_name
    if not pkg_resources.resource_isdir(Requirement(zenpack_name), file_name):
        return False
    return pkg_resources.resource_exists(Requirement(zenpack_name), file_name)

def zenpack_file_string(zenpack_name, file_name, in_module=True):
    if in_module:
        file_name = zenpack_name.replace('.', '/') + "/" + file_name
    return pkg_resources.resource_string(Requirement(zenpack_name), file_name)

def zenpack_file_stream(zenpack_name, file_name, in_module=True):
    if in_module:
        file_name = zenpack_name.replace('.', '/') + "/" + file_name
    return pkg_resources.resource_stream(Requirement(zenpack_name), file_name)

def zenpack_listdir(zenpack_name, dir_name, in_module=True):
    if in_module:
        dir_name = zenpack_name.replace('.', '/') + "/" + dir_name

    return [os.path.normpath(pkg_resources.resource_filename(Requirement(zenpack_name), dir_name) + "/" + x) for x in pkg_resources.resource_listdir(Requirement(zenpack_name), dir_name)]




