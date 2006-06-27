import sys
import os
import glob
import pprint

import Globals
import transaction


from Products.ZenUtils.ZCmdBase import ZCmdBase


class zenmib(ZCmdBase):
    
    MIB_MOD_ATTS = ('language', 'contact', 'description')

    def load(self):

        if len(self.args) > 0:
            mibnames = self.args
        else:
            smimibdir = os.path.join(os.environ['ZENHOME'], 'share/mibs')
            mibnames = glob.glob(smimibdir + '/site/*')

            
        mibs = self.dmd.Mibs
        for mibname in mibnames:
            try:
                result = {}
                self.log.debug("%s", mibname.split('/')[-1])
                exec os.popen('smidump -fpython %s 2>/dev/null' % mibname) in result
                mib = result.get('MIB', None)
                if mib:
                    modname = mib['moduleName']
                    #mod = mibs.findMibModule(modname)
                    mod = None
                    if mod:
                        self.log.warn("skipping %s already loaded", modname)
                        continue
                    mod = mibs.createMibModule(modname, self.options.path)
                    for key, val in mib[modname].items():
                        if key in self.MIB_MOD_ATTS:
                            setattr(mod, key, val)
                    if mib.has_key('nodes'):
                        for name, values in mib['nodes'].items():
                            mod.createMibNode(name, **values) 
                    if mib.has_key('notifications'):
                        for name, values in mib['notifications'].items():
                            mod.createMibNotification(name, **values) 
                    self.log.info("Loaded mib %s oid names", modname)
                    if not self.options.nocommit: transaction.commit() 
                else:
                    self.log.error("Failed to load mib: %s", mibname)
            except (SystemExit, KeyboardInterrupt): raise
            except Exception:
                self.log.exception("Failed to load mib: %s", mibname)

        
    def buildOptions(self):
        ZCmdBase.buildOptions(self)
        self.parser.add_option('--path', 
                               dest='path',default="/",
                               help="path to load mib into")
        self.parser.add_option('--nocommit', action='store_true',
                               dest='nocommit',default=False,
                               help="don't commit after loading")


if __name__ == '__main__':
    zm = zenmib()
    zm.load()
