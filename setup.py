from os import path, walk
from distutils.command.build import build
from setuptools import setup, find_packages
from setuptools.command.develop import develop
from setuptools.command.install import install

_here = path.abspath(path.dirname(__file__))

with open(path.join(_here, "VERSION"), "r") as f:
    _version = ''.join(f.readlines()).strip()


class ZenInstallCommand(install):
    """Used to disable installs."""

    def run(self):
        print "Installation disabled"
        import sys
        sys.exit(1)


class ZenBuildCommand(build):
    """Used to disable builds."""

    def run(self):
        print "Build disabled"
        import sys
        sys.exit(1)


class ZenDevelopCommand(develop):
    """Used to override the 'develop' command to provide custom pth file."""

    _nspkg_tmpl = (
        "import sys, types, os",
        "p = os.path.join(sys.prefix, *%(pth)r)",
        "m = sys.modules.setdefault(%(pkg)r, types.ModuleType(%(pkg)r))",
        "mp = m.__dict__.setdefault('__path__', [])",
        "(p not in mp) and mp.append(p)",
    )


def _get_bin_data():
    # Returns the list of scripts in the bin directory.
    # Ignores .pyc files and the zensocket binary file.
    # Running 'pip install -e .' re-installs these scripts
    # to /opt/zenoss/bin.
    result = []
    for dirpath, _, filenames in walk("./bin"):
        names = tuple(
            path.join(dirpath, name)
            for name in filenames
            if not name.endswith(".pyc")
            and name != "zensocket"
            and not path.isdir(path.join(dirpath, name))
        )
        result.append((dirpath[2:], names))
    return result


data_files = [
    ("share/mibs/site", ("share/mibs/site/ZENOSS-MIB.txt",)),
    ("lib/python2.7/site-packages", ("legacy/sitecustomize.py",)),
]
data_files.extend(_get_bin_data())


setup(
    name="zenoss-prodbin",
    version=_version,
    description="Zenoss Platform",
    author="Zenoss, Inc.",
    author_email="dev@zenoss.com",
    url="https://www.zenoss.com",
    license="",
    package_dir={"": "."},
    packages=find_packages(),
    namespace_packages=["Products"],
    include_package_data=True,
    data_files=data_files,
    zip_safe=False,
    install_requires=[],
    python_requires=">=2.7,<3",
    cmdclass={
        "build": ZenBuildCommand,
        "develop": ZenDevelopCommand,
        "install": ZenInstallCommand,
    },
)
