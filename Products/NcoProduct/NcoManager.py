#################################################################
#
#   Copyright (c) 2002 Confmon Corporation. All rights reserved.
#
#################################################################

"""NcoManager

Data connector for Micromuse Omnibus

$Id: NcoManager.py,v 1.6 2004/04/22 19:08:47 edahl Exp $"""

__version__ = "$Revision: 1.6 $"[11:-2]

import types, time, re, struct

from Acquisition import Implicit
from OFS.PropertyManager import PropertyManager
from Globals import Persistent
from Globals import DTMLFile
from Globals import InitializeClass
from AccessControl.Role import RoleManager
from AccessControl import ClassSecurityInfo
from OFS.SimpleItem import Item
from ImageFile import ImageFile
import DateTime

from zLOG import LOG, ERROR

from Products.CMFCore import CMFCorePermissions

import Sybase

from NcoEvent import NcoEvent, NcoEventDetail, NcoEventJournal, NcoEventData
from Products.ZenUtils.ObjectCache import ObjectCache
from Products.ZenUtils.Utils import cleanstring

def manage_addNcoManager(context, id, REQUEST=None):
    '''make an NcoManager'''
    if not id: id = "netcool"
    ncp = NcoManager(id) 
    context._setObject(id, ncp)
    ncp = context._getOb(id)
    ncp.installIntoPortal()
    if REQUEST is not None:
        REQUEST['RESPONSE'].redirect(
            context.absolute_url()+'/manage_main')
            

#addNcoManager = DTMLFile('dtml/addNcoManager',globals())

defaultFields = ['Acknowledged', 'Severity', 'ServerSerial', 'ServerName']


