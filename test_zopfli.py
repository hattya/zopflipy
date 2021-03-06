#
# test_zopfli
#
#   Copyright (c) 2015-2021 Akinori Hattori <hattya@gmail.com>
#
#   SPDX-License-Identifier: Apache-2.0
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
        for i in range(2):
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
        self.assertEqual(c.flush(), b'\x03\x00')
        with self.assertRaises(ValueError):
            c.compress(b'')
        with self.assertRaises(ValueError):
            c.flush()

    def test_deflater(self):
        for i in range(2):
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

    def test_verbose(self):
        png = zopfli.ZopfliPNG()
        self.assertFalse(png.verbose)

        png.verbose = True
        self.assertTrue(png.verbose)

        png = zopfli.ZopfliPNG(verbose=True)
        self.assertTrue(png.verbose)

        with self.assertRaises(TypeError):
            del zopfli.ZopfliPNG().verbose

    def test_lossy_transparent(self):
        png = zopfli.ZopfliPNG()
        self.assertFalse(png.lossy_transparent)

        png.lossy_transparent = True
        self.assertTrue(png.lossy_transparent)

        png = zopfli.ZopfliPNG(lossy_transparent=True)
        self.assertTrue(png.lossy_transparent)

        with self.assertRaises(TypeError):
            del zopfli.ZopfliPNG().lossy_transparent

    def test_lossy_8bit(self):
        png = zopfli.ZopfliPNG()
        self.assertFalse(png.lossy_8bit)

        png.lossy_8bit = True
        self.assertTrue(png.lossy_8bit)

        png = zopfli.ZopfliPNG(lossy_8bit=True)
        self.assertTrue(png.lossy_8bit)

        with self.assertRaises(TypeError):
            del zopfli.ZopfliPNG().lossy_8bit

    def test_filter_strategies(self):
        png = zopfli.ZopfliPNG()
        self.assertEqual(png.filter_strategies, '')
        self.assertTrue(png.auto_filter_strategy)

        png.filter_strategies = '01234mepb'
        self.assertEqual(png.filter_strategies, '01234mepb')
        self.assertFalse(png.auto_filter_strategy)

        with self.assertRaises(ValueError):
            png.filter_strategies = '.'
        self.assertEqual(png.filter_strategies, '')
        self.assertTrue(png.auto_filter_strategy)

        png = zopfli.ZopfliPNG(filter_strategies='01234mepb')
        self.assertEqual(png.filter_strategies, '01234mepb')
        self.assertFalse(png.auto_filter_strategy)

        png.auto_filter_strategy = True
        self.assertEqual(png.filter_strategies, '')
        self.assertTrue(png.auto_filter_strategy)

        with self.assertRaises(TypeError):
            zopfli.ZopfliPNG(filter_strategies=None)
        with self.assertRaises(ValueError):
            zopfli.ZopfliPNG(filter_strategies=u'\u00B7')
        with self.assertRaises(ValueError):
            zopfli.ZopfliPNG(filter_strategies='z')
        with self.assertRaises(TypeError):
            del zopfli.ZopfliPNG().filter_strategies

        with self.assertRaises(TypeError):
            del zopfli.ZopfliPNG().auto_filter_strategy

    def test_keep_color_type(self):
        png = zopfli.ZopfliPNG()
        self.assertFalse(png.keep_color_type)

        png.keep_color_type = True
        self.assertTrue(png.keep_color_type)

        png = zopfli.ZopfliPNG(keep_color_type=True)
        self.assertTrue(png.keep_color_type)

        with self.assertRaises(TypeError):
            del zopfli.ZopfliPNG().keep_color_type

    def test_keep_chunks(self):
        png = zopfli.ZopfliPNG()
        self.assertEqual(png.keep_chunks, ())

        png.keep_chunks = ['tEXt', 'zTXt', 'iTXt']
        self.assertEqual(png.keep_chunks, ('tEXt', 'zTXt', 'iTXt'))

        png = zopfli.ZopfliPNG(keep_chunks=['tEXt', 'zTXt', 'iTXt'])
        self.assertEqual(png.keep_chunks, ('tEXt', 'zTXt', 'iTXt'))

        with self.assertRaises(TypeError):
            zopfli.ZopfliPNG(keep_chunks=None)
        with self.assertRaises(TypeError):
            zopfli.ZopfliPNG(keep_chunks=[None])
        with self.assertRaises(ValueError):
            zopfli.ZopfliPNG(keep_chunks=[u'\u00B7'])
        with self.assertRaises(TypeError):
            del zopfli.ZopfliPNG().keep_chunks

    def test_use_zopfli(self):
        png = zopfli.ZopfliPNG()
        self.assertTrue(png.use_zopfli)

        png.use_zopfli = False
        self.assertFalse(png.use_zopfli)

        png = zopfli.ZopfliPNG(use_zopfli=False)
        self.assertFalse(png.use_zopfli)

        with self.assertRaises(TypeError):
            del zopfli.ZopfliPNG().use_zopfli

    def test_iterations(self):
        png = zopfli.ZopfliPNG()
        self.assertEqual(png.iterations, 15)

        png.iterations *= 2
        self.assertEqual(png.iterations, 30)

        png = zopfli.ZopfliPNG(iterations=30)
        self.assertEqual(png.iterations, 30)

        with self.assertRaises(TypeError):
            zopfli.ZopfliPNG(iterations=None)
        with self.assertRaises(TypeError):
            zopfli.ZopfliPNG().iterations = None
        with self.assertRaises(TypeError):
            del zopfli.ZopfliPNG().iterations

    def test_iterations_large(self):
        png = zopfli.ZopfliPNG()
        self.assertEqual(png.iterations_large, 5)

        png.iterations_large *= 2
        self.assertEqual(png.iterations_large, 10)

        png = zopfli.ZopfliPNG(iterations_large=10)
        self.assertEqual(png.iterations_large, 10)

        with self.assertRaises(TypeError):
            zopfli.ZopfliPNG(iterations_large=None)
        with self.assertRaises(TypeError):
            zopfli.ZopfliPNG().iterations_large = None
        with self.assertRaises(TypeError):
            del zopfli.ZopfliPNG().iterations_large

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
            zf.write(u(os.path.join(self.path, folder)), u(folder))
            write(zf, u(os.path.join(folder, '{spam}.txt')))
            write(zf, u(os.path.join(folder, '{eggs}.txt')), deflate=False)
            writestr(zf, u(os.path.join(folder, '{ham}.txt')))
            writestr(zf, u(os.path.join(folder, '{toast}.txt')), deflate=False)
            write(zf, u(os.path.join(folder, '{beans}.txt')))
            writestr(zf, u(os.path.join(folder, '{bacon}.txt')), zinfo=True)
            writestr(zf, u(os.path.join(folder, '{sausage}.txt')), deflate=False, zinfo=True)
            write(zf, u(os.path.join(folder, '{tomato}.txt')), deflate=False)
        with zopfli.ZipFile(path, 'r', encoding=encoding) as zf:
            for n, compress_type in (('{New Folder}/', zipfile.ZIP_STORED),
                                     ('{New Folder}/{spam}.txt', zipfile.ZIP_DEFLATED),
                                     ('{New Folder}/{eggs}.txt', zipfile.ZIP_STORED),
                                     ('{New Folder}/{ham}.txt', zipfile.ZIP_DEFLATED),
                                     ('{New Folder}/{toast}.txt', zipfile.ZIP_STORED),
                                     ('{New Folder}/{beans}.txt', zipfile.ZIP_DEFLATED),
                                     ('{New Folder}/{bacon}.txt', zipfile.ZIP_DEFLATED),
                                     ('{New Folder}/{sausage}.txt', zipfile.ZIP_STORED),
                                     ('{New Folder}/{tomato}.txt', zipfile.ZIP_STORED)):
                name = u(n)
                raw_name = name.encode(encoding)
                if sys.version_info >= (3, 0):
                    raw_name = raw_name.decode('utf-8' if encoding == 'utf-8' else 'cp437')
                zi = zf.getinfo(name)
                self.assertEqual(zi.orig_filename, raw_name)
                self.assertEqual(zi.filename, name)
                self.assertEqual(zi.compress_type, compress_type)
                self.assertEqual(zi.flag_bits, 0x800 if encoding == 'utf-8' else 0)
                self.assertEqual(zf.read(zi), os.path.splitext(os.path.basename(name))[0].encode(encoding))

    def _u(self, names):
        if sys.version_info < (3, 0):
            def u(s):
                return s.decode('utf-8').format(**names)
        else:
            def u(s):
                return s.format(**names)
        return u
