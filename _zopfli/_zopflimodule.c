/*
 * _zopfli/_zopflimodule.c
 *
 *   Copyright (c) 2015 Akinori Hattori <hattya@gmail.com>
 *
 *   Licensed under the Apache License, Version 2.0 (the "License");
 *   you may not use this file except in compliance with the License.
 *   You may obtain a copy of the License at
 *
 *       http://www.apache.org/licenses/LICENSE-2.0
 *
 *   Unless required by applicable law or agreed to in writing, software
 *   distributed under the License is distributed on an "AS IS" BASIS,
 *   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 *   See the License for the specific language governing permissions and
 *   limitations under the License.
 */

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#ifdef WITH_THREAD
# include <pythread.h>
#endif

#include "zopfli/zopfli.h"


#define MODULE "_zopfli"

#ifdef WITH_THREAD
# define ALLOCATE_LOCK(self)                                                \
     do {                                                                   \
         if ((self)->lock != NULL) {                                        \
             break;                                                         \
         }                                                                  \
         (self)->lock = PyThread_allocate_lock();                           \
         if ((self)->lock == NULL) {                                        \
             PyErr_SetString(PyExc_MemoryError, "unable to allocate lock"); \
         }                                                                  \
     } while (0)
# define FREE_LOCK(self)                        \
     do {                                       \
         if ((self)->lock != NULL) {            \
             PyThread_free_lock((self)->lock);  \
         }                                      \
     } while (0)
# define ACQUIRE_LOCK(self)                             \
     do {                                               \
         if (!PyThread_acquire_lock((self)->lock, 0)) { \
             Py_BEGIN_ALLOW_THREADS                     \
             PyThread_acquire_lock((self)->lock, 1);    \
             Py_END_ALLOW_THREADS                       \
         }                                              \
     } while (0)
# define RELEASE_LOCK(self) PyThread_release_lock((self)->lock)
#else
# define FREE_LOCK(self)
# define ACQUIRE_LOCK(self)
# define RELEASE_LOCK(self)
#endif


typedef struct {
    PyObject_HEAD
    ZopfliFormat   format;
    ZopfliOptions  options;
    PyObject      *data;
    int            flushed;
#ifdef WITH_THREAD
    PyThread_type_lock lock;
#endif
} Compressor;

