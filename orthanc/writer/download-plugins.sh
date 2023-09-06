#!/bin/bash

set -e
cd

URL=https://lsb.orthanc-server.com
VERSION_MYSQL=5.1
VERSION_PYTHON=4.1

wget ${URL}/plugin-mysql/${VERSION_MYSQL}/libOrthancMySQLIndex.so
wget ${URL}/plugin-mysql/${VERSION_MYSQL}/libOrthancMySQLStorage.so
wget ${URL}/plugin-python/debian-buster-python-3.7/${VERSION_PYTHON}/libOrthancPython.so

mv ./libOrthancMySQLIndex.so           /usr/local/share/orthanc/plugins/
mv ./libOrthancMySQLStorage.so         /usr/local/share/orthanc/plugins/
mv ./libOrthancPython.so               /usr/local/share/orthanc/plugins/