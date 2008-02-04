from setuptools import setup, find_packages

setup(
    name = 'ZENPACKID',
    version = '1.0',
    author = '',
    organization = '',
    description = '',    
    long_description = '',
    author_email = '',
    maintainer = '',
    maintainer_email = '',

    namespace_packages = ['ZenPacks', 'ZenPacks.PACKAGE'],
    packages = ['ZenPacks', 'ZenPacks.PACKAGE', 'ZenPacks.PACKAGE.ZENPACKID'],
    include_package_data = True,
    package_data = {
         '': ['*.txt'],
         'ZenPacks.PACKAGE.ZENPACKID': ['objects/*','skins/ZENPACKID/*'],
         },

    install_requires = [],

    # Every ZenPack egg must define exactly one zenoss.zenpacks entry point
    # of this form.
    entry_points = {
        'zenoss.zenpacks': 'ZENPACKID = ZenPacks.PACKAGE.ZENPACKID',
    },

    # All ZenPack eggs must be installed in unzipped form.
    zip_safe = False,    
)