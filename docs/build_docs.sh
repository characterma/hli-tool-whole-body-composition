#!/bin/bash

VERSION=$1

#Set the version using the Makefile
r="${VERSION}"
v=$(echo $r | cut -f1-2 -d.)

#### Always write out minor version (r) instead of v
sed -i "s/^release.*$/release = u'$v'/g"  /opt/project/docs/conf.py
sed -i "s/^version.*$/version = u'$r'/g"  /opt/project/docs/conf.py
sed -i "s/^Release.*$/Release $r/g" /opt/project/docs/index.rst

make clean
make html
make latexpdf
