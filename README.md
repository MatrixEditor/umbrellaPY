# umbrella-py 🚧

[![python](https://img.shields.io/badge/python-3.11+-blue.svg?logo=python&labelColor=grey)](https://www.python.org/downloads/)
![Codestyle](https://img.shields.io:/static/v1?label=Codestyle&message=black&color=black)
![License](https://img.shields.io:/static/v1?label=License&message=Apache+v2.0&color=blue)
[![PyPI](https://img.shields.io/pypi/v/umbrella-py)](https://pypi.org/project/umbrella-py/)

![Status](https://img.shields.io:/static/v1?label=Status&message=Under%20Construction&color=teal)

Pure Python implementation for the Umbrella project - a tool to instpect static
runtime information of Objective-C and Swift binaries. As of now, MachO and PE
binaries will be accepted by the API. There is also support for parsing Java
class files.

**Plase follow the [documentation](https://matrixeditor.github.io/umbrella-py/)
for more details on how to use this library. Python 3.12 support is in preparation and will be published as soon as LIEF
uploads wheels for 3.12.**

## Installation

To install the Python package you can use pip:

```shell
pip install umbrella-py
# or
pip install git+https://github.com/MatrixEditor/umbrella-py.git
```

The documentation can be build using Make and required dependencies defined in
`docs/requirements.txt`:

```shell
pip install -r docs/requirements.txt && cd docs && make html
```

## License

Distributed under the Apache 2.0 License. See LICENSE for more information.