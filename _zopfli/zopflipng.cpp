//
// _zopfli :: zopflipng.cpp
//
//   Copyright (c) 2015-2021 Akinori Hattori <hattya@gmail.com>
//
//   SPDX-License-Identifier: Apache-2.0
//

#include "_zopflimodule.h"

#include "zopflipng/zopflipng_lib.h"
#include "zopflipng/lodepng/lodepng.h"


template<typename T>
static inline void clear(T*& p) {
    delete p;
    p = 0;
}

static inline PyObject* int_FromLong(long i) {
    return PyLong_FromLong(i);
}

static inline PyObject* str_AsASCIIString(PyObject* u) {
    return PyUnicode_AsASCIIString(u);
}

static inline bool str_Check(PyObject* v) {
    if (PyUnicode_Check(v)) {
        return true;
    }
    PyErr_Format(PyExc_TypeError, "expected str, got '%.200s'", Py_TYPE(v)->tp_name);
    return false;
}

static inline PyObject* str_FromString(const char* s) {
    return PyUnicode_FromString(s);
}


struct PNG {
    PyObject_HEAD
    PyObject*         filter_strategies;
    PyObject*         keep_chunks;
    ZopfliPNGOptions* options;
#ifdef WITH_THREAD
    PyThread_type_lock lock;
#endif
};

static int PNG_traverse(PNG* self, visitproc visit, void* arg) {
    Py_VISIT(self->filter_strategies);
    Py_VISIT(self->keep_chunks);
    return 0;
}

static int PNG_clear(PNG* self) {
    Py_CLEAR(self->filter_strategies);
    Py_CLEAR(self->keep_chunks);
    return 0;
}

static void PNG_dealloc(PNG* self) {
    PyObject_GC_UnTrack(self);
    PNG_clear(self);
    clear(self->options);
    FREE_LOCK(self);
    Py_TYPE(self)->tp_free(reinterpret_cast<PyObject*>(self));
}

static int parse_filter_strategies(PNG* self, PyObject* filter_strategies) {
    PyObject* b = 0;
    char* s;
    Py_CLEAR(self->filter_strategies);
    if (!str_Check(filter_strategies)) {
        goto err;
    }
    b = str_AsASCIIString(filter_strategies);
    if (b == 0) {
        goto err;
    }
    s = PyBytes_AsString(b);
    if (s == 0) {
        goto err;
    }
    self->options->filter_strategies.clear();
    for (; *s != '\0'; ++s) {
        ZopfliPNGFilterStrategy fs;
        switch (*s) {
        case '0':
            fs = kStrategyZero;
            break;
        case '1':
            fs = kStrategyOne;
            break;
        case '2':
            fs = kStrategyTwo;
            break;
        case '3':
            fs = kStrategyThree;
            break;
        case '4':
            fs = kStrategyFour;
            break;
        case 'm':
            fs = kStrategyMinSum;
            break;
        case 'e':
            fs = kStrategyEntropy;
            break;
        case 'p':
            fs = kStrategyPredefined;
            break;
        case 'b':
            fs = kStrategyBruteForce;
            break;
        default:
            PyErr_Format(PyExc_ValueError, "unknown filter strategy: %c", *s);
            goto err;
        }
        self->options->filter_strategies.push_back(fs);
        self->options->auto_filter_strategy = false;
    }

    Py_DECREF(b);
    Py_INCREF(filter_strategies);
    self->filter_strategies = filter_strategies;
    return 0;
err:
    Py_XDECREF(b);
    self->filter_strategies = str_FromString("");
    self->options->filter_strategies.clear();
    self->options->auto_filter_strategy = true;
    return -1;
}

