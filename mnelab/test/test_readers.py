import pytest

from mnelab.io.readers import split_name_ext, supported


@pytest.mark.parametrize("ext", supported.keys())
def test_split_name_ext(ext):
    fname = f"test{ext}"
    assert split_name_ext(fname) == ("test", ext)


def test_split_name_ext_unsupported():
    assert split_name_ext("test.xxx") is None
