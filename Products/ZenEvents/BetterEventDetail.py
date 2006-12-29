from EventDetail import EventDetail
from Globals import InitializeClass
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions as permissions
from Acquisition import aq_base, aq_parent

class BetterEventDetail(EventDetail):
    security = ClassSecurityInfo()
    security.setDefaultAccess("allow")

    factory_type_information = ( 
        { 
            'id'             : 'BetterEventDetail',
            'meta_type'      : 'BetterEventDetail',
            'description'    : """Detail view of event""",
            'icon'           : 'EventDetail_icon.gif',
            'product'        : 'ZenEvents',
            'factory'        : '',
            'immediate_view' : 'eventFields',
            'actions'        :
            ( 
                { 'id'            : 'fields'
                , 'name'          : 'Fields'
                , 'action'        : 'eventFields'
                , 'permissions'   : (
                  permissions.view, )
                },
                { 'id'            : 'details'
                , 'name'          : 'Details'
                , 'action'        : 'eventDetail'
                , 'permissions'   : (
                  permissions.view, )
                },
                { 'id'            : 'log'
                , 'name'          : 'Log'
                , 'action'        : 'eventLog'
                , 'permissions'   : (
                  permissions.view, )
                },
            )
          },
        )


    def breadCrumbs(self, terminator='dmd'):
        """Return the breadcrumb links for this object add event.
        [('url','id'), ...]
        """
        device = self.device and self.dmd.Devices.findDevice(self.device)       
        if device:
            crumbs = device.breadCrumbs('dmd')
        else:
            crumbs = []
            #crumbs = self.dmd.ZenEventManager.breadCrumbs('dmd')
        url = self.dmd.ZenEventManager.absolute_url_path() + \
                "/eventFields?evid=%s" % self.evid
        crumbs.append((url,'Event %s' % self.evid))
        return crumbs


    def getContext(self):
        '''something here to get this published'''
        device = self.device and self.dmd.Devices.findDevice(self.device)       
        if device:
            context = device.primaryAq()
        else:
            context = self.dmd.ZenEventManager.primaryAq()
        context = self.__of__(context)
        return context


    def zentinelTabs(self, templateName):
        """Return a list of hashs that define the screen tabs for this object.
        [{'name':'Name','action':'template','selected':False},...]
        """
        tabs = EventDetail.zentinelTabs(self, templateName)
        for tab in tabs:
            tab['action'] += '?evid=%s' % self.evid
        return tabs


InitializeClass(BetterEventDetail)

