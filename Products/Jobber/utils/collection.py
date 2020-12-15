##############################################################################
#
# Copyright (C) Zenoss, Inc. 2020, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

from __future__ import absolute_import

from collections import Mapping


class FrozenDictProxy(Mapping):

    def __init__(self, source):
        self.__source = source

    def __getitem__(self, key):
        return self.__source[key]

    def __iter__(self):
        return iter(self.__source)

    def __len__(self):
        return len(self.__source)
