from ctypes import cdll
import os
__author__ = 'Kevin Napier'

# Fetch or compute a version
try:
    from ._version import version as  __version__
except ImportError:
    try:
        from setuptools_scm import get_version
        __version__ = get_version()
        del get_version
    except ImportError:
        __version__ = "unknown"

# Find suffix
import sysconfig
suffix = sysconfig.get_config_var('EXT_SUFFIX')
if suffix is None:
    suffix = ".so"

# Import shared libraries
pymodulepath = os.path.dirname(__file__)

__libpath__ = pymodulepath + "/../libspacerocks" + suffix
clibspacerocks = cdll.LoadLibrary(__libpath__)

from .spacerock import SpaceRock
from .units import Units