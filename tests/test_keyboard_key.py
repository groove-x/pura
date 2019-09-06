from pura import KeyboardKey


def test_key():
    a = KeyboardKey('a')
    a2 = KeyboardKey('a')
    a_alt = KeyboardKey('a', alt_modifier=True)
    b = KeyboardKey('b')

    assert a == a2
    assert a == 'a'
    assert str(a) == 'a'

    assert a != a_alt

    assert a < b
    assert a < 'b'
