============================
Tespeed (terminal speedtest)
============================

:copyright: Copyright 2012 Janis Jansons (janis.jansons@janhouse.lv)

This is a new TeSpeed version written in Python (for the purpose of learning it).

The old one was written in PHP years ago and wasn't really made for general public (was fine tuned and possibly working
only on my server).

Even though the old version didn't work on most boxes, it somehow got almost 17'000 downloads on Sourceforge.
I guess some people could use this (those who hate Flash, JavaScript, has GUI-less servers, etc.) so I'll try to make
this one a bit better working in time.

Let's call this version 0.1.0-alpha

Of course, this script could not work like this without the best speed testing site out there - http://www.speedtest.net/

Support them in any way you can (going to their website and clicking on ads could probably make them a bit happier). :)

------------
Installation
------------

When doing the checkout, remember to pull submodules.

If you have a decent git version (1.6.5 and up), get everything by doing::

    git clone --recursive git://github.com/Janhouse/tespeed.git

Otherwise do::

    git clone git://github.com/Janhouse/tespeed.git
    cd tespeed
    git submodule init
    git submodule update

Then install it thanks to the project's setup script::

    sudo ./setup.py install

-----
Usage
-----

::

    usage: tespeed [-h] [-ls [LIST_SERVERS]] [-w] [-s] [-mib] [-n [SERVER_COUNT]]
                   [-p [USE_PROXY]] [-ph [PROXY_HOST]] [-pp [PROXY_PORT]]
                   [-cs [CHUNK_SIZE]]
                   [server]

    TeSpeed, CLI SpeedTest.net

    positional arguments:
      server                Use the specified server for testing (skip checking
                            for location and closest server).

    optional arguments:
      -h, --help            show this help message and exit
      -ls [LIST_SERVERS], --list-servers [LIST_SERVERS]
                            List the servers sorted by distance, nearest first.
                            Optionally specify number of servers to show.
      -w, --csv             Print CSV formated output to STDOUT.
      -s, --suppress        Suppress debugging (STDERR) output.
      -mib, --mebibit       Show results in mebibits.
      -n [SERVER_COUNT], --server-count [SERVER_COUNT]
                            Specify how many different servers should be used in
                            parallel. (Default: 1) (Increase it for >100Mbit
                            testing.)
      -p [USE_PROXY], --proxy [USE_PROXY]
                            Specify 4 or 5 to use SOCKS4 or SOCKS5 proxy.
      -ph [PROXY_HOST], --proxy-host [PROXY_HOST]
                            Specify socks proxy host. (Default: 127.0.0.1)
      -pp [PROXY_PORT], --proxy-port [PROXY_PORT]
                            Specify socks proxy port. (Default: 9050)
      -cs [CHUNK_SIZE], --chunk-size [CHUNK_SIZE]
                            Specify chunk size after which tespeed calculates
                            speed. Increase this number 4 or 5 times if you use
                            weak hardware like RaspberryPi. (Default: 10240)

What the script does:

* Loads configuration from speedtest.net (http://speedtest.net/speedtest-config.php).
* Gets server list (http://speedtest.net/speedtest-servers.php).
* Picks 5 closest servers using the coordinates provides by speedtest.net config and serverlist.
* Checks latency for those servers and picks one with the lowest.
* Does download speed test and returns results.
* Does upload speed test and returns results.
* Optionally can return CSV formated results.
* Can measure through SOCKS proxy.

TODO (ideas):

* Add more error checking.
* Make it less messy.
* Send found results to speedtest.net API (needs some hash?) and get the link to the generated image.
* Store the measurement data and draw graphs.
* Measure the speed for the whole network interface (similar like it was in the old version of Tespeed).
* Start upload timer only after 1st byte is read.
* Figure out the amount of data that was transfered only when all threads were actively sending/receiving data at the
  same time. (Should provide more precise test results.)


