#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun 13 16:24:17 2019

@author: ggaregnani
"""

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()


setuptools.setup(
    name="resutils",
    version="0.0.1",
    author="Giulia Garegnani",
    author_email="giuliagaregnani@gmail.com",
    description="Useful functions for Solar and Wind module",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/HotMaps/resutils.git",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: Apache License :: 2.0",
        "Operating System :: OS Independent",
    ],
    install_requires=["numpy", "pandas", "gdal", "pint", "matplotlib"],
)
