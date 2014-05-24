# -*- coding: utf-8 -*-

# Copyright:
#   2012-2013 Janis Jansons (janis.jansons@janhouse.lv)
#   2014      David Fischer (david.fischer.ch@gmail.com)

from __future__ import absolute_import, division, print_function, unicode_literals

import gzip, socket, socks, sys
from math import radians, cos, sin, asin, sqrt
from StringIO import StringIO

__all__ = (
    'CallbackStringIO', 'Log', 'closest', 'decompress_response', 'distance', 'num_download_threads_for',
    'num_upload_threads_for', 'set_proxy'
)


# Magic!
def getaddrinfo(*args):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (args[0], args[1]))]
socket.getaddrinfo = getaddrinfo


class CallbackStringIO(StringIO):
    """Using StringIO with callback to measure upload progress"""

    def __init__(self, num, th, d, buf='', log=None):
        # Force self.buf to be a string or unicode
        if not isinstance(buf, basestring):
            buf = str(buf)
        self.buf = buf
        self.len = len(buf)
        self.buflist = []
        self.pos = 0
        self.closed = False
        self.softspace = 0
        self.th = th
        self.num = num
        self.d = d
        self.total = self.len*self.th
        self.log = log

    def read(self, n=10240):
        next_chunk = StringIO.read(self, n)
        #if 'done' in self.d:
        #    return
        self.d[self.num] = self.pos
        down = 0
        for i in xrange(self.th):
            down = down + self.d.get(i, 0)
        if self.num == 0:
            percent = down / self.total
            percent = round(percent * 100, 2)
            if self.log:
                self.log.debug('Uploaded %d of %d bytes (%0.2f%%) in %d threads\r' %
                               (down, self.total, percent, self.th))
        #if down >= self.total:
        #    if self.log: self.log.debug('\n')
        #    self.d['done']=1
        return next_chunk

    def __len__(self):
        return self.len


class Log(object):

    BLANK_LINE = '                                                                                           \r'

    def __init__(self, suppress=False, store=False):
        self.suppress = suppress
        self.store = store

    def debug(self, string):
        if not self.suppress:
            sys.stderr.write(string.encode('utf8'))

    def result(self, string):
        if self.store:
            sys.stdout.write(string.encode('utf8'))


def closest(center, points, num=5):
    """Return object that is closest to center."""
    closest = {}
    for p in xrange(len(points)):
        p_distance = distance(center, [points[p]['lat'], points[p]['lon']])
        points[p]['distance'] = p_distance
        while True:
            if p_distance in closest:
                p_distance = p_distance + 00.1
            else:
                break
        closest[p_distance] = points[p]
    closest_objects = []
    # FIXME can be simplified
    for key in sorted(closest):
        closest_objects.append(closest[key])
        if len(closest_objects) >= num and num != 0:
            break
    return closest_objects


def decompress_response(response):
    """Return decompressed gzip response."""
    data = StringIO(response.read())
    gzipper = gzip.GzipFile(fileobj=data)
    return gzipper.read()


def distance(one, two):
    """
    Compute the great circle distance between two points on the earth specified in decimal degrees `haversine
    formula <http://stackoverflow.com/posts/4913653/revisions>`_ convert decimal degrees to radians.
    """
    lon1, lat1, lon2, lat2 = map(radians, [one[0], one[1], two[0], two[1]])
    a = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    c = 2 * asin(sqrt(a))
    km = 6367 * c
    return km


def num_download_threads_for(num_downloads):
    if num_downloads < 2:
        return 1
    elif num_downloads < 11:
        return 2
    elif num_downloads < 13:
        return 4
    elif num_downloads < 25:
        return 2
    elif num_downloads < 45:
        return 3
    elif num_downloads < 65:
        return 2
    return 2


def num_upload_threads_for(num_uploads):
    if num_uploads < 2:
        return 1
    elif num_uploads < 7:
        return 2
    elif num_uploads < 10:
        return 3
    elif num_uploads < 25:
        return 6
    elif num_uploads < 45:
        return 4
    elif num_uploads < 65:
        return 3
    return 2


# Thanks to Ryan Sears for http://bit.ly/17HhSli
def set_proxy(version, host='127.0.0.1', port=9050):
    socks.setdefaultproxy(getattr(socks, 'PROXY_TYPE_SOCKS' + version), host, port)
    socket.socket = socks.socksocket
