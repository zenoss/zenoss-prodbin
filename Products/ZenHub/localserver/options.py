

def add_options(parser):
    parser.add_option(
        "--localport",
        dest="localport",
        type="int",
        default=14682,
        help="The app responds to localhost HTTP connections on this port",
    )


def add_arguments(parser):
    parser.add_argument(
        "--localport",
        type=int,
        default=14682,
        help="The app responds to localhost HTTP connections on this port",
    )
