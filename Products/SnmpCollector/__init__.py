#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################
__doc__="""__init__

Initialize the Confmon Product

$Id: __init__.py,v 1.2 2002/06/14 20:01:10 edahl Exp $"""


__version__ = "$Revision: 1.2 $"[11:-2]
def initialize(registrar):
    # Global module assertions for Python scripts
    from Products.PythonScripts.Utility import allow_module
    allow_module('Products.SnmpCollector.snmp')

    from SnmpTableMap import SnmpTableMap, addSnmpTableMap, manage_addSnmpTableMap
    from SnmpAttMap import SnmpAttMap, addSnmpAttMap, manage_addSnmpAttMap
    registrar.registerClass(
        SnmpAttMap,
        constructors = (addSnmpAttMap, manage_addSnmpAttMap),
        )
    registrar.registerClass(
        SnmpTableMap,
        constructors = (addSnmpTableMap, manage_addSnmpTableMap),
        )
        #icon = 'www/Folder_icon.gif')
