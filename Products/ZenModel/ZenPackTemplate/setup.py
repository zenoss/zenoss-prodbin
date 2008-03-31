################################
# These variables are overwritten by Zenoss when the ZenPack is exported
# or saved.  Do not modify them directly here.
NAME = ''
VERSION = '1.0'
AUTHOR = ''
LICENSE = ''
NAMESPACE_PACKAGES = []
PACKAGES = []
INSTALL_REQUIRES = []
# STOP_REPLACEMENTS
################################
# Zenoss will not overwrite any changes you make below here.

from setuptools import setup, find_packages

setup(
    # This ZenPack metadata should usually be edited with the Zenoss
    # ZenPack edit page.  Whenever the edit page is submitted it will
    # overwrite the values below (the ones it knows about) with new values.
    name = NAME,
    version = VERSION,
    author = AUTHOR,
    license = LICENSE,
    
    # Indicate to setuptools which namespace packages the zenpack
    # participates in
    namespace_packages = NAMESPACE_PACKAGES,
    
    # Tell setuptools what packages this zenpack provides.
    packages = PACKAGES,
    
    # Tell setuptools to figure out for itself which files to include
    # in the binary egg when it is built.
    include_package_data = True,
    
    # Tell setuptools what non-python files should also be included
    # with the binary egg.
    package_data = {
         '': ['*.txt'],
         NAME: ['objects/*','skins/%s/*' % NAME],
         },

    # Indicate dependencies on other python modules or ZenPacks.  This line
    # is modified by zenoss when the ZenPack edit page is submitted.  Zenoss
    # tries to put add/delete the names it manages at the beginning of this
    # list, so any manual additions should be added to the end.  Things will
    # go poorly if this line is broken into multiple lines or modified to
    # dramatically.
    install_requires = INSTALL_REQUIRES,

    # Every ZenPack egg must define exactly one zenoss.zenpacks entry point
    # of this form.
    entry_points = {
        'zenoss.zenpacks': '%s = %s' % (NAME, NAME),
    },

    # All ZenPack eggs must be installed in unzipped form.
    zip_safe = False,    
)