/*
 * _zopfli/_zopflimodule.h
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

#ifndef ZOPFLIPY_H
#define ZOPFLIPY_H

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <structmember.h>
#ifdef WITH_THREAD
# include <pythread.h>
#endif

#ifdef __cplusplus
extern "C" {
#endif /* __cplusplus */


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


extern PyTypeObject Compressor_Type;

extern PyTypeObject Deflater_Type;

extern PyTypeObject PNG_Type;


#ifdef __cplusplus
}
#endif /* __cplusplus */

#endif /* ZOPFLIPY_H */
