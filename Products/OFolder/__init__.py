import OFolder


def initialize(context):

    context.registerClass(
        OFolder.OFolder,
        constructors=(OFolder.manage_addOFolderForm,
                      OFolder.manage_addOFolder),
        icon='www/Folder_icon.gif'
        )
    
    context.registerBaseClass(OFolder.OFolder)
