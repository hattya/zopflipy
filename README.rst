ZopfliPy
========

A Python_ bindings for Zopfli_.

.. image:: https://img.shields.io/pypi/v/zopflipy.svg
   :target: https://pypi.org/project/zopflipy

.. image:: https://github.com/hattya/zopflipy/actions/workflows/ci.yml/badge.svg
   :target: https://github.com/hattya/zopflipy/actions/workflows/ci.yml

.. image:: https://ci.appveyor.com/api/projects/status/98a7e7d6qlkvs6vl/branch/master?svg=true
   :target: https://ci.appveyor.com/project/hattya/zopflipy

.. image:: https://codecov.io/gh/hattya/zopflipy/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/hattya/zopflipy

.. _Python: https://www.python.org/
.. _Zopfli: https://github.com/google/zopfli


Installation
------------

.. code:: console

   $ pip install zopflipy


Requirements
------------

- Python 3.7+
- setuptools


Usage
-----

ZopfliCompressor
~~~~~~~~~~~~~~~~

.. code:: pycon

   >>> import zopfli
   >>> c = zopfli.ZopfliCompressor(zopfli.ZOPFLI_FORMAT_DEFLATE)
   >>> z = c.compress(b'Hello, world!') + c.flush()
   >>> d = zopfli.ZopfliDecompressor(zopfli.ZOPFLI_FORMAT_DEFLATE)
   >>> d.decompress(z) + d.flush()
   b'Hello, world!''


ZopfliDeflater
~~~~~~~~~~~~~~

.. code:: pycon

   >>> import zopfli
   >>> c = zopfli.ZopfliDeflater()
   >>> z = c.compress(b'Hello, world!') + c.flush()
   >>> d = zopfli.ZopfliDecompressor(zopfli.ZOPFLI_FORMAT_DEFLATE)
   >>> d.decompress(z) + d.flush()
   b'Hello, world!''


ZopfliPNG
~~~~~~~~~

.. code:: pycon

   >>> import zopfli
   >>> png = zopfli.ZopfliPNG()
   >>> with open('in.png', 'rb') as fp:
   ...     data = fp.read()
   >>> len(png.optimize(data)) < len(data)
   True


ZipFile
~~~~~~~

A subclass of |zipfile.ZipFile|_ which uses |ZopfliCompressor|_ for the
|zipfile.ZIP_DEFLATED|_ compression method.

.. code:: pycon

   >>> import zipfile
   >>> import zopfli
   >>> with zopfli.ZipFile('a.zip', 'w', zipfile.ZIP_DEFLATED) as zf:
   ...     zf.writestr('a.txt', b'Hello, world!')


.. |zipfile.ZipFile| replace:: ``zipfile.ZipFile``
.. _zipfile.ZipFile: https://docs.python.org/3/library/zipfile.html#zipfile.ZipFile
.. |ZopfliCompressor| replace:: ``ZopfliCompressor``
.. |zipfile.ZIP_DEFLATED| replace:: ``zipfile.ZIP_DEFLATED``
.. _zipfile.ZIP_DEFLATED: https://docs.python.org/3/library/zipfile.html#zipfile.ZIP_DEFLATED


License
-------

ZopfliPy is distributed under the terms of the Apache License, Version 2.0.
