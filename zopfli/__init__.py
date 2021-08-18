#
# zopfli
#
#   Copyright (c) 2015-2021 Akinori Hattori <hattya@gmail.com>
#
#   SPDX-License-Identifier: Apache-2.0
#

"""Zopfli Compression Algorithm"""

import codecs
import os
import struct
import sys
import threading
from typing import cast, Any, AnyStr, IO, Optional, Tuple, Union
import zipfile
import zlib

from ._zopfli import (ZOPFLI_FORMAT_GZIP, ZOPFLI_FORMAT_ZLIB, ZOPFLI_FORMAT_DEFLATE,
                      ZopfliCompressor, ZopfliDeflater, ZopfliPNG)


__version__ = '1.6.dev'
__all__ = ['ZOPFLI_FORMAT_GZIP', 'ZOPFLI_FORMAT_ZLIB', 'ZOPFLI_FORMAT_DEFLATE',
           'ZopfliCompressor', 'ZopfliDeflater', 'ZopfliDecompressor', 'ZopfliPNG',
           'ZipFile', 'ZipInfo']

if sys.version_info >= (3, 9):
    P = Union[str, os.PathLike[str]]
else:
    P = Union[str, os.PathLike]


class ZopfliDecompressor:

    def __init__(self, format: int = ZOPFLI_FORMAT_DEFLATE) -> None:
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
    def unused_data(self) -> bytes:
        return self.__z.unused_data

    @property
    def unconsumed_tail(self) -> bytes:
        return self.__z.unconsumed_tail

    @property
    def eof(self) -> bool:
        return self.__z.eof

    def decompress(self, data: bytes, max_length: int = 0) -> bytes:
        return self.__z.decompress(data, max_length)

    def flush(self, length: int = zlib.DEF_BUF_SIZE) -> bytes:
        return self.__z.flush(length)


class ZipFile(zipfile.ZipFile):

    fp: Any
    compression: int
    _lock: threading.RLock

    def __init__(self, file: P, mode: str = 'r', compression: int = zipfile.ZIP_DEFLATED, allowZip64: bool = True,
                 encoding: str = 'cp437', **kwargs: Any) -> None:
        self.encoding = encoding
        self._options = kwargs
        super(ZipFile, self).__init__(file, mode, compression, allowZip64)
        if sys.version_info >= (3, 8):
            self._strict_timestamps = kwargs.pop('strict_timestamps', True)

    def _RealGetContents(self) -> None:
        super(ZipFile, self)._RealGetContents()
        for i, zi in enumerate(self.filelist):
            self.filelist[i] = zi = self._convert(zi)
            if not zi.flag_bits & 0x800:
                n = zi.orig_filename.encode('cp437').decode(self.encoding)
                if os.sep != '/':
                    n = n.replace(os.sep, '/')
                del self.NameToInfo[zi.filename]
                zi.filename = n
            self.NameToInfo[zi.filename] = zi

    def write(self, filename: P, arcname: Optional[P] = None, compress_type: Optional[int] = None, **kwargs: Any) -> None:
        class ZopfliFile:
            def __init__(self, zf: ZipFile, z: Optional[ZopfliCompressor]) -> None:
                self.size = 0
                self.pos = 0
                self._fp = cast(IO[bytes], zf.fp)
                self._rewrite = zf._rewrite
                self._w = 0
                self._z = z

            def __getattr__(self, name: str) -> Any:
                return getattr(self._fp, name)

            def seek(self, offset: int, whence: int = os.SEEK_SET) -> int:
                if (self._w > 0
                    and self._z):
                    data = self._z.flush()
                    self.size += len(data)
                    self._fp.write(data)
                    self._z = None
                    self.pos = self._fp.tell()
                self._w = -self._w
                return self._fp.seek(offset, whence)

            def write(self, data: bytes) -> None:
                if self._w == 0:
                    self._fp.write(self._rewrite(data))
                elif self._w > 0:
                    if self._z:
                        data = self._z.compress(data)
                        self.size += len(data)
                    self._fp.write(data)
                self._w += 1

        zopflify = self._zopflify(compress_type)
        z: Optional[ZopfliCompressor] = None
        if zopflify:
            compress_type = zipfile.ZIP_STORED
            opts = self._options.copy()
            opts.update(kwargs)
            z = ZopfliCompressor(ZOPFLI_FORMAT_DEFLATE, **opts)
        self._lock.acquire()
        try:
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
            self.fp.write(zi.FileHeader(self._zip64(zi)))
            self.fp.seek(self.start_dir)
            self.filelist[-1] = zi
            self.NameToInfo[zi.filename] = zi
        finally:
            self._lock.release()

    def writestr(self, zinfo_or_arcname: Union[str, zipfile.ZipInfo], data: AnyStr, compress_type: Optional[int] = None, **kwargs: Any) -> None:
        class ZopfliFile:
            def __init__(self, zf: ZipFile, z: Optional[ZopfliCompressor], rw: bool) -> None:
                self.size = 0
                self._fp = zf.fp
                self._rewrite = zf._rewrite if rw else None
                self._w = 0
                self._z = z

            def __getattr__(self, name: str) -> Any:
                return getattr(self._fp, name)

            def write(self, data: bytes) -> None:
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
        z: Optional[ZopfliCompressor] = None
        if zopflify:
            compress_type = zipfile.ZIP_STORED
            opts = self._options.copy()
            opts.update(kwargs)
            z = ZopfliCompressor(ZOPFLI_FORMAT_DEFLATE, **opts)
        self._lock.acquire()
        try:
            fp = self.fp
            try:
                self.fp = ZopfliFile(self, z, rw)
                super(ZipFile, self).writestr(zinfo_or_arcname, data, compress_type)
                zi = self._convert(self.filelist[-1])
                if zopflify:
                    zi.compress_type = zipfile.ZIP_DEFLATED
                    zi.compress_size = self.fp.size
            finally:
                self.fp = fp
            self.start_dir = self.fp.tell()
            self.fp.seek(zi.header_offset)
            self.fp.write(zi.FileHeader(self._zip64(zi)))
            self.fp.seek(self.start_dir)
            self.filelist[-1] = zi
            self.NameToInfo[zi.filename] = zi
        finally:
            self._lock.release()

    def _convert(self, src: zipfile.ZipInfo) -> 'ZipInfo':
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

    def _rewrite(self, fh: bytes) -> bytes:
        n = struct.unpack('<H', fh[26:28])[0]
        name = fh[30:30+n].decode('utf-8').encode(self.encoding)
        return fh[:30] + name + fh[30+n:]

    def _zip64(self, zi: zipfile.ZipInfo) -> bool:
        return (zi.file_size > zipfile.ZIP64_LIMIT
                or zi.compress_size > zipfile.ZIP64_LIMIT)

    def _zopflify(self, compression: Optional[int]) -> bool:
        return (compression == zipfile.ZIP_DEFLATED
                or (compression is None
                    and self.compression == zipfile.ZIP_DEFLATED))


class ZipInfo(zipfile.ZipInfo):

    __slots__ = ('encoding',)

    encoding: Optional[str]
    orig_filename: str

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super(ZipInfo, self).__init__(*args, **kwargs)
        self.encoding = None

    def _encodeFilenameFlags(self) -> Tuple[bytes, int]:
        if isinstance(self.filename, bytes):
            return self.filename, self.flag_bits
        encoding = codecs.lookup(self.encoding).name if self.encoding else 'ascii'
        if encoding != 'utf-8':
            try:
                return self.filename.encode(encoding), self.flag_bits
            except UnicodeEncodeError:
                pass
        return self.filename.encode('utf-8'), self.flag_bits | 0x800
