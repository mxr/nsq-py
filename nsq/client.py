'''A client for talking to NSQ'''

try:
    import simplejson as json
except ImportError:
    import json

from . import logger
from . import connection

import requests
import select
import time


class Client(object):
    '''A client for talking to NSQ over a connection'''
    def __init__(self, topic, lookupd):
        self._connections = {}
        self._lookupd = lookupd
        self._topic = topic
        self._last_discovery = 0

    def discover(self):
        '''Run the discovery mechanism'''
        res = requests.get(
            'http://%s/lookup?topic=%s' % (self._lookupd, self._topic))
        data = json.loads(res.content)['data']

        # Find all the current producers
        producers = list(
            (producer['broadcast_address'], producer['tcp_port'])
            for producer in data['producers'])

        # Connect to all the new producers
        new = set(producers) - set(self._connections.keys())
        for host, port in new:
            logger.info('Discovered %s:%s' % (host, port))
            self._connections[(host, port)] = connection.Connection(host, port)

        # Disconnect from all the deceased connections
        old = set(self._connections.keys()) - set(producers)
        for key in old:
            logger.info('Closing disappeared %s:%s' % key)
            self._connections.delete(key).close()

        # Reset the time since the last discovery
        self._last_discovery = time.time()

        # And return all the new connections
        return [self._connections[key] for key in new]

    def remove(self, connection):
        '''Remove a connection'''
        key = (connection.host, connection.port)
        found = self._connections.delete(key, None)
        try:
            found.close()
        except Exception as exc:
            logger.warn('Failed to close %s: %s' % (connection, exc))
        return found

    def read(self):
        '''Read from any of the connections that need it'''
        connections = self._connections.values()

        # Not all connections need to be written to, so we'll only concern
        # ourselves with those that require writes
        writes = [c for c in connections if c.pending()]
        readable, writable, exceptions = select.select(
            connections, writes, connections)

        responses = []
        # For each readable socket, we'll try to read some responses
        for conn in readable:
            responses.extend(conn.read())

        # For each writable socket, flush some data out
        for conn in writable:
            conn.flush()

        # For each connection with an exception, try to close it and remove it
        # from our connections
        for conn in exceptions:
            self.remove(conn)

        return responses