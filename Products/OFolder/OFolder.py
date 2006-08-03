'''OFolder, a folder with explicit control over the order of elements.'''

from Globals import InitializeClass, DTMLFile
from AccessControl import ClassSecurityInfo
from OFS.Folder import Folder

class OFolder(Folder):
  '''OFolder contain an ordered sequence of objects. Otherwise, they behave like folders.'''
  meta_type= 'OFolder'

  security= ClassSecurityInfo()

  security.declareProtected('OFolder: reorder',
                            'manage_reorder',
                            )

  def manage_reorder(self,order, REQUEST=None, cmp= lambda x,y: cmp(x.order,y.order)):
    '''reorder the folders children according to *order*.'''
    order.sort(cmp)
    d= _dictify(self._objects); l= []
    for x in order: l.append(d[x.id])
    self._objects= tuple(l)
    if REQUEST is not None:
      return self.manage_main(self,REQUEST,
                              manage_tabs_message='reordered')

  manage_main= DTMLFile('dtml/main', globals())

InitializeClass(OFolder)


manage_addOFolderForm= DTMLFile('dtml/ofolderAdd',globals())
def manage_addOFolder(self,id, title='', REQUEST=None):
  '''add an OFolder.'''
  ob= OFolder()
  ob.id= id; ob.title= title
  self._setObject(id,ob)

  if REQUEST is not None:
    du= getattr(self,'DestinationURL',self.absolute_url)
    du= du()
    REQUEST.RESPONSE.redirect('%s/manage_main?manage_tabs_message=OFolder+created&update_menu:int=1' % du)
    

def _dictify(t):
  d= {}
  for r in t: d[r['id']]= r
  return d
