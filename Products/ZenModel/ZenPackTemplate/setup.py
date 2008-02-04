from setuptools import setup, find_packages

setup(
    # This ZenPack metadata should usually be edited with the Zenoss
    # ZenPack edit page.  Whenever the edit page is submitted it will
    # overwrite the values below (the ones it knows about) with new values.
    name = 'ZENPACKID',
    version = '1.0',
    author = '',
    license = '',
    
    # Indicate to setuptools which namespace packages the zenpack
    # participates in
    namespace_packages = ['ZenPacks', 'ZenPacks.PACKAGE'],
    
    # Tell setuptools what packages this zenpack provides.
    packages = ['ZenPacks', 'ZenPacks.PACKAGE', 'ZenPacks.PACKAGE.ZENPACKID'],
    
    # Tell setuptools to figure out for itself which files to include
    # in the binary egg when it is built.
    include_package_data = True,
    
    # Tell setuptools what non-python files should also be included
    # with the binary egg.
    package_data = {
         '': ['*.txt'],
         'ZenPacks.PACKAGE.ZENPACKID': ['objects/*','skins/ZENPACKID/*'],
         },

    # Indicate dependencies on other python modules or ZenPacks.  This line
    # is modified by zenoss when the ZenPack edit page is submitted.  Zenoss
    # tries to put add/delete the names it manages at the beginning of this
    # list, so any manual additions should be added to the end.  Things will
    # go poorly if this line is broken into multiple lines or modified to
    # dramatically.
    install_requires = [],

    # Every ZenPack egg must define exactly one zenoss.zenpacks entry point
    # of this form.
    entry_points = {
        'zenoss.zenpacks': 'ZENPACKID = ZenPacks.PACKAGE.ZENPACKID',
    },

    # All ZenPack eggs must be installed in unzipped form.
    zip_safe = False,    
)