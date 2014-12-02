##############################################################################
#
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

import sys
import os
import urllib2
from HTMLParser import HTMLParser
from urlparse import urlparse, urlunparse
from email.MIMEMultipart import MIMEMultipart
from email.mime.application import MIMEApplication
import Globals
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from Products.ZenUtils import Utils
import subprocess

gValidReportFileTypes = ['PDF','PNG','JPG','GIF']

def sibling(url, path):
    parts = list(urlparse(url))
    parts[2] = '/'.join(parts[2].split('/')[:-1] + [path])
    return urlunparse(parts[0:3] + ['', '',''])

class Page(HTMLParser):
    """Turn an html page into a mime-encoded multi-part email.
    Turn the <title> into the subject and keep only the text of the
    content pane.  Url references are turned into absolute references,
    and images are sent with the page."""

    def __init__(self, user, passwd):
        HTMLParser.__init__(self)
        self.user = user
        self.passwd = passwd

    def generateScreenShot(self, url, reportFileName):
        fullFileName = "/tmp/" + reportFileName
        command = ["/opt/zenoss/bin/phantomjs", "/opt/zenoss/Products/ZenReports/rasterize.js", url, self.user, self.passwd, fullFileName]
        print "Running: %s" % " ".join(command)
        phanomjsProcess = subprocess.Popen(command)
        phanomjsProcessRC = phanomjsProcess.wait()
        if phanomjsProcessRC:
            sys.stderr.write(" ##### ERROR: phantomjs process return code: %s \n" % phanomjsProcessRC)
            sys.exit(phanomjsProcessRC)
        else:
            print "file created: %s" % fullFileName

    def mail(self, reportFileName):
        msg = MIMEMultipart('related')
        msg.preamble = 'This is a multi-part message in MIME format'

        # Attaching PDF screenshot
        part = MIMEApplication(open("/tmp/" + reportFileName,"rb").read())
        part.add_header('Content-Disposition', 'attachment', filename=reportFileName)
        msg.attach(part)

        return msg

class ReportMail(ZenScriptBase):

    def run(self):
        'Fetch a report by URL and post as a mime encoded email'
        self.connect()
        o = self.options
        if not o.passwd and not o.url:
            sys.stderr.write("No zenoss password or url provided\n")
            sys.exit(1)
        try:
            user = self.dmd.ZenUsers._getOb(o.user)
        except AttributeError:
            sys.stderr.write("Unknown user %s\n" % o.user)
            sys.exit(1)

        if not o.addresses and user.email:
            o.addresses = [user.email]
        if not o.addresses:
            sys.stderr.write("No address for user %s\n" % o.user)
            sys.exit(1)
        page = Page(o.user, o.passwd)
        url = self.mangleUrl(o.url)

        reportFileType = self.determineFileFormat(o.reportFileType)
        reportFileName = "report_screenshot." + reportFileType
        page.generateScreenShot(url, reportFileName)
        msg = page.mail(reportFileName)

        # we aren't actually parsing any HTML so rely on the last "segment"
        # of the URL for the subject if one is not provided
        title = urllib2.unquote(url.split("/")[-1].split("?")[0])
        if o.subject:
            msg['Subject'] = o.subject
        elif title:
            msg['Subject'] = title
        else:
            msg['Subject'] = 'Zenoss Report'
        msg['From'] = o.fromAddress
        msg['To'] = ', '.join(o.addresses)

        result, errorMsg = Utils.sendEmail(msg,
                                           self.dmd.smtpHost,
                                           self.dmd.smtpPort,
                                           self.dmd.smtpUseTLS,
                                           self.dmd.smtpUser,
                                           self.dmd.smtpPass)

        # delete the file so we don't resend it with the next failing request
        if os.path.isfile(reportFileName):
            os.remove(reportFileName)

        if result:
            print "sent email: %s to:%s" % ( msg.as_string(), o.addresses)
        else:
            sys.stderr.write("failed to send email to %s: %s %s\n" %(o.addresses, msg.as_string(), errorMsg))
            sys.exit(1)

        sys.exit(0)

    def determineFileFormat(self, reportFileType):
        if reportFileType in gValidReportFileTypes:
            return reportFileType.lower()

        sys.stderr.write("Invalid file type: %s (creating a %s)\n" % (reportFileType, gValidReportFileTypes[0]))
        return gValidReportFileTypes[0].lower() # create a pdf

    def mangleUrl(self, url):
        if url.find('/zport/dmd/reports#reporttree:') != -1 :
            urlSplit = url.split('/zport/dmd/reports#reporttree:')
            url = urlSplit[0] + urlSplit[1].replace('.', '/')
        if url.find('adapt=false') == -1 :
            url += '?adapt=false' if url.find('?') == -1 else '&adapt=false'
        return url

    def buildOptions(self):
        ZenScriptBase.buildOptions(self)
        self.parser.add_option('--url', '-u',
                               dest='url',
                               default=None,
                               help='URL of report to send')
        self.parser.add_option('--reportFileType', '-r',
                               dest='reportFileType',
                               default='PDF',
                               help='report file type (%s)' % "|".join(gValidReportFileTypes))
        self.parser.add_option('--user', '-U',
                               dest='user',
                               default='admin',
                               help="User to log into Zenoss")
        self.parser.add_option('--passwd', '-p',
                               dest='passwd',
                               help="Password to log into Zenoss")
        self.parser.add_option('--address', '-a',
                               dest='addresses',
                               default=[],
                               action='append',
                               help='Email address destination '
                               '(may be given more than once).  Default value'
                               "comes from the user's profile.")
        self.parser.add_option('--subject', '-s',
                               dest='subject',
                               default='',
                               help='Subject line for email message.'
                               'Default value is the title of the html page.')
        self.parser.add_option('--from', '-f',
                               dest='fromAddress',
                               default='zenoss@localhost',
                               help='Origination address')

if __name__ == '__main__':
    ReportMail().run()
