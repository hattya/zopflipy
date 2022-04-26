#! /usr/bin/env python
#
# setup.py -- zopflipy setup script
#

import os
import sys

from setuptools import setup, Command, Extension


zopfli_dir = os.path.join('zopfli', '_zopfli', 'zopfli', 'src')


def list_sources(path, exts):
    srcs = []
    for root, dirs, files in os.walk(path):
        dirs[:] = (d for d in dirs if not d.startswith('.'))
        for f in files:
            n, ext = os.path.splitext(f)
            if (ext in exts
                and not n.endswith('_bin')):
                srcs.append(os.path.normpath(os.path.join(root, f)))
    return srcs


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


try:
    with open('README.rst') as fp:
        long_description = fp.read()
except OSError:
    long_description = ''

packages = ['zopfli']
package_data = {
    'zopfli': ['py.typed', '*.pyi'],
}
ext_modules = [Extension('zopfli._zopfli',
                         include_dirs=[zopfli_dir],
                         sources=list_sources('.', ['.c', '.cc', '.cpp']))]

cmdclass = {
    'test': test,
}

setup(name='zopflipy',
      description='A Python bindings for Zopfli',
      long_description=long_description,
      author='Akinori Hattori',
      author_email='hattya@gmail.com',
      url='https://github.com/hattya/zopflipy',
      license='ALv2',
      packages=packages,
      package_data=package_data,
      ext_modules=ext_modules,
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: Apache Software License',
          'Operating System :: OS Independent',
          'Programming Language :: C',
          'Programming Language :: C++',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: 3.8',
          'Programming Language :: Python :: 3.9',
          'Programming Language :: Python :: 3.10',
          'Topic :: Software Development :: Libraries :: Python Modules',
          'Topic :: System :: Archiving :: Compression',
      ],
      python_requires='>= 3.7',
      cmdclass=cmdclass,
      setup_requires=['scmver'],
      scmver={
          'root': os.path.dirname(os.path.abspath(__file__)),
          'spec': 'micro',
          'write_to': os.path.join('zopfli', '__version__.py'),
          'fallback': ['__version__:version', 'zopfli'],
      })
