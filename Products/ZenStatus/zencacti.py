from zenagios import zenagios

class zencacti(zenagios):
    dataSourceType = 'CACTI'
    
    def parseResults(self, cmd):
        output = cmd.result.output.replace(':', '=')
        if output.find('=') < 0:
            pointName = cmd.points.keys()[0]
            output = '|%s=%s' % (pointName,output)
        else:
            output = '|' + output
        cmd.result.output = output
        print output
        return zenagios.parseResults(self, cmd)
    

if __name__ == '__main__':
    z = zencacti()
    z.main()
