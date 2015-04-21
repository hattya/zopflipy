#
# test_zopfli
#
#   Copyright (c) 2015 Akinori Hattori <hattya@gmail.com>
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

import sys
import unittest
import zlib

import zopfli


class ZopfliTestCase(unittest.TestCase):

    def test_format(self):
        self.assertEqual(zopfli.ZOPFLI_FORMAT_GZIP, 0)
        self.assertEqual(zopfli.ZOPFLI_FORMAT_ZLIB, 1)
        self.assertEqual(zopfli.ZOPFLI_FORMAT_DEFLATE, 2)

    def test_gzip(self):
        c = zlib.compressobj(9, zlib.DEFLATED, zlib.MAX_WBITS + 16)
        d = zopfli.ZopfliDecompressor(zopfli.ZOPFLI_FORMAT_GZIP)
        self._test_zopfli(c, d)

    def test_zlib(self):
        c = zlib.compressobj(9, zlib.DEFLATED, zlib.MAX_WBITS)
        d = zopfli.ZopfliDecompressor(zopfli.ZOPFLI_FORMAT_ZLIB)
        self._test_zopfli(c, d)

    def test_deflate(self):
        c = zlib.compressobj(9, zlib.DEFLATED, -zlib.MAX_WBITS)
        d = zopfli.ZopfliDecompressor(zopfli.ZOPFLI_FORMAT_DEFLATE)
        self._test_zopfli(c, d)

    def _test_zopfli(self, c, d):
        b = b'Hello, world!'
        z = c.compress(b) + c.flush()
        self.assertEqual(d.decompress(z) + d.flush(), b)
        self.assertEqual(d.unused_data, b'')
        self.assertEqual(d.unconsumed_tail, b'')
        if sys.version_info >= (3, 3):
            self.assertTrue(d.eof)

    def test_unknown(self):
        with self.assertRaises(ValueError):
            zopfli.ZopfliDecompressor(-1)
