#! /usr/bin/env python
#
# setup.py -- zopflipy setup script
#

import os
import sys

try:
    from setuptools import setup, Command, Extension
except ImportError:
    from distutils.core import setup, Command, Extension


version = 'unknown'

try:
    with open('zopfli.py') as fp:
        for l in fp:
            if l.startswith('__version__ = '):
                version = l.split('=', 2)[1].strip("\n '")
except:
    pass


zopfli_dir = os.path.join('_zopfli', 'zopfli', 'src')


def list_sources(path, exts):
    srcs = []
    for root, dirs, files in os.walk(path):
        dirs[:] = (d for d in dirs if not d.startswith('.'))
        for f in files:
            n, ext = os.path.splitext(f)
            if (ext in exts and
                not n.endswith('_bin')):
                srcs.append(os.path.normpath(os.path.join(root, f)))
    return srcs


class test(Command):

    description = 'run unit tests'
    user_options = [('failfast', 'f', 'stop on first fail or error')]

    boolean_options = ['failfast']

    def initialize_options(self):
        self.failfast = 0

    def finalize_options(self):
        pass

    def run(self):
        import unittest

        build_ext = self.reinitialize_command('build_ext')
        build_ext.inplace = True
        self.run_command('build_ext')
        # run unittest
        argv = [sys.argv[0]]
        if self.verbose:
            argv.append('--verbose')
        if self.failfast:
            argv.append('--failfast')
        unittest.main('test_zopfli', argv=argv)


try:
    with open('README.rst') as fp:
        long_description = fp.read()
except:
    long_description = ''

py_modules = ['zopfli']
ext_modules = [Extension('_zopfli',
                         include_dirs=[zopfli_dir],
                         sources=list_sources('.', ['.c', '.cc', '.cpp']))]

cmdclass = {
    'test': test,
}

setup(name='zopflipy',
      version=version,
      description='A Python bindings for Zopfli',
      long_description=long_description,
      author='Akinori Hattori',
      author_email='hattya@gmail.com',
      url='https://github.com/hattya/zopflipy',
      license='ALv2',
      py_modules=py_modules,
      ext_modules=ext_modules,
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: Apache Software License',
          'Operating System :: OS Independent',
          'Programming Language :: C',
          'Programming Language :: C++',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.3',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'Topic :: System :: Archiving :: Compression',
      ],
      cmdclass=cmdclass)