static int parse_keep_chunks(PNG* self, PyObject* keep_chunks) {
    PyObject* u = 0;
    PyObject* b = 0;
    Py_CLEAR(self->keep_chunks);
    Py_ssize_t n = PySequence_Size(keep_chunks);
    if (n < 0) {
        goto err;
    }
    self->options->keepchunks.clear();
    for (Py_ssize_t i = 0; i < n; ++i) {
        u = PySequence_GetItem(keep_chunks, i);
        if (u == 0) {
            goto err;
        }
        if (!str_Check(u)) {
            goto err;
        }
        b = str_AsASCIIString(u);
        if (b == 0) {
            goto err;
        }
        char* s = PyBytes_AsString(b);
        if (s == 0) {
            goto err;
        }
        self->options->keepchunks.push_back(s);
        Py_CLEAR(u);
        Py_CLEAR(b);
    }

    self->keep_chunks = PySequence_Tuple(keep_chunks);
    return 0;
err:
    Py_XDECREF(u);
    Py_XDECREF(b);
    self->keep_chunks = PyTuple_New(0);
    self->options->keepchunks.clear();
    return -1;
}

PyDoc_STRVAR(PNG__doc__,
"ZopfliPNG(verbose=False, lossy_transparent=False, lossy_8bit=False,"
" filter_strategies='', auto_filter_strategy=True, keep_color_type=False,"
" keep_chunks=None, use_zopfli=True, iterations=15, iterations_large=5)\n"
"\n"
"Create a PNG optimizer which is using the ZopfliPNGOptimize()\n"
"function for optimizing PNG files.\n"
"");

static int PNG_init(PNG* self, PyObject* args, PyObject* kwargs) {
    static const char* kwlist[] = {
        "verbose",
        "lossy_transparent",
        "lossy_8bit",
        "filter_strategies",
        "auto_filter_strategy",
        "keep_color_type",
        "keep_chunks",
        "use_zopfli",
        "iterations",
        "iterations_large",
        0,
    };

    PyObject* verbose = Py_False;
    PyObject* lossy_transparent = Py_False;
    PyObject* lossy_8bit = Py_False;
    PyObject* filter_strategies = 0;
    PyObject* auto_filter_strategy = Py_True;
    PyObject* keep_color_type = Py_False;
    PyObject* keep_chunks = 0;
    PyObject* use_zopfli = Py_True;
    clear(self->options);
    self->options = new ZopfliPNGOptions;
    if (!PyArg_ParseTupleAndKeywords(args, kwargs,
                                     "|OOOOOOOOii:ZopfliPNG", const_cast<char**>(kwlist),
                                     &verbose,
                                     &lossy_transparent,
                                     &lossy_8bit,
                                     &filter_strategies,
                                     &auto_filter_strategy,
                                     &keep_color_type,
                                     &keep_chunks,
                                     &use_zopfli,
                                     &self->options->num_iterations,
                                     &self->options->num_iterations_large)) {
        return -1;
    }

#define PARSE_BOOL(var, val)            \
    do {                                \
        int b = PyObject_IsTrue(val);   \
        if (b < 0) {                    \
            goto err;                   \
        }                               \
        var = !!b;                      \
    } while (false)

    PARSE_BOOL(self->options->verbose,              verbose);
    PARSE_BOOL(self->options->lossy_transparent,    lossy_transparent);
    PARSE_BOOL(self->options->lossy_8bit,           lossy_8bit);
    PARSE_BOOL(self->options->auto_filter_strategy, auto_filter_strategy);
    PARSE_BOOL(self->options->keep_colortype,       keep_color_type);
    PARSE_BOOL(self->options->use_zopfli,           use_zopfli);

#undef PARSE_BOOL

#define PARSE_OBJECT(self, var, dv)                 \
    do {                                            \
        if (var != 0) {                             \
            if (parse_ ## var((self), var) < 0) {   \
                goto err;                           \
            }                                       \
        } else {                                    \
            Py_XDECREF((self)->var);                \
            (self)->var = (dv);                     \
        }                                           \
    } while (false)

    PARSE_OBJECT(self, filter_strategies, str_FromString(""));
    PARSE_OBJECT(self, keep_chunks,       PyTuple_New(0));

#undef PARSE_OBJECT

#ifdef WITH_THREAD
    ALLOCATE_LOCK(self);
    if (PyErr_Occurred() != 0) {
        goto err;
    }
#endif

    return 0;
err:
    Py_CLEAR(self->filter_strategies);
    Py_CLEAR(self->keep_chunks);
    clear(self->options);
    return -1;
}

