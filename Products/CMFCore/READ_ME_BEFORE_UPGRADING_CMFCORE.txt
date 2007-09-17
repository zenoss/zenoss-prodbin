The file DirectoryView.py has a change at line 281 that allows all authenticated Users to see page templates and other files that are stored in the skins directories of our # products and zenpacks.  If you upgrade CMFCore you will break this functionailty!!!!!

The change is an addition to the if clause:

else:
    ob.manage_permission('View',('Authenticated',),1)


-EAD
