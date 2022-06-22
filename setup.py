from os import path  # , walk
from distutils.command.build import build
from setuptools import setup, find_packages
from setuptools.command.develop import develop
from setuptools.command.install import install
from setuptools.command.sdist import sdist

_here = path.abspath(path.dirname(__file__))

with open(path.join(_here, "VERSION"), "r") as _f:
    _version = ''.join(_f.readlines()).strip()


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


def applySchemaVersion(*args, **kw):
    print("Applied: %s %s" % (args, kw))


sdist.sub_commands.append(("apply_schema_version", applySchemaVersion))


setup(
    name="Zenoss",
    version=_version,
    description="Zenoss Platform",
    author="Zenoss, Inc.",
    author_email="dev@zenoss.com",
    url="https://www.zenoss.com",
    package_dir={"": "."},
    packages=find_packages(
        exclude=[
            "bdd",
            "bdd.*",
            "Products.ZenUITests",
            "Products.ZenUITests.*",
            "Products.ZenModel.migrate.tests",
        ],
    ),
    namespace_packages=["Products"],
    include_package_data=True,
    zip_safe=False,
    install_requires=[],
    python_requires=">=2.7,<3",
    cmdclass={
        "build": ZenBuildCommand,
        "develop": ZenDevelopCommand,
        "install": ZenInstallCommand,
    },
    entry_points={
        "celery.commands": [
            "monitor=Products.Jobber.monitor:ZenJobsMonitor",
        ],
    },
)
