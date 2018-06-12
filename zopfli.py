#
# zopfli
#
#   Copyright (c) 2015-2018 Akinori Hattori <hattya@gmail.com>
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

"""Zopfli Compression Algorithm"""

import codecs
import os
import struct
import sys
import zipfile
import zlib

from _zopfli import (ZOPFLI_FORMAT_GZIP, ZOPFLI_FORMAT_ZLIB, ZOPFLI_FORMAT_DEFLATE,
                     ZopfliCompressor, ZopfliDeflater, ZopfliPNG)


__version__ = '1.1.dev'
__all__ = ['ZOPFLI_FORMAT_GZIP', 'ZOPFLI_FORMAT_ZLIB', 'ZOPFLI_FORMAT_DEFLATE',
           'ZopfliCompressor', 'ZopfliDeflater', 'ZopfliDecompressor', 'ZopfliPNG',
           'ZipFile', 'ZipInfo']


class ZopfliDecompressor(object):

    def __init__(self, format=ZOPFLI_FORMAT_DEFLATE):
        if format == ZOPFLI_FORMAT_GZIP:
            wbits = zlib.MAX_WBITS + 16
        elif format == ZOPFLI_FORMAT_ZLIB:
            wbits = zlib.MAX_WBITS
        elif format == ZOPFLI_FORMAT_DEFLATE:
            wbits = -zlib.MAX_WBITS
        else:
            raise ValueError('unknown format')
        self.__z = zlib.decompressobj(wbits)

    @property
    def unused_data(self):
        return self.__z.unused_data

    @property
    def unconsumed_tail(self):
        return self.__z.unconsumed_tail

    if sys.version_info >= (3, 3):
        @property
        def eof(self):
            return self.__z.eof

    def decompress(self, *args, **kwargs):
        return self.__z.decompress(*args, **kwargs)

    def flush(self, *args, **kwargs):
        return self.__z.flush(*args, **kwargs)


