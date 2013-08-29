##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2008, 2009, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


from pprint import pprint

from Products.ZenTestCase.BaseTestCase import BaseTestCase
from Products.ZenRRD.tests.BaseParsersTestCase import Object
from Products.ZenRRD.CommandParser import ParsedResults

from Products.ZenRRD.parsers.ps import ps

class TestParsers(BaseTestCase):
    def testPs1(self):
        """
        A one-off test of the ps parser that does not use the data files.
        """
        deviceConfig = Object()
        deviceConfig.device = 'localhost'
        cmd = Object()
        cmd.deviceConfig = deviceConfig
        cmd.command = 'command'
        
        cmd.regex = ".*Job.*"
        cmd.excludeRegex = "nothing"
        cmd.componentId = "url_Job"

        p1 = Object()
        p1.id = 'cpu'
        p1.data = dict(id='url_Job',
                       alertOnRestart=True,
                       failSeverity=3)
        p2 = Object()
        p2.id = 'mem'
        p2.data = dict(id='url_Job',
                       alertOnRestart=True,
                       failSeverity=3)
        p3 = Object()
        p3.id = 'count'
        p3.data = dict(id='url_Job',
                       alertOnRestart=True,
                       failSeverity=3)
        cmd.points = [p1, p2, p3]
        cmd.result = Object()

        # the last process (with timestamp 10:23 is = 62300?)
        cmd.result.output = """  PID   RSS     TIME COMMAND
345 1 10:23 notherJob1 a b c
123 1 00:00:00 someJob a b c
234 1 00:00:00 anotherJob a b c
"""
        #create empty data structure for results
        results = ParsedResults()
        
        parser = ps()
        # populate results
        parser.processResults(cmd, results)
        
        self.assertEqual(len(results.values), 3)
        self.assertEqual(len(results.events), 3)
        # Check time of 10:23 equals 623 minutes
        #print "623 number = %s" % results.values[0][1]
        #assert results.values[0][1] == 623
        self.assertEqual(len([value for dp, value in results.values if value == 62300]), 1)
        self.assertEqual(len([ev for ev in results.events if ev['severity'] == 0]), 3)
        
        results = ParsedResults()
        cmd.result.output = """  PID   RSS     TIME COMMAND
124 1 00:00:00 someJob a b c
456 1 00:00:00 someOtherJob 1 2 3
"""
        parser.processResults(cmd, results)

        self.assertEqual(len(results.values), 3) # ????? == 2
        # anotherJob went down
        # someJob restarted
        # noSuchProcess started
        self.assertEqual(len(results.events), 4) # ????? == 4
        for ev in results.events:
            summary = ev['summary']
            if summary.find('someJob') >= 0:
                self.assert_(summary.find('restarted') >= 0, "Did not find that \'%s\' contained \'restarted\'..." % summary)
            elif summary.find('notherJob') >= 0:
                self.assert_(summary.find('stopped') >= 0, "Did not find that \'%s\' contained \'stopped\'..." % summary)
            elif summary.find('someOtherJob') >= 0:
                self.assert_(summary.find('running') >= 0, "Did not find that \'%s\' contained \'running\'..." % summary)
            else:
                raise AssertionError("unexpected event")
    
    def testPsCase10733(self):
        """
        Case 10733
        """
        deviceConfig = Object()
        deviceConfig.device = 'localhost'
        cmd = Object()
        cmd.deviceConfig = deviceConfig
        cmd.command = 'command'

        cmd.regex = ".*bogo.*"
        cmd.excludeRegex = "nothing"
        cmd.componentId = "url_bogo"

        p1 = Object()
        p1.id = 'cpu'
        p1.data = dict(id='url_bogo',
                       alertOnRestart=True,
                       failSeverity=3)
        p2 = Object()
        p2.id = 'mem'
        p2.data = dict(id='url_bogo',
                       alertOnRestart=True,
                       failSeverity=3)
        p3 = Object()
        p3.id = 'count'
        p3.data = dict(id='url_bogo',
                       alertOnRestart=True,
                       failSeverity=3)

        cmd.points = [p1, p2, p3]
        cmd.result = Object()
        cmd.result.output = """ PID   RSS        TIME COMMAND
483362 146300    22:58:11 /usr/local/bin/bogoApplication --conf bogo.conf instance5
495844 137916    22:45:57 /usr/local/bin/bogoApplication --conf bogo.conf instance6
508130 138196    22:23:08 /usr/local/bin/bogoApplication --conf bogo.conf instance3
520290  1808    00:00:00 /usr/sbin/aixmibd
561300 140440    22:13:15 /usr/local/bin/bogoApplication --conf bogo.conf instance4
561301 140440    22:13:15 /usr/local/bin/bogoApplication --conf bogo.conf instance4
561302 140440    22:13:15 /usr/local/bin/wrapper bogoApplication --conf bogo.conf instance4
749772  3652    00:00:00 /bin/nmon_aix53 -f -A -P -V -m /tmp
"""
        results = ParsedResults()
        parser = ps()
        parser.processResults(cmd, results)

        self.assertEquals(len(results.values), 3)
        self.assertEquals(len(results.events), 6)
        self.assertEquals(results.events[0]['severity'], 0)
        for dp, value in results.values:
            if 'count' in dp.id:
                self.assertEquals(value, 6)
            elif 'cpu' in dp.id:
                self.assertEquals(value, 48522100.0)
            elif 'mem' in dp.id:
                self.assertEquals(value, 843732.0)
            else:
                raise AssertionError("unexpected value")
    
    def testPsCase15745(self):
        """
        Case 15745
        """
        deviceConfig = Object()
        deviceConfig.device = 'localhost'
        cmd = Object()
        cmd.deviceConfig = deviceConfig
        cmd.command = 'command'

        cmd.regex = ".*oracle.*"
        cmd.excludeRegex = "nothing"
        cmd.componentId = "url_sendmail"

        p1 = Object()
        p1.id = 'cpu_cpu'
        p1.data = dict(id='url_oracle',
                       alertOnRestart=True,
                       failSeverity=3)
        cmd.points = [p1]
        cmd.result = Object()
        cmd.result.output = """ PID   RSS        TIME COMMAND
483362 146300    22:58:11 /usr/local/test/oracleYAMDB1 (LOCAL=NO)
495844 137916    22:45:57 /usr/bin/sendmail: MTA: accepting connections
520290  1808    00:00:00 /usr/sbin/aixmibd
"""
        results = ParsedResults()
        parser = ps()
        parser.processResults(cmd, results)
        # Oracle process with parenthesis in args should be detected
        for ev in results.events:
            summary = ev['summary']
            if summary.find('oracleYAMDB1') >= 0:
                self.assert_(summary.find('running') >= 0, "\'%s\' did not contain running")
            else:
                raise AssertionError("unexpected event")
    
    def testPsZen5278(self):
        """
        Jira 5278 - defunct process matching
        """
        deviceConfig = Object()
        deviceConfig.device = 'localhost'
        cmd = Object()
        cmd.deviceConfig = deviceConfig
        cmd.command = 'command'

        cmd.regex = ".*defunct.*"
        cmd.excludeRegex = "nothing"
        cmd.componentId = "url_defunct"

        p1 = Object()
        p1.id = 'cpu_cpu'
        p1.data = dict(id='url_defunct',
        #p1.data = dict(processName='aioserver',
                       alertOnRestart=False,
                       failSeverity=0)
        cmd.points = [p1]
        cmd.result = Object()
        cmd.result.output = """ PID   RSS        TIME COMMAND
28835916 00:00:00 <defunct>
28967020 1788 00:00:00 sshd: root@sherwood
29622478 448 00:00:08 aioserver
29688042 00:00:00 <defunct>
"""
        results = ParsedResults()
        parser = ps()
        parser.processResults(cmd, results)
        # Ensure that we can track defunct processes
        for ev in results.events:
            summary = ev['summary']
            if summary.find('defunct') >= 0:
                self.assert_(summary.find('running') >= 0, "\'%s\' did not contain running")
            else:
                raise AssertionError("unexpected event")

    def testPsExcludeRegex(self):
        """
        test the search regex and excule regex
        """
        deviceConfig = Object()
        deviceConfig.device = 'localhost'
        cmd = Object()
        cmd.deviceConfig = deviceConfig
        cmd.command = 'command'
        
        cmd.regex = ".*myapp.*"
        cmd.excludeRegex = ".*(vim|tail|grep|tar|cat|bash).*"
        cmd.componentId = "url_myapp"

        p1 = Object()
        p1.id = 'cpu'
        p1.data = dict(id='url_myapp',
                       alertOnRestart=True,
                       failSeverity=3)
        p2 = Object()
        p2.id = 'mem'
        p2.data = dict(id='url_myapp',
                       alertOnRestart=True,
                       failSeverity=3)
        p3 = Object()
        p3.id = 'count'
        p3.data = dict(id='url_myapp',
                       alertOnRestart=True,
                       failSeverity=3)
        cmd.points = [p1, p2, p3]
        cmd.result = Object()

        cmd.result.output = """  PID   RSS     TIME COMMAND
120 1 00:00:01 myapp
121 1 00:00:02 vim myapp
122 1 00:00:03 vim /path/to/myapp
123 1 00:00:04 tail -f myapp.log
124 1 00:00:05 tail -f /path/to/myapp.log
125 1 00:00:06 /path/to/myapp
126 1 00:00:07 grep foo myapp
127 1 00:00:08 grep foo /path/to/myapp
128 1 00:00:09 tar cvfz bar.tgz /path/to/myapp
129 1 00:00:10 tar cvfz bar.tgz /path/to/myapp
130 1 00:00:11 cat /path/to/myapp
131 1 00:00:12 bash -c /path/to/myapp
132 1 00:00:13 bash -c myapp
"""
        #create empty data structure for results
        results = ParsedResults()
        
        parser = ps()
        # populate results
        parser.processResults(cmd, results)

        self.assertEqual(len(results.values), 3)
        self.assertEqual(len(results.events), 2) # only 2 events ... 
        
        for val in results.values:
            if val[0].id == 'cpu':
                self.assertEqual(val[1], 700.0)

    def testPsNameCaptureGroups(self):
        """
        test the search regex and excule regex
        """
        deviceConfig = Object()
        deviceConfig.device = 'localhost'
        cmd = Object()
        cmd.deviceConfig = deviceConfig
        cmd.command = 'command'
        
        cmd.regex = "(tele.[^\/]*\/).*(cel[^\/].*\/)"
        cmd.excludeRegex = "nothing"
        cmd.componentId = "url_telekinesis_celery"

        p1 = Object()
        p1.id = 'cpu'
        p1.data = dict(id='url_telekinesis_celery',
                       alertOnRestart=True,
                       failSeverity=3)
        p2 = Object()
        p2.id = 'mem'
        p2.data = dict(id='url_telekinesis_celery',
                       alertOnRestart=True,
                       failSeverity=3)
        p3 = Object()
        p3.id = 'count'
        p3.data = dict(id='url_telekinesis_celery',
                       alertOnRestart=True,
                       failSeverity=3)
        cmd.points = [p1, p2, p3]
        cmd.result = Object()

        cmd.result.output = """  PID   RSS     TIME COMMAND
120 1 00:00:01 /home/zenoss/dummy_processes/test_two_name_capture_groups/television/folder1/celtic/test1.sh
121 1 00:00:02 /home/zenoss/dummy_processes/test_two_name_capture_groups/television/folder1/celtic/test11.sh
122 1 00:00:03 /home/zenoss/dummy_processes/test_two_name_capture_groups/television/folder1/celery/test2.sh
123 1 00:00:04 /home/zenoss/dummy_processes/test_two_name_capture_groups/television/folder1/celery/test22.sh
124 1 00:00:05 /home/zenoss/dummy_processes/test_two_name_capture_groups/television/folder1/cellular_phones/test3.sh
125 1 00:00:06 /home/zenoss/dummy_processes/test_two_name_capture_groups/television/folder1/cellular_phones/test33.sh
126 1 00:00:07 /home/zenoss/dummy_processes/test_two_name_capture_groups/telephone/folder1/celtic/test1.sh
127 1 00:00:08 /home/zenoss/dummy_processes/test_two_name_capture_groups/telephone/folder1/celtic/test11.sh
128 1 00:00:09 /home/zenoss/dummy_processes/test_two_name_capture_groups/telephone/folder1/celery/test2.sh
129 1 00:00:10 /home/zenoss/dummy_processes/test_two_name_capture_groups/telephone/folder1/celery/test22.sh
130 1 00:00:11 /home/zenoss/dummy_processes/test_two_name_capture_groups/telephone/folder1/cellular_phones/test3.sh
131 1 00:00:12 /home/zenoss/dummy_processes/test_two_name_capture_groups/telephone/folder1/cellular_phones/test33.sh
132 1 00:00:13 /home/zenoss/dummy_processes/test_two_name_capture_groups/telekinesis/folder1/celtic/test1.sh
133 1 00:00:14 /home/zenoss/dummy_processes/test_two_name_capture_groups/telekinesis/folder1/celtic/test11.sh
134 1 00:00:15 /home/zenoss/dummy_processes/test_two_name_capture_groups/telekinesis/folder1/celery/test2.sh
135 1 00:00:16 /home/zenoss/dummy_processes/test_two_name_capture_groups/telekinesis/folder1/celery/test22.sh
136 1 00:00:17 /home/zenoss/dummy_processes/test_two_name_capture_groups/telekinesis/folder1/cellular_phones/test3.sh
137 1 00:00:18 /home/zenoss/dummy_processes/test_two_name_capture_groups/telekinesis/folder1/cellular_phones/test33.sh
"""
        #create empty data structure for results
        results = ParsedResults()
        
        parser = ps()
        # populate results
        parser.processResults(cmd, results)

        self.assertEqual(len(results.values), 3)
        self.assertEqual(len(results.events), 2) # only 2 events ... 
        
        for val in results.values:
            if val[0].id == 'cpu':
                self.assertEqual(val[1], 3100.0)
    
def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestParsers))
    return suite
