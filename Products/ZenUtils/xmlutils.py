###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2007, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from lxml import etree

class XsdValidator(object):
    """
    This validator uses lxml to validate XML files against schemas defined by
    XSD files.
    """

    def __init__(self, xsd_path):
        self.xsd_path = xsd_path
        self.load_xsd(self.xsd_path)

    def load_xsd(self, xsd_path):
        """
        Load the XSD schema at `xsd_path`.
        """
        with open(xsd_path) as schema_file:
            xml_schema_doc = etree.parse(schema_file)
            self.xml_schema = etree.XMLSchema(xml_schema_doc)
            return self.xml_schema

    def validate_path(self, path):
        """
        Determine whether the file at `path` is valid using the configured xml schema.
        """
        with open(path) as xml_file:
            return self.validate_file(xml_file)

    def validate_file(self, f):
        """
        Determine whether a file is valid using the configured xml schema.
        """
        return self.xml_schema.validate(etree.parse(f))

    def check_path(self, path):
        """
        This method will throw exceptions when trying to validate a path.
        """
        with open(path) as xml_file:
            return self.check_file(xml_file)

    def check_file(self, xml_file):
        """
        This method will throw exceptions when trying to validate a file.
        """
        return self.xml_schema.assertValid(etree.parse(xml_file))