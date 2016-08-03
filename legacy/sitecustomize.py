import sys, os, site
sys.setdefaultencoding('utf-8')
site.addsitedir(os.path.join(os.getenv('ZENHOME'), 'ZenPacks'))
if not os.getenv("RESTORE_ZENPACKS", None):
	site.addsitedir('/var/zenoss/ZenPacks')
import warnings
warnings.filterwarnings('ignore', '.*', DeprecationWarning)
