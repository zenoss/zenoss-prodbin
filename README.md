# Zenoss Prodbin
A repository for several Zenoss Products, including the User Interface


## Build
Zenoss Prodbin is a standard Python package.  It installs into the site-packages directory like a normal Python distribution.

The included makefile provides the following targets:

   build - (default) Build the distribution artifact, a .whl file, and place it in the dist/ folder
   clean - Remove all build artifacts
   test - Configure the testing environment and run the tests


## Developmemt
See [Zenoss product-assembly](https://github.com/zenoss/product-assembly)

Once in a devshell, change directory to /mnt/src/zenoss-prodbin and run `pip install -e .`, which will (re)install
prodbin as an editable package.
