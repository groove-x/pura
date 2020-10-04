from collections.abc import Hashable

import pytest

from pura._web_view import _canvas_color, Color


@pytest.mark.parametrize("test_input,expected_rgba", [
    ((5,), (5, 5, 5, 255)),  # gray
    ((5, 30), (5, 5, 5, 30)),  # gray, alpha
    ((5, 10, 20), (5, 10, 20, 255)),  # r, g, b
    ((5, 10, 20, 30), (5, 10, 20, 30)),  # r, g, b, a
    ((Color(5, 10, 20), 30), (5, 10, 20, 30)),  # non_alpha_color_obj, alpha
])
def test_color(test_input, expected_rgba):
    c = Color(*test_input)
    assert (c.r, c.g, c.b, c.a) == expected_rgba


def test_color_hashable():
    assert isinstance(Color(255), Hashable)
    assert Color(128) == Color(128, 128, 128) == Color(128, 128, 128, 255)


def test_color_alpha_mix():
    assert Color(Color(5, 10, 20, 30), 40) == Color(5, 10, 20, 30 * 40 // 255)


@pytest.mark.parametrize("test_input,expected", [
    ((0xaa, 0xbb, 0xcc), '#AABBCC'),
    ((0xaa, 0xbb, 0xcc, 0xdd), '#AABBCCDD'),
    ((0xef,), '#EFEFEF'),
    ((0xef, 0xdd), '#EFEFEFDD'),
])
def test_color_js_string(test_input, expected):
    assert Color(*test_input).js_string() == expected


@pytest.mark.parametrize("test_input,expected", [
    ((0xaa, 0xbb, 0xcc), '#AABBCC'),
    ((0xaa, 0xbb, 0xcc, 0xdd), '#AABBCCDD'),
    ((0xef,), '#EFEFEF'),
    ((0xef, 0xdd), '#EFEFEFDD'),
    ((Color(0xaa, 0xbb, 0xcc),), '#AABBCC'),
])
def test_canvas_color(test_input, expected):
    assert _canvas_color(*test_input) == expected
