#!/usr/bin/python
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

#
# Contained below is the class that tests elements located under
# the "Networks" Browse By subheading.
#
# Noel Brockett
#

import unittest

from util.selTestUtils import *

from SelTestBase import SelTestBase

class _TestMonitors(SelTestBase):
    """Defines a class that runs tests under the Monitors heading"""

    def _addStatusMonitor(self):
        self.waitForElement("link=Monitors")
        self.selenium.click("link=Monitors")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        if self.selenium.is_element_present("link=statusTestingString"):
            self._deleteStatusMonitor()
        self.addDialog("StatusMonitorlistaddSMonitor",new_id=("text",
                    "statusTestingString"))
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    def _deleteStatusMonitor(self):
        self.waitForElement("link=Monitors")
        self.selenium.click("link=Monitors")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.deleteDialog("StatusMonitorlistremoveSMonitors",
                "manage_removeMonitor:method", pathsList="ids:list", form_name="StatusMonitors", testData="statusTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    def _addPerformanceMonitor(self):
        self.waitForElement("link=Monitors")
        self.selenium.click("link=Monitors")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        if self.selenium.is_element_present("link=performanceTestingString"):
            self._deletePerformanceMonitor()
        self.addDialog("PerformanceMonitorlistaddPMonitor",new_id=("text",
                    "performanceTestingString"))
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    def _deletePerformanceMonitor(self):
        self.waitForElement("link=Monitors")
        self.selenium.click("link=Monitors")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.deleteDialog("PerformanceMonitorlistremovePMonitors",
                "manage_removeMonitor:method", pathsList="ids:list",
                form_name="Performance", testData="performanceTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    def _addPerformanceTemplate(self):
        #self._addPerformanceMonitor()   
        self.waitForElement("link=Monitors")
        self.selenium.click("link=Monitors")
        self.waitForElement("id=PerformanceMonitorlistperformanceTemplates")
        self.selenium.click("id=PerformanceMonitorlistperformanceTemplates")
        self.addDialog("AllTemplatesaddTemplate","manage_addRRDTemplate:method", 
            new_id=("text", "testingString"))
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    def _deletePerformanceTemplate(self):
        self.waitForElement("link=Monitors")
        self.selenium.click("link=Monitors")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.waitForElement("id=PerformanceMonitorlistperformanceTemplates")
        self.selenium.click("id=PerformanceMonitorlistperformanceTemplates")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.deleteDialog("AllTemplatesdeleteTemplates",
                "manage_deleteRRDTemplates:method", pathsList="paths:list",
                form_name="performanceTemplates", testData="testingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        #self._deleteStatusMonitor()

        
        
    def testAddPerformanceMonitor(self):
        """Run tests on the Performance Monitors table"""
        self._addPerformanceMonitor()
        self._deletePerformanceMonitor()       

    def _testEditPerformanceTemplateDescription(self):
        self._addPerformanceTemplate()
        self._deletePerformanceTemplate()

    def testEditPerformanceMonitorSettings(self):
        """Go into a Performance Monitor, edit the time interval and verify the information is saved"""
        self._addPerformanceMonitor()   
        self.selenium.click("link=performanceTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.click("link=Performance")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.waitForElement("id=graph_4_panr")
        self.waitForElement("id=linkcheck_label")
        self.selenium.do_command('assertTextPresent', ['Performance Graphs'])
        self.selenium.do_command('assertElementPresent', ['id=linkcheck_label'])
        self.selenium.do_command('assertElementPresent', ['id=graph_4_panr'])
        self.selenium.click("link=Modifications")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.do_command('assertTextNotPresent', ['/zport/dmd/Monitors/Performance/performanceTestingString/zmanage_editProperties'])
        self.selenium.click("link=Edit")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.type("eventlogCycleInterval:int", "61") 
        self.selenium.type("perfsnmpCycleInterval:int", "301") 
        self.selenium.type("processCycleInterval:int", "181") 
        self.selenium.type("statusCycleInterval:int", "62") 
        self.selenium.type("winCycleInterval:int", "63") 
        self.selenium.type("winmodelerCycleInterval:int", "64") 
        self.selenium.type("configCycleInterval:int", "361") 
        self.selenium.type("renderurl", "/zport/RenderServerTest") 
        self.selenium.type("renderuser", "admin") 
        self.selenium.click("name=zmanage_editProperties:method")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.click("link=Overview")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.do_command('assertTextPresent', ['61'])
        self.selenium.do_command('assertTextPresent', ['301'])
        self.selenium.do_command('assertTextPresent', ['181'])
        self.selenium.do_command('assertTextPresent', ['62'])
        self.selenium.do_command('assertTextPresent', ['63'])
        self.selenium.do_command('assertTextPresent', ['64'])
        self.selenium.do_command('assertTextPresent', ['361'])
        self.selenium.do_command('assertTextPresent', ['/zport/RenderServerTest'])
        self.selenium.do_command('assertTextPresent', ['admin'])
        self.selenium.click("link=Modifications")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.do_command('assertTextPresent', ['/zport/dmd/Monitors/Performance/performanceTestingString/zmanage_editProperties'])
        self._deletePerformanceMonitor()


class TestMonitorsPerformanceConfTemplates(SelTestBase):
    """Defines a class that runs tests under the Monitors Performance Templates heading"""

    def _goToPerformanceConfTemplate(self):
        self.waitForElement("link=Monitors")
        self.selenium.click("link=Monitors")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.waitForElement("id=PerformanceMonitorlistperformanceTemplates")
        self.selenium.click("id=PerformanceMonitorlistperformanceTemplates")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.waitForElement("link=PerformanceConf")
        self.selenium.click("link=PerformanceConf")
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    def _addGraphDefinition(self):
        self._goToPerformanceConfTemplate()
        if self.selenium.is_element_present("link=graphTestingString"):
            self._deleteGraphDefinition()
        if self.selenium.is_element_present("link=graphTestingStringEdit"):
            self._deleteGraphDefinitionEdit()
        self.addDialog("GraphlistaddGraph",new_id=("text",
                    "graphTestingString"))
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        
    def _deleteGraphDefinition(self):
        self._goToPerformanceConfTemplate()
        self.deleteDialog("GraphlistdeleteGraph",
                "manage_deleteGraphDefinitions:method", pathsList="ids:list",
                form_name="graphList", testData="graphTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    def _deleteGraphDefinitionEdit(self):
        self._goToPerformanceConfTemplate()
        self.deleteDialog("GraphlistdeleteGraph",
                "manage_deleteGraphDefinitions:method", pathsList="ids:list",
                form_name="graphList", testData="graphTestingStringEdit")
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    def _addPerformanceMonitor(self):
        self.waitForElement("link=Monitors")
        self.selenium.click("link=Monitors")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        if self.selenium.is_element_present("link=performanceTestingString"):
            self._deletePerformanceMonitor()
        self.addDialog("PerformanceMonitorlistaddPMonitor",new_id=("text",
                    "performanceTestingString"))
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    def _deletePerformanceMonitor(self):
        self.waitForElement("link=Monitors")
        self.selenium.click("link=Monitors")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.deleteDialog("PerformanceMonitorlistremovePMonitors",
                "manage_removeMonitor:method", pathsList="ids:list",
                form_name="Performance", testData="performanceTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
  
    def _addGraphPointDataPointSuccess(self):
        self.selenium.click("link=graphTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        if self.selenium.is_element_present("link=success"):
            self._deleteGraphPointSuccess()
        self.addDialog("GraphPointlistaddGPFromDataPoint",
                        dpNames=("select", "zenperfsnmp_success"))
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        
    def _deleteGraphPointDataPointSuccess(self):
        self.selenium.click("link=graphTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.deleteDialog("GraphPointlistdeleteGraphPoint",
                "manage_deleteGraphPoints:method", pathsList="ids:list",
                form_name="graphPointList", testData="success")
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    def _addGraphPointThresholdPing(self):
        self.selenium.click("link=graphTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        if self.selenium.is_element_present("link=zenping cycle time"):
            self._deleteGraphPointThresholdPing()
        self.addDialog("GraphPointlistaddGPFromThreshold",
                        threshNames=("select", "zenping cycle time"))
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        
    def _deleteGraphPointThresholdPing(self):
        self.selenium.click("link=graphTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.deleteDialog("GraphPointlistdeleteGraphPoint",
                "manage_deleteGraphPoints:method", pathsList="ids:list",
                form_name="graphPointList", testData="zenping cycle time")
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    def _addGraphPointCustom(self):
        self.selenium.click("link=graphTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        if self.selenium.is_element_present("link=customGraphPointTest"):
            self._deleteGraphPointCustom()
        self.addDialog("GraphPointlistaddGPCustom",
                        new_id=("text", "customGraphPointTest"),
                        flavor=("select", "HRULE"))
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.click("link=graphTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        
    def _deleteGraphPointCustom(self):
        self.selenium.click("link=graphTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.deleteDialog("GraphPointlistdeleteGraphPoint",
                "manage_deleteGraphPoints:method", pathsList="ids:list",
                form_name="graphPointList", testData="customGraphPointTest")
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    def _addDataSource(self):
        self._goToPerformanceConfTemplate()
        if self.selenium.is_element_present("link=dataSourceTestingString"):
            self._deleteDataSource()
        self.addDialog("DataSourcelistaddDataSource", "manage_addRRDDataSource:method", 
                        new_id=("text", "dataSourceTestingString"),
                        dsOption=("select", "SNMP"))       
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        
    def _deleteDataSource(self):
        self._goToPerformanceConfTemplate()
        self.waitForElement("id=DataSourcelistdeleteDataSource")
        self.deleteDialog("DataSourcelistdeleteDataSource", "manage_deleteRRDDataSources:method", 
                pathsList="ids:list",
                form_name="datasourceList", testData="dataSourceTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    def _addDataSourceDataPoint(self):
        if self.selenium.is_element_present("link=dataPointTestingString"):
            self._deleteDataSourceDataPoint()
        self.addDialog("DataPointlistaddDataPoint", "manage_addRRDDataPoint:method",
                        id=("text", "dataPointTestingString"))       
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        
    def _deleteDataSourceDataPoint(self):
        self.deleteDialog("DataPointlistdeleteDataPoint",
                "manage_deleteRRDDataPoints:method", pathsList="ids:list",
                form_name="dataPointsList", testData="dataPointTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    def _addGraphPointDataPointTestingString(self):
        self.selenium.click("link=graphTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        if self.selenium.is_element_present("link=dataSourceTestingString"):
            self._deleteGraphPointTestingString()
        self.addDialog("GraphPointlistaddGPFromDataPoint",
                        dpNames=("select", "dataSourceTestingString_dataPointTestingString"))
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        
    def _deleteGraphPointDataPointTestingString(self):
        self.selenium.click("link=graphTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.deleteDialog("GraphPointlistdeleteGraphPoint",
                "manage_deleteGraphPoints:method", pathsList="ids:list",
                form_name="graphPointList", testData="dataPointTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
    
    def _addThreshold(self):
        self._goToPerformanceConfTemplate()
        if self.selenium.is_element_present("link=thresholdTestingString"):
            self._deleteThreshold()
        self.addDialog("ThresholdlistaddThreshold", "manage_addRRDThreshold:method", 
                        new_id=("text", "thresholdTestingString"),
                        thresholdClassName=("select", "MinMaxThreshold"))       
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        
    def _deleteThreshold(self):
        self._goToPerformanceConfTemplate()
        self.waitForElement("id=ThresholdlistdeleteThreshold")
        self.deleteDialog("ThresholdlistdeleteThreshold",
                "manage_deleteRRDThresholds:method", 
                pathsList="ids:list",
                form_name="thresholdList", testData="thresholdTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)

    def _addGraphPointThresholdTestingString(self):
        self.selenium.click("link=graphTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        if self.selenium.is_element_present("link=thresholdTestingString"):
            self._deleteGraphPointThresholdPing()
        self.addDialog("GraphPointlistaddGPFromThreshold",
                        threshNames=("select", "thresholdTestingString"))
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        
    def _deleteGraphPointThresholdTestingString(self):
        self.selenium.click("link=graphTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.deleteDialog("GraphPointlistdeleteGraphPoint",
                "manage_deleteGraphPoints:method", pathsList="ids:list",
                form_name="graphPointList", testData="thresholdTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)


    def testEditTemplateNameAndDescription(self):
        """Changes PerformanceConf template name"""
        self._goToPerformanceConfTemplate()
        self.selenium.type("newId", "PerformanceConfEdit") 
        self.selenium.type("description:text", "This is a new and Improved Description") 
        self.selenium.click("name=zmanage_editProperties:method")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.do_command('assertTextPresent', ['PerformanceConfEdit'])
        self.selenium.do_command('assertTextPresent', ['This is a new and Improved Description'])
        self.selenium.click("link=Templates")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.do_command('assertElementPresent',
                ['link=PerformanceConfEdit'])
        self.selenium.click("link=PerformanceConfEdit")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.type("newId", "PerformanceConf") 
        self.selenium.type("description:text", "Graphs and Thresholds for Core Collectors") 
        self.selenium.click("name=zmanage_editProperties:method")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.do_command('assertTextNotPresent', ['PerformanceConfEdit'])
        self.selenium.do_command('assertTextNotPresent', ['This is a new and Improved Description'])

    def testEditGraphDefinitions(self):
        """Changes graph definition in the PerformanceConf template"""
        self._addGraphDefinition()
        self.selenium.click("link=graphTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.click("link=Graph Commands")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.do_command('assertTextNotPresent', ['101'])
        self.selenium.do_command('assertTextNotPresent', ['501'])
        self.selenium.do_command('assertTextNotPresent', ['seconds'])
        self.selenium.do_command('assertTextNotPresent', ['logarithmic'])
        self.selenium.do_command('assertTextNotPresent', ['base=1024'])
        self.selenium.click("link=Graph Definition")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.type("newId", "graphTestingStringEdit") 
        self.selenium.type("height:int", "101") 
        self.selenium.type("width:int", "501") 
        self.selenium.type("units", "seconds") 
        self.selenium.select("log:boolean", "label=True")
        self.selenium.select("base:boolean", "label=True")
        self.selenium.type("miny:int", "-2") 
        self.selenium.type("maxy:int", "-3") 
        self.selenium.select("hasSummary:boolean", "label=False")
        self.selenium.click("name=zmanage_editProperties:method")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.do_command('assertValue', ['miny:int', '-2'])
        self.selenium.do_command('assertValue', ['maxy:int', '-3'])
        self.selenium.do_command('assertSelectedValue', ['hasSummary:boolean', 'False'])
        self.selenium.click("link=Graph Commands")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.do_command('assertTextPresent', ['101'])
        self.selenium.do_command('assertTextPresent', ['501'])
        self.selenium.do_command('assertTextPresent', ['seconds'])
        self.selenium.do_command('assertTextPresent', ['logarithmic'])
        self.selenium.do_command('assertTextPresent', ['base=1024'])
        self.selenium.click("link=PerformanceConf")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.do_command('assertElementPresent', ['link=graphTestingStringEdit'])
        self.selenium.do_command('assertTextPresent', ['101'])
        self.selenium.do_command('assertTextPresent', ['501'])
        self.selenium.do_command('assertTextPresent', ['seconds'])
        self.selenium.click("link=graphTestingStringEdit")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.type("newId", "graphTestingString") 
        self.selenium.click("name=zmanage_editProperties:method")
        self._deleteGraphDefinition()

    def testEditGraphCustomDefinition(self):
        """Adds custom graph definition in the PerformanceConf template"""
        self._addGraphDefinition()
        self.selenium.click("link=graphTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.click("link=Graph Commands")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.do_command('assertTextNotPresent', ['CustomDefinitionTest'])
        self.selenium.do_command('assertTextNotPresent', ['CustomDefinitionTest2'])
        self.selenium.do_command('assertTextNotPresent', ['CustomDefinitionTest3'])
        self.selenium.click("link=Graph Custom Definition")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.type("custom:text", "CustomDefinitionTest, CustomDefinitionTest2, CustomDefinitionTest3") 
        self.selenium.click("name=zmanage_editProperties:method")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.click("link=Graph Commands")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.do_command('assertTextPresent', ['CustomDefinitionTest,'])
        self.selenium.do_command('assertTextPresent', ['CustomDefinitionTest2,'])
        self.selenium.do_command('assertTextPresent', ['CustomDefinitionTest3'])
        self._deleteGraphDefinition()
    
    def testAddGraphDefinitionAndCheckPerformanceMonitor(self):
        """Adds graph definition in the PerformanceConf template and then checks in a performance Monitor to make sure it has been added there"""
        self._addGraphDefinition()
        self._addPerformanceMonitor()   
        self.selenium.click("link=performanceTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.click("link=Performance")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.waitForElement("id=graph_4_panr")
        self.waitForElement("id=linkcheck_label")
        self.selenium.do_command('assertTextPresent', ['graphTestingString'])
        self._deletePerformanceMonitor()
        self._deleteGraphDefinition()

    def testAddAndDeleteGraphPoints(self):
        """Adds and Deletes a pre defined Data Source, Threshold, and Custom Data Points, changes their settings and verifies them against the PerformaceConf page"""
        self._addGraphDefinition()
        self._addGraphPointDataPointSuccess()
        self._addGraphPointThresholdPing()
        self._addGraphPointCustom()
        self.selenium.click("link=PerformanceConf")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.do_command('assertTextPresent', ['zenping cycle time, success, customGraphPointTest'])
        self.selenium.click("link=graphTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self._deleteGraphPointDataPointSuccess()
        self._deleteGraphPointThresholdPing()
        self._deleteGraphPointCustom()
        self._deleteGraphDefinition()

    def testAddDataSource(self):
        """Adds and deletes a data source and a Datapoint"""
        self._addDataSource()
        self._addDataSourceDataPoint()
        self.waitForElement("link=dataSourceTestingString")
        self.selenium.click("link=dataSourceTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self._deleteDataSourceDataPoint()
        self._deleteDataSource()

    def testAddTestingDataPointToGraphDef(self):
        """Creates a testing data source and data point, adds the data point as a graph definition of a test graph, then verifies against the PerformanceConf page"""
        self._addDataSource()
        self._addDataSourceDataPoint()
        self.waitForElement("link=PerformanceConf")
        self.selenium.click("link=PerformanceConf")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self._addGraphDefinition()
        self._addGraphPointDataPointTestingString()
        self.selenium.do_command('assertTextPresent',
                ['dataSourceTestingString_dataPointTestingString'])
        self._deleteGraphPointDataPointTestingString()
        self._deleteGraphDefinition()
        self._deleteDataSource()
           
    def testMissingDataPointInGraphDefIsHandledProperly(self):
        """Verifies the Missing text is displayed next to a Datapoint that has been deleted but is still defined in a Graph Definition"""
        self._addDataSource()
        self._addDataSourceDataPoint()
        self.waitForElement("link=PerformanceConf")
        self.selenium.click("link=PerformanceConf")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self._addGraphDefinition()
        self._addGraphPointDataPointTestingString()
        self._deleteDataSource()
        self.selenium.do_command('assertTextPresent',
                ['dataPointTestingString(missing)'])
        self._deleteGraphDefinition()

    def testAddsEditAndDeleteThreshold(self):
        """Adds, edits/verifies settings and deletes a Threshold"""
        self._addDataSource()
        self._addDataSourceDataPoint()
        self._addThreshold() 
        self.selenium.click("link=thresholdTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        #self.selenium.type("newId", "thresholdTestingStringEdit")
           #Disabled because of Ticket 2610
        self.selenium.select("dsnames:list", "label=dataSourceTestingString_dataPointTestingString")
        self.selenium.type("minval", "25") 
        self.selenium.type("maxval", "30") 
        self.selenium.select("eventClass", "label=/App/Email")
        self.selenium.select("severity:int", "value=5")
        self.selenium.type("escalateCount:int", "23") 
        self.selenium.select("enabled:boolean", "label=False")
        self.selenium.click("name=zmanage_editProperties:method")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.do_command('assertValue', ['minval', '25'])
        self.selenium.do_command('assertValue', ['maxval', '30'])
        self.selenium.do_command('assertSelectedValue', ['eventClass',
                '/App/Email'])
        self.selenium.do_command('assertValue', ['escalateCount:int', '23'])
        self.selenium.click("link=PerformanceConf")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        #self.selenium.do_command('assertElementPresent', ['link=thresholdTestingStringEdit'])
        self.selenium.do_command('assertTextPresent', ['dataSourceTestingString_dataPointTestingString'])
        self.selenium.do_command('assertTextPresent', ['Critical'])
        self.selenium.do_command('assertTextPresent', ['False'])
        #self.selenium.click("link=thresholdTestingStringEdit")
        #self.selenium.wait_for_page_to_load(self.WAITTIME)
        #self.selenium.type("newId", "thresholdTestingString") 
        #self.selenium.click("name=zmanage_editProperties:method")
        self._deleteThreshold()
        self._deleteDataSource()

    def testMissingDataPointForThreshold(self):
        """Verifies the Missing text is displayed next to a Datapoint that has been deleted but is still defined in a Threshold"""
        self._addDataSource()
        self._addDataSourceDataPoint()
        self._addThreshold() 
        self.selenium.click("link=thresholdTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.select("dsnames:list", "label=dataSourceTestingString_dataPointTestingString")
        self.selenium.click("name=zmanage_editProperties:method")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self._deleteDataSource()
        self.selenium.do_command('assertTextPresent',
                ['dataSourceTestingString_dataPointTestingString(missing)'])
        self._deleteThreshold()

    def testAddTestingThresholdToGraphDef(self):
        """Creates a testing data source and data point, adds the data point to a threshold, adds the threshold as a graph definition of a test graph, then verifies against the PerformanceConf page"""
        self._addDataSource()
        self._addDataSourceDataPoint()
        self._addThreshold() 
        self.selenium.click("link=thresholdTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.select("dsnames:list", "label=dataSourceTestingString_dataPointTestingString")
        self.selenium.click("name=zmanage_editProperties:method")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self._addGraphDefinition()
        self._addGraphPointThresholdTestingString()
        self.selenium.do_command('assertTextPresent', ['thresholdTestingString'])
        self.selenium.click("link=thresholdTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.type("newId", "thresholdTestingStringEdit")
        self.selenium.click("name=manage_editProperties:method")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.click("link=graphTestingString")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.do_command('assertTextPresent',
                ['thresholdTestingStringEdit'])
        self.waitForElement("link=PerformanceConf")
        self.selenium.click("link=PerformanceConf")
        self.selenium.wait_for_page_to_load(self.WAITTIME)
        self.selenium.do_command('assertTextPresent',
                ['thresholdTestingStringEdit'])
        self._deleteGraphDefinition()
        self._deleteThreshold() 
        self._deleteDataSource()

if __name__ == "__main__":
    unittest.main()
