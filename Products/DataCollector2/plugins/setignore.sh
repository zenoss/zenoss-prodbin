#!/bin/sh
find . -not -path \*.svn\* -type d -exec svn propset svn:ignore "*.pyc" {} \;
