#
# zopfli
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

"""Zopfli Compression Algorithm"""

import sys
import zlib

from _zopfli import (ZOPFLI_FORMAT_GZIP, ZOPFLI_FORMAT_ZLIB, ZOPFLI_FORMAT_DEFLATE)


__version__ = '1.0.dev'
__all__ = ['ZOPFLI_FORMAT_GZIP', 'ZOPFLI_FORMAT_ZLIB', 'ZOPFLI_FORMAT_DEFLATE',
           'ZopfliDecompressor']


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
