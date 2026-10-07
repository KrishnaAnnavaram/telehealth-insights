import pytest

from telehealth_insights.codebook import load
from telehealth_insights.decode import decode
from telehealth_insights.synthetic import generate


@pytest.fixture(scope="session")
def book():
    return load()


@pytest.fixture(scope="session")
def raw():
    return generate(3000, seed=7)


@pytest.fixture(scope="session")
def decoded(raw, book):
    return decode(raw, book)
