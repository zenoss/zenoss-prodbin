from HTMLParser import HTMLParser
import getopt, sys, urllib
import pprint

STATUS = ('good', 'g', 'warning', 'W', 'error', 'E')

class ParseSiteScope(HTMLParser):

    def __init__(self, tcount):
        self.result = {}
        self.curset = {}
        self.lcount = 0
        self.tcount = tcount 
        HTMLParser.__init__(self)

    def handle_starttag(self, tag, attrs):
    	if tag == "img": 
            for x in attrs:
                a = x[0]
                v = x[1]
                if a == "alt":
                    if v in STATUS:
                        self.curset["status"] = v

        elif tag == "a":
            for x in attrs:
                a = x[0]
                v = x[1]

                if self.curset:
                    self.lcount += 1

                if (a == "href" and self.curset 
                        and self.lcount == self.tcount):
                    self.curset[a] = v
                     
                elif a =="title" and self.curset:
                    self.result[v] = self.curset
                    self.curset = {}
                    self.lcount = 0

    def handle_data(self, data):
        print "data =", data
        if self.curset and self.lcount == self.tcount:
            self.result[data] = self.curset
            self.curset = {} 
            self.lcount = 0

if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hc:f:u:", 
                                    ["help", "file=", "url=", "count="])
    except getopt.GetoptError:
        # print help information and exit:
        #usage()
        sys.exit(2)

    file = None
    url = None
    count = 0
    for o, a in opts:
        if o in ("-h", "--help"):
            #usage()
            sys.exit()
        if o in ("-u", "--url"):
            url = a
        if o in ("-f", "--file"):
            file = a
        if o in ("-c", "--count"):
            count = int(a)

    x = ParseSiteScope(count)
    if file:
        x.feed(open(file).read())
    elif url:
        sock = urllib.urlopen(url)
        htmlsource = sock.read()
        sock.close()
        x.feed(htmlsource)

    x.close()
    pprint.pprint(x.result)
