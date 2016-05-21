#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2014 Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

import os
import requests
import time

from .. import base
from girder import config
from girder.api import access
from girder.api.rest import Resource, iterBody

_chunks = []
os.environ['GIRDER_PORT'] = os.environ.get('GIRDER_TEST_PORT', '20200')
config.loadConfig()  # Must reload config to pickup correct port


def setUpModule():
    server = base.startServer(mock=False)
    server.root.api.v1.stream_test = StreamTestResource()


def tearDownModule():
    base.stopServer()


class StreamTestResource(Resource):
    def __init__(self):
        super(StreamTestResource, self).__init__()
        self.resourceName = 'stream_test'
        self.route('POST', ('input_stream',), self.inputStream)

    @access.public
    def inputStream(self, params):
        # Read body 8 bytes at a time so we can test chunking a small body
        for chunk in iterBody(8):
            _chunks.append(chunk)
        return _chunks


class StreamTestCase(base.TestCase):
    def setUp(self):
        base.TestCase.setUp(self)

        global _chunks
        _chunks = []

        self.apiUrl = 'http://localhost:%s/api/v1' % os.environ['GIRDER_PORT']

    def testChunkedTransferEncoding(self):
        """
        This test verifies that chunked transfer encoding bodies are received
        as the chunks are sent, rather than waiting for the final chunk to
        be sent.
        """
        def genChunks():
            """
            Passing a generator to requests.request as the data argument causes
            a chunked transfer encoding, where each yielded buffer is sent as
            a separate chunk.
            """
            for i in range(1, 4):
                buf = 'chunk%d' % i
                yield buf
                start = time.time()
                while len(_chunks) != i:
                    time.sleep(.1)
                    # Wait for server thread to read the chunk
                    if time.time() - start > 5:
                        raise Exception('Timeout waiting for chunk')

                self.assertEqual(len(_chunks), i)
                self.assertEqual(_chunks[-1], buf)

        resp = requests.post(self.apiUrl + '/stream_test/input_stream',
                             data=genChunks())
        resp.raise_for_status()
        self.assertEqual(resp.json(), ['chunk1', 'chunk2', 'chunk3'])

    def testKnownLengthBodyReady(self):
        """
        This exercises the behavior of iterBody in the case of requests with
        Content-Length passed.
        """
        resp = requests.post(self.apiUrl + '/stream_test/input_stream',
                             data='a normal request body')
        resp.raise_for_status()
        self.assertEqual(resp.json(), ['a normal', ' request', ' body'])
