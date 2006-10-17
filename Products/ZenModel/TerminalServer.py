import warnings
warnings.warn("TerminalServer is deprecated", DeprecationWarning)
import Globals
from Device import Device

class TerminalServer(Device):
    def getRRDTemplateName(self):
        return "Device"

