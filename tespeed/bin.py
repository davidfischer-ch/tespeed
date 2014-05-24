# -*- coding: utf-8 -*-

# Copyright:
#   2012-2013 Janis Jansons (janis.jansons@janhouse.lv)
#   2014      David Fischer (david.fischer.ch@gmail.com)

from __future__ import absolute_import, division, print_function, unicode_literals

import argparse

from .core import TeSpeed
from .utils import Log, set_proxy

__all__ = ('tespeed', )


def tespeed():

    parser = argparse.ArgumentParser(description='TeSpeed, CLI SpeedTest.net')

    parser.add_argument('server', nargs='?', type=str, default='', help='Use the specified server for testing (skip '
                        'checking for location and closest server).')
    parser.add_argument('-ls', '--list-servers', dest='list_servers', nargs='?', default=0, const=10,
                        help='List the servers sorted by distance, nearest first. Optionally specify number of servers '
                        'to show.')
    parser.add_argument('-w', '--csv', dest='store', action='store_true', help='Print CSV formated output to STDOUT.')
    parser.add_argument('-s', '--suppress', dest='suppress', action='store_true',
                        help='Suppress debugging (STDERR) output.')
    parser.add_argument('-mib', '--mebibit', dest='unit', action='store_true', help='Show results in mebibits.')
    parser.add_argument('-n', '--server-count', dest='server_count', nargs='?', default=1, const=1,
                        help='Specify how many different servers should be used in parallel. (Default: 1) '
                        '(Increase it for >100Mbit testing.)')

    parser.add_argument('-p', '--proxy', dest='use_proxy', type=int, nargs='?', const=4,
                        help='Specify 4 or 5 to use SOCKS4 or SOCKS5 proxy.')
    parser.add_argument('-ph', '--proxy-host', dest='proxy_host', type=str, nargs='?', default='127.0.0.1',
                        help='Specify socks proxy host. (Default: 127.0.0.1)')
    parser.add_argument('-pp', '--proxy-port', dest='proxy_port', type=int, nargs='?', default=9050,
                        help='Specify socks proxy port. (Default: 9050)')

    parser.add_argument('-cs', '--chunk-size', dest='chunk_size', nargs='?', type=int, default=10240,
                        help='Specify chunk size after which tespeed calculates speed. Increase this number 4 or 5 '
                        'times if you use weak hardware like RaspberryPi. (Default: 10240)')

    # parser.add_argument('-i', '--interface', dest='interface', nargs='?',
    #                     help='If specified, measures speed from data for the whole network interface.')

    args = parser.parse_args()

    if args.use_proxy:
        set_proxy(version=args.use_proxy, host=args.proxy_host, port=args.proxy_port)

    if args.list_servers:
        args.store = True

    log = Log(suppress=args.suppress, store=args.store)
    if not args.list_servers and args.server == '' and not args.store:
        log.debug('Getting ready. Use parameter -h or --help to see available features.\n')
    else:
        log.debug('Getting ready\n')
    try:
        tespeed = TeSpeed(server=args.list_servers and 'list-servers' or args.server, num_servers=args.server_count,
                          num_top=args.list_servers, unit=args.unit, chunk_size=args.chunk_size, log=log)
        tespeed.run_tests()
    except (KeyboardInterrupt, SystemExit):
        log.debug('\nSpeed test stopped.\n')
