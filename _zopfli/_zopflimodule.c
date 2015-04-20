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

#include "zopfli/zopfli.h"


#define MODULE "_zopfli"


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

    RETURN_MODULE(m);
err:
    RETURN_MODULE(NULL);
}
