#################################################################
#
#   Copyright (c) 2002 Zenoss, Inc. All rights reserved.
#
#################################################################

__doc__="""SnmpClassifier

Collects snmp data about a device which will be used to classify the device
Instances point the classifier to the oid to be collected.

$Id: ClassifierBase.py,v 1.1 2002/12/07 02:40:36 edahl Exp $"""

__version__ = "$Revision: 1.1 $"[11:-2]

from AccessControl import ClassSecurityInfo
from Globals import DTMLFile
from Globals import Persistent
from Globals import InitializeClass

from Products.ZCatalog import ZCatalog

def manage_addSnmpClassifier(context, id, title = None, REQUEST = None):
    """make a device"""
    ce = SnmpClassifier(id, title)
    context._setObject(ce.id, ce)

    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url()
                                     +'/manage_main')

addSnmpClassifier = DTMLFile('dtml/addSnmpClassifier',globals())


class SnmpClassifier(ZCatalog):
    """classify devices based on snmp information"""

    