PyDoc_STRVAR(PNG_optimize__doc__,
"optimize(data) -> bytes");

static PyObject* PNG_optimize(PNG* self, PyObject* data) {
    PyObject* v = 0;
    Py_buffer in = {0};
    std::vector<unsigned char> out, buf;
    unsigned char* p;
    ACQUIRE_LOCK(self);
    if (PyObject_GetBuffer(data, &in, PyBUF_CONTIG_RO) < 0) {
        goto out;
    }
    p = static_cast<unsigned char*>(in.buf);
    buf.assign(p, p + in.len);
    unsigned err;
    Py_BEGIN_ALLOW_THREADS
    err = ZopfliPNGOptimize(buf, *self->options, self->options->verbose, &out);
    Py_END_ALLOW_THREADS
    if (err) {
        PyErr_SetString(PyExc_ValueError, lodepng_error_text(err));
        goto out;
    }
    buf.clear();
    unsigned w, h;
    Py_BEGIN_ALLOW_THREADS
    err = lodepng::decode(buf, w, h, out);
    Py_END_ALLOW_THREADS
    if (err) {
        PyErr_SetString(PyExc_ValueError, "verification failed");
        goto out;
    }
    v = PyBytes_FromStringAndSize(reinterpret_cast<char*>(&out[0]), out.size());
out:
    PyBuffer_Release(&in);
    RELEASE_LOCK(self);
    return v;
}

static PyMethodDef PNG_methods[] = {
    {"optimize", reinterpret_cast<PyCFunction>(PNG_optimize), METH_O, PNG_optimize__doc__},
    {0},
};

static PyObject* PNG_get_object(PNG* self, void* closure) {
    const char *s = static_cast<char*>(closure);
    PyObject* v = 0;
    if (strcmp(s, "filter_strategies") == 0) {
        v = self->filter_strategies;
    } else if (strcmp(s, "keep_chunks") == 0) {
        v = self->keep_chunks;
    }

    Py_INCREF(v);
    return v;
}

static int PNG_set_object(PNG* self, PyObject* value, void* closure) {
    const char* s = static_cast<char*>(closure);
    if (value == 0) {
        PyErr_Format(PyExc_TypeError, "cannot delete %s", s);
        return -1;
    }

    if (strcmp(s, "filter_strategies") == 0) {
        if (parse_filter_strategies(self, value) < 0) {
            return -1;
        }
    } else if (strcmp(s, "keep_chunks") == 0) {
        if (parse_keep_chunks(self, value) < 0) {
            return -1;
        }
    }
    return 0;
}

static PyObject* PNG_get_bool(PNG* self, void* closure) {
    const char *s = static_cast<char*>(closure);
    bool v = false;
    if (strcmp(s, "verbose") == 0) {
        v = self->options->verbose;
    } else if (strcmp(s, "lossy_transparent") == 0) {
        v = self->options->lossy_transparent;
    } else if (strcmp(s, "lossy_8bit") == 0) {
        v = self->options->lossy_8bit;
    } else if (strcmp(s, "auto_filter_strategy") == 0) {
        v = self->options->auto_filter_strategy;
    } else if (strcmp(s, "keep_color_type") == 0) {
        v = self->options->keep_colortype;
    } else if (strcmp(s, "use_zopfli") == 0) {
        v = self->options->use_zopfli;
    }

    if (v) {
        Py_RETURN_TRUE;
    }
    Py_RETURN_FALSE;
}

