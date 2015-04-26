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

import zopfli


class ZopfliTestCase(unittest.TestCase):

    def test_format(self):
        self.assertEqual(zopfli.ZOPFLI_FORMAT_GZIP, 0)
        self.assertEqual(zopfli.ZOPFLI_FORMAT_ZLIB, 1)
        self.assertEqual(zopfli.ZOPFLI_FORMAT_DEFLATE, 2)

    def test_gzip(self):
        self._test_zopfli(zopfli.ZOPFLI_FORMAT_GZIP)

    def test_zlib(self):
        self._test_zopfli(zopfli.ZOPFLI_FORMAT_ZLIB)

    def test_deflate(self):
        self._test_zopfli(zopfli.ZOPFLI_FORMAT_DEFLATE)

    def _test_zopfli(self, fmt):
        for i in range(-1, 5):
            c = zopfli.ZopfliCompressor(fmt, block_splitting=i)
            b = b'Hello, world!'
            z = c.compress(b) + c.flush()
            self._test_decompress(fmt, z, b)

    def test_unknown(self):
        with self.assertRaises(ValueError):
            zopfli.ZopfliCompressor(-1)

        with self.assertRaises(ValueError):
            zopfli.ZopfliDecompressor(-1)

    def test_compressor(self):
        with self.assertRaises(TypeError):
            zopfli.ZopfliCompressor(None)

        c = zopfli.ZopfliCompressor()
        with self.assertRaises(TypeError):
            c.compress(None)

        c = zopfli.ZopfliCompressor()
        self.assertEqual(c.flush(), b'')
        with self.assertRaises(ValueError):
            c.compress(b'')
        with self.assertRaises(ValueError):
            c.flush()

    def test_deflater(self):
        for i in range(3):
            c = zopfli.ZopfliDeflater(block_splitting=i)
            b = b'Hello, world!'
            z = c.compress(b) + c.flush()
            self._test_decompress(zopfli.ZOPFLI_FORMAT_DEFLATE, z, b)

            c = zopfli.ZopfliDeflater(block_splitting=i)
            b = b'Hello, world!'
            z = c.compress(b) + c.compress(b) + c.compress(b) + c.flush()
            self._test_decompress(zopfli.ZOPFLI_FORMAT_DEFLATE, z, b * 3)

        with self.assertRaises(TypeError):
            zopfli.ZopfliDeflater(iterations=None)

        with self.assertRaises(TypeError):
            zopfli.ZopfliDeflater(block_splitting=None)

        with self.assertRaises(TypeError):
            zopfli.ZopfliDeflater(block_splitting_max=None)

        c = zopfli.ZopfliDeflater()
        c.compress(None)
        with self.assertRaises(TypeError):
            c.compress(None)

        c = zopfli.ZopfliDeflater()
        self.assertEqual(c.flush(), b'')
        with self.assertRaises(ValueError):
            c.compress(b'')
        with self.assertRaises(ValueError):
            c.flush()

    def _test_decompress(self, fmt, z, b):
        d = zopfli.ZopfliDecompressor(fmt)
        self.assertEqual(d.decompress(z) + d.flush(), b)
        self.assertEqual(d.unused_data, b'')
        self.assertEqual(d.unconsumed_tail, b'')
        if sys.version_info >= (3, 3):
            self.assertTrue(d.eof)


# 8-bit PNG (64x64 pixels)
black_png = (
    b'\x89\x50\x4e\x47\x0d\x0a\x1a\x0a\x00\x00\x00\x0d\x49\x48\x44\x52\x00\x00'
    b'\x00\x40\x00\x00\x00\x40\x08\x00\x00\x00\x00\x8f\x02\x2e\x02\x00\x00\x00'
    b'\x1b\x49\x44\x41\x54\x78\x9c\xed\xc1\x81\x00\x00\x00\x00\xc3\xa0\xf9\x53'
    b'\xdf\xe0\x04\x55\x01\x00\x00\x00\x7c\x03\x10\x40\x00\x01\x46\x38\x0d\x1d'
    b'\x00\x00\x00\x00\x49\x45\x4e\x44\xae\x42\x60\x82'
)


class ZopfliPNGTestCase(unittest.TestCase):

    def test_png(self):
        png = zopfli.ZopfliPNG()
        self.assertFalse(png.verbose)
        self.assertFalse(png.lossy_transparent)
        self.assertFalse(png.lossy_8bit)
        self.assertEqual(png.filter_strategies, '')
        self.assertTrue(png.auto_filter_strategy)
        self.assertEqual(png.keep_chunks, ())
        self.assertTrue(png.use_zopfli)
        self.assertEqual(png.iterations, 15)
        self.assertEqual(png.iterations_large, 5)
        self.assertEqual(png.block_split_strategy, 1)

        png = zopfli.ZopfliPNG(verbose=True,
                               lossy_transparent=True,
                               lossy_8bit=True,
                               filter_strategies='01234mepb',
                               keep_chunks=['tEXt', 'zTXt', 'iTXt'],
                               use_zopfli=False,
                               iterations=30,
                               iterations_large=10,
                               block_split_strategy=3)
        self.assertTrue(png.verbose)
        self.assertTrue(png.lossy_transparent)
        self.assertTrue(png.lossy_8bit)
        self.assertEqual(png.filter_strategies, '01234mepb')
        self.assertFalse(png.auto_filter_strategy)
        self.assertEqual(png.keep_chunks, ('tEXt', 'zTXt', 'iTXt'))
        self.assertFalse(png.use_zopfli)
        self.assertEqual(png.iterations, 30)
        self.assertEqual(png.iterations_large, 10)
        self.assertEqual(png.block_split_strategy, 3)

        with self.assertRaises(TypeError):
            zopfli.ZopfliPNG(filter_strategies=None)
        with self.assertRaises(ValueError):
            zopfli.ZopfliPNG(filter_strategies=u'\u00B7')
        with self.assertRaises(ValueError):
            zopfli.ZopfliPNG(filter_strategies='z')

        with self.assertRaises(TypeError):
            zopfli.ZopfliPNG(keep_chunks=None)
        with self.assertRaises(TypeError):
            zopfli.ZopfliPNG(keep_chunks=[None])
        with self.assertRaises(ValueError):
            zopfli.ZopfliPNG(keep_chunks=[u'\u00B7'])

        with self.assertRaises(TypeError):
            zopfli.ZopfliPNG(iterations=None)

        with self.assertRaises(TypeError):
            zopfli.ZopfliPNG(iterations_large=None)

        png = zopfli.ZopfliPNG(block_split_strategy=-1)
        self.assertEqual(png.block_split_strategy, 1)
        png = zopfli.ZopfliPNG(block_split_strategy=4)
        self.assertEqual(png.block_split_strategy, 1)
        with self.assertRaises(TypeError):
            zopfli.ZopfliPNG(block_split_strategy=None)

    def test_optimize(self):
        png = zopfli.ZopfliPNG()
        self.assertGreater(len(black_png), len(png.optimize(black_png)))

        with self.assertRaises(TypeError):
            png.optimize(None)
        with self.assertRaises(ValueError):
            png.optimize(b'')
