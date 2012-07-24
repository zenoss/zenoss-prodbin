##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2007, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################


import sys
import base64
import urllib2
from HTMLParser import HTMLParser
from urlparse import urlparse, urlunparse
import mimetypes
from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart
from email.MIMEImage import MIMEImage
from email.MIMEBase import MIMEBase

import Globals
from Products.ZenUtils.ZenScriptBase import ZenScriptBase
from Products.ZenUtils import Utils
import md5

def sibling(url, path):
    parts = list(urlparse(url))
    parts[2] = '/'.join(parts[2].split('/')[:-1] + [path])
    return urlunparse(parts[0:3] + ['', '',''])

class Page(HTMLParser):
    """Turn an html page into a mime-encoded multi-part email.
    Turn the <title> into the subject and keep only the text of the
    content pane.  Url references are turned into absolute references,
    and images are sent with the page."""

    def __init__(self, user, passwd, div, comment):
        HTMLParser.__init__(self)
        self.user = user
        self.passwd = passwd
        self.html = []
        self.images = {}
        self.contentPane = 0
        self.inTitle = False
        self.title = ''
        self.div = div
        self.comment = comment
        self.csv = None

    def fetchImage(self, url):
        return self.slurp(url).read()

    def absolute(self, url):
        url = url.strip()
        if url.startswith('http'):
            return url
        if url.startswith('/'):
            base = list(urlparse(self.base))
            base[2] = url
            return urlunparse(base[0:3] + ['', '',''])
        return sibling(self.base, url)

    def alter(self, attrs, name, function):
        result = []
        for a, v in attrs:
            if a.lower() == name:
                v = function(v)
            result.append( (a, v) )
        return result
        
    def updateSrc(self, attrs):
        def cache(v):
            if v not in self.images:
                v = self.absolute(v)
                name = 'img%s.png' % md5.md5(v).hexdigest()
                self.images[v] = (name, self.fetchImage(v))
            v, _ = self.images[v]
            return 'cid:%s' % v
        return self.alter(attrs, 'src', cache)
    
    def updateHref(self, attrs):
        return self.alter(attrs, 'href', self.absolute)

    def handle_starttag(self, tag, attrs):
        tag = tag.upper()
        if tag == 'TITLE':
            self.inTitle = True
        if tag == 'IMG':
            attrs = self.updateSrc(attrs)
        if tag == 'A':
            attrs = self.updateHref(attrs)
        if tag == 'DIV':
            if ('id',self.div) in attrs:
                self.contentPane = 1
            elif self.contentPane:
                self.contentPane += 1
        if self.contentPane:
            attrs = ' '.join(("%s=%s" % (a, repr(v))) for a, v in attrs)
            if attrs: attrs = ' ' + attrs
            self.html.append('<%s%s>' % (tag, attrs))

    def handle_endtag(self, tag):
        tag = tag.upper()
        if tag == 'TITLE':
            self.inTitle = False
        if self.contentPane:
            self.html.append('</%s>' % tag.upper())
        if tag == 'DIV':
            if self.contentPane:
                self.contentPane -= 1

    def handle_data(self, data):
        if self.contentPane:
            self.html.append(data)
        if self.inTitle:
            self.title += data

    def handleCSV(self, data):
        self.csv = data

    def slurp(self, url):
        req = urllib2.Request(url)
        encoded = base64.encodestring('%s:%s' % (self.user, self.passwd))[:-1]
        req.add_header("Authorization", "Basic %s" % encoded)
        try:
            result = urllib2.urlopen(req)
        except urllib2.HTTPError:
            import StringIO
            result = StringIO.StringIO('')
        return result

    def fetch(self, url):
        url = url.replace(' ', '%20')
        self.base = url.strip()
        response = self.slurp(url)

        # Handle CSV.
        if hasattr(response, 'headers') and \
            response.headers.get('Content-Type') == 'application/vnd.ms-excel':
            self.handleCSV(response.read())
        else:
            # Handle everything else as HTML.
            self.feed(response.read())

    def mail(self):
        msg = MIMEMultipart('related')
        msg.preamble = 'This is a multi-part message in MIME format'
        if self.csv is not None:
            txt = MIMEText(self.comment, 'plain')
            msg.attach(txt)
            csv = MIMEBase('application', 'vnd.ms-excel')
            csv.add_header('Content-ID', '<Zenoss Report>')
            csv.add_header('Content-Disposition', 'attachment',
                filename='zenoss_report.csv')
            csv.set_payload(self.csv)
            msg.attach(csv)
        else:
            txt = MIMEText(''.join(self.html), 'html')
            msg.attach(txt)
        for url, (name, img) in self.images.items():
            ctype, encoding = mimetypes.guess_type(url)
            if ctype == None:
                ctype = 'image/png'
            maintype, subtype = ctype.split('/', 1)
            img = MIMEImage(img, subtype)
            img.add_header('Content-ID', '<%s>' % name)
            msg.attach(img)
        return msg

class NoDestinationAddressForUser(Exception): pass
class UnknownUser(Exception): pass

class ReportMail(ZenScriptBase):

    def run(self):
        'Fetch a report by URL and post as a mime encoded email'
        self.connect()
        o = self.options
        if not o.passwd and not o.url:
            self.log.error("No zenoss password or url provided")
            sys.exit(1)
        try:
            user = self.dmd.ZenUsers._getOb(o.user)
        except AttributeError:
            self.log.error("Unknown user %s" % o.user)
            sys.exit(1)

        if not o.addresses and user.email:
            o.addresses = [user.email]
        if not o.addresses:
            self.log.error("No address for user %s" % o.user)
            sys.exit(1)
        page = Page(o.user, o.passwd, o.div, o.comment)
        url = self.mangleUrl(o.url)
        page.fetch(url)
        msg = page.mail()
        if o.subject:
            msg['Subject'] = o.subject
        elif page.title:
            msg['Subject'] = page.title
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
        if result:
            self.log.debug("sent email: %s to:%s", msg.as_string(), o.addresses)
        else:
            self.log.info("failed to send email to %s: %s %s",
                          o.addresses, msg.as_string(), errorMsg)
            sys.exit(1)
        sys.exit(0)

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
        self.parser.add_option('--div', '-d',
                               dest='div',
                               default='contentPane',
                               help='DIV to extract from URL')
        self.parser.add_option('--comment', '-c',
                               dest='comment',
                               default='Report CSV attached.',
                               help='Comment to include in body of CSV reports')


if __name__ == '__main__':
    ReportMail().run()
