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

import io
import os
import shutil
import sys
import tempfile
import time
import unittest
import zipfile

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


class ZipFileTest(unittest.TestCase):

    def setUp(self):
        super(ZipFileTest, self).setUp()
        self.path = tempfile.mkdtemp(prefix='zopfli-')
        if sys.version_info < (3, 0):
            self.path = self.path.decode(sys.getfilesystemencoding(), 'surrogateescape')

    def tearDown(self):
        super(ZipFileTest, self).tearDown()
        shutil.rmtree(self.path)

    def test_ascii(self):
        names = {
            'New Folder': 'New Folder',
            'spam': 'spam',
            'eggs': 'eggs',
            'ham': 'ham',
            'toast': 'toast',
            'beans': 'beans',
            'bacon': 'bacon',
            'sausage': 'sausage',
            'tomato': 'tomato',
        }
        self._test_zip('ascii', names)

    def test_cp932(self):
        encoding = 'cp932'
        names = {
            'New Folder': u'\u65b0\u3057\u3044\u30d5\u30a9\u30eb\u30c0\u30fc',
            'spam': u'\u30b9\u30d1\u30e0',
            'eggs': u'\u30a8\u30c3\u30b0\u30b9',
            'ham': u'\u30cf\u30e0',
            'toast': u'\u30c8\u30fc\u30b9\u30c8',
            'beans': u'\u30d3\u30fc\u30f3\u30ba',
            'bacon': u'\u30d9\u30fc\u30b3\u30f3',
            'sausage': u'\u30bd\u30fc\u30bb\u30fc\u30b8',
            'tomato': u'\u30c8\u30de\u30c8',
        }
        self._test_encode(encoding, names)
        self._test_zip(encoding, names)

    def test_utf_8(self):
        encoding = 'utf-8'
        names = {
            'New Folder': u'\u65b0\u3057\u3044\u30d5\u30a9\u30eb\u30c0\u30fc',
            'spam': u'\u30b9\u30d1\u30e0',
            'eggs': u'\u30a8\u30c3\u30b0\u30b9',
            'ham': u'\u30cf\u30e0',
            'toast': u'\u30c8\u30fc\u30b9\u30c8',
            'beans': u'\u30d3\u30fc\u30f3\u30ba',
            'bacon': u'\u30d9\u30fc\u30b3\u30f3',
            'sausage': u'\u30bd\u30fc\u30bb\u30fc\u30b8',
            'tomato': u'\u30c8\u30de\u30c8',
        }
        self._test_encode(encoding, names)
        self._test_zip(encoding, names)

    def _test_encode(self, encoding, names):
        u = self._u(names)

        def writestr(zf, name, raw_name=None):
            zi = zopfli.ZipInfo(name, time.localtime(time.time())[:6])
            if raw_name:
                zi.filename = raw_name
            data = os.path.splitext(os.path.basename(name))[0].encode(encoding)
            zf.writestr(zi, data)

        path = os.path.join(self.path, 'cp437.zip')
        with zopfli.ZipFile(path, 'w', encoding='cp437') as zf:
            writestr(zf, u('{spam}.txt'))
            writestr(zf, u('{eggs}.txt'), u('{eggs}.txt').encode(encoding))
        with zopfli.ZipFile(path, 'r', encoding=encoding) as zf:
            for n, flag_bits in (('{spam}.txt', 0x800),
                                 ('{eggs}.txt', 0)):
                name = u(n)
                raw_name = name.encode('utf-8' if flag_bits else encoding)
                if sys.version_info >= (3, 0):
                    raw_name = raw_name.decode('utf-8' if flag_bits else 'cp437')
                zi = zf.getinfo(name)
                self.assertEqual(zi.orig_filename, raw_name)
                self.assertEqual(zi.filename, name)
                self.assertEqual(zi.flag_bits, flag_bits)
                self.assertEqual(zf.read(zi), u(os.path.splitext(n)[0]).encode(encoding))

    def _test_zip(self, encoding, names):
        u = self._u(names)

        def write(zf, name, deflate=True):
            p = os.path.join(self.path, name)
            with io.open(p, 'w', encoding=encoding) as fp:
                fp.write(os.path.splitext(os.path.basename(name))[0])
            zf.write(p, name, zipfile.ZIP_DEFLATED if deflate else zipfile.ZIP_STORED)

        def writestr(zf, name, deflate=True, zinfo=False):
            data = os.path.splitext(os.path.basename(name))[0].encode(encoding)
            compress_type = zipfile.ZIP_DEFLATED if deflate else zipfile.ZIP_STORED
            if zinfo:
                name = zopfli.ZipInfo(name, time.localtime(time.time())[:6])
                name.compress_type = compress_type
            zf.writestr(name, data, compress_type)

        path = os.path.join(self.path, '{}.zip'.format(encoding))
        folder = '{New Folder}'
        os.mkdir(u(os.path.join(self.path, folder)))
        with zopfli.ZipFile(path, 'w', encoding=encoding) as zf:
            zf.write(u(os.path.join(self.path, folder)))
            write(zf, u(os.path.join(folder, '{spam}.txt')))
            write(zf, u(os.path.join(folder, '{eggs}.txt')), deflate=False)
            writestr(zf, u(os.path.join(folder, '{ham}.txt')))
            writestr(zf, u(os.path.join(folder, '{toast}.txt')), deflate=False)
            write(zf, u(os.path.join(folder, '{beans}.txt')))
            writestr(zf, u(os.path.join(folder, '{bacon}.txt')), zinfo=True)
            writestr(zf, u(os.path.join(folder, '{sausage}.txt')), deflate=False, zinfo=True)
            write(zf, u(os.path.join(folder, '{tomato}.txt')), deflate=False)
        with zopfli.ZipFile(path, 'r', encoding=encoding) as zf:
            for n, compress_type in (('{spam}.txt', zipfile.ZIP_DEFLATED),
                                     ('{eggs}.txt', zipfile.ZIP_STORED),
                                     ('{ham}.txt', zipfile.ZIP_DEFLATED),
                                     ('{toast}.txt', zipfile.ZIP_STORED),
                                     ('{beans}.txt', zipfile.ZIP_DEFLATED),
                                     ('{bacon}.txt', zipfile.ZIP_DEFLATED),
                                     ('{sausage}.txt', zipfile.ZIP_STORED),
                                     ('{tomato}.txt', zipfile.ZIP_STORED)):
                name = u(os.path.join(folder, n)).replace(os.path.sep, '/')
                raw_name = name.encode(encoding)
                if sys.version_info >= (3, 0):
                    raw_name = raw_name.decode('utf-8' if encoding == 'utf-8' else 'cp437')
                zi = zf.getinfo(name)
                self.assertEqual(zi.orig_filename, raw_name)
                self.assertEqual(zi.filename, name)
                self.assertEqual(zi.compress_type, compress_type)
                self.assertEqual(zi.flag_bits, 0x800 if encoding == 'utf-8' else 0)
                self.assertEqual(zf.read(zi), u(os.path.splitext(n)[0]).encode(encoding))

    def _u(self, names):
        if sys.version_info < (3, 0):
            def u(s):
                return s.decode('utf-8').format(**names)
        else:
            def u(s):
                return s.format(**names)
        return u
