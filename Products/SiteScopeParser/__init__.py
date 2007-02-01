from ParserProduct import ParserProduct, manage_addParserForm, manage_addParser
from App.ImageFile import ImageFile

def initialize(registrar):
    registrar.registerClass(
        ParserProduct,
        constructors = (manage_addParserForm, manage_addParser),
    )
    registrar.registerHelp()

misc_ = {'redball_img': ImageFile('www/red-ball.gif', globals()),
        'greenball_img': ImageFile('www/green-ball.gif', globals()),
        'yellowball_img': ImageFile('www/yellow-ball.gif', globals()),
        'magentaball_img': ImageFile('www/magenta-ball.gif', globals()),
        'detail_img': ImageFile('www/detail.gif', globals()),
        }
