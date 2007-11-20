###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

#
# Contained below are items used in selenium testing that don't fit elsewhere.
#
# Adam Modlin and Nate Avers
#

def getByValue (listName, value, formName="subdeviceForm"):
    """Handles checkbox selections"""
    return "dom=function fun (){var ha = document.forms.%s.elements['%s']; if (!ha.length)  ha=Array(ha); for (i = 0; i < ha.length; i++) {if (ha[i].value=='%s') return ha[i];}}; fun ()" %(formName, listName, value) 

class TimeoutError(Exception):
    """This will be thrown when an element is not found
        on a page and times out."""
    pass

def do_command_byname(selenium, command, name):
    """Runs specified command on all elements with the given name"""
    _flag = True
    i = 0
    while _flag:
       locator = "name=%s index=%s" % (name, i)
       try:
           selenium.do_command(command, [locator,])
           i += 1
       except Exception, data:
           if "ndex out of range" in data[0]: _flag = False
           else: raise Exception, data

