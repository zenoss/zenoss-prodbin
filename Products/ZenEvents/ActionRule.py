#################################################################
#
#   Copyright (c) 2006 Zenoss, Inc. All rights reserved.
#
#################################################################
import re
from sets import Set
import logging
log = logging.getLogger("zen.ActionRule")

from Globals import InitializeClass
from Globals import DTMLFile
from AccessControl import ClassSecurityInfo
from AccessControl import Permissions as permissions
from Acquisition import aq_parent

from Products.ZenModel.ZenModelRM import ZenModelRM

def _downcase(s):
    return s[0:1].lower() + s[1:]

def manage_addActionRule(context, id, REQUEST=None):
    """Create an aciton rule"""
    ed = ActionRule(id)
    context._setObject(id, ed)
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(context.absolute_url() + '/manage_main') 

addActionRule = DTMLFile('dtml/addActionRule',globals())

class Text:
    type = 'text'
    def __init__(self, label):
        self.label = label
    def toJS(self, operator, value):
        if mode == 'like':
            if value.startswith('%') and not value.endswith('%'):
                return '$', [value[1]]
            elif not value.startswith('%') and value.endswith('%'):
                return '^', [value[-1]]
            elif value.startswith('%') and value.endswith('%'):
                return '~', [value[1:-1]]
        if mode == 'not like':
            return '!~', [value[1:-1]]
        if mode == '=':
            return '', [value]
        if mode == '!=':
            return '!', [value]
    def genProperties(self, name):
        return '%s:{type:"%s",label:"%s"}' % (name, self.type, self.label)
    def buildClause(self, name, value, mode):
        result = []
        for v in value:
            if mode == '~':
                result.append("%s like '%%%s%%'" % (name, v))
            if mode == '^':
                result.append("%s like '%s%%'" % (name, v))
            if mode == '$':
                result.append("%s like '%%%s'" % (name, v))
            if mode == '!=':
                result.append("%s not like '%%%s%%'" % (name, v))
            if mode == '':
                result.append("%s = '%s%'" % (name, v))
            if mode == '!':
                result.append("%s != '%s%'" % (name, v))
        if not result:
            return None
        return ' or '.join(result)
        

class Select:
    type = 'select'
    def __init__(self, label, options):
        self.label = label
        if type(options[0]) != type(()):
            options = zip(range(len(options)), options)
        self.options = options
    def labelFromValue(self, value):
        return dict(self.options).get(value, 'Unknown')
    def valueFromLabel(self, value):
        return dict([(v, l) for l, v in self.options]).get(value, -1)
    def toJS(self, operator, value):
        if operator == '=':
            return ('', [self.labelFromValue(value)])
        if operator == '!=':
            return ('!', [self.labelFromValue(value)])
        result = []
        if operator in ('<', '>', '<=', '>='):
            for i, name in self.options:
                if eval('%d %s %d' % (i, operator, value)):
                    result.append(name)
        return ('', result)
    def genProperties(self, name):
        return '%s:{type:"%s",label:"%s", options:%r}' % (
            name, self.type, self.label, [s[1] for s in self.options])
    def buildClause(self, name, value, mode):
        result = []
        for v in value:
            v = self.valueFromLabel(v)
            if mode == '':
                result.append("%s = %d" % (name, mode, v))
            else:
                result.append("%s != %d" % (name, mode, v))
        return ' or '.join(result)

class Compare(Text):
    type = 'compare'
    def toJS(self, operator, value):
        return operator, [value]
    def buildClause(self, name, value, mode):
        result = []
        for v in value:
            result.append("%s %s %s" % (name, mode, v))
        return ' or '.join(result)

class CSelect(Select):
    type='cselect'
    def toJS(self, operator, value):
        return operator, [self.labelFromValue(value)]
    def buildClause(self, name, value, mode):
        result = []
        for v in value:
            result.append("%s %s %s" % (name, mode, self.valueFromLabel(v)))
        return ' or '.join(result)


