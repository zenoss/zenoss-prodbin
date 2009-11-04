
Option (1) - browser

    You can run the test in the browser by running
        PYTHONPATH="$ZENHOME:$PYTHONPATH" ./server.py

    and then hitting
        http://localhost:7999/modules/directstore/index.html


Option (2) - command line

    Or you can run them on the command line by running
        PYTHONPATH="$ZENHOME:$PYTHONPATH" ./runtests.py

    the exit code indicates the number of test failures.
