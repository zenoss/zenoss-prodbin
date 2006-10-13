##############################################################################
#
# Copyright (c) 2001 Zope Corporation and Contributors. All Rights
# Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this
# distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE
#
##############################################################################
""" PluginRegistry interface declarations

$Id: interfaces.py 40099 2005-11-14 20:48:24Z tseaver $
"""
try:
    from zope.interface import Interface
except:  # BBB?
    from Interface import Interface
    _HAS_Z3_INTERFACES = False
else:
    _HAS_Z3_INTERFACES = True

class IPluginRegistry( Interface ):


    """ Manage a set of plugin definitions, grouped by type.
    """
    def listPluginTypeInfo():

        """ Return a sequence of mappings describing our plugin types.

        o Keys for the mappings must include:

          'id' -- a string used to identify the plugin type (should be
            the __name__ of the interface)

          'interface' -- the plugin type interface

          'methods' -- the methods expected by the plugin type interface

          'title' -- a display title for the plugin type

          'description' -- a description of what the plugins do
        """

    def listPlugins( plugin_type ):

        """ Return a sequence of tuples, one for each plugin of the given type.

        o 'plugin_type' must be one of the known types, else raise KeyError.

        o Tuples will be of the form, '( plugin_id, plugin )'.
        """

    def listPluginIds( plugin_type ):

        """ Return a sequence of plugin ids
        
        o Return ids for each active plugin of the given type.

        o 'plugin_type' must be one of the known types, else raise KeyError.
        """

    def activatePlugin( plugin_type, plugin_id ):

        """ Activate a plugin of the given type.

        o 'plugin_type' must be one of the known types, else raise KeyError.

        o 'plugin_id' must be the ID of an available plugin, else raise
          KeyError.

        o Append 'plugin_id' to the list of active plugins for the given
          'plugin_type'.
        """

    def deactivatePlugin( plugin_type, plugin_id ):

        """ Deactivate a plugin of the given type.

        o 'plugin_type' must be one of the known types, else raise KeyError.

        o 'plugin_id' must be an ID of an existing plugin of that type,
          else raise KeyError.
        """

    def movePluginsUp( plugin_type, ids_to_move ):

        """ Move a set of plugins "up" in their list.

        o 'plugin_type' must be one of the known types, else raise KeyError.

        o 'ids_to_move' must be a sequence of ids of current plugins
          for that type.
          
          - If any item is not the ID of a current plugin, raise ValueError.
        """

    def movePluginsDown( plugin_type, ids_to_move ):

        """ Move a set of plugins "down" in their list.

        o 'plugin_type' must be one of the known types, else raise KeyError.

        o 'ids_to_move' must be a sequence of indexes of items in the current
          list of plugins for that type.
          
          - If any item is not the ID of a current plugin, raise ValueError.
        """
