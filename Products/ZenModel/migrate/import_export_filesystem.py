#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__='''

Create the directories on the file system necessary for importing and exporting
templates to and from Zenoss.

'''

__version__ = "$Revision$"[11:-2]


import Migrate

from Acquisition import aq_base

import os

zenhome = os.getenv('ZENHOME')

class ImportExportFilesystem(Migrate.Step):
    version = 23.0

    def cutover(self, dmd):
        for directory in ['import', 'export']:
            path = os.path.join(zenhome, directory)
            if not os.path.exists(path):
                os.mkdir(path)

ImportExportFilesystem()
