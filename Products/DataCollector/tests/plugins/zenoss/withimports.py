from CollectorPlugin import TestPlugin
import re

class withimports(TestPlugin):

    def get_re(self):
        return re
