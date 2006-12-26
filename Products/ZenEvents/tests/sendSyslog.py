from socket import *

s = socket(AF_INET, SOCK_DGRAM)
import time
now = time.strftime('%b %d %T %Z %Y')
m = '''<165>%s localhost myproc[10]: %%%% It's time to make the do-nuts.  %%%%  Ingredients: Mix=OK, Jelly=OK # Devices: Mixer=OK, Jelly_Injector=OK, Frier=OK # Transport: Conveyer1=OK, Conveyer2=OK # %%%%''' % now
m = '''<165>%s xlocalhost myproc[10]: %%%% It's time to make the do-nuts.  %%%%  Ingredients: Mix=OK, Jelly=OK # Devices: Mixer=OK, Jelly_Injector=OK, Frier=OK # Transport: Conveyer1=OK, Conveyer2=OK # %%%%''' % now
s.sendto(m, ('localhost', 514) )

