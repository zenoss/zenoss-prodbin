
from AccessControl import ClassSecurityInfo
from Acquisition import aq_parent
from Products.ZenModel.ZenModelRM import ZenModelRM
from Products.ZenModel.Commandable import Commandable
from Products.ZenRelations.RelSchema import *
from Globals import InitializeClass
from EventFilter import EventFilter

class EventCommand(ZenModelRM, Commandable, EventFilter):

    zenRelationsBaseModule = "Products.ZenEvents"
    
    where = ''
    command = ''
    enabled = False
    delay = 0
    
    _properties = ZenModelRM._properties + (
        {'id':'command', 'type':'string', 'mode':'w'},
        {'id':'where', 'type':'string', 'mode':'w'},
        {'id':'defaultTimeout', 'type':'int', 'mode':'w'},
        {'id':'enabled', 'type':'boolean', 'mode':'w'},
        {'id':'delay', 'type':'int', 'mode':'w'},
    )
    
    _relations =  (
        ("eventManager", ToOne(ToManyCont, "EventManagerBase", "commands")),
    )

    factory_type_information = ( 
        { 
            'immediate_view' : 'editEventCommand',
            'actions'        :
            ( 
                { 'id'            : 'edit'
                , 'name'          : 'Edit'
                , 'action'        : 'editEventCommand'
                , 'permissions'   : ( "Manage DMD", )
                },
            )
          },
        )

    security = ClassSecurityInfo()

    def getEventFields(self):
        return self.eventManager.getFieldList()

    def getUserid(self):
        return ''

    def breadCrumbs(self, terminator='dmd'):
        """Return the breadcrumb links for this object add ActionRules list.
        [('url','id'), ...]
        """
        crumbs = super(EventCommand, self).breadCrumbs(terminator)
        url = aq_parent(self).absolute_url_path() + "/listEventCommands"
        crumbs.insert(-1,(url,'Event Commands'))
        return crumbs

    
    def manage_beforeDelete(self, item, container):
        """Clear state in alert_state before we are deleted.
        """
        self._clearAlertState()


    def sqlwhere(self):
        """Return sql where to select alert_state data for this event.
        """
        return "userid = '' and rule = '%s'" % (self.id)

    def _clearAlertState(self):
        """Clear state in alert_state before we are deleted.
        """
        db = self.ZenEventManager.connect()
        curs = db.cursor()
        delcmd = "delete from alert_state where %s" % self.sqlwhere()
        #is this an important logging message?
        #log.debug("clear alert state '%s'", delcmd)
        curs.execute(delcmd)
        db.close()


    security.declareProtected('Manage EventManager', 'manage_editEventCommand')
    def manage_editEventCommand(self, REQUEST=None):
        "edit the commands run when events match"
        import WhereClause
        if REQUEST and not REQUEST.form.has_key('where'):
            clause = WhereClause.fromFormVariables(self.genMeta(), REQUEST.form)
            if clause:
                REQUEST.form['where'] = clause
        return self.zmanage_editProperties(REQUEST)
        
    
InitializeClass(EventCommand)
