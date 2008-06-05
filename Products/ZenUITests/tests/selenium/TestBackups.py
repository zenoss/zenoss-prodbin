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
# the "Backups" Tab in the Settings.
#
# Noel Brockett
#

import unittest

from util.selTestUtils import *

from SelTestBase import SelTestBase

class TestBackups(SelTestBase):
    """Defines an object that runs tests under the Backups tab in Settings"""

    
    def _goToBackups(self):
        sel = self.selenium
        sel.click("link=Settings")
        sel.wait_for_page_to_load("30000")
        sel.click("link=Backups")
        sel.wait_for_page_to_load("30000")

    def _createBackup(self):
        sel = self.selenium

    def _deleteBackup(self):
        sel = self.selenium
        sel.click("fileNames:list")
        sel.click("BackupFiles_list_btn")
        sel.click("BackupFileslistdeleteBackup")
        self.waitForElement("manage_deleteBackups:method")
        sel.click("manage_deleteBackups:method")
        sel.wait_for_page_to_load("30000")
        if sel.is_element_present("fileNames:list"):
            self._deleteBackup()
        
    def _deleteAllBackup(self):
        sel = self.selenium
        sel.click("selectall_1")
        sel.click("BackupFiles_list_btn")
        sel.click("BackupFileslistdeleteBackup")
        self.waitForElement("manage_deleteBackups:method")
        sel.click("manage_deleteBackups:method")
        sel.wait_for_page_to_load("30000")
        if sel.is_element_present("fileNames:list"):   
            self._deleteBackup()

    def testNoMySQL(self):
        """Tests Backups with No MySQL options"""
        sel = self.selenium
        self._goToBackups()
        sel.click("includeEvents")
        sel.click("includeMysqlLogin")
        if sel.is_element_present("fileNames:list"):   
            self._deleteBackup()
        self.failIf(sel.is_element_present("fileNames:list"))
        sel.click("manage_createBackup:method")
        sel.wait_for_page_to_load("30000")
        try: self.failUnless(sel.is_text_present("Command Output"))
        except AssertionError, e: self.verificationErrors.append(str(e))
        try: self.failUnless(sel.is_text_present("DONE"))
        except AssertionError, e: self.verificationErrors.append(str(e))
        try: self.failUnless(sel.is_text_present("Backup complete."))
        except AssertionError, e: self.verificationErrors.append(str(e))
        sel.click("link=Backups")
        sel.wait_for_page_to_load("30000")
        sel.click("includeEvents")
        sel.click("includeMysqlLogin")
        sel.click("manage_createBackup:method")
        sel.wait_for_page_to_load("30000")
        try: self.failUnless(sel.is_text_present("Command Output"))
        except AssertionError, e: self.verificationErrors.append(str(e))
        try: self.failUnless(sel.is_text_present("DONE"))
        except AssertionError, e: self.verificationErrors.append(str(e))
        try: self.failUnless(sel.is_text_present("Backup complete."))
        except AssertionError, e: self.verificationErrors.append(str(e))
        sel.click("link=Backups")
        sel.wait_for_page_to_load("30000")
        sel.click("selectall_1")
        sel.click("selectnone_1")
        self._deleteAllBackup()
        self.failIf(sel.is_text_present("Error"))
        self.failIf(sel.is_element_present("fileNames:list"))
 
    
    def testMySQLEventsDB(self):
        """Tests Backups with the events database MySQL option selected"""
        sel = self.selenium
        self._goToBackups()
        sel.click("includeMysqlLogin")
        if sel.is_element_present("fileNames:list"):   
            self._deleteBackup()
        self.failIf(sel.is_element_present("fileNames:list"))
        sel.click("manage_createBackup:method")
        sel.wait_for_page_to_load("30000")
        try: self.failUnless(sel.is_text_present("Command Output"))
        except AssertionError, e: self.verificationErrors.append(str(e))
        try: self.failUnless(sel.is_text_present("DONE"))
        except AssertionError, e: self.verificationErrors.append(str(e))
        try: self.failUnless(sel.is_text_present("Backup complete."))
        except AssertionError, e: self.verificationErrors.append(str(e))
        sel.click("link=Backups")
        sel.wait_for_page_to_load("30000")
        sel.click("includeMysqlLogin")
        sel.click("manage_createBackup:method")
        sel.wait_for_page_to_load("30000")
        try: self.failUnless(sel.is_text_present("Command Output"))
        except AssertionError, e: self.verificationErrors.append(str(e))
        try: self.failUnless(sel.is_text_present("DONE"))
        except AssertionError, e: self.verificationErrors.append(str(e))
        try: self.failUnless(sel.is_text_present("Backup complete."))
        except AssertionError, e: self.verificationErrors.append(str(e))
        sel.click("link=Backups")
        sel.wait_for_page_to_load("30000")
        sel.click("selectall_1")
        sel.click("selectnone_1")
        self._deleteAllBackup()
        self.failIf(sel.is_text_present("Error"))
        self.failIf(sel.is_element_present("fileNames:list"))



    def testMySQLLogin(self):
        """Tests Backups with only the MySQL login option selected"""
        sel = self.selenium
        self._goToBackups()
        sel.click("includeEvents")
        if sel.is_element_present("fileNames:list"):   
            self._deleteBackup()
        self.failIf(sel.is_element_present("fileNames:list"))
        sel.click("manage_createBackup:method")
        sel.wait_for_page_to_load("30000")
        try: self.failUnless(sel.is_text_present("Command Output"))
        except AssertionError, e: self.verificationErrors.append(str(e))
        try: self.failUnless(sel.is_text_present("DONE"))
        except AssertionError, e: self.verificationErrors.append(str(e))
        try: self.failUnless(sel.is_text_present("Backup complete."))
        except AssertionError, e: self.verificationErrors.append(str(e))
        sel.click("link=Backups")
        sel.wait_for_page_to_load("30000")
        sel.click("includeEvents")
        sel.click("manage_createBackup:method")
        sel.wait_for_page_to_load("30000")
        try: self.failUnless(sel.is_text_present("Command Output"))
        except AssertionError, e: self.verificationErrors.append(str(e))
        try: self.failUnless(sel.is_text_present("DONE"))
        except AssertionError, e: self.verificationErrors.append(str(e))
        try: self.failUnless(sel.is_text_present("Backup complete."))
        except AssertionError, e: self.verificationErrors.append(str(e))
        sel.click("link=Backups")
        sel.wait_for_page_to_load("30000")
        sel.click("selectall_1")
        sel.click("selectnone_1")
        self._deleteAllBackup()
        self.failIf(sel.is_text_present("Error"))
        self.failIf(sel.is_element_present("fileNames:list"))
 

    
    def testMySQLBoth(self):
        """Tests Backups with both MySQL options checked"""
        sel = self.selenium
        self._goToBackups()
        if sel.is_element_present("fileNames:list"):   
            self._deleteBackup()
        self.failIf(sel.is_element_present("fileNames:list"))
        sel.click("manage_createBackup:method")
        sel.wait_for_page_to_load("30000")
        try: self.failUnless(sel.is_text_present("Command Output"))
        except AssertionError, e: self.verificationErrors.append(str(e))
        try: self.failUnless(sel.is_text_present("DONE"))
        except AssertionError, e: self.verificationErrors.append(str(e))
        try: self.failUnless(sel.is_text_present("Backup complete."))
        except AssertionError, e: self.verificationErrors.append(str(e))
        sel.click("link=Backups")
        sel.wait_for_page_to_load("30000")
        sel.click("manage_createBackup:method")
        sel.wait_for_page_to_load("30000")
        try: self.failUnless(sel.is_text_present("Command Output"))
        except AssertionError, e: self.verificationErrors.append(str(e))
        try: self.failUnless(sel.is_text_present("DONE"))
        except AssertionError, e: self.verificationErrors.append(str(e))
        try: self.failUnless(sel.is_text_present("Backup complete."))
        except AssertionError, e: self.verificationErrors.append(str(e))
        sel.click("link=Backups")
        sel.wait_for_page_to_load("30000")
        sel.click("selectall_1")
        sel.click("selectnone_1")
        self._deleteAllBackup()
        self.failIf(sel.is_text_present("Error"))
        self.failIf(sel.is_element_present("fileNames:list"))



if __name__ == "__main__":
        unittest.main()

