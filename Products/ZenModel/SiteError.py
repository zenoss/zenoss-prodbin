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

__doc__="""SiteError

SiteError consolidates code used to handle and report site errors.
"""

import smtplib
import re
import cgi # for cgi.escape()

class SiteError:

    SMTP_HOST = 'mail.zenoss.com'
    ERRORS_ADDRESS = 'errors@zenoss.com'

    def cleanUrl(cls, errorUrl):
        ''' Strip protocol and domain from the url
        '''
        stripDomain = False
        if errorUrl.startswith('http://'):
            errorUrl = errorUrl[len('http://'):]
            stripDomain = True
        elif errorUrl.startswith('https://'):
            errorUrl = errorUrl[len('https://'):]
            stripDomain = True
        if stripDomain and '/' in errorUrl:
            errorUrl = errorUrl[errorUrl.find('/'):]
        return errorUrl
    cleanUrl = classmethod(cleanUrl)


    def createEmailHeader(cls, fromAddress, toAddress, subject):
        ''' Create the smnp header for an error email
        '''
        header = 'To: %s\nFrom: %s\nSubject: %s\n' % (
                    toAddress, fromAddress, subject)
        return header
    createEmailHeader = classmethod(createEmailHeader)

        
    def createReport(cls, errorType, errorValue, errorTrace, errorUrl, revision,
                        inHtml=True, contactName=None, contactEmail=None, 
                        comments=None):
        ''' Produce a summary of the given error details suitable for use
        in an error email (inHtml=false) or on a page (inHtml=true)
        '''
        def StripTags(s):
            ''' Strip html tags from string
            '''
            return re.sub('<[^>]*>', '', s)

        # If not inHtml then strip html tags from the errorTrace
        if inHtml:
            linebreak = '<br />\n'
            contactName = cgi.escape(contactName)
            contactEmail = cgi.escape(contactEmail)
            comments = cgi.escape(comments)
        else:
            linebreak = '\n'
            errorType = StripTags(errorType)
            errorValue = StripTags(errorValue)
            errorTrace = StripTags(errorTrace)
            errorTrace = re.sub('\r\n\r\n', '\r\n', errorTrace)
        msg = linebreak.join(['Type: %s' % errorType,
                                'Value: %s' % errorValue,
                                'URL: %s' % cls.cleanUrl(errorUrl),
                                'Revision: %s' % revision,
                                '%s' % errorTrace,
                                'Contact name: %s' % (contactName or ''),
                                'Email address: %s' % (contactEmail or ''),
                                'Comments: %s' % (comments or '')])
        return msg
    createReport = classmethod(createReport)


    def sendErrorEmail(cls, errorType, errorValue, errorTrace, errorUrl, 
                        revision,
                        contactName=None, contactEmail=None, comments=None):
        ''' Attempt to send an email to the zenoss errors email address
        with details of this error.
        Returns true if mail was sent, false otherwise.
        '''
        import socket
        fqdn = socket.getfqdn()
        fromAddress = 'errors@%s' % fqdn
        cleanUrl = cls.cleanUrl(errorUrl)
        subject = '%s: %s (%s)' % (errorType, errorValue[:15], cleanUrl)
        header = cls.createEmailHeader(
                    fromAddress, cls.ERRORS_ADDRESS, subject)
        body = cls.createReport(errorType, errorValue, errorTrace, cleanUrl,
                                revision,
                                0, contactName, contactEmail, comments)
        mailSent = False
        server = smtplib.SMTP(cls.SMTP_HOST)
        try:
            server.sendmail(fromAddress, cls.ERRORS_ADDRESS, 
                            '%s\n\n%s' % (header, body))
            mailSent = True
        finally:
            server.quit()
        return mailSent
    sendErrorEmail = classmethod(sendErrorEmail)
    