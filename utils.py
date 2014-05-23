# -*- coding: utf-8 -*-

# Copyright:
#   2012-2013 Janis Jansons (janis.jansons@janhouse.lv)
#   2014      David Fischer (david.fischer.ch@gmail.com)

from __future__ import absolute_import, division, print_function, unicode_literals

import socket, sys
from SocksiPy import socks
from StringIO import StringIO

__all__ = ('CallbackStringIO', 'StringIO', 'print_debug', 'print_result', 'set_proxy', 'socks')


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

    def __init__(self, suppress=False, store=False):
        self.suppress = suppress
        self.store = store

    def debug(self, string):
        if not self.suppress:
            sys.stderr.write(string.encode('utf8'))

    def result(self, string):
        if self.store:
            sys.stdout.write(string.encode('utf8'))


# Thanks to Ryan Sears for http://bit.ly/17HhSli
def set_proxy(typ=socks.PROXY_TYPE_SOCKS4, host='127.0.0.1', port=9050):
    socks.setdefaultproxy(typ, host, port)
    socket.socket = socks.socksocket
