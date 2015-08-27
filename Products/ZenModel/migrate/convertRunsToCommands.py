##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

__doc__ = """
Update all Runs to new 5.1 Commands
"""
import logging
log = logging.getLogger("zen.migrate")

import Migrate
import servicemigration as sm
sm.require("1.0.0")




class ConvertRunsToCommands(Migrate.Step):

    version = Migrate.Version(5, 0, 70)

    def cutover(self, dmd):
        try:
            ctx = sm.ServiceContext()
        except sm.ServiceMigrationError:
            log.info("Couldn't generate service context, skipping.")
            return

        # Update the zope service commands.
        zopes = filter(lambda s: s.name == "Zope", ctx.services)
        if len(zopes) == 1:
            zopes[0].commands = 
                commandDictList(commandListDict(zopes[0].commands).update(zopeCommands))
        mariadbModels = filter(lambda s: s.name == "mariadb-model", ctx.services)
        if len(mariadbModels) == 1:
            mariadbModels[0] =
                commandDictList(commandListDict(mariadbModels[0].commands).update(mariadbModelCommands))
        mariadbs = filter(lambda s: s.name == "mariadb", ctx.services)
        if len(mariadbs) == 1:
            mariadbs[0] =
                commandDictList(commandListDict(mariadbs[0].commands).update(mariadbCommands))
        # Commit our changes.
        ctx.commit()

ConvertRunsToCommands()

def commandListDict(commandList):
    commandDict = {}
    for command in commandList:
        commandDict[command.name] = {
            "Command": command.command,
            "CommitOnSuccess": command.commitOnSuccess
        }
    return commandDict

def commandDictList(commandDict):
    commandList = []
    for k, v in commandDict.iteritems():
        commandList[k] = sm.Command(k, v.command, v.commitOnSuccess)
    return commandList

zopeCommands = {
    "zendmd": {
        "Command": "${ZENHOME:-/opt/zenoss}/bin/zenrun zendmd",
        "CommitOnSuccess": true
    },
    "upgrade": {
        "Command": "${ZENHOME:-/opt/zenoss}/bin/zenrun upgrade.sh doUpgrade",
        "CommitOnSuccess": false
    },
    "apply-custom-patches": {
        "Command": "${ZENHOME:-/opt/zenoss}/bin/zenrun patch.sh applyPatches",
        "CommitOnSuccess": true
    },
    "reportmail": {
        "Command": "${ZENHOME:-/opt/zenoss}/bin/zenrun reportmail.sh",
        "CommitOnSuccess": false
    },
    "help": {
        "Command": "${ZENHOME:-/opt/zenoss}/bin/zenrun help.sh",
        "CommitOnSuccess": false
    },
    "zenpack-manager": {
        "Command": "${ZENHOME:-/opt/zenoss}/bin/zenrun zenpack-manager.sh --service-id={{.ID}}",
        "CommitOnSuccess": true
    },
    "zenpack": {
        "Command": "${ZENHOME:-/opt/zenoss}/bin/zenrun zenpack.sh --service-id={{.ID}}",
        "CommitOnSuccess": false
    },
    "install-percona": {
        "Command": "${ZENHOME:-/opt/zenoss}/bin/zenrun percona.sh install",
        "CommitOnSuccess": true
    },
    "zenmib": {
        "Command": "${ZENHOME:-/opt/zenoss}/bin/zenrun zenmib.sh",
        "CommitOnSuccess": true
    }
}

mariadbCommands = {
    "rebuild_zodb_session": {
        "Command": "${ZENHOME:-/opt/zenoss}/bin/zenrun mysql.sh rebuild_zodb_session",
        "CommitOnSuccess": false
    }
}

mariadbModelCommands = {
    "rebuild_zodb_session": {
        "Command": "${ZENHOME:-/opt/zenoss}/bin/zenrun mysql.sh rebuild_zodb_session",
        "CommitOnSuccess": false
    }
}
