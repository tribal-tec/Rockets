# Rockets

The rockets package provides a python API to the Rockets websocket server.

## Documentation

Rockets documentation is built and hosted on [readthedocs](https://readthedocs.org/).

* [latest snapshot](http://rockets.readthedocs.org/en/latest/)
* [latest release](http://rockets.readthedocs.org/en/stable/)

## Installation

It is recommended that you use [`pip`](https://pip.pypa.io/en/stable/) to install
`Rockets` into a [`virtualenv`](https://virtualenv.pypa.io/en/stable/). The following
assumes a `virtualenv` named `venv` has been set up and
activated. We will see three ways to install `Rockets`


### 1. From the Python Package Index

```
(venv)$ pip install rockets
```

### 2. From git repository

```
(venv)$ pip install git+https://github.com/Rockets/Rockets.git#subdirectory=python
```

### 3. From source

Clone the repository and install it:

```
(venv)$ git clone https://github.com/Rockets/Rockets.git
(venv)$ pip install -e ./Rockets/python
```

This installs `Rockets` into your `virtualenv` in "editable" mode. That means changes
made to the source code are seen by the installation. To install in read-only mode, omit
the `-e`.

## Connect to running Rockets instance

```python
>>> from rockets import Client

>>> rockets = Client('localhost:8200')
>>> print(rockets)
Rockets client version 0.7.0.c52dd4b running on http://localhost:8200/
```

## Examples

Please find some examples how to interact with Rockets from python on
[`Read the Docs`](https://rockets.readthedocs.io/en/latest/examples.html).