static int PNG_set_bool(PNG* self, PyObject* value, void* closure) {
    const char* s = static_cast<char*>(closure);
    if (value == 0) {
        PyErr_Format(PyExc_TypeError, "cannot delete %s", s);
        return -1;
    }
    int b = PyObject_IsTrue(value);
    if (b < 0) {
        return -1;
    }
    bool v = !!b;

    if (strcmp(s, "verbose") == 0) {
        self->options->verbose = v;
    } else if (strcmp(s, "lossy_transparent") == 0) {
        self->options->lossy_transparent = v;
    } else if (strcmp(s, "lossy_8bit") == 0) {
        self->options->lossy_8bit = v;
    } else if (strcmp(s, "auto_filter_strategy") == 0) {
        if (v) {
            Py_CLEAR(self->filter_strategies);
            self->filter_strategies = str_FromString("");
            self->options->filter_strategies.clear();
        }
        self->options->auto_filter_strategy = v;
    } else if (strcmp(s, "keep_color_type") == 0) {
        self->options->keep_colortype = v;
    } else if (strcmp(s, "use_zopfli") == 0) {
        self->options->use_zopfli = v;
    }
    return 0;
}

static PyObject* PNG_get_int(PNG* self, void* closure) {
    const char* s = static_cast<char*>(closure);
    long v = 0;
    if (strcmp(s, "iterations") == 0) {
        v = self->options->num_iterations;
    } else if (strcmp(s, "iterations_large") == 0) {
        v = self->options->num_iterations_large;
    }

    return int_FromLong(v);
}

static int PNG_set_int(PNG* self, PyObject* value, void* closure) {
    const char* s = static_cast<char*>(closure);
    if (value == 0) {
        PyErr_Format(PyExc_TypeError, "cannot delete %s", s);
        return -1;
    }
    long v = PyLong_AsLong(value);
    if (PyErr_Occurred() != 0) {
        return -1;
    }

    if (strcmp(s, "iterations") == 0) {
        self->options->num_iterations = v;
    } else if (strcmp(s, "iterations_large") == 0) {
        self->options->num_iterations_large = v;
    }
    return 0;
}

#define GET_SET(v, tp) \
    {const_cast<char*>(#v), reinterpret_cast<getter>(PNG_get_ ## tp), reinterpret_cast<setter>(PNG_set_ ## tp), 0, const_cast<char*>(#v)}

static PyGetSetDef PNG_getset[] = {
    GET_SET(filter_strategies,    object),
    GET_SET(keep_chunks,          object),
    GET_SET(verbose,              bool),
    GET_SET(lossy_transparent,    bool),
    GET_SET(lossy_8bit,           bool),
    GET_SET(auto_filter_strategy, bool),
    GET_SET(keep_color_type,      bool),
    GET_SET(use_zopfli,           bool),
    GET_SET(iterations,           int),
    GET_SET(iterations_large,     int),
    {0},
};

#undef GET_SET

PyTypeObject PNG_Type = {
    PyVarObject_HEAD_INIT(0, 0)
    MODULE ".ZopfliPNG",                          // tp_name
    sizeof(PNG),                                  // tp_basicsize
    0,                                            // tp_itemsize
    reinterpret_cast<destructor>(PNG_dealloc),    // tp_dealloc
    0,                                            // tp_print
    0,                                            // tp_getattr
    0,                                            // tp_setattr
    0,                                            // tp_reserved
    0,                                            // tp_repr
    0,                                            // tp_as_number
    0,                                            // tp_as_sequence
    0,                                            // tp_as_mapping
    0,                                            // tp_hash
    0,                                            // tp_call
    0,                                            // tp_str
    0,                                            // tp_getattro
    0,                                            // tp_setattro
    0,                                            // tp_as_buffer
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE |
        Py_TPFLAGS_HAVE_GC,                       // tp_flags
    PNG__doc__,                                   // tp_doc
    reinterpret_cast<traverseproc>(PNG_traverse), // tp_traverse
    reinterpret_cast<inquiry>(PNG_clear),         // tp_clear
    0,                                            // tp_richcompare
    0,                                            // tp_weaklistoffset
    0,                                            // tp_iter
    0,                                            // tp_iternext
    PNG_methods,                                  // tp_methods
    0,                                            // tp_members
    PNG_getset,                                   // tp_getset
    0,                                            // tp_base
    0,                                            // tp_dict
    0,                                            // tp_descr_get
    0,                                            // tp_descr_set
    0,                                            // tp_dictoffset
    reinterpret_cast<initproc>(PNG_init),         // tp_init
    0,                                            // tp_alloc
    PyType_GenericNew,                            // tp_new
};
