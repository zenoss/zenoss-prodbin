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

import urllib

from Globals import InitializeClass
from AccessControl import ClassSecurityInfo

from Event import Event

class ZEvent(Event):
    """
    Event that lives in the zope context has zope security mechanisms and
    url back to event manager
    """
    security = ClassSecurityInfo()
    security.setDefaultAccess("allow")
 
    def __init__(self, manager, fields, data, eventPermission=True):
        Event.__init__(self)
        self.updateFromFields(fields, data)
        self._zem = manager.getId()
        self._baseurl = manager.absolute_url_path()
        self.eventPermission = eventPermission

    def getDataForJSON(self, fields):
        """ returns data ready for serialization
        """
        return self.getDataListWithLinks(list(fields)+['evid'])

    def getDataListWithLinks(self, fields, cssClass=''):
        """return a list of data elements that map to the fields parameter.
        """
        def _sanitize(val):
            return val.replace('<', '&lt;').replace('>','&gt;')

        data = []
        for field in fields:
            value = getattr(self, field)
            _shortvalue = str(value) or ''
            if field == "device":
                value = urllib.quote('<a class="%s"' % (cssClass) +
                            ' href="/zport/dmd/deviceSearchResults'
                            '?query=%s">%s</a>' % (value, _shortvalue))
            elif field == 'eventClass':
                _shortvalue = _shortvalue.replace('/','/&shy;')
                if not self.eventPermission: 
                    value = _shortvalue
                else:
                    value = urllib.quote('<a class="%s" ' % (cssClass) +
                      'href="/zport/dmd/Events%s">%s</a>' % (value,_shortvalue))
            elif field == 'component' and getattr(self, 'device', None):
                value = urllib.quote('<a class="%s"' % (cssClass) +
                            ' href="/zport/dmd/searchComponents'
                            '?device=%s&component=%s">%s</a>' % (
                                getattr(self, 'device'), value, _shortvalue))
            elif field == 'summary':
                value = urllib.quote(
                    value.replace('<','&lt;').replace('>','&gt;'))
            else:
                value = _shortvalue
            data.append(value)
        return data


    def getEventDetailHref(self):
        """build an href to call the detail of this event"""
        return "%s/viewEventFields?evid=%s" % (self._baseurl, self.evid)


    def getCssClass(self):
        """return the css class name to be used for this event.
        """
        __pychecker__='no-constCond'
        value = self.severity < 0 and "unknown" or self.severity
        acked = self.eventState > 0 and "acked" or "noack"
        return "zenevents_%s_%s %s" % (value, acked, acked)

    def zem(self):
        """return the id of our manager.
        """
        return self._zem

InitializeClass(ZEvent)
