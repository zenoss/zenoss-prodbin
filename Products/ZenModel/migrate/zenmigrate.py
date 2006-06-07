import Globals
from Products.ZenModel.migrate import Migrate

def main():
    m = Migrate.Migration()
    m.main()

if __name__ == '__main__':
    main()
