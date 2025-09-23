from setuptools import setup, Extension
import os

extra_compile_args = ["-O3"]
libraries = []
define_macros = []

if os.name == "nt":
    # Link GDI+ for fast PNG loading
    libraries.append("gdiplus")

ext_modules = [
    Extension(
        "lapimg",
        sources=["fast_lapimg/lapimg.cpp"],
        extra_compile_args=extra_compile_args,
        libraries=libraries,
        define_macros=define_macros,
    )
]

setup(
    name="lapimg",
    version="0.1.0",
    description="Fast lap image composition",
    ext_modules=ext_modules,
)
