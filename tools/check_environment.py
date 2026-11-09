"""Offline development-environment check; no clients, credentials or API calls."""

import importlib.metadata
import sys

import openai


if __name__ == "__main__":
    assert sys.version_info >= (3, 11), "Python 3.11+ is required"
    print("Python", sys.version.split()[0])
    print("openai", openai.__version__)
    for name in ("jsonschema", "referencing", "rfc3339-validator"):
        print(name, importlib.metadata.version(name))
