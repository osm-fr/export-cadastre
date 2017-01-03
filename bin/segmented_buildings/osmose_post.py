#!/usr/bin/env python
# -*- coding: utf-8 -*- 
#
# This script is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# It is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with it. If not, see <http://www.gnu.org/licenses/>.


import sys
import os.path

import time
import socket
import urllib
import urllib2
import traceback
import poster.encode
import poster.streaminghttp
poster.streaminghttp.register_openers()
from cStringIO import StringIO


def osmose_frontend_post(updt_url, source, password, content_filepath):
    update_finished = False
    err_code = 0
    nb_iter = 0
    while not update_finished and nb_iter < 3:
        time.sleep(nb_iter * 15)
        nb_iter += 1
        try:
            (tmp_dat, tmp_headers) = poster.encode.multipart_encode(
                    {"content": open(content_filepath, "rb"),
                     "source": source,
                     "code": password})
            tmp_req = urllib2.Request(updt_url, tmp_dat, tmp_headers)
            #fd = urllib2.urlopen(tmp_req, timeout=1800)
            fd = urllib2.urlopen(tmp_req)
            dt = fd.read().decode("utf8").strip()
            if dt[-2:] != "OK":
                sys.stderr.write((u"UPDATE ERROR %s: %s\n"%(content_filepath, dt)).encode("utf8"))
                err_code |= 4
            else:
                print("POST " + content_filepath + " OK")
            update_finished = True
        except socket.timeout:
            sys.stderr.write("got a timeout\n")
            pass
        except:
            s = StringIO()
            traceback.print_exc()
            sys.stderr.write("error on update...\n")

    if not update_finished:
        sys.stderr.write("failed to upload " + content_filepath + "\n")
        err_code |= 1

    return err_code

def main(args):
    updt_url, source, password, content_filepath = args
    return osmose_frontend_post(updt_url, source, password, content_filepath)


if __name__ == "__main__":
    err_code = main(sys.argv[1:])
    sys.exit(err_code)
