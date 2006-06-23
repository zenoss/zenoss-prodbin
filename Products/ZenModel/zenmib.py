import sys
import os
import glob
import pprint

import Globals
import transaction


SMI_MIB_DIR = os.path.join(os.environ['ZENHOME'], 'share/mibs')
MIBS = glob.glob(SMI_MIB_DIR + '/*/*-MIB*')

from Products.ZenUtils.ZCmdBase import ZCmdBase


class zenmib(ZCmdBase):
    
    MIB_MOD_ATTS = ('language', 'contact', 'description')

    def load(self, name):
        #for m in MIBS:
        mibs = self.dmd.Mibs
        result = {}
        self.log.debug("%s", name.split('/')[-1])
        exec os.popen('smidump -fpython %s 2>/dev/null' % name) in result
        mib = result.get('MIB', None)
        #pprint.pprint(mib)
        if mib:
            modname = mib['moduleName']
            mod = mibs.createMibModule(modname) #, path)
            for key, val in mib[modname].items():
                if key in self.MIB_MOD_ATTS:
                    setattr(mod, key, val)
            for name, values in mib['nodes'].items():
                mod.createMibNode(name, **values) 
            for name, values in mib['notifications'].items():
                mod.createMibNotification(name, **values) 
        #self.log.debug("Loaded %d oid names", len(Oids))
        transaction.commit() 

if __name__ == '__main__':
    zm = zenmib()
    zm.load(sys.argv[1])
