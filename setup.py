from setuptools import setup, find_packages
import io
import os

VERSION = "0.1.0"


def get_long_description():
    with io.open(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md"),
            encoding="utf8",
    ) as fp:
        return fp.read()


setup(
    name="warcdb",
    description="WarcDB: Web crawl data as SQLite databases",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    author="Florents Tselai",
    author_email="florents@tselai.com",
    version=VERSION,
    license="Apache License, Version 2.0",
    packages=["warcdb"],
    install_requires=[
        "sqlite-utils==3.26.1",
        "warcio==1.7.4",
        "click==8.1.3",
        "more-itertools",
        "tqdm"
    ],
    extras_require={"test": ["pytest"]},
    entry_points="""
        [console_scripts]
        warcdb=warcdb:warcdb_cli
    """,
    url="https://github.com/Florents-Tselai/warcdb",
    project_urls={
        "Source code": "https://github.com/Florents-Tselai/warcdb",
        "Issues": "https://github.com/Florents-Tselai/warcdb/issues",
        "CI": "https://github.com/Florents-Tselai/warcdb/actions",
    },
    python_requires=">=3.6",
    classifiers=[
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ]
)
