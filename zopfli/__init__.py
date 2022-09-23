#
# zopfli
#
#   Copyright (c) 2015-2022 Akinori Hattori <hattya@gmail.com>
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
if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal
import zipfile
import zlib

from ._zopfli import (ZOPFLI_FORMAT_GZIP, ZOPFLI_FORMAT_ZLIB, ZOPFLI_FORMAT_DEFLATE,
                      ZopfliCompressor, ZopfliDeflater, ZopfliPNG)


__all__ = ['ZOPFLI_FORMAT_GZIP', 'ZOPFLI_FORMAT_ZLIB', 'ZOPFLI_FORMAT_DEFLATE',
           'ZopfliCompressor', 'ZopfliDeflater', 'ZopfliDecompressor', 'ZopfliPNG',
           'ZipFile', 'ZipInfo']
__author__ = 'Akinori Hattori <hattya@gmail.com>'
try:
    from .__version__ import version as __version__
except ImportError:
    __version__ = 'unknown'

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

    fp: IO[bytes]
    compression: int
    _lock: threading.RLock

    def __init__(self, file: Union[P, IO[bytes]], mode: Literal['r', 'w', 'x', 'a'] = 'r', compression: int = zipfile.ZIP_DEFLATED, allowZip64: bool = True,
                 compresslevel: Optional[int] = None, *, strict_timestamps: bool = True, encoding: str = 'cp437', **kwargs: Any) -> None:
        self.encoding = encoding
        self._options = kwargs
        super().__init__(file, mode, compression, allowZip64, compresslevel)
        if sys.version_info >= (3, 8):
            self._strict_timestamps = strict_timestamps

    def _RealGetContents(self) -> None:
        super()._RealGetContents()
        for i, zi in enumerate(self.filelist):
            self.filelist[i] = zi = self._convert(zi)
            if not zi.flag_bits & 0x800:
                n = zi.orig_filename.encode('cp437').decode(self.encoding)
                if os.sep != '/':
                    n = n.replace(os.sep, '/')
                del self.NameToInfo[zi.filename]
                zi.filename = n
            self.NameToInfo[zi.filename] = zi

    def open(self, name: Union[str, zipfile.ZipInfo], mode: Literal['r', 'w'] = 'r', pwd: Optional[bytes] = None,
             *, force_zip64: bool = False, **kwargs: Any) -> IO[bytes]:
        fp = super().open(name, mode, pwd, force_zip64=force_zip64)
        if (mode == 'w'
            and self._zopflify(None)
            and fp._compressor):
            opts = self._options.copy()
            opts.update(kwargs)
            fp._compressor = ZopfliCompressor(ZOPFLI_FORMAT_DEFLATE, **opts)
        return fp

    def _open_to_write(self, zinfo: zipfile.ZipInfo, force_zip64: bool = False) -> IO[bytes]:
        return cast(IO[bytes], super()._open_to_write(self._convert(zinfo), force_zip64))

    def write(self, filename: P, arcname: Optional[P] = None,
              compress_type: Optional[int] = None, compresslevel: Optional[int] = None, **kwargs: Any) -> None:
        zopflify = self._zopflify(compress_type)
        z: Optional[ZopfliCompressor] = None
        if zopflify:
            compress_type = zipfile.ZIP_STORED
            opts = self._options.copy()
            opts.update(kwargs)
            z = ZopfliCompressor(ZOPFLI_FORMAT_DEFLATE, **opts)
        with self._lock:
            fp = self.fp
            try:
                self.fp = self._file(z)
                super().write(filename, arcname, compress_type, compresslevel)
                zi = self._convert(self.filelist[-1])
                if zopflify:
                    zi.compress_size = self.fp.size
                    if not zi.is_dir():
                        zi.compress_type = zipfile.ZIP_DEFLATED
            finally:
                self.fp = fp
            if zopflify:
                self.fp.seek(zi.header_offset)
                self.fp.write(zi.FileHeader(self._zip64(zi)))
                self.fp.seek(self.start_dir)
            self.filelist[-1] = zi
            self.NameToInfo[zi.filename] = zi

    def writestr(self, zinfo_or_arcname: Union[str, zipfile.ZipInfo], data: AnyStr,
                 compress_type: Optional[int] = None, compresslevel: Optional[int] = None, **kwargs: Any) -> None:
        if isinstance(zinfo_or_arcname, zipfile.ZipInfo):
            compress_type = zinfo_or_arcname.compress_type
            if isinstance(zinfo_or_arcname, ZipInfo):
                zinfo_or_arcname.encoding = self.encoding
        zopflify = self._zopflify(compress_type)
        z: Optional[ZopfliCompressor] = None
        if zopflify:
            compress_type = zipfile.ZIP_STORED
            opts = self._options.copy()
            opts.update(kwargs)
            z = ZopfliCompressor(ZOPFLI_FORMAT_DEFLATE, **opts)
        with self._lock:
            fp = self.fp
            try:
                self.fp = self._file(z)
                super().writestr(zinfo_or_arcname, data, compress_type, compresslevel)
                zi = self._convert(self.filelist[-1])
                if zopflify:
                    zi.compress_type = zipfile.ZIP_DEFLATED
                    zi.compress_size = self.fp.size
            finally:
                self.fp = fp
            if zopflify:
                self.fp.seek(zi.header_offset)
                self.fp.write(zi.FileHeader(self._zip64(zi)))
                self.fp.seek(self.start_dir)
            self.filelist[-1] = zi
            self.NameToInfo[zi.filename] = zi

    if sys.version_info >= (3, 11):
        def mkdir(self, zinfo_or_directory: Union[str, zipfile.ZipInfo], mode: int = 511) -> None:
            with self._lock:
                fp = self.fp
                try:
                    self.fp = self._file(None)
                    super().mkdir(zinfo_or_directory, mode)
                    zi = self._convert(self.filelist[-1])
                finally:
                    self.fp = fp
                self.filelist[-1] = zi
                self.NameToInfo[zi.filename] = zi

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

    def _file(self, z: Optional[ZopfliCompressor]) -> IO[bytes]:
        LFH = '<4s5H3L2H'
        EFS = 1 << 11

        class ZopfliFile:

            def __init__(self, zf: ZipFile, z: Optional[ZopfliCompressor]) -> None:
                self.size = 0
                self._zf = zf
                self._fp = zf.fp
                self._pos = zf.start_dir
                self._z = z
                self._fh = 0

            def __getattr__(self, name: str) -> Any:
                return getattr(self._fp, name)

            def seek(self, offset: int, whence: int = os.SEEK_SET) -> int:
                if (offset == self._pos
                    and whence == os.SEEK_SET):
                    self._fh = -self._fh + 1
                    if (self._fh > 1
                        and self._z):
                        data = self._z.flush()
                        self.size += len(data)
                        self._fp.write(data)
                        self._z = None
                        self._zf.start_dir = self._fp.tell()
                return self._fp.seek(offset, whence)

            def write(self, data: bytes) -> None:
                if self._fh > 0:
                    self._fp.write(self._rewrite(data))
                    self._fh = -self._fh
                else:
                    if self._z:
                        data = self._z.compress(data)
                        self.size += len(data)
                    self._fp.write(data)

            def _rewrite(self, fh: bytes) -> bytes:
                sig, ver, flag, meth, lmt, lmd, crc, csize, fsize, n, m = struct.unpack(LFH, fh[:30])
                if flag & EFS:
                    try:
                        name = fh[30:30+n].decode('utf-8').encode(self._zf.encoding)
                        if name != fh[30:30+n]:
                            return struct.pack(LFH, sig, ver, flag & ~EFS, meth, lmt, lmd, crc, csize, fsize, len(name), m) + name + fh[30+n:]
                    except UnicodeEncodeError:
                        pass
                return fh

        return cast(IO[bytes], ZopfliFile(self, z))

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
        super().__init__(*args, **kwargs)
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
