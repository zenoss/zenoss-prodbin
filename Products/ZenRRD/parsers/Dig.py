##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2017, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import re

from Products.ZenUtils.Utils import getExitMessage
from Products.ZenRRD.CommandParser import CommandParser
from Products.ZenUtils.IpUtil import checkip

class Dig(CommandParser):

    def getAnswer(self, lst):
        answerHeader = filter(lambda x: 'ANSWER SECTION' in x,lst)[0]
        if answerHeader:
            return lst[lst.index(answerHeader)+1]
        return None

    def getExpectedIP(self, lst):
        topLine = lst[0]
        expectedIP = None
        match = re.search(r'.*% -e(.*)', topLine)
        if match:
            IPcandidate = match.group(1).strip()
            try:
                if checkip(IPcandidate):
                    expectedIP = IPcandidate
            except Exception:
                pass
        return expectedIP
    
    def getReturnedIP(self, answer):
        parts = answer.split('\t')
        returnedIP = None
        hostNameCandidate, IPcandidate = parts[0], parts[-1]
        hostName = hostNameCandidate.split()[0][:-1]
        try:
            if checkip(IPcandidate):
                returnedIP = IPcandidate
        except Exception:
            pass
        return (hostName, returnedIP)        
    
    def processResults(self, cmd, result):
        output = cmd.result.output
        exitCode = cmd.result.exitCode
        severity = cmd.severity
        expectedIP = None
        perfData = {}
        if exitCode == 0:
            severity = 0
        elif exitCode == 2:
            severity = min(severity + 1, 5)

        evt = {
                "device": cmd.deviceConfig.device,
                "message": '',
                "severity": severity,
                "component": cmd.component,
                "eventKey": cmd.eventKey,
                "eventClass": cmd.eventClass,
            }           

        lines = filter(None, output.splitlines())
        lines = [x.strip(' ;') for x in lines]
        
        answer = self.getAnswer(lines)

        if answer:

            expectedIP = self.getExpectedIP(lines)

            if expectedIP:
                hostName, returnedIP = self.getReturnedIP(answer)
                if not expectedIP == returnedIP:
                    message = 'DNS CRITICAL - expected {} but got {}'.format(expectedIP, returnedIP)
                    severity = 4
                    perfData = None

                    evt.update({
                        "message": message,
                        "performanceData": perfData,
                        "summary": message,
                        "severity": severity,
                    })
                    result.events.append(evt)
                    return

            header = filter(lambda x: 'HEADER' in x,lines)[0]
                
            status = re.search(r'status:(.*),', header).group(1).strip()
            if status == 'NOERROR':
                time = re.search(r'Query time:(.*\n)', output).group(1).strip()
                timeParts = time.split()
                timeValue = int(timeParts[0])
                if timeParts[1] == 'msec':
                    timeValue = timeValue/1000.0
                if expectedIP:
                    message = 'DNS OK - {} seconds response time. {} returns {}'.format(
                        timeValue, hostName, expectedIP)
                perfData['time'] = timeValue
                for dp in cmd.points:
                    if dp.id in perfData:
                        result.values.append((dp, perfData[dp.id]))
                        
            else:
                message = "DNS CRITICAL - Got an error from the server"
                severity = 4
                perfData = None

        else:
            message = "DNS CRITICAL - No payload from the server"
            severity = 4
            perfData = None

        evt.update({
            "message": message,
            "performanceData": perfData,
            "summary": message,
            "severity": severity,
        })

        result.events.append(evt)

