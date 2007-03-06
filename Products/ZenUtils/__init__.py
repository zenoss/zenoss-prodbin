from Products.CMFCore.DirectoryView import registerDirectory
registerDirectory('js', globals())

# import any monkey patches that may be necessary
from patches import pasmonkey
