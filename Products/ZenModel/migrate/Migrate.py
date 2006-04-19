import Globals
import transaction
from Products.ZenUtils.ZCmdBase import ZCmdBase


allSteps = []

class Step:
    'A single migration step, to be subclassed for each new change'

    # Every subclass should set this so we know when to run it
    version = -1


    def __init__(self):
        "self insert ourselves in the list of all steps"
        allSteps.append(self)


    def prepare(self):
        "do anything you must before running the cutover"
        pass

    def cutover(self, dmd):
        "perform changes to the database"
        raise NotImplementedError

    def cleanup(self):
        "remove any intermediate results"
        pass


class Migration:
    "main driver for migration: walks the steps and performs commit/abort"
    commit = False

    def message(self, msg):
        print msg


    def migrate(self):
        "walk the steps and apply them"
        steps = allSteps[:]
        steps.sort(lambda a, b: cmp(a.version, b.version))
        
        # check version numbers
        good = True
        while steps and steps[0].version < 0:
            self.message("Migration %s does not set the version number")
            steps.pop(0)
            good = False
        if not good:
            self.message("Errors found, quitting")
            return

        class zendmd(ZCmdBase): pass
        zendmd = zendmd()
        dmd = zendmd.dmd
        app = dmd.getPhysicalRoot()

        # dump old steps
        if not hasattr(dmd, 'version'):
            dmd.version = 1.0
        current = dmd.version
        while steps and steps[0].version < current:
            steps.pop(0)

        for m in steps:
            m.prepare()

        for m in steps:
            if m.version != current:
                self.message("Database going to version %s" % m.version)
            self.message('Installing %s' % m.__class__)
            m.cutover(dmd)
            dmd.version = m.version

        for m in steps:
            m.cleanup()


    def cutover(self):
        '''perform the migration, applying all the new steps,
        recovering on error'''
        self.backup()
        try:
            self.migrate()
            self.success()
        except Exception, ex:
            self.error("Recovering")
            self.recover()
            raise


    def error(self, msg):
        import sys
        print >>sys.stderr, msg


    def backup(self):
        pass


    def recover(self):
        transaction.abort()


    def success(self):
        self.message('committing')
        if self.commit:
            transaction.commit()
        self.message("Migration successful")

def main():
    import sys
    m = Migration()
    m.commit = sys.argv[1:].count('commit') > 0
    m.cutover()

if __name__ == '__main__':
    # reimport ourselves using the name everyone else uses
    from Products.ZenModel.migrate import Migrate
    # reset allSteps using the one from the normal import
    allSteps = Migrate.allSteps
    main()