from Products.ZenModel.DataRoot import DataRoot
prodStateConversions = [d.split(':') for d in DataRoot.prodStateConversions]
prodStateConversions = [(int(b), a) for a, b in prodStateConversions]

meta = dict(
   summary=Text("Summary"),
   prodState=CSelect("Production State",prodStateConversions),
   severity=CSelect("Severity",[
    "Clear", "Debug", "Info", "Warning", "Error", "Critical"
    ]),
   eventState=CSelect("Event State",["New", "Acknowledged", "Supressed"]),
   device=Text("Device"),
   deviceClass=Text("Device Class"),
   eventClass=Text("Event Class"),
   eventClassKey=Text("Event Class Key"),
   count=Compare("Count"),
   lastAge=Compare("Time since last update"),
   firstAge=Compare("Time since first event"),
   manager=Text("Manager"),
   agent=Select("Agent",[
    "zentrap", "zenprocess", "zenstatus", "zenperfsnmp", "zensyslog"]),
   facility=Select("Facility",[
    "auth","authpriv","cron","daemon","kern","lpr","mail",
    "mark","news","security","syslog","user","uucp",
    "local0","local1","local2","local3","local4",
    "local05","local6","local7"
    ]),
   priority=Select("Priority",[
    "debug","info","notice","warning","error","critical",
    "alert","emergency"]),
   component=Text("Component"),
   message=Text("Message"),
   changeAge=Compare("Time since last state change"),
   ntevid=Text("ntevid"),
   ipAddress=Text("IP Address"),
   location=Text("Location"),
   systems=Text("Systems"),
   deviceGroups=Text("Device Groups"),
   ownerId=Text("Owner Id")
   )


