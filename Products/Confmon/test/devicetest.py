from Products.ZenUtils.ZCmdBase import ZCmdBase

class devicetest(ZCmdBase):

    def parseOptions(self):
        (self.options, args) = self.parser.parse_args()
        if len(args) < 1:
            self.parser.error("incorrect number of arguments")    
        self.devicename = args[0]


    def getdevice(self):
        return self.getDmdObj(self.devicename)


if __name__ == '__main__':
    dt = devicetest()
    device = dt.getdevice()
