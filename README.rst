ZopfliPy
========

A Python_ bindings for Zopfli_.

.. _Python: https://www.python.org/
.. _Zopfli: https://github.com/google/zopfli


Requirements
------------

- Python 2.7 or 3.3+


Installation
------------

.. code:: console

   $ git clone --recursive https://github.com/hattya/zopfipy
   $ cd zopflipy
   $ python setup.py install

or

.. code:: console

   $ pip install git+https://github.com/hattya/zopflipy


Usage
-----

.. code:: pycon

   >>> import zopfli
   >>> c = zopfli.ZopfliCompressor(zopfli.ZOPFLI_FORMAT_DEFLATE)
   >>> z = c.compress(b'Hello, world!') + c.flush()
   >>> d = zopfli.ZopfliDecompressor(zopfli.ZOPFLI_FORMAT_DEFLATE)
   >>> d.decompress(z) + d.flush()
   b'Hello, world!''


License
-------

ZopfliPy is distributed under the terms of the Apache License, Version 2.0.
