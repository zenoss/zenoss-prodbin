###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2009, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################



def setTextValue( selenium, name, value ):
    selenium.type( name, value )
        
def setSelectValue( selenium, name, value ):
    selenium.select( name, value )

def setListValue( selenium, name, value ):
    for item in value:
        selenium.select( item )


_inputTypeMap = {
                'text':setTextValue,
                'select':setSelectValue,
                'list':setListValue
                }

class Input:
    def __init__(self, name, inputType):
        self._name = name
        self._inputMethod = _inputTypeMap[ inputType ]

    def setValue(self, selenium, value ):
        self._inputMethod( selenium, self._name, value )

class InputPage:
    """
    For a page with several input fields, create an InputPage with
    a map of the input names to the input types.  The input types
    can be one of text, select, or list.

    Once created, call setValue on the instance passing the selenium instance,
    the input name, and the value to be set.
    """
    def __init__(self, **kw):
        self.inputs={}
        for inputTitle, inputType in kw.iteritems():
            self.inputs[inputTitle] = Input( inputTitle, inputType )

    def setValue(self, selenium, name, value):
        self.inputs[name].setValue( selenium, value )
