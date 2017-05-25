#!/usr/bin/python -R
####################################################
# Copy this file in the Web Root directory of      #
# your shared hosting account. Make sure it has    #
# executable permissions.                          #
#                                                  #
# Do not forget to replace "yourusername" below    #
# with your real username on the server!           #
#                                                  #
# You may need to make additional changes in       #
# this file if you have created a customized       #
# python environment (like virtualenv).            #
####################################################

import sys, os

# Add your cmbarter directory to the Python path:
#
# Put the absolute path to your "cmbarter" directory here. (This is
# the directory that contains the file "INSTALL".)
sys.path.insert(0, "/home/yourusername/cmbarter")

os.environ['DJANGO_SETTINGS_MODULE'] = "cmbarter.settings"

from django.core.servers.fastcgi import runfastcgi
runfastcgi(method="threaded", daemonize="false")
