#!/usr/bin/env python2
# -*- coding: utf-8 -*-

# Copyright:
#   2012-2013 Janis Jansons (janis.jansons@janhouse.lv)
#   2014      David Fischer (david.fischer.ch@gmail.com)

from __future__ import absolute_import, division, print_function, unicode_literals

import argparse, gzip, urllib, urllib2, time
from lxml import etree
from math import radians, cos, sin, asin, sqrt
from multiprocessing import Process, Pipe, Manager

from utils import CallbackStringIO, StringIO, Log, set_proxy, socks


class TeSpeed(object):

    DOWNLOAD_LIST = [
        '350x350', '350x350', '500x500', '500x500', '750x750', '750x750', '1000x1000', '1500x1500', '2000x2000',
        '2500x2500',

        '3000x3000', '3500x3500', '4000x4000', '1000x1000', '1000x1000', '1000x1000', '1000x1000', '1000x1000',
        '1000x1000', '1000x1000', '1000x1000', '1000x1000', '1000x1000', '1000x1000', '1000x1000', '1000x1000',
        '1000x1000', '1000x1000', '1000x1000', '1000x1000',

        '2000x2000', '2000x2000', '2000x2000', '2000x2000', '2000x2000', '2000x2000', '2000x2000', '2000x2000',
        '2000x2000', '2000x2000', '2000x2000', '2000x2000', '2000x2000', '2000x2000', '2000x2000', '2000x2000',
        '2000x2000', '2000x2000', '2000x2000', '2000x2000',

        '4000x4000', '4000x4000', '4000x4000', '4000x4000', '4000x4000'
    ]

    UPLOAD_SIZES = [
        1024*256, 1024*256, 1024*512, 1024*512, 1024*1024, 1024*1024, 1024*1024*2, 1024*1024*2, 1024*1024*2,  1024*512,
        1024*256, 1024*256, 1024*256, 1024*256, 1024*256, 1024*256, 1024*256, 1024*256, 1024*256, 1024*256,

        1024*512, 1024*512, 1024*512, 1024*512, 1024*512, 1024*512, 1024*512, 1024*512, 1024*512, 1024*512,
        1024*512, 1024*512, 1024*512, 1024*512, 1024*512, 1024*512, 1024*512, 1024*512, 1024*512, 1024*512,

        1024*256, 1024*256, 1024*256, 1024*256, 1024*256, 1024*256, 1024*256, 1024*256, 1024*256, 1024*256,
        1024*512, 1024*512, 1024*512, 1024*512, 1024*512, 1024*512, 1024*512, 1024*512, 1024*512, 1024*512,

        1024*1024*2, 1024*1024*2, 1024*1024*2, 1024*1024*2,  1024*1024*2, 1024*1024*2, 1024*1024*2, 1024*1024*2,
        1024*1024*2, 1024*1024*2, 1024*1024*2, 1024*1024*2, 1024*1024*2, 1024*1024*2,  1024*1024*2, 1024*1024*2,
        1024*1024*2, 1024*1024*2, 1024*1024*2, 1024*1024*2
    ]

    def __init__(self, server='', num_top=0, servercount=3, unit=False, chunk_size=10240, log=None):

        self.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:11.0) Gecko/20100101 Firefox/11.0',
            'Accept-Language': 'en-us,en;q=0.5',
            'Connection': 'keep-alive',
            'Accept-Encoding': 'gzip, deflate',
            #'Referer' : 'http://c.speedtest.net/flash/speedtest.swf?v=301256',
        }

        self.num_servers = servercount
        self.servers = [] if server == '' else [server]
        self.server = server
        self.down_speed = self.up_speed = -1
        self.latency_count = 10
        self.best_servers = 5
        self.chunk_size = chunk_size
        self.log = log

        if unit:
            self.units = 'MiB'
            self.unit = 1
        else:
            self.units = 'Mbit'
            self.unit = 0

        if log.store:
            log.debug('Printing CSV formated results to STDOUT.\n')

        self.num_top = int(num_top)

        self.post_data = ''
        self.test_speed()

    def distance(self, one, two):
    #Calculate the great circle distance between two points
    #on the earth specified in decimal degrees (haversine formula)
    #(http://stackoverflow.com/posts/4913653/revisions)
    # convert decimal degrees to radians

        lon1, lat1, lon2, lat2 = map(radians, [one[0], one[1], two[0], two[1]])
        # haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))
        km = 6367 * c
        return km

    def closest(self, center, points, num=5):
    # Returns object that is closest to center
        closest = {}
        for p in xrange(len(points)):
            now = self.distance(center, [points[p]['lat'], points[p]['lon']])
            points[p]['distance'] = now
            while True:
                if now in closest:
                    now = now + 00.1
                else:
                    break
            closest[now] = points[p]
        n = 0
        ret = []
        for key in sorted(closest):
            ret.append(closest[key])
            n += 1
            if n >= num and num != 0:
                break
        return ret

    def test_latency(self, servers):
    # Finding servers with lowest latency
        self.log.debug('Testing latency...\n')
        po = []
        for server in servers:
            now = self.test_single_latency(server['url'] + 'latency.txt?x=' + str(time.time()))*1000
            now = now / 2  # Evil hack or just pure stupidity? Nobody knows...
            if now == -1 or now == 0:
                continue
            self.log.debug('%0.0f ms latency for %s (%s, %s, %s) [%0.2f km]\n' %
                           (now, server['url'], server['sponsor'], server['name'], server['country'],
                            server['distance']))

            server['latency'] = now

            # Pick specified ammount of servers with best latency for testing
            if int(len(po)) < int(self.num_servers):
                po.append(server)
            else:
                largest = -1

                for x in xrange(len(po)):
                    if largest < 0:
                        if now < po[x]['latency']:
                            largest = x
                    elif po[largest]['latency'] < po[x]['latency']:
                        largest = x
                    #if cur['latency']

                if largest >= 0:
                    po[largest] = server

        return po

    def test_single_latency(self, dest_addr):
    # Checking latency for single server
    # Does that by loading latency.txt (empty page)
        request = self.get_request(dest_addr)

        average_time = 0
        total = 0
        for i in xrange(self.latency_count):
            error = 0
            start_time = time.time()
            try:
                urllib2.urlopen(request, timeout=5)
            except urllib2.URLError:
                error = 1

            if error == 0:
                average_time = average_time + (time.time() - start_time)
                total = total + 1

            if total == 0:
                return False

        return average_time / total

    def get_request(self, uri):
    # Generates a GET request to be used with urlopen
        req = urllib2.Request(uri, headers=self.headers)
        return req

    def post_request(self, uri, stream):
    # Generate a POST request to be used with urlopen
        req = urllib2.Request(uri, stream, headers=self.headers)
        return req

    def chunk_report(self, bytes_so_far, chunk_size, total_size, num, th, d, w):
    # Receiving status update from download thread

        if w == 1:
            return
        d[num] = bytes_so_far
        down = 0
        for i in xrange(th):
            down = down + d.get(i, 0)

        if num == 0 or down >= total_size * th:

            percent = down / (total_size * th)
            percent = round(percent * 100, 2)

            self.log.debug('Downloaded %d of %d bytes (%0.2f%%) in %d threads\r' % (down, total_size*th, percent, th))

        #if down >= total_size*th:
        #   self.log.debug('\n')

    def chunk_read(self, response, num, th, d, w=0, chunk_size=False, report_hook=None):
        # self.log.debug('Thread num %d %d %d starting to report\n' % (th, num, d))

        if not chunk_size:
            chunk_size = self.chunk_size

        if w == 1:
            return [0, 0, 0]

        total_size = response.info().getheader('Content-Length').strip()
        total_size = int(total_size)
        bytes_so_far = 0

        start = 0
        while 1:
            chunk = 0
            if start == 0:
                # self.log.debug('Started receiving data\n')
                chunk = response.read(1)
                start = time.time()

            else:
                chunk = response.read(chunk_size)
            if not chunk:
                break
            bytes_so_far += len(chunk)
            if report_hook:
                report_hook(bytes_so_far, chunk_size, total_size, num, th, d, w)
        end = time.time()

        return [bytes_so_far, start, end]

    def async_get(self, conn, uri, num, th, d):
        request = self.get_request(uri)
        start = end = size = 0
        try:
            response = urllib2.urlopen(request, timeout=30)
            size, start, end = self.chunk_read(response, num, th, d, report_hook=self.chunk_report)
        #except urllib2.URLError, e:
        #    self.log.debug('Failed downloading.\n')
        except:
            self.log.debug('                                                                                           \r')
            self.log.debug('Failed downloading.\n')
            conn.send([0, 0, False])
            conn.close()
            return
        conn.send([size, start, end])
        conn.close()

    def async_post(self, conn, uri, num, th, d):
        postlen = len(self.post_data)
        stream = CallbackStringIO(num, th, d, self.post_data, log=self.log)
        request = self.post_request(uri, stream)
        start = end = 0
        try:
            response = urllib2.urlopen(request, timeout=30)
            size, start, end = self.chunk_read(response, num, th, d, 1, report_hook=self.chunk_report)
        #except urllib2.URLError:
        #    self.log.debug('Failed uploading.\n')
        except:
            self.log.debug('                                                                                           \r')
            self.log.debug('Failed uploading.\n')
            conn.send([0, 0, False])
            conn.close()
            return
        conn.send([postlen, start, end])
        conn.close()

    def load_config(self):
    # Load the configuration file
        self.log.debug('Loading speedtest configuration...\n')
        uri = 'http://speedtest.net/speedtest-config.php?x=' + str(time.time())
        request = self.get_request(uri)
        response = urllib2.urlopen(request)

        # Load etree from XML data
        config = etree.fromstring(self.decompress_response(response))

        ip = config.find('client').attrib['ip']
        isp = config.find('client').attrib['isp']
        lat = float(config.find('client').attrib['lat'])
        lon = float(config.find('client').attrib['lon'])

        self.log.debug('IP: %s; Lat: %f; Lon: %f; ISP: %s\n' % (ip, lat, lon, isp))

        return {'ip': ip, 'lat': lat, 'lon': lon, 'isp': isp}

    def load_servers(self):
    # Load server list
        self.log.debug('Loading server list...\n')
        uri = 'http://speedtest.net/speedtest-servers.php?x=' + str(time.time())
        request = self.get_request(uri)
        response = urllib2.urlopen(request)

        # Load etree from XML data
        servers_xml = etree.fromstring(self.decompress_response(response))
        servers = servers_xml.find('servers').findall('server')
        server_list = []

        for server in servers:
            server_list.append({
                'lat': float(server.attrib['lat']),
                'lon': float(server.attrib['lon']),
                'url': server.attrib['url'].rsplit('/', 1)[0] + '/',
                #'url2': server.attrib['url2'].rsplit('/', 1)[0] + '/',
                'name': server.attrib['name'],
                'country': server.attrib['country'],
                'sponsor': server.attrib['sponsor'],
                'id': server.attrib['id'],
            })

        return server_list

    def decompress_response(sefl, response):
    # Decompress gzipped response
        data = StringIO(response.read())
        gzipper = gzip.GzipFile(fileobj=data)
        return gzipper.read()

    def find_best_server(self):
        self.log.debug('Looking for closest and best server...\n')
        best = self.test_latency(self.closest([self.config['lat'], self.config['lon']],
                                 self.server_list, self.best_servers))
        for server in best:
            self.servers.append(server['url'])

    def async_request(self, url, num, upload=0):
        connections = []
        d = Manager().dict()
        start = time.time()
        for i in xrange(num):
            full_url = self.servers[i % len(self.servers)] + url
            #print full_url
            connection = {}
            connection['parent'], connection['child'] = Pipe()
            connection['connection'] = Process(target=self.async_post if upload == 1 else self.async_get,
                                               args=(connection['child'], full_url, i, num, d))
            connection['connection'].start()
            connections.append(connection)

        for c in xrange(num):
            connections[c]['size'], connections[c]['start'], connections[c]['end'] = connections[c]['parent'].recv()
            connections[c]['connection'].join()

        end = time.time()

        self.log.debug('                                                                                           \r')

        sizes = 0
        #tspeed=0
        for c in xrange(num):
            if connections[c]['end'] is not False:
                #tspeed=tspeed+(connections[c]['size']/(connections[c]['end']-connections[c]['start']))
                sizes = sizes + connections[c]['size']

                # Using more precise times for downloads
                if upload == 0:
                    if c == 0:
                        start = connections[c]['start']
                        end = connections[c]['end']
                    else:
                        if connections[c]['start'] < start:
                            start = connections[c]['start']
                        if connections[c]['end'] > end:
                            end = connections[c]['end']

        took = end - start

        return [sizes, took]

    def test_upload(self):
    # Testing upload speed

        url = 'upload.php?x=' + str(time.time())

        sizes, took = [0, 0]
        data = ''
        for i in xrange(0, len(self.UPLOAD_SIZES)):
            if len(data) == 0 or self.UPLOAD_SIZES[i] != self.UPLOAD_SIZES[i-1]:
                #self.log.debug('Generating new string to upload. Length: %d\n' % (self.UPLOAD_SIZES[i]))
                data = ''.join('1' for x in xrange(self.UPLOAD_SIZES[i]))
            self.post_data = urllib.urlencode({'upload6': data})

            if i < 2:
                thrds = 1
            elif i < 5:
                thrds = 2
            elif i < 7:
                thrds = 2
            elif i < 10:
                thrds = 3
            elif i < 25:
                thrds = 6
            elif i < 45:
                thrds = 4
            elif i < 65:
                thrds = 3
            else:
                thrds = 2

            sizes, took = self.async_request(url, thrds, 1)
            #sizes, took=self.async_request(url, (i<4 and 1 or (i<6 and 2 or (i<6 and 4 or 8))), 1)
            if sizes == 0:
                continue

            size = self.speed_conversion(sizes)
            speed = size / took
            self.log.debug('Upload size: %0.2f MiB; Uploaded in %0.2f s\n' % (size, took))
            self.log.debug('\033[92mUpload speed: %0.2f %s/s\033[0m\n' % (speed, self.units))

            if self.up_speed < speed:
                self.up_speed = speed

            if took > 5:
                break

        #self.log.debug('Upload size: %0.2f MiB; Uploaded in %0.2f s\n' % (self.speed_conversion(sizes), took))
        #self.log.debug('Upload speed: %0.2f MiB/s\n' % (self.speed_conversion(sizes)/took))

    def speed_conversion(self, data):
        return data / 1024 ** 2 * (1 if self.unit == 1 else 1.048576 * 8)

    def test_download(self):
    # Testing download speed
        sizes, took = [0, 0]
        for i in xrange(0, len(self.DOWNLOAD_LIST)):
            url = 'random' + self.DOWNLOAD_LIST[i] + '.jpg?x=' + str(time.time()) + '&y=3'

            if i < 2:
                thrds = 1
            elif i < 5:
                thrds = 2
            elif i < 11:
                thrds = 2
            elif i < 13:
                thrds = 4
            elif i < 25:
                thrds = 2
            elif i < 45:
                thrds = 3
            elif i < 65:
                thrds = 2
            else:
                thrds = 2

            sizes, took = self.async_request(url, thrds)
            #sizes, took=self.async_request(url, (i<1 and 2 or (i<6 and 4 or (i<10 and 6 or 8))) )
            if sizes == 0:
                continue

            size = self.speed_conversion(sizes)
            speed = size / took
            self.log.debug('Download size: %0.2f MiB; Downloaded in %0.2f s\n' % (size, took))
            self.log.debug('\033[91mDownload speed: %0.2f %s/s\033[0m\n' % (speed, self.units))

            if self.down_speed < speed:
                self.down_speed = speed

            if took > 5:
                break

        #self.log.debug('Download size: %0.2f MiB; Downloaded in %0.2f s\n' % (self.speed_conversion(sizes), took))
        #self.log.debug('Download speed: %0.2f %s/s\n' % (self.speed_conversion(sizes)/took, self.units))

    def test_speed(self):

        if self.server == 'list-servers':
            self.config = self.load_config()
            self.server_list = self.load_servers()
            self.list_servers(self.num_top)
            return

        if self.server == '':
            self.config = self.load_config()
            self.server_list = self.load_servers()
            self.find_best_server()

        self.test_download()
        self.test_upload()

        self.log.result('%0.2f,%0.2f,"%s","%s"\n' % (self.down_speed, self.up_speed, self.units, self.servers))

    def list_servers(self, num=0):

        all_sorted = self.closest([self.config['lat'], self.config['lon']], self.server_list, num)

        for i in xrange(0, len(all_sorted)):
            self.log.result('%s. %s (%s, %s, %s) [%0.2f km]\n' %
                            (i + 1, all_sorted[i]['url'], all_sorted[i]['sponsor'], all_sorted[i]['name'],
                             all_sorted[i]['country'], all_sorted[i]['distance']))


