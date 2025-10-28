#! /usr/bin/env python
#
# setup.py -- zopflipy setup script
#

import os
import sysconfig

from setuptools import setup, Extension


def sources(path, exts):
    for root, dirs, files in os.walk(path):
        dirs[:] = (d for d in dirs if not d.startswith('.'))
        for f in files:
            n, ext = os.path.splitext(f)
            if (ext in exts
                and not n.endswith('_bin')):
                yield os.path.normpath(os.path.join(root, f))


setup(
    ext_modules=[Extension('zopfli._zopfli',
                           sources=list(sources('zopfli', ['.c', '.cc', '.cpp'])),
                           include_dirs=[os.path.join('zopfli', '_zopfli', 'zopfli', 'src')],
                           define_macros=[('Py_GIL_DISABLED', 1)] if sysconfig.get_config_var('Py_GIL_DISABLED') else [])],
)
