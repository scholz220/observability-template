import unittest

from base16_hex_pair import encode, decode, DecodeError


class TestEncode(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(encode(b""), "")

    def test_single_byte_zero(self):
        self.assertEqual(encode(b"\x00"), "00")

    def test_single_byte_ff(self):
        self.assertEqual(encode(b"\xff"), "ff")

    def test_known_vector(self):
        # "Hello" -> 48656c6c6f
        self.assertEqual(encode(b"Hello"), "48656c6c6f")

    def test_lowercase_output(self):
        # 0xAB 0xCD 0xEF should come out lowercase
        self.assertEqual(encode(b"\xab\xcd\xef"), "abcdef")

    def test_bytearray_input(self):
        self.assertEqual(encode(bytearray(b"\x01\x02")), "0102")

    def test_memoryview_input(self):
        self.assertEqual(encode(memoryview(b"\x01\x02")), "0102")

    def test_rejects_str(self):
        with self.assertRaises(TypeError):
            encode("not bytes")

    def test_rejects_int(self):
        with self.assertRaises(TypeError):
            encode(42)


class TestDecode(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(decode(""), b"")

    def test_single_pair(self):
        self.assertEqual(decode("00"), b"\x00")

    def test_known_vector(self):
        self.assertEqual(decode("48656c6c6f"), b"Hello")

    def test_uppercase_accepted(self):
        self.assertEqual(decode("ABCDEF"), b"\xab\xcd\xef")

    def test_mixed_case_accepted(self):
        self.assertEqual(decode("AbCdEf"), b"\xab\xcd\xef")

    def test_ignores_spaces(self):
        self.assertEqual(decode("00 ff"), b"\x00\xff")

    def test_ignores_newlines_and_tabs(self):
        self.assertEqual(decode("00\nff\t"), b"\x00\xff")

    def test_ignores_all_whitespace_kinds(self):
        # space, tab, newline, CR, form feed, vertical tab
        self.assertEqual(decode("00 \t\n\r\x0b\x0cff"), b"\x00\xff")

    def test_round_trip(self):
        data = bytes(range(256))
        self.assertEqual(decode(encode(data)), data)

    def test_round_trip_with_whitespace(self):
        data = bytes(range(256))
        hex_str = encode(data)
        # Insert whitespace every 4 chars
        spaced = " ".join(hex_str[i:i + 4] for i in range(0, len(hex_str), 4))
        self.assertEqual(decode(spaced), data)

    def test_odd_length_no_whitespace_is_error(self):
        with self.assertRaises(DecodeError):
            decode("abc")

    def test_odd_length_after_strip_is_error(self):
        with self.assertRaises(DecodeError):
            decode("ab c")

    def test_invalid_character_is_error(self):
        with self.assertRaises(DecodeError):
            decode("00gg")

    def test_colon_not_stripped(self):
        # We deliberately do not strip punctuation.
        with self.assertRaises(DecodeError):
            decode("00:ff")

    def test_0x_prefix_not_stripped(self):
        with self.assertRaises(DecodeError):
            decode("0x00ff")

    def test_rejects_bytes_input(self):
        with self.assertRaises(TypeError):
            decode(b"00ff")

    def test_rejects_int_input(self):
        with self.assertRaises(TypeError):
            decode(42)

    def test_non_ascii_is_error(self):
        with self.assertRaises(DecodeError):
            decode("00\u00e9")

    def test_decode_error_is_value_error(self):
        # Callers catching ValueError should still catch our error.
        try:
            decode("zz")
        except ValueError:
            pass
        else:
            self.fail("DecodeError should be a ValueError")


class TestRoundTrip(unittest.TestCase):
    def test_all_byte_values(self):
        for b in range(256):
            data = bytes([b])
            self.assertEqual(decode(encode(data)), data)

    def test_all_pairs(self):
        for high in range(16):
            for low in range(16):
                pair = f"{high:x}{low:x}"
                self.assertEqual(decode(pair), bytes([high * 16 + low]))


if __name__ == "__main__":
    unittest.main()