class ZipFile(zipfile.ZipFile, object):

    def __init__(self, file, mode='r', compression=zipfile.ZIP_DEFLATED,
                 allowZip64=False, encoding='cp437', **kwargs):
        self.encoding = encoding
        self._options = kwargs
        super(ZipFile, self).__init__(file, mode, compression, allowZip64)

    def _RealGetContents(self):
        super(ZipFile, self)._RealGetContents()
        py2 = sys.version_info < (3, 0)
        for i, zi in enumerate(self.filelist):
            self.filelist[i] = zi = self._convert(zi)
            if not zi.flag_bits & 0x800:
                n = (zi.orig_filename if py2 else zi.orig_filename.encode('cp437')).decode(self.encoding)
                if os.sep != '/':
                    n = n.replace(os.sep, '/')
                del self.NameToInfo[zi.filename]
                zi.filename = n
            self.NameToInfo[zi.filename] = zi

    def write(self, filename, arcname=None, compress_type=None, **kwargs):
        class ZopfliFile(object):
            def __init__(self, zf, z):
                self.size = 0
                self.pos = 0
                self._fp = zf.fp
                self._rewrite = zf._rewrite
                self._w = 0
                self._z = z

            def __getattr__(self, name):
                return getattr(self._fp, name)

            def seek(self, offset, whence=os.SEEK_SET):
                if (0 < self._w
                    and self._z):
                    data = self._z.flush()
                    self.size += len(data)
                    self._fp.write(data)
                    self._z = None
                    self.pos = self._fp.tell()
                self._w = -self._w
                return self._fp.seek(offset, whence)

            def write(self, data):
                if self._w == 0:
                    self._fp.write(self._rewrite(data))
                elif 0 < self._w:
                    if self._z:
                        data = self._z.compress(data)
                        self.size += len(data)
                    self._fp.write(data)
                self._w += 1

        zopflify = self._zopflify(compress_type)
        if zopflify:
            compress_type = zipfile.ZIP_STORED
            opts = self._options.copy()
            opts.update(kwargs)
            z = ZopfliCompressor(ZOPFLI_FORMAT_DEFLATE, **opts)
        else:
            z = None
        fp = self.fp
        try:
            self.fp = ZopfliFile(self, z)
            super(ZipFile, self).write(filename, arcname, compress_type)
            zi = self._convert(self.filelist[-1])
            if zopflify:
                zi.compress_size = self.fp.size
                if not zi.filename.endswith('/'):
                    zi.compress_type = zipfile.ZIP_DEFLATED
                    fp.seek(self.fp.pos)
        finally:
            self.fp = fp
        self.start_dir = self.fp.tell()
        self.fp.seek(zi.header_offset)
        if sys.version_info < (2, 7, 4):
            self.fp.write(zi.FileHeader())
        else:
            self.fp.write(zi.FileHeader(self._zip64(zi)))
        self.fp.seek(self.start_dir)
        self.filelist[-1] = zi
        self.NameToInfo[zi.filename] = zi

    def writestr(self, zinfo_or_arcname, data, compress_type=None, **kwargs):
        class ZopfliFile(object):
            def __init__(self, zf, z, rw):
                self.size = 0
                self._fp = zf.fp
                self._rewrite = zf._rewrite if rw else None
                self._w = 0
                self._z = z

            def __getattr__(self, name):
                return getattr(self._fp, name)

            def write(self, data):
                if self._w == 0:
                    self._fp.write(self._rewrite(data) if self._rewrite else data)
                elif self._w == 1:
                    if self._z:
                        data = self._z.compress(data) + self._z.flush()
                        self.size = len(data)
                    self._fp.write(data)
                self._w += 1

        rw = True
        if isinstance(zinfo_or_arcname, zipfile.ZipInfo):
            compress_type = zinfo_or_arcname.compress_type
            if isinstance(zinfo_or_arcname, ZipInfo):
                zinfo_or_arcname.encoding = self.encoding
                rw = False
        zopflify = self._zopflify(compress_type)
        if zopflify:
            compress_type = zipfile.ZIP_STORED
            opts = self._options.copy()
            opts.update(kwargs)
            z = ZopfliCompressor(ZOPFLI_FORMAT_DEFLATE, **opts)
        else:
            z = None
        fp = self.fp
        try:
            self.fp = ZopfliFile(self, z, rw)
            super(ZipFile, self).writestr(zinfo_or_arcname, data, compress_type)
            zi = self._convert(self.filelist[-1])
            if zopflify:
                zi.compress_type = zipfile.ZIP_DEFLATED
                zi.compress_size = self.fp.size
                if zi.flag_bits & 0x08:
                    data = struct.pack('<LQQ' if self._zip64(zi) else '<LLL',
                                       zi.CRC, zi.compress_size, zi.file_size)
                    fp.write(data)
        finally:
            self.fp = fp
        self.start_dir = self.fp.tell()
        self.fp.seek(zi.header_offset)
        if sys.version_info < (2, 7, 4):
            self.fp.write(zi.FileHeader())
        else:
            self.fp.write(zi.FileHeader(self._zip64(zi)))
        self.fp.seek(self.start_dir)
        self.filelist[-1] = zi
        self.NameToInfo[zi.filename] = zi

    def _convert(self, src):
        if isinstance(src, ZipInfo):
            dst = src
        else:
            dst = ZipInfo()
            for n in src.__slots__:
                try:
                    setattr(dst, n, getattr(src, n))
                except AttributeError:
                    pass
        dst.encoding = self.encoding
        return dst

    def _rewrite(self, fh):
        n = struct.unpack('<H', fh[26:28])[0]
        name = fh[30:30+n].decode('utf-8').encode(self.encoding)
        return fh[:30] + name + fh[30+n:]

    def _zip64(self, zi):
        return (zipfile.ZIP64_LIMIT < zi.file_size
                or zipfile.ZIP64_LIMIT < zi.compress_size)

    def _zopflify(self, compression):
        return (compression == zipfile.ZIP_DEFLATED
                or (compression is None
                    and self.compression == zipfile.ZIP_DEFLATED))


class ZipInfo(zipfile.ZipInfo):

    __slots__ = ('encoding',)

    def __init__(self, *args, **kwargs):
        super(ZipInfo, self).__init__(*args, **kwargs)
        self.encoding = None

    def _encodeFilenameFlags(self):
        if isinstance(self.filename, bytes):
            return self.filename, self.flag_bits
        encoding = codecs.lookup(self.encoding).name if self.encoding else 'ascii'
        if encoding != 'utf-8':
            try:
                return self.filename.encode(encoding), self.flag_bits
            except UnicodeEncodeError:
                pass
        return self.filename.encode('utf-8'), self.flag_bits | 0x800
