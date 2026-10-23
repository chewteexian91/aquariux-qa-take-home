"""Turns every .feature file under features/ into pytest tests.

New feature files are picked up automatically; no change needed here.
Step code lives in the *_steps.py files registered in tests/conftest.py.
"""
from pytest_bdd import scenarios

# "." is relative to bdd_features_base_dir (features/) in pytest.ini.
scenarios(".")
