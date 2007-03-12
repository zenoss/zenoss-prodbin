import sys
from xml.dom.minidom import parseString
import StringIO
import re

import Globals

from Products.ZenUtils.ZCmdBase import ZCmdBase
from Products.ZenRelations.RelationshipManager import RelationshipManager

_newlines = re.compile('\n[\t \r]*\n', re.M)

class ExportDevices(ZCmdBase):

    def __init__(self):
        ZCmdBase.__init__(self)
        if not self.options.outfile:
            self.outfile = sys.stdout
        else:
            self.outfile = open(self.options.outfile, 'w')
        
    
    def buildOptions(self):
        """basic options setup sub classes can add more options here"""
        ZCmdBase.buildOptions(self)
        self.parser.add_option('-o', '--outfile',
                    dest="outfile",
                    help="output file for export default is stdout")
        self.parser.add_option('--ignore', action="append",
                    dest="ignorerels", default=[],
                    help="relations that should be ignored can be many")


    def stripUseless(self, doc):

        _retain_class = (
            "Products.ZenModel.DeviceClass",
            "Products.ZenModel.Device",
            )

        _retain_props = (
            "description",
            "productionState",
            "priority",
            "monitors",
            )

        def denewline(s):
            while re.search(_newlines, s):
                s = re.sub(_newlines, '\n', s)
            return s
        
        def clearObjects(node):
            def keepDevice(dev):
                try: return not dev.getAttribute('module') in _retain_class
                except: return True
            try: devs = node.getElementsByTagName('object')
            except AttributeError: pass
            else:
                devs = filter(keepDevice, devs)
                map(dev.parentNode.removeChild, devs)

        def clearProps(node):
            try: props = node.getElementsByTagName('property')
            except AttributeError: pass
            else:
                for prop in props:
                    if prop.getAttribute('module') not in _retain_props:
                        prop.parentNode.removeChild(prop)
        
        root = doc.getElementsByTagName('objects')[0]
        clearObjects(root)
        clearProps(root)

        #for dev in getDevices(doc): print dev.getAttribute('id')

        return denewline(doc.toprettyxml().replace('\t', ' '*4))


    def export(self):
        root = self.dmd.Devices
        buffer = StringIO.StringIO()
        if hasattr(root, "exportXml"):
            buffer.write("""<?xml version="1.0"?>\n""")
            buffer.write("<objects>\n")
            root.exportXml(buffer,self.options.ignorerels,True)
            buffer.write("</objects>\n")
            doc = parseString(buffer.getvalue())
            finalxml = self.stripUseless(doc)
            self.outfile.write(finalxml)
            doc.unlink()
            buffer.close()
        else:
            print "ERROR: root object not a exportable (exportXml not found)"
            


if __name__ == '__main__':
    ex = ExportDevices()
    ex.export()