class ActionRule(ZenModelRM):
    """
    Rule applied to events that then executes an action on matching events.
    """
    
    meta_type = "ActionRule"

    where = "severity >= 4 and eventState = 0 and prodState = 1000"
    delay = 0
    action = "email"
    format = "%(device)s %(summary)s"
    body =  "Device: %(device)s\n" \
            "Component: %(component)s\n" \
            "Severity: %(severity)s\n" \
            "Time: %(firstTime)s:\n" \
            "Message:\n%(message)s\n" \
            "Event: %(eventUrl)s\n" 
    clearFormat = "CLEAR: %(device)s %(clearOrEventSummary)s"
    clearBody =  \
            "Event: '%(summary)s'\n" \
            "Cleared by: '%(clearSummary)s'\n" \
            "At: %(clearFirstTime)s\n" \
            "Device: %(device)s\n" \
            "Component: %(component)s\n" \
            "Severity: %(severity)s\n" \
            "Message:\n%(message)s\n"
    enabled = False
    actionTypes = ("page", "email") 
    targetAddr = ""

    _properties = ZenModelRM._properties + (
        {'id':'where', 'type':'text', 'mode':'w'},
        {'id':'format', 'type':'text', 'mode':'w'},
        {'id':'body', 'type':'text', 'mode':'w'},
        {'id':'clearFormat', 'type':'text', 'mode':'w'},
        {'id':'clearBody', 'type':'text', 'mode':'w'},
        {'id':'delay', 'type':'int', 'mode':'w'},
        {'id':'action', 'type':'selection', 'mode':'w',
            'select_variable': 'actionTypes',},
        {'id':'enabled', 'type':'boolean', 'mode':'w'},
        {'id':'targetAddr', 'type':'string', 'mode':'w'},
    )

    factory_type_information = ( 
        { 
            'id'             : 'ActionRule',
            'meta_type'      : 'ActionRule',
            'description'    : """Define action taken against events""",
            'icon'           : 'ActionRule.gif',
            'product'        : 'ZenEvents',
            'factory'        : 'manage_addActionRule',
            'immediate_view' : 'editActionRule',
            'actions'        :
            ( 
                { 'id'            : 'edit'
                , 'name'          : 'Edit'
                , 'action'        : 'editActionRule'
                , 'permissions'   : ("Change Settings",)
                },
            )
         },
        )

    security = ClassSecurityInfo()


    def breadCrumbs(self, terminator='dmd'):
        """Return the breadcrumb links for this object add ActionRules list.
        [('url','id'), ...]
        """
        crumbs = super(ActionRule, self).breadCrumbs(terminator)
        url = aq_parent(self).absolute_url_path() + "/editActionRules"
        crumbs.insert(-1,(url,'Alerting Rules'))
        return crumbs

    def getEventFields(self):
        """Return list of fields used in format.
        """
        result = Set()
        result.update(re.findall("%\((\S+)\)s", self.format))
        result.update(re.findall("%\((\S+)\)s", self.body))
        result.update(map(_downcase, re.findall("%\(clear(\S+)\)s", self.clearFormat)))
        result.update(map(_downcase, re.findall("%\(clear(\S+)\)s", self.clearBody)))
        result.discard('eventUrl')
        return list(result)


    def checkFormat(self):
        """Check that the format string has valid fields.
        """
        evtfields = self.ZenEventManager.getFieldList()
        for field in self.getEventFields():
            if field not in evtfields:
                return False
        return True


    def getAddress(self):
        """Return the correct address for the action this rule uses.
        """
        if self.targetAddr:
            return self.targetAddr
        elif self.action == "page":
            return self.pager
        elif self.action == "email":
            return self.email


    def getUserid(self):
        """Return the userid this action is for.
        """
        return self.getPrimaryParent().getId()

    
    security.declareProtected('Change Settings', 'manage_editActionRule')
    def manage_editActionRule(self, REQUEST=None):
        """Update user settings.
        """
        if not self.enabled:
            self._clearAlertState()
        import WhereClause
        REQUEST.form['where'] = WhereClause.fromFormVariables(REQUEST.form)
        return self.zmanage_editProperties(REQUEST)


    def manage_beforeDelete(self, item, container):
        """Clear state in alert_state before we are deleted.
        """
        self._clearAlertState()


    def _clearAlertState(self):
        """Clear state in alert_state before we are deleted.
        """
        db = self.ZenEventManager.connect()
        curs = db.cursor()
        delcmd = "delete from alert_state where %s" % self.sqlwhere()
        log.debug("clear alert state '%s'", delcmd)
        curs.execute(delcmd)
        db.close()


    def sqlwhere(self):
        """Return sql where to select alert_state data for this event.
        """
        return "userid = '%s' and rule = '%s'" % (self.getUserid(), self.id)

    def _whereClauseAsJavaScript(self):
        import WhereClause
        return WhereClause.toJavaScript(meta, self.where)

    def getWhereClauseAsJavaScript(self):
        s = meta.items()
        s.sort()
        result = ['var properties={']
        for name, attrType in s:
            result.append('   %s,\n' % attrType.genProperties(name))
        result.append('};\n')
        result.append((Modes + 'var current = %s \n') %
                       self._whereClauseAsJavaScript())
        result.append('initializeFilters(current)\n')
        return ''.join(result)

Modes = """
 var modes = {
   text:[{text:"contains",value:"~"},
         {text:"doesn't contain",value:"!~"},
         {text:"begins with",value:"^"},
         {text:"ends with",value:"$"},
         {text:"is",value:""},
         {text:"is not",value:"!"}],
   select:[{text:"is",value:""},
           {text:"is not",value:"!"}],
   compare:[{text:"<",value:"<"},
            {text:"<=",value:"<="},
            {text:"=",value:"="},
            {text:">",value:">"},
            {text:">=",value:">"}],
   cselect:[{text:"<",value:"<"},
            {text:"<=",value:"<="},
            {text:"=",value:"="},
            {text:">",value:">"},
            {text:">=",value:">="}]};
"""


InitializeClass(ActionRule)
