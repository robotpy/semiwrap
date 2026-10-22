import pytest

from swtest import ft


@pytest.mark.parametrize("prefix", ["", "v_"])
def test_buffer_roundtrip(prefix):
    buffers = ft.Buffers()
    getattr(buffers, prefix + "set_buffer")(b"hello")
    output = bytearray(5)
    assert getattr(buffers, prefix + "get_buffer1")(output) == 5
    assert output == b"hello"
    output = bytearray(3)
    assert getattr(buffers, prefix + "get_buffer2")(output) == 3
    assert output == b"hel"
    with pytest.raises(BufferError):
        getattr(buffers, prefix + "get_buffer1")(b"readonly")


def test_shared_buffer_length():
    buffers = ft.Buffers()
    output = bytearray(3)
    assert buffers.inout_buffer(b"abc", output) == 3
    assert output == b"bcd"
