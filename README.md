# Base16 Hex Pair

Encodes bytes to a lowercase hexadecimal string and decodes hex pairs back to bytes, ignoring ASCII whitespace and validating character ranges.

## Usage

```python
from base16_hex_pair import encode, decode, DecodeError

encoded = encode(b"Hello")      # '48656c6c6f'
decoded = decode("48 65 6c 6c 6f")  # b'Hello'

try:
    decode("zz")
except DecodeError as exc:
    print(f"bad hex: {exc}")
```

`encode(data: bytes) -> str` — returns lowercase hex. Accepts `bytes`, `bytearray`, `memoryview`.

`decode(text: str) -> bytes` — accepts upper- and lowercase hex, ignores ASCII whitespace (space, tab, newline, CR, form feed, vertical tab). Raises `DecodeError` (a `ValueError` subclass) on invalid characters or an odd number of hex digits.

## Why this exists

The standard library has `bytes.hex()` and `bytes.fromhex()`, but they sit on `bytes` and behave slightly differently: `fromhex` accepts spaces but not other whitespace, and the error type is a bare `ValueError`. This library gives a small, symmetric pair of functions with a named exception type and consistent whitespace handling, so callers can catch decode failures precisely without parsing error strings.

The trade-off: `decode` is permissive about whitespace but strict about everything else. It will not strip `0x` prefixes, colons, or dashes. Silent punctuation stripping turns typos into valid data; if you have a delimited format, strip the delimiters yourself before calling `decode`.

## Awkward edge

An odd number of hex digits after stripping whitespace is an error — the library will not guess whether the missing nibble was the high or low half of the final byte. If your input is a single nibble (e.g. `"f"`), pad it to `"0f"` or `"f0"` explicitly before decoding.
