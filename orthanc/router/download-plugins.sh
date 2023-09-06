#!/bin/bash

set -e
cd

URL=https://lsb.orthanc-server.com
VERSION_PYTHON=4.1

wget ${URL}/plugin-python/debian-buster-python-3.7/${VERSION_PYTHON}/libOrthancPython.so

mv ./libOrthancPython.so               /usr/local/share/orthanc/plugins/