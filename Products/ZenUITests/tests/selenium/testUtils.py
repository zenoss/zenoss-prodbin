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
# Contained below is a function that returns the correct string to be
# interpeted as javascript.
#
# Adam Modlin and Nate Avers
#
import time


def getByValue (listName, value, formName="subdeviceForm"):
    return "dom=function fun (){var ha = document.forms.%s.elements['%s']; if (!ha.length)  ha=Array(ha); for (i = 0; i < ha.length; i++) {if (ha[i].value=='%s') return ha[i];}}; fun ()" %(formName, listName, value) 




class TimeoutException(Exception):
    """This will be thrown when an element is not found and times out
    """
    pass