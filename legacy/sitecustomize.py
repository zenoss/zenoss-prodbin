import sys, os, site
sys.setdefaultencoding('utf-8')
site.addsitedir(os.path.join(os.getenv('ZENHOME'), 'ZenPacks'))
site.addsitedir('/var/zenoss/ZenPacks')
import warnings
warnings.filterwarnings('ignore', '.*', DeprecationWarning)