def main(args):

    if args.use_proxy:
        if args.use_proxy == 5:
            set_proxy(typ=socks.PROXY_TYPE_SOCKS5, host=args.proxy_host, port=args.proxy_port)
        else:
            set_proxy(typ=socks.PROXY_TYPE_SOCKS4, host=args.proxy_host, port=args.proxy_port)

    if args.listservers:
        args.store = True

    log = Log(suppress=args.suppress, store=args.store)
    if not args.listservers and args.server == '' and not args.store:
        log.debug('Getting ready. Use parameter -h or --help to see available features.\n')
    else:
        log.debug('Getting ready\n')
    try:
        TeSpeed(args.listservers and 'list-servers' or args.server, args.listservers, args.servercount, args.unit,
                chunk_size=args.chunksize, log=log)
    except (KeyboardInterrupt, SystemExit):
        log.debug('\nTesting stopped.\n')
        #raise

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='TeSpeed, CLI SpeedTest.net')

    parser.add_argument('server', nargs='?', type=str, default='', help='Use the specified server for testing (skip checking for location and closest server).')
    parser.add_argument('-ls', '--list-servers', dest='listservers', nargs='?', default=0, const=10, help='List the servers sorted by distance, nearest first. Optionally specify number of servers to show.')
    parser.add_argument('-w', '--csv', dest='store', action='store_true', help='Print CSV formated output to STDOUT.')
    parser.add_argument('-s', '--suppress', dest='suppress', action='store_true', help='Suppress debugging (STDERR) output.')
    parser.add_argument('-mib', '--mebibit', dest='unit', action='store_true', help='Show results in mebibits.')
    parser.add_argument('-n', '--server-count', dest='servercount', nargs='?', default=1, const=1, help='Specify how many different servers should be used in paralel. (Default: 1) (Increase it for >100Mbit testing.)')

    parser.add_argument('-p', '--proxy', dest='use_proxy', type=int, nargs='?', const=4, help='Specify 4 or 5 to use SOCKS4 or SOCKS5 proxy.')
    parser.add_argument('-ph', '--proxy-host', dest='proxy_host', type=str, nargs='?', default='127.0.0.1', help='Specify socks proxy host. (Default: 127.0.0.1)')
    parser.add_argument('-pp', '--proxy-port', dest='proxy_port', type=int, nargs='?', default=9050, help='Specify socks proxy port. (Default: 9050)')

    parser.add_argument('-cs', '--chunk-size', dest='chunksize', nargs='?', type=int, default=10240, help='Specify chunk size after wich tespeed calculates speed. Increase this number 4 or 5 times if you use weak hardware like RaspberryPi. (Default: 10240)')

    #parser.add_argument('-i', '--interface', dest='interface', nargs='?', help='If specified, measures speed from data for the whole network interface.')

    main(parser.parse_args())
