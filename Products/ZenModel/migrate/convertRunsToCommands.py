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
        commit = False
        zopes = filter(lambda s: s.name in ("zope", "Zope"), ctx.services)
        if len(zopes) == 1:
            temp = commandListDict(zopes[0].commands)
            temp.update(zopeCommands)
            if not zopes[0].commands:
                commit = True
            zopes[0].commands = commandDictList(temp)
        mariadbModels = filter(lambda s: s.name == "mariadb-model", ctx.services)
        if len(mariadbModels) == 1:
            temp = commandListDict(mariadbModels[0].commands)
            temp.update(mariadbModelCommands)
            if not mariadbModels[0].commands:
                commit = True
            mariadbModels[0].commands = commandDictList(temp)
        mariadbs = filter(lambda s: s.name == "mariadb", ctx.services)
        if len(mariadbs) == 1:
            temp = commandListDict(mariadbs[0].commands)
            temp.update(mariadbCommands)
            if not mariadbs[0].commands:
                commit = True
            mariadbs[0].commands = commandDictList(temp)
        # Commit our changes.
        if commit:
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
        commandList.append(sm.Command(k, v["Command"], v["CommitOnSuccess"]))
    return commandList


zopeCommands = {
    "zendmd": {
        "Command": "${ZENHOME:-/opt/zenoss}/bin/zenrun zendmd",
        "CommitOnSuccess": False
    },
    "upgrade": {
        "Command": "${ZENHOME:-/opt/zenoss}/bin/zenrun upgrade.sh doUpgrade",
        "CommitOnSuccess": False
    },
    "apply-custom-patches": {
        "Command": "${ZENHOME:-/opt/zenoss}/bin/zenrun patch.sh applyPatches",
        "CommitOnSuccess": True
    },
    "reportmail": {
        "Command": "${ZENHOME:-/opt/zenoss}/bin/zenrun reportmail.sh",
        "CommitOnSuccess": False
    },
    "help": {
        "Command": "${ZENHOME:-/opt/zenoss}/bin/zenrun help.sh",
        "CommitOnSuccess": False
    },
    "zenpack-manager": {
        "Command": "${ZENHOME:-/opt/zenoss}/bin/zenrun zenpack-manager.sh --service-id={{.ID}}",
        "CommitOnSuccess": True
    },
    "zenpack": {
        "Command": "${ZENHOME:-/opt/zenoss}/bin/zenrun zenpack.sh --service-id={{.ID}}",
        "CommitOnSuccess": False
    },
    "install-percona": {
        "Command": "${ZENHOME:-/opt/zenoss}/bin/zenrun percona.sh install",
        "CommitOnSuccess": True
    },
    "zenmib": {
        "Command": "${ZENHOME:-/opt/zenoss}/bin/zenrun zenmib.sh",
        "CommitOnSuccess": True
    }
}


mariadbCommands = {
    "rebuild_zodb_session": {
        "Command": "${ZENHOME:-/opt/zenoss}/bin/zenrun mysql.sh rebuild_zodb_session",
        "CommitOnSuccess": False
    }
}


mariadbModelCommands = {
    "rebuild_zodb_session": {
        "Command": "${ZENHOME:-/opt/zenoss}/bin/zenrun mysql.sh rebuild_zodb_session",
        "CommitOnSuccess": False
    }
}
