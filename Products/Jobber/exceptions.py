##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2012, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


class NoSuchJobException(Exception):
    """
    No such job exists.
    """

class SubprocessJobFailed(Exception):
    """
    A subprocess job exited with a non-zero return code.
    """
    def __init__(self, exitcode):
        self.exitcode = exitcode
