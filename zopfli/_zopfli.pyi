#
# zopfli._zopfli
#
#   Copyright (c) 2021-2024 Akinori Hattori <hattya@gmail.com>
#
#   SPDX-License-Identifier: MIT
#

from collections.abc import Sequence
from typing import Optional


ZOPFLI_FORMAT_GZIP: int
ZOPFLI_FORMAT_ZLIB: int
ZOPFLI_FORMAT_DEFLATE: int


class ZopfliCompressor:

    def __init__(self, format: int = ..., verbose: Optional[bool] = ..., iterations: int = ...,
                 block_splitting: Optional[bool] = ..., block_splitting_max: int = ...) -> None: ...
    def compress(self, data: bytes) -> bytes: ...
    def flush(self) -> bytes: ...


class ZopfliDeflater:

    def __init__(self, verbose: Optional[bool] = ..., iterations: int = ...,
                 block_splitting: Optional[bool] = ..., block_splitting_max: int = ...) -> None: ...
    def compress(self, data: bytes) -> bytes: ...
    def flush(self) -> bytes: ...


class ZopfliPNG:

    verbose: bool
    lossy_transparent: bool
    lossy_8bit: bool
    filter_strategies: str
    auto_filter_strategy: bool
    keep_color_type: bool
    keep_chunks: tuple[str, ...]
    use_zopfli: bool
    iterations: int
    iterations_large: int
 
    def __init__(self, verbose: Optional[bool] = ..., lossy_transparent: Optional[bool] = ..., lossy_8bit: Optional[bool] = ..., filter_strategies: str = ...,
                 auto_filter_strategy: Optional[bool] = ..., keep_color_type: Optional[bool] = ..., keep_chunks: Sequence[str] = ...,
                 use_zopfli: Optional[bool] = ..., iterations: int = ..., iterations_large: int = ...) -> None: ...
    def optimize(self, data: bytes) -> bytes: ...