static void
Compressor_dealloc(Compressor *self) {
    Py_XDECREF(self->data);
    FREE_LOCK(self);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

PyDoc_STRVAR(Compressor__doc__,
"ZopfliCompressor(format=ZOPFLI_FORMAT_DEFLATE, verbose=False,"
" iterations=15, block_splitting=1, block_splitting_max=15)\n"
"\n"
"Create a compressor object which is using the ZopfliCompress()\n"
"function for compressing data.");

static int
Compressor_init(Compressor *self, PyObject *args, PyObject *kwargs) {
    static char *kwlist[] = {
        "format",
        "verbose",
        "iterations",
        "block_splitting",
        "block_splitting_max",
        NULL,
    };
    PyObject *verbose, *io;

    self->format = ZOPFLI_FORMAT_DEFLATE;
    ZopfliInitOptions(&self->options);
    verbose = Py_False;
    if (!PyArg_ParseTupleAndKeywords(args, kwargs,
                                     "|iOiii:ZopfliCompressor", kwlist,
                                     &self->format,
                                     &verbose,
                                     &self->options.numiterations,
                                     &self->options.blocksplitting,
                                     &self->options.blocksplittingmax)) {
        return -1;
    }

    switch (self->format) {
    case ZOPFLI_FORMAT_GZIP:
    case ZOPFLI_FORMAT_ZLIB:
    case ZOPFLI_FORMAT_DEFLATE:
        break;
    default:
        PyErr_SetString(PyExc_ValueError, "unknown format");
        return -1;
    }

    self->options.verbose = PyObject_IsTrue(verbose);
    if (self->options.verbose < 0) {
        return -1;
    }
    if (self->options.blocksplitting < 0 ||
        3 < self->options.blocksplitting) {
        self->options.blocksplitting = 1;
    }

    io = PyImport_ImportModule("io");
    if (io == NULL) {
        return -1;
    }
    Py_XDECREF(self->data);
    self->data = PyObject_CallMethod(io, "BytesIO", NULL);
    Py_DECREF(io);
    if (self->data == NULL) {
        return -1;
    }

    self->flushed = 0;
#ifdef WITH_THREAD
    ALLOCATE_LOCK(self);
    if (PyErr_Occurred() != NULL) {
        return -1;
    }
#endif
    return 0;
}

PyDoc_STRVAR(Compressor_compress__doc__,
"compress(data) -> bytes");

static PyObject *
Compressor_compress(Compressor *self, PyObject *data) {
    PyObject *v, *n;

    v = NULL;
    ACQUIRE_LOCK(self);
    if (self->flushed) {
        PyErr_SetString(PyExc_ValueError, "Compressor has been flushed");
        goto out;
    }
    n = PyObject_CallMethod(self->data, "write", "O", data);
    if (n == NULL) {
        goto out;
    }
    Py_DECREF(n);
    v = PyBytes_FromString("");
out:
    RELEASE_LOCK(self);
    return v;
}

PyDoc_STRVAR(Compressor_flush__doc__,
"flush() -> bytes\n"
"\n"
"The compressor object cannot be used after this method is called.");

static PyObject *
Compressor_flush(Compressor *self) {
    PyObject *v, *b;
    Py_buffer in = {0};
    unsigned char *out, *out2;
    size_t outsize, outsize2;

    v = NULL;
    b = NULL;
    ACQUIRE_LOCK(self);
    if (self->flushed) {
        PyErr_SetString(PyExc_ValueError, "repeated call to flush()");
        goto out;
    }
#if PY_VERSION_HEX < 0x03020000
    b = PyObject_CallMethod(self->data, "getvalue", NULL);
#else
    b = PyObject_CallMethod(self->data, "getbuffer", NULL);
#endif
    if (b == NULL) {
        goto out;
    }
    if (PyObject_GetBuffer(b, &in, PyBUF_CONTIG_RO) < 0) {
        goto out;
    }

    out = NULL;
    outsize = 0;
    Py_BEGIN_ALLOW_THREADS
    if (self->options.blocksplitting == 3) {
        /* try block splitting first and last */
        self->options.blocksplitting = 1;
        self->options.blocksplittinglast = 0;
        ZopfliCompress(&self->options, self->format, in.buf, in.len,
                       &out, &outsize);

        out2 = NULL;
        outsize2 = 0;
        self->options.blocksplittinglast = 1;
        ZopfliCompress(&self->options, self->format, in.buf, in.len,
                       &out2, &outsize2);

        if (outsize < outsize2) {
            free(out2);
        } else {
            free(out);
            out = out2;
            outsize = outsize2;
        }
    } else {
        ZopfliCompress(&self->options, self->format, in.buf, in.len,
                       &out, &outsize);
    }
    Py_END_ALLOW_THREADS

    v = PyBytes_FromStringAndSize((char *)out, outsize);
    free(out);
    PyBuffer_Release(&in);
out:
    self->flushed = 1;
    Py_XDECREF(b);
    RELEASE_LOCK(self);
    return v;
}

static PyMethodDef Compressor_methods[] = {
    {"compress", (PyCFunction)Compressor_compress, METH_O,
     Compressor_compress__doc__},
    {"flush",    (PyCFunction)Compressor_flush,    METH_NOARGS,
     Compressor_flush__doc__},
    {0},
};

static PyTypeObject Compressor_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    MODULE ".ZopfliCompressor",               /* tp_name           */
    sizeof(Compressor),                       /* tp_basicsize      */
    0,                                        /* tp_itemsize       */
    (destructor)Compressor_dealloc,           /* tp_dealloc        */
    NULL,                                     /* tp_print          */
    NULL,                                     /* tp_getattr        */
    NULL,                                     /* tp_setattr        */
    NULL,                                     /* tp_reserved       */
    NULL,                                     /* tp_repr           */
    NULL,                                     /* tp_as_number      */
    NULL,                                     /* tp_as_sequence    */
    NULL,                                     /* tp_as_mapping     */
    NULL,                                     /* tp_hash           */
    NULL,                                     /* tp_call           */
    NULL,                                     /* tp_str            */
    NULL,                                     /* tp_getattro       */
    NULL,                                     /* tp_setattro       */
    NULL,                                     /* tp_as_buffer      */
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /* tp_flags          */
    Compressor__doc__,                        /* tp_doc            */
    NULL,                                     /* tp_traverse       */
    NULL,                                     /* tp_clear          */
    NULL,                                     /* tp_richcompare    */
    0,                                        /* tp_weaklistoffset */
    NULL,                                     /* tp_iter           */
    NULL,                                     /* tp_iternext       */
    Compressor_methods,                       /* tp_methods        */
    NULL,                                     /* tp_members        */
    NULL,                                     /* tp_getset         */
    NULL,                                     /* tp_base           */
    NULL,                                     /* tp_dict           */
    NULL,                                     /* tp_descr_get      */
    NULL,                                     /* tp_descr_set      */
    0,                                        /* tp_dictoffset     */
    (initproc)Compressor_init,                /* tp_init           */
    NULL,                                     /* tp_alloc          */
    PyType_GenericNew,                        /* tp_new            */
};


#if PY_MAJOR_VERSION < 3
# define PyInit__zopfli   init_zopfli
# define RETURN_MODULE(m) return
#else
# define RETURN_MODULE(m) return m

static struct PyModuleDef _zopflimodule = {
    PyModuleDef_HEAD_INIT,
    MODULE,
    NULL,
    -1,
    NULL,
};
#endif


PyMODINIT_FUNC
PyInit__zopfli(void) {
    PyObject *m;

#if PY_MAJOR_VERSION < 3
    m = Py_InitModule(MODULE, NULL);
#else
    m = PyModule_Create(&_zopflimodule);
#endif
    if (m == NULL) {
        goto err;
    }
    if (PyModule_AddIntMacro(m, ZOPFLI_FORMAT_GZIP) < 0 ||
        PyModule_AddIntMacro(m, ZOPFLI_FORMAT_ZLIB) < 0 ||
        PyModule_AddIntMacro(m, ZOPFLI_FORMAT_DEFLATE) < 0) {
        goto err;
    }

#define ADD_TYPE(m, tp)                                                 \
    do {                                                                \
        if (PyType_Ready(tp) < 0) {                                     \
            goto err;                                                   \
        }                                                               \
        Py_INCREF(tp);                                                  \
        if (PyModule_AddObject((m), strrchr((tp)->tp_name, '.') + 1,    \
                               (PyObject *)(tp)) < 0) {                 \
            Py_DECREF(tp);                                              \
            goto err;                                                   \
        }                                                               \
    } while (0)

    ADD_TYPE(m, &Compressor_Type);

#undef ADD_TYPE

    RETURN_MODULE(m);
err:
    RETURN_MODULE(NULL);
}