class NcoManager(Implicit, Persistent, RoleManager, Item, PropertyManager, ObjectCache):

    portal_type = meta_type = 'NcoManager'
   
    security = ClassSecurityInfo()
    
    refreshConversionsForm = DTMLFile('dtml/refreshNcoProduct', globals())
    
    manage_options = (PropertyManager.manage_options +
                    ({'label':'View', 'action':'viewEvents'}, 
                    {'label':'Refresh', 'action':'refreshConversionsForm'},) +
                    ObjectCache.manage_options +
                    Item.manage_options +
                    RoleManager.manage_options)

    _properties = (
                    {'id':'omniname', 'type':'string', 'mode':'w'},
                    {'id':'username', 'type':'string', 'mode':'w'},
                    {'id':'password', 'type':'string', 'mode':'w'},
                    {'id':'oracleconnstr', 'type':'string', 'mode':'w'},
                    {'id':'defaultwhere', 'type':'text', 'mode':'w'},
                    {'id':'defaultorderby', 'type':'text', 'mode':'w'},
                    {'id':'batchsize', 'type':'int', 'mode':'w'},
                    {'id':'resultFields', 'type':'lines', 'mode':'w'},
                )
    
    

    def __init__(self, id, title='',
                    omniname='', 
                    username='', 
                    password='',
                    oracleconnstr='',
                    defaultwhere='',
                    defaultorderby='',
                    batchsize=20,
                    resultFields=[]):

        self.id = id
        self.title = title
        self.omniname = omniname #omnibus db name
        self.username = username
        self.password = password
        self.oracleconnstr = oracleconnstr #user/pass@tnsname
        self.defaultwhere = defaultwhere
        self.defaultorderby = defaultorderby
        self.batchsize = batchsize
        self.resultFields = resultFields   # user defined fields for list
        self._conversions = {}  # [Colname] = {Value:Conversion,}
        self._colors = ()
        self._ackedcolors = ()
        ObjectCache.__init__(self)
        self.initCache()



    security.declareProtected('View','getEvents')
    def getEvents(self, where=None, orderby=None, resultFields=None):
        """get events from the omnibus database"""
        try:
            if resultFields:
                resultFields = list(resultFields) + defaultFields
            else:
                resultFields = self.resultFields + defaultFields
            select = ("select " + ','.join(resultFields)
                        + " from status")
            if where: 
                select += " where " + where 
            elif self.defaultwhere:
                select += " where " + self.defaultwhere
            if orderby:
                select += " order by " + orderby
            elif self.defaultorderby:
                select += " order by " + self.defaultorderby
            #print select
            if select[-1] != ';': select += ';'
            retdata = self.checkCache(select)
            if not retdata:
                curs = self._getCursor()
                curs.execute(select)
                retdata = self._getEvents(curs, resultFields)
                self._closeDb()
                self.addToCache(select, retdata)
                self.cleanCache()
            return retdata
        except:
            LOG("NcoManager", ERROR, "Failure querying omnibus")
        return []


    security.declareProtected('View','getHistoryEvents')
    def getHistoryEvents(self, startdate=None, enddate=None,
                        where="", orderby=None, resultFields=None):
        """query an oracle event history database"""
        try:
            import DCOracle2
            if not resultFields:
                resultFields = self.resultFields
            select = self.historySelectPrep(where, orderby, resultFields)
            startdate, enddate = self.historyDatesPrep(startdate, enddate)
            cachekey = select, str(startdate), str(enddate)
            #print cachekey 
            #print select
            retdata = self.checkCache(cachekey)
            if not retdata:
                curs = self._getHistoryCursor()
                curs.execute(select, startdate, enddate)
                retdata = self._getEvents(curs, resultFields, hist=1)
                self._closeHistoryDb()
                self.addToCache(cachekey, retdata)
                self.cleanCache()
            return retdata
        except:
            LOG("NcoManager", ERROR, "Failure querying oracle history")
        return []
        

    def getHistorySummary(self, startdate=None, enddate=None,
                        where="", orderby=None):
        """build a summary of history events returns the following
        [{'node':'node','url':'url to node',
            'evcount':'number of events',
            'tallysum':'sum of all event tallies'},]"""
        import DCOracle2
        resultFields = ['Identifier', 'Tally', 'Node', 'DeviceClass']
        if where: where += ' and'
        where += ' Severity > 1'
        select = self.historySelectPrep(where, orderby, resultFields)
        startdate, enddate = self.historyDatesPrep(startdate, enddate)
        cachekey = select, str(startdate), str(enddate)
        #print cachekey 
        #print select
        retdata = self.checkCache(cachekey)
        if not retdata:
            curs = self._getHistoryCursor()
            curs.execute(select, startdate, enddate)
            burl = '/'.join(self.absolute_url().split('/')[:-1])
            retdata = {}
            for row in curs.fetchall():
                identifier, tally, node, deviceclass = row[:4]
                sumdata = None
                if retdata.has_key(identifier):
                    sumdata = retdata[identifier]
                else:
                    if deviceclass:
                        url = burl + '/Devices' + deviceclass +'/'+ node
                    else: 
                        url = ''
                    sumdata = SummaryData(node, url, identifier)
                if not sumdata.url and deviceclass:
                    sumdata.url = burl + '/Devices' + deviceclass +'/'+ node
                sumdata.incEventCount()
                sumdata.incTallySum(tally)
                retdata[identifier] = sumdata

            self._closeHistoryDb()
            self.addToCache(cachekey, retdata)
            self.cleanCache()
        return retdata.values()


    def historySelectPrep(self, where, orderby, resultFields):
        """build the select for a history query 
        (we need to handle date conversions)"""
        if not resultFields:
            resultFields = self.resultFields
        resultFields = list(resultFields) + defaultFields
        select = "select " 
        for field in resultFields:
            if self.isDate(field):
                select += "TO_CHAR(%s, 'YYYY/MM/DD HH24:MI:SS')," % field
            else:
                select += field + ","
        select = select[:-1]
        select += " from reporter_status"
        if not where and self.defaultwhere:
            where = self.defaultwhere
        if where: where += " and"
        else: where = ""
        where += " LastOccurrence >= :1 and FirstOccurrence <= :2"
        select += " where " + where
        if orderby and orderby > 0:
            select += " order by " + orderby
        elif self.defaultorderby and orderby > 0:
            select += " order by " + self.defaultorderby
        return select


    def historyDatesPrep(self, startdate=None, enddate=None,):
        """build two DCOracle2.Timestamp object to deliniate this search
        if enddate is None we set it to the current time
        if startdate is None it is set to 1 day before enddate"""
        import DCOracle2

        if not enddate: 
            enddate = DateTime.DateTime()
        elif type(enddate) == types.StringType:
            enddate = Datetime.DateTime(enddate)
        enddate = enddate.latestTime()
        if not startdate: 
            startdate = enddate - 1
        elif type(startdate) == types.StringType:
            startdate = DateTime.DateTime(startdate)
        startdate = startdate.earliestTime()
        enddate = DCOracle2.Timestamp(
                                enddate.year(), 
                                enddate.month(), 
                                enddate.day(),
                                enddate.hour(),
                                enddate.minute(),
                                enddate.second())
        startdate = DCOracle2.Timestamp(
                                    startdate.year(), 
                                    startdate.month(),
                                    startdate.day(),
                                    startdate.hour(),
                                    startdate.minute(),
                                    startdate.second())
        return startdate, enddate


    def _getEvents(self, curs, resultFields, hist=0): 
        """check cache and execute query against passed cursor"""
        result = []
        outfields = resultFields[:-len(defaultFields)]
        for row in curs.fetchall():
            nrow = []
            for i in range(len(row)):
                col = row[i]
                if i < len(outfields):
                    col = self._convert(outfields[i], col) 
                else:
                    col = self._cleanstring(col)
                nrow.append(col)
            evt = NcoEvent(tuple(nrow), resultFields)
            evt = evt.__of__(self)
            if evt.Acknowledged:
                evt.bgcolor = self._ackedcolors[evt.Severity]
                evt.fgcolor = "#FFFFFF"
            else:
                evt.bgcolor = self._colors[evt.Severity]
                evt.fgcolor = "#000000"
            result.append(evt)
        return result


    security.declareProtected('View','getDeviceEventSummary')
    def getDeviceEventSummary(self, device):
        where = "Node = '" + device + "'"
        return self.getEventSummary(where)



    security.declareProtected('View','getEventSummary')
    def getEventSummary(self, where=None):
        """getEventSummary(where) return a list of tuples with number of events
        and the color of the severity that the number represents""" 
        severities = [5,4,3,2,1,0]
        select = 'select '
        for severity in severities:
            select = select + 'dist(Severity,' + str(severity) + '),'
        select = select[:-1] + ' from status '
        if where:
            select += ' where ' + where
        elif self.defaultwhere:
            select += ' where ' + self.defaultwhere
        select += ';'
        curs = self._getCursor()
        curs.execute(select)
        row = curs.fetchone()
        self._closeDb()
        retdata = []
        for i in range(len(severities)):
            sev = severities[i]
            if row:
                retdata.append((row[i], self._colors[sev],))
            else:
                retdata.append((0, self._colors[sev],))
        return retdata    
            

    security.declareProtected('View','getEventDetail')
    def getEventDetail(self, serverserial, servername, ishist=0):
        """build an NcoEventDetail object"""

        if ishist:
            tablebase = 'reporter_';
            getcursor = self._getHistoryCursor
        else:
            tablebase = ''
            getcursor = self._getCursor
        
        cachekey = 'ncoeventdetail'+str(serverserial)+servername
        event = self.checkCache(cachekey)
        if not event:
            fields = self.getFieldList()
            allfields = fields + defaultFields
            if ishist:
                nfields=[]
                for field in allfields:
                    if self.isDate(field):
                        nfields.append("TO_CHAR(%s, 'YYYY/MM/DD HH24:MI:SS')" 
                                                        % field)
                    else:
                        nfields.append(field)
                allfields = nfields
            selectevent = "select " 
            selectevent += ", ".join(allfields)
            selectevent += " from %sstatus where" % tablebase
            selectevent += " ServerSerial = " + str(serverserial)
            selectevent += " and ServerName = '" + servername + "'"
            if not ishist: selectevent += ";"
            
            #print selectevent
            curs = getcursor()
            curs.execute(selectevent)
            evrow = curs.fetchone()
            curs.close()
            if not evrow:
                raise ("NoEventDetailFound", 
                    "No Event Detail for Serial %s Server %s" % (
                                        serverserial, servername))
            evrow = map(self._convert, allfields, evrow)
            event = NcoEventDetail(evrow, fields)
            event = event.__of__(self)
            selectdetails = "select Name, Detail from %sdetails where" % (
                                                                tablebase)
            selectdetails += " Identifier = '" + event.Identifier + "'"
            if not ishist: selectdetails += ";"
            #print selectdetails
            curs = getcursor()
            curs.execute(selectdetails)
            detailrows = curs.fetchall()
            details = []
            for name, detail in detailrows:
                ddict = NcoEventData(name, detail)
                details.append(ddict)
            event.details = details
            curs.close()

            selectjournals = "select UID, Chrono, Text1, Text2, Text3, Text4"
            selectjournals += " from %sjournal where" % tablebase
            selectjournals += " Serial = " + str(event.Serial)
            if not ishist: selectjournals += ";"
            #print selectjournals
            curs = getcursor()
            curs.execute(selectjournals)
            jrows = curs.fetchall()
            journals = []
            for row in jrows:
                user = self._convert('OwnerUID', row[0])
                date = self._convertDate(row[1])
                textar = map(lambda x: x and x or '', row[2:])
                text = "".join(textar)
                jdict = NcoEventJournal(user,date,text)
                journals.append(jdict)
            event.journals = journals
            curs.close()
            self._closeDb()
            self.addToCache(cachekey, event)
            self.cleanCache()
        return event


    security.declarePublic("isDate")
    def isDate(self, colName):
        """check to see if a column is of type date"""
        return self._schema.get(colName,None)


    security.declareProtected('Send Events', 'sendEvents')
    def sendEvents(self, events):
        """send a group of events to netcool"""
        for event in events:
            self.sendEvent(event, keepopen=1)
        self._closeDb()


    security.declareProtected('Send Events', 'sendEvent')
    def sendEvent(self, event, keepopen=0):
        """send and event to the netcool server"""

        requiredFields = ('Node', 'Summary', 'AlertGroup', 'Severity')
                            
        for field in requiredFields:
            if not event.has_key(field):
                raise "NcoEventError", \
                    "Required event field %s not found" % field
        
        if not event.has_key('Identifier'):
            evid = (event['Node'] +'|'+ 
                    event['AlertGroup'] +'|')
            if event.has_key('AlertKey'):
                evid += event['AlertKey'] +'|'
            evid += str(event['Severity'])
            event['Identifier'] = evid

        fields = self.getFieldList()
        insert = "insert into status ("
        for fieldName in event.keys():
            if fieldName not in fields:
                raise "NcoEventError", \
                    "Field %s not a valid Omnibus field" % fieldName
            insert = insert + fieldName + ", "
        insert = insert[:-2] + ") values ("

        for value in event.values():
            if type(value) == types.IntType or type(value) == types.LongType:
                insert = insert + str(value) + ", "
            else:
                insert = insert + "'" + value + "', "
        insert = insert[:-2] + ")"

        insert += " updating(Summary, Severity);"
                  
        #print insert
        curs = self._getCursor()
        curs.execute(insert)
        if not keepopen: self._closeDb()



    security.declareProtected('Manage NcoManager','manage_refreshConversions')
    def manage_refreshConversions(self, curs=None, REQUEST=None):
        """get the conversion information from the omnibus server"""
        conversions = {}
        if not curs: curs = self._getCursor()
        sql = "select KeyField, Conversion from conversions;"
        curs.execute(sql)
        for row in curs.fetchall():
            conversions[row[0][:-1]] = row[1][:-1]
        if conversions: self._conversions = conversions
        self._getColors(curs)
        self._getSchema(curs)
        self._closeDb()
        if REQUEST:
            message = "Refreshed Conversions"
            return self.refreshConversionsForm(self, REQUEST, 
                        manage_tabs_message=message)


    security.declareProtected('Manage NcoManager','manage_editCache')
    def manage_editCache(self, timeout=20, clearthresh=20, REQUEST=None):
        """Reset cache values"""
        self.timeout = int(timeout)
        self.clearthresh = int(clearthresh)
        if REQUEST:
            message = "Cache parameters set"
            return self.editCache(self, REQUEST, manage_tabs_message=message)
   

    security.declareProtected('Manage NcoManager','manage_clearCache')
    def manage_clearCache(self, REQUEST=None):
        """Reset cache values"""
        self.cleanCache(force=1)
        if REQUEST:
            message = "Cache cleared"
            return self.editCache(self, REQUEST, manage_tabs_message=message)


    security.declareProtected('View','getSeverities')
    def getSeverities(self):
        """build a list of tuples of severities where 
        the name of the severity is first and index is second"""
        if not self._conversions: return []
        sevs = [] 
        list = range(6)
        list.reverse()
        for i in list:
            sevs.append((self._conversions['Severity'+str(i)], i))
        return sevs


    def _getColors(self, curs):
        """load the severity colors from omnibus"""
        colors = []
        ackedcolors = []
        sql = "select Severity, AckedRed, AckedGreen, AckedBlue, "
        sql += "UnackedRed, UnackedGreen, UnackedBlue from colors "
        sql += "order by Severity;"
        curs.execute(sql)
        for row in curs.fetchall():
            ackedcolors.append(self._colorConv(row[1], row[2], row[3]))
            colors.append(self._colorConv(row[4], row[5], row[6]))
        if colors:
            self._colors = colors
            self._ackedcolors = ackedcolors

    
    def _getSchema(self, curs):
        schema = {}
        sql = "describe status;"
        curs.execute(sql)
        for row in curs.fetchall():
            col = row[0][:-1]
            type = row[1] in (1, 4, 7, 8) #different date types
            schema[row[0][:-1]] = type
        if schema: self._schema = schema 


    def _colorConv(self,r,g,b):
        """convert rgb in decimal to web hex string"""
        return "#%02x%02x%02x" % (r, g, b)

    
    def _cleanstring(self,value):
        """take the trailing \x00 off the end of a string"""
        return cleanstring(value)
       

    def _convert(self, field, value):
        """convert a netcool value if nessesary"""
        value = self._cleanstring(value)
        key = field + str(value)
        if self._conversions.has_key(key):
            value = self._conversions[key]
        if self.isDate(field):
            value = self._convertDate(value)
        return value
  

    def _convertDate(self, value):
        """convert dates to proper string format"""
        if type(value) != types.StringType:
            return DateTime.DateTime(value).strftime("%Y/%m/%d %H:%M:%S")
        else:
            return value


    def _getCursor(self):
        """try to get a cursor to get data from database"""
        if not hasattr(self, '_v_db') or not self._v_db:
            self._v_db = Sybase.connect(
                self.omniname,
                self.username,
                self.password)
        try:
            cur = self._v_db.cursor()
        except:
            self._v_db = Sybase.connect(
                self.omniname,
                self.username,
                self.password)
            cur = self._v_db.cursor()
        return cur


    def _closeDb(self):
        """close the databaes handle"""
        if hasattr(self, '_v_db') and self._v_db:
            self._v_db.close()
            self._v_db = None


    def _getHistoryCursor(self):
        import DCOracle2
        self._v_hdb = DCOracle2.connect(self.oracleconnstr)
        cur = self._v_hdb.cursor()
        return cur


    def _closeHistoryDb(self):
        if hasattr(self, '_v_hdb') and self._v_hdb:
            self._v_hdb.close()
            self._v_hdb = None


    def _checkConn(self):
        """check to see if the connection information in product works"""
        self._getCursor()
        self._closeDb()


    security.declareProtected("View", "getFieldList")
    def getFieldList(self):
        """build the list of all fields in the omnibus database"""
        return self._schema.keys()


    security.declareProtected('Manage NcoManager','installIntoPortal')
    def installIntoPortal(self):
        """install type and skins into portal"""
        from Products.CMFCore.utils import getToolByName
        from Products.CMFCore.DirectoryView import addDirectoryViews
        from Products.CMFCore.TypesTool import ContentFactoryMetadata
        from cStringIO import StringIO
        import string

        out = StringIO()

        skinstool = getToolByName(self, 'portal_skins') 
        
        if 'ncoproduct' not in skinstool.objectIds():
            # We need to add Filesystem Directory Views for any directories
            # in our skins/ directory.  These directories should already be
            # configured.
            addDirectoryViews(skinstool, 'skins', globals())
            out.write("Added 'ncoproduct' directory view to portal_skins\n")

        # Now we need to go through the skin configurations and insert
        # 'ncoproduct' into the configurations.  Preferably, this should be
        # right before where 'misc' is placed.  Otherwise, we append
        # it to the end.
        skins = skinstool.getSkinSelections()
        for skin in skins:
            path = skinstool.getSkinPath(skin)
            path = map(string.strip, string.split(path,','))
            if 'ncoproduct' not in path:
                try: path.insert(path.index('misc'), 'ncoproduct')
                except ValueError:
                    path.append('ncoproduct')
                    
                path = string.join(path, ', ')
                # addSkinSelection will replace exissting skins as well.
                skinstool.addSkinSelection(skin, path)
                out.write("Added 'ncoproduct' to %s skin\n" % skin)
            else:
                out.write("Skipping %s skin, 'ncoproduct' is already set up\n"
                                            % (skin)) 

        return out.getvalue()


InitializeClass(NcoManager)

class SummaryData:

    security = ClassSecurityInfo()
    security.setDefaultAccess('allow')

    def __init__(self, node, url, identifier, evcount=0, tallysum=0):
        self.node = node
        self.url = url
        self.evcount = evcount
        self.tallysum = tallysum
        self.identifier = identifier

    def incEventCount(self):
        self.evcount += 1

    def incTallySum(self, tally):
        self.tallysum += tally
 
InitializeClass(SummaryData)
