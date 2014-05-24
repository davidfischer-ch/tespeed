# -*- coding: utf-8 -*-

# Copyright:
#   2012-2013 Janis Jansons (janis.jansons@janhouse.lv)
#   2014      David Fischer (david.fischer.ch@gmail.com)

from __future__ import absolute_import, division, print_function, unicode_literals

import urllib, urllib2, time
from lxml import etree
from multiprocessing import Process, Pipe, Manager

from .utils import CallbackStringIO, Log, closest, decompress_response, num_download_threads_for, num_upload_threads_for

__all__ = ('TeSpeed', )


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
        1024*256, 1024*256, 1024*512, 1024*512, 1024*1024, 1024*1024, 1024*1024*2, 1024*1024*2, 1024*1024*2, 1024*512,
        1024*256, 1024*256, 1024*256, 1024*256, 1024*256,  1024*256,  1024*256,    1024*256,    1024*256,    1024*256,

        1024*512, 1024*512, 1024*512, 1024*512, 1024*512, 1024*512, 1024*512, 1024*512, 1024*512, 1024*512,
        1024*512, 1024*512, 1024*512, 1024*512, 1024*512, 1024*512, 1024*512, 1024*512, 1024*512, 1024*512,

        1024*256, 1024*256, 1024*256, 1024*256, 1024*256, 1024*256, 1024*256, 1024*256, 1024*256, 1024*256,
        1024*512, 1024*512, 1024*512, 1024*512, 1024*512, 1024*512, 1024*512, 1024*512, 1024*512, 1024*512,

        1024*1024*2, 1024*1024*2, 1024*1024*2, 1024*1024*2, 1024*1024*2, 1024*1024*2, 1024*1024*2, 1024*1024*2,
        1024*1024*2, 1024*1024*2, 1024*1024*2, 1024*1024*2, 1024*1024*2, 1024*1024*2, 1024*1024*2, 1024*1024*2,
        1024*1024*2, 1024*1024*2, 1024*1024*2, 1024*1024*2
    ]

    HEADERS = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:11.0) Gecko/20100101 Firefox/11.0',
        'Accept-Language': 'en-us,en;q=0.5',
        'Connection': 'keep-alive',
        'Accept-Encoding': 'gzip, deflate',
        #'Referer' : 'http://c.speedtest.net/flash/speedtest.swf?v=301256',
    }

    def __init__(self, server=None, num_servers=3, num_top=0, unit=False, chunk_size=10240, log=None):
        # FIXME having server, num_servers, ... looks like a hack that should be the responsibility of the caller
        self.server = server
        self.servers = [server] if server else []
        self.num_servers = num_servers
        self.num_top = int(num_top)
        if unit:
            self.units = 'MiB'
            self.unit = 1
        else:
            self.units = 'Mbit'
            self.unit = 0
        self.chunk_size = chunk_size
        self.log = log

        if log.store:
            log.debug('Printing CSV formated results to STDOUT.\n')

        self.best_servers = 5
        self.latency_count = 10
        self.post_data = ''

    def convert_size(self, value):
        return value / 1024 ** 2 * (1 if self.unit == 1 else 1.048576 * 8)

    def get_request(self, uri):
        """Generate a GET request to be used with urlopen."""
        return urllib2.Request(uri, headers=self.HEADERS)

    def post_request(self, uri, stream):
        """Generate a POST request to be used with urlopen."""
        return urllib2.Request(uri, stream, headers=self.HEADERS)

    def chunk_report(self, bytes_so_far, chunk_size, total_size, num, num_threads, d, w):
        """Receive status update from download thread."""
        if w != 1:
            d[num] = bytes_so_far
            down = 0
            for i in xrange(num_threads):
                down += d.get(i, 0)
            if num == 0 or down >= total_size * num_threads:
                percent = round(down / (total_size * num_threads) * 100, 2)
                self.log.debug('Downloaded %d of %d bytes (%0.2f%%) in %d threads\r' %
                               (down, total_size * num_threads, percent, num_threads))

    def chunk_read(self, response, num, num_threads, d, w=0, chunk_size=False, report_hook=None):

        chunk_size = chunk_size or self.chunk_size

        if w == 1:
            return [0, 0, 0]

        total_size = int(response.info().getheader('Content-Length').strip())
        bytes_so_far = start_time = 0
        while True:
            chunk = 0
            if not start_time:
                chunk = response.read(1)
                start_time = time.time()
            else:
                chunk = response.read(chunk_size)
            if not chunk:
                break
            bytes_so_far += len(chunk)
            if report_hook:
                report_hook(bytes_so_far, chunk_size, total_size, num, num_threads, d, w)

        return [bytes_so_far, start_time, time.time()]

    def async_get(self, conn, uri, num, num_threads, d):
        request = self.get_request(uri)
        start_time = end_time = size = 0
        try:
            response = urllib2.urlopen(request, timeout=30)
            size, start_time, end_time = self.chunk_read(response, num, num_threads, d, report_hook=self.chunk_report)
        except:
            self.log.debug(Log.BLANK_LINE)
            self.log.debug('Failed downloading.\n')
            conn.send([0, 0, False])
            conn.close()
            return
        conn.send([size, start_time, end_time])
        conn.close()

    def async_post(self, conn, uri, num, num_threads, d):
        postlen = len(self.post_data)
        stream = CallbackStringIO(num, num_threads, d, self.post_data, log=self.log)
        request = self.post_request(uri, stream)
        start_time = end_time = 0
        try:
            response = urllib2.urlopen(request, timeout=30)
            size, start_time, end_time = self.chunk_read(response, num, num_threads, d, 1,
                                                         report_hook=self.chunk_report)
        except:
            self.log.debug(Log.BLANK_LINE)
            self.log.debug('Failed uploading.\n')
            conn.send([0, 0, False])
            conn.close()
            return
        conn.send([postlen, start_time, end_time])
        conn.close()

    def async_request(self, url, num, upload=0):
        connections = []
        d = Manager().dict()

        start_time = time.time()

        for i in xrange(num):
            full_url = self.servers[i % len(self.servers)] + url
            connection = {}
            connection['parent'], connection['child'] = Pipe()
            connection['connection'] = Process(target=self.async_post if upload == 1 else self.async_get,
                                               args=(connection['child'], full_url, i, num, d))
            connection['connection'].start()
            connections.append(connection)

        for c in xrange(num):
            connections[c]['size'], connections[c]['start'], connections[c]['end'] = connections[c]['parent'].recv()
            connections[c]['connection'].join()

        end_time = time.time()

        self.log.debug(Log.BLANK_LINE)

        sizes = 0
        for c in xrange(num):
            if connections[c]['end'] is not False:
                sizes += connections[c]['size']

                # Using more precise times for downloads
                if upload == 0:
                    if c == 0:
                        start_time = connections[c]['start']
                        end_time = connections[c]['end']
                    else:
                        if connections[c]['start'] < start_time:
                            start_time = connections[c]['start']
                        if connections[c]['end'] > end_time:
                            end_time = connections[c]['end']

        return [sizes, end_time - start_time]

    def load_config(self):
        """Load the configuration file."""
        self.log.debug('Loading speedtest configuration...\n')
        uri = 'http://speedtest.net/speedtest-config.php?x=' + str(time.time())
        request = self.get_request(uri)
        response = urllib2.urlopen(request)

        # Load etree from XML data
        client = etree.fromstring(decompress_response(response)).find('client')
        self.config = {
            'ip': client.attrib['ip'],
            'isp': client.attrib['isp'],
            'lat': float(client.attrib['lat']),
            'lon': float(client.attrib['lon'])
        }
        self.log.debug('IP: {ip}; Lat: {lat}; Lon: {lon}; ISP: {isp}\n'.format(**self.config))

    def find_best_server(self):
        self.log.debug('Looking for closest and best server...\n')
        best_servers = self.test_latency(closest([self.config['lat'], self.config['lon']], self.server_list,
                                         self.best_servers))
        self.servers.extend(server['url'] for server in best_servers)

    def load_servers(self):
        """Load server list."""
        self.log.debug('Loading server list...\n')
        uri = 'http://speedtest.net/speedtest-servers.php?x=' + str(time.time())
        request = self.get_request(uri)
        response = urllib2.urlopen(request)

        # Load etree from XML data
        servers_xml = etree.fromstring(decompress_response(response))
        self.server_list = [
            {
                'lat': float(server.attrib['lat']),
                'lon': float(server.attrib['lon']),
                'url': server.attrib['url'].rsplit('/', 1)[0] + '/',
                #'url2': server.attrib['url2'].rsplit('/', 1)[0] + '/',
                'name': server.attrib['name'],
                'country': server.attrib['country'],
                'sponsor': server.attrib['sponsor'],
                'id': server.attrib['id'],
            } for server in servers_xml.find('servers').findall('server')
        ]

    def list_servers(self, num=0):

        all_sorted = closest([self.config['lat'], self.config['lon']], self.server_list, num)

        for i in xrange(len(all_sorted)):
            self.log.result('%s. %s (%s, %s, %s) [%0.2f km]\n' %
                            (i + 1, all_sorted[i]['url'], all_sorted[i]['sponsor'], all_sorted[i]['name'],
                             all_sorted[i]['country'], all_sorted[i]['distance']))

    def test_latency(self, servers):
        """Find servers with lowest latency."""
        self.log.debug('Testing latency...\n')
        po = []
        for server in servers:
            latency = self.test_single_latency(server['url'] + 'latency.txt?x=' + str(time.time())) * 1000
            if not latency:
                continue
            self.log.debug('%0.0f ms latency for %s (%s, %s, %s) [%0.2f km]\n' %
                           (latency, server['url'], server['sponsor'], server['name'], server['country'],
                            server['distance']))
            server['latency'] = latency
            # Pick specified amount of servers with best latency for testing
            if int(len(po)) < int(self.num_servers):
                po.append(server)
            else:
                largest = -1
                for x in xrange(len(po)):
                    if largest < 0:
                        if latency < po[x]['latency']:
                            largest = x
                    elif po[largest]['latency'] < po[x]['latency']:
                        largest = x
                if largest >= 0:
                    po[largest] = server
        return po

    def test_single_latency(self, destination_address):
        """Check latency for single server. Does that by loading latency.txt (empty page)."""
        request = self.get_request(destination_address)
        average_time = total = 0
        for i in xrange(self.latency_count):
            start_time = time.time()
            try:
                urllib2.urlopen(request, timeout=5)
                average_time += time.time() - start_time
                total += 2  # Already "multiply" by 2 to return half of the round-trip (the latency) for free
            except urllib2.URLError:
                pass
        return average_time / total if total else None

    def test_download(self):
        """Test download speed."""
        max_speed = -1
        for i in xrange(len(self.DOWNLOAD_LIST)):
            url = 'random' + self.DOWNLOAD_LIST[i] + '.jpg?x=' + str(time.time()) + '&y=3'

            sizes, took = self.async_request(url, num_download_threads_for(i))
            if sizes == 0:
                continue

            size = self.convert_size(sizes)  # FIXME rename sizes to something more meaningful
            speed = size / took
            max_speed = max(speed, max_speed)
            self.log.debug('Download size: %0.2f MiB; Downloaded in %0.2f s\n' % (size, took))
            self.log.debug('\033[91mDownload speed: %0.2f %s/s\033[0m\n' % (speed, self.units))

            if took > 5:
                break
        return max_speed

    def test_upload(self):
        """Test upload speed."""
        max_speed = -1
        data, url = '', 'upload.php?x=' + str(time.time())
        for i in xrange(len(self.UPLOAD_SIZES)):
            if len(data) == 0 or self.UPLOAD_SIZES[i] != self.UPLOAD_SIZES[i-1]:
                data = ''.join('1' for x in xrange(self.UPLOAD_SIZES[i]))
            self.post_data = urllib.urlencode({'upload6': data})

            sizes, took = self.async_request(url, num_upload_threads_for(i), 1)
            if sizes == 0:
                continue

            size = self.convert_size(sizes)  # FIXME rename sizes to something more meaningful
            speed = size / took
            max_speed = max(speed, max_speed)
            self.log.debug('Upload size: %0.2f MiB; Uploaded in %0.2f s\n' % (size, took))
            self.log.debug('\033[92mUpload speed: %0.2f %s/s\033[0m\n' % (speed, self.units))

            if took > 5:
                break
        return max_speed

    def run_tests(self):
        if self.server == 'list-servers':
            self.load_config()
            self.load_servers()
            self.list_servers(self.num_top)
        else:
            if not self.server:
                self.load_config()
                self.load_servers()
                self.find_best_server()
            download_speed = self.test_download()
            upload_speed = self.test_upload()
            self.log.result('%0.2f,%0.2f,"%s","%s"\n' % (download_speed, upload_speed, self.units, self.servers))
