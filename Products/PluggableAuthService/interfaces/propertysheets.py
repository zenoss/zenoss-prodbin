##############################################################################
#
# Copyright (c) 2001 Zope Corporation and Contributors. All Rights
# Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this
# distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
""" Interfaces:  IPropertySheet

$Id: propertysheets.py 39343 2005-08-17 20:53:14Z sidnei $
"""

try:
    from zope.interface import Interface
except ImportError:
    from Interface import Interface

class IPropertySheet( Interface ):

    """ Interface for queryable property sheets.
    
    o Objects implementing this interface can play in read-only fashion
      in OFS.PropertySheets' framework.
    """

    def getId():

        """ Identify the sheet within a collection.
        """

    def hasProperty( id ):

        """ Does the sheet have a property corresponding to 'id'?
        """

    def getProperty( id, default=None ):

        """ Return the value of the property corresponding to 'id'.

        o If no such property exists within the sheet, return 'default'.
        """

    def getPropertyType( id ):

        """ Return the string identifying the type of property, 'id'.

        o If no such property exists within the sheet, return None.
        """

    def propertyInfo( id ):

        """ Return a mapping describing property, 'id'.

        o Keys must include:

          'id'  -- the unique identifier of the property.

          'type' -- the string identifying the property type.

          'meta' -- a mapping containing additional info about the property.
        """

    def propertyMap():

        """ Return a tuple of 'propertyInfo' mappings, one per property.
        """

    def propertyIds():

        """ Return a sequence of the IDs of the sheet's properties.
        """

    def propertyValues():

        """ Return a sequence of the values of the sheet's properties.
        """

    def propertyItems():

        """ Return a sequence of ( id, value ) tuples, one per property.
        """
