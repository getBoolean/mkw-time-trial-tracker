from setuptools import setup, Extension
import os

# Platform-specific compiler flags
extra_compile_args = []
extra_link_args = []
libraries = []
define_macros = []

if os.name == "nt":
    # MSVC flags; require C++17 for newer Windows SDK GDI+ headers
    extra_compile_args.extend(["/O2", "/std:c++17"])
    # Link GDI+ for fast PNG loading on Windows only
    libraries.append("gdiplus")
else:
    # GCC/Clang flags for Linux/macOS
    extra_compile_args.extend(["-O3", "-std=c++17"])

ext_modules = [
    Extension(
        "lapimg",
        sources=["fast_lapimg/lapimg.cpp"],
        extra_compile_args=extra_compile_args,
        extra_link_args=extra_link_args,
        libraries=libraries,
        define_macros=define_macros,
        # language is inferred from .cpp, but being explicit is harmless
        language="c++",
    )
]

setup(
    name="lapimg",
    version="0.1.0",
    description="Fast lap image composition",
    ext_modules=ext_modules,
)
