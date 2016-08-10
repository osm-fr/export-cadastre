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


import os
import sys
import math
import time
import zipfile
import os.path
import itertools
import unicodedata
import timeit
from functools import reduce

def write_string_to_file(string, filename):
  f = open(filename, "w")
  f.write(string)
  f.close()

def write_stream_to_file(stream, filename):
    CHUNK = 16 * 1024
    output = open(filename, "wb")
    while True:
        chunk = stream.read(CHUNK)
        if not chunk: break
        output.write(chunk)
    stream.close()
    output.close()


def download_cached(open_function, filename):
    ok_filename = filename + ".ok"
    if not (os.path.exists(filename) and os.path.exists(ok_filename)):
        if os.path.exists(ok_filename):
            os.remove(ok_filename)
        write_stream_to_file(open_function(), filename)
        open(ok_filename, 'a').close()
        return True
    else:
        return False

class open_cached:
    """Cache the content of a stream (given with a opening lambda function).
       Return the opening of the cached file.
    """
    def __init__(self, open_function, cache_filename):
        self.open_function = open_function
        self.cache_filename = cache_filename
        self.check_filename = cache_filename + ".ok"
    def __enter__(self):
        if not (os.path.exists(self.cache_filename) and os.path.exists(self.check_filename)):
            if os.path.exists(self.check_filename):
                os.unlink(self.check_filename)
            write_stream_to_file(self.open_function(), self.cache_filename)
            open(self.check_filename, "a").close()
        self.cache_file = open(self.cache_filename)
        return self.cache_file
    def __exit__(self, type, value, traceback):
        self.cache_file.close()
        if value == None:
            return True
        else:
            # In case of exception, we assume the content was wrong
            # so we delete the .ok file check so that it will
            # be downloaded again from the original stream next time.
            os.unlink(self.check_filename)
            return False

def print_flush(text):
    sys.stdout.write((text + "\n").encode("utf-8"))
    sys.stdout.flush()


def peek(list):
    """Return the last element of a list, or None if the list is empty"""
    if len(list):
      return list[-1]
    else:
      return None


def toposort(data):
    """Dependencies are expressed as a dictionary whose keys are items
       and whose values are a set of dependent items. Output is a list of
       sets in topological order. The first set consists of items with no
       dependences, each subsequent set consists of items that depend upon
       items in the preceeding sets.

       >>> print '\\n'.join(repr(sorted(x)) for x in toposort2({
       ...     2: set([11]),
       ...     9: set([11,8]),
       ...     10: set([11,3]),
       ...     11: set([7,5]),
       ...     8: set([7,3]),
       ...     }) )
       [3, 5, 7]
       [8, 11]
       [2, 9, 10]
    """
    def toposort2(data):
        # Ignore self dependencies.
        for k, v in data.items():
            v.discard(k)
        # Find all items that don't depend on anything.
        extra_items_in_deps = reduce(set.union, itervalues(data)) - set(iterkeys(data))
        # Add empty dependences where needed
        data.update({item:set() for item in extra_items_in_deps})
        while True:
            ordered = set(item for item, dep in iteritems(data) if not dep)
            if not ordered:
                break
            yield ordered
            data = {item: (dep - ordered)
                    for item, dep in iteritems(data)
                        if item not in ordered}
        assert not data, "Cyclic dependencies exist among these items:\n%s" % '\n'.join(repr(x) for x in iteritems(data))
    return itertools.chain.from_iterable(toposort2(data))

if (sys.version_info > (3, 0)):
    def iteritems(dictionary):
        return dictionary.items()
    def itervalues(dictionary):
        return dictionary.values()
    def iterkeys(dictionary):
        return dictionary.keys()
else:
    def iteritems(dictionary):
        return dictionary.iteritems()
    def itervalues(dictionary):
        return dictionary.itervalues()
    def iterkeys(dictionary):
        return dictionary.iterkeys()


def to_ascii(utf):
    return unicodedata.normalize('NFD',unicode(utf)).encode("ascii","ignore")


def named_chunks(l, n):
    """ Yield successive n-sized chunks from l.  """
    nb_chunks = (len(l) + n - 1) / n
    name_size = int(math.ceil(math.log10(nb_chunks+1)))
    name_format = "%%0%dd" % name_size
    for i,j in enumerate(xrange(0, len(l), n)):
        yield name_format % (i+1), l[j:j+n]


def command_line_error(error_message, help_message=""):
    if error_message:
        output = sys.stderr
    else:
        output = sys.stdout
    if help_message: 
        output.write(help_message.encode("utf-8") + "\n")
    if error_message:
        output.write(("ERREUR: " + error_message + "\n").encode("utf-8"))
        sys.exit(-1)
    else:
        sys.exit(0)


class Timer():
    def __init__(self, msg):
        self.start = timeit.default_timer()
        self.msg = msg
        print(msg)
    def __call__(self):
        return timeit.default_timer() - self.start
    def prnt(self):
        print(self.msg + " => " + str(round(self(), 4)) +  " s")


def open_zip_and_files_with_extension(file_list, extension):
    for name in file_list:
        if name.endswith(".zip"):
            inputzip = zipfile.ZipFile(name, "r")
            for name in inputzip.namelist():
                if name.endswith(extension):
                    f = inputzip.open(name)
                    yield name, f
                    f.close()
            inputzip.close()
        elif name.endswith(extension):
            f = open(name, "rb")
            yield name, f
            f.close()



def test(argv):
    # toppsort
    assert( [x for x in toposort({
           2: set([11,9]),
           9: set([11,8]),
           10: set([11,3,2]),
           11: set([7,5,8]),
           8: set([7,3]),
           7: set([5]),
           5 : set([3]),
       })] == [3, 5, 7, 8, 11, 9, 2, 10])

    #open_cached
    if os.path.exists("/tmp/test_cache.ok"): os.unlink("/tmp/test_cache.ok")
    with open_cached(lambda : open("/proc/uptime"), "/tmp/test_cache") as f:
        uptime = f.read()
        assert(len(uptime) > 0)
    assert(os.path.exists("/tmp/test_cache.ok"))
    time.sleep(1)
    with open_cached(lambda : open("/proc/uptime"), "/tmp/test_cache") as f:
        assert(uptime == f.read())
    os.unlink("/tmp/test_cache.ok")
    try:
        with open_cached(lambda : open("/proc/uptime"), "/tmp/test_cache") as f:
            assert(uptime != f.read())
            raise IndexError()
        assert(False)
    except IndexError:
        pass
    assert(not os.path.exists("/tmp/test_cache.ok"))


if __name__ == '__main__':
    test(sys.argv)


