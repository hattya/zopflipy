#! /usr/bin/env python
#
# setup.py -- zopflipy setup script
#

import os
import sys

from setuptools import setup, Command, Extension


def sources(path, exts):
    for root, dirs, files in os.walk(path):
        dirs[:] = (d for d in dirs if not d.startswith('.'))
        for f in files:
            n, ext = os.path.splitext(f)
            if (ext in exts
                and not n.endswith('_bin')):
                yield os.path.normpath(os.path.join(root, f))


class test(Command):

    description = 'run unit tests'
    user_options = [('failfast', 'f', 'stop on first fail or error')]

    boolean_options = ['failfast']

    def initialize_options(self):
        self.failfast = False

    def finalize_options(self):
        pass

    def run(self):
        import unittest

        build_ext = self.reinitialize_command('build_ext')
        build_ext.inplace = True
        self.run_command('build_ext')
        # run unittest discover
        argv = [sys.argv[0], 'discover', '--start-directory', 'tests']
        if self.verbose:
            argv.append('--verbose')
        if self.failfast:
            argv.append('--failfast')
        unittest.main(None, argv=argv)


setup(
    ext_modules=[Extension('zopfli._zopfli',
                           include_dirs=[os.path.join('zopfli', '_zopfli', 'zopfli', 'src')],
                           sources=list(sources('zopfli', ['.c', '.cc', '.cpp'])))],
    cmdclass={
        'test': test,
    },
)
