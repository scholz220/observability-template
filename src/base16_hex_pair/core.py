"""Core encode/decode for Base16 hex pairs.

Design decisions (stated plainly so the tests and README agree):

- encode() returns a lowercase str. Lowercase is the canonical form for hex
  digests in Python (see hashlib.hexdigest) and avoids the ambiguity of
  accepting both cases on round-trip.
- decode() accepts a str, ignores all ASCII whitespace (space, tab, newline,
  carriage return, form feed, vertical tab) so that wrapped or indented hex
  blobs round-trip cleanly, and requires an even number of hex digits after
  stripping. A trailing nibble is an error, not a guess.
- decode() accepts both upper- and lowercase hex digits. encode() always
  emits lowercase; decode() is permissive on input because real-world hex
  blobs are often uppercase (e.g. PEM-adjacent formats, certificate
  fingerprints).
- Non-hex characters (including '0x' prefixes, colons, dashes) are errors.
  We do not strip punctuation because doing so silently turns typos into
  valid data. If you have a colon-separated MAC address, strip the colons
  yourself; the library will not guess.
- decode(b'') returns b''. encode(b'') returns ''. Empty in, empty out.
"""

from __future__ import annotations

__all__ = ["encode", "decode", "DecodeError"]


class DecodeError(ValueError):
    """Raised when a hex string cannot be decoded to bytes.

    Subclassing ValueError keeps the exception hierarchy familiar: callers
    who already catch ValueError for malformed input keep working, while those
    who want precision can catch DecodeError specifically.
    """


# Precomputed lookup table mapping byte values 0-255 to hex digit values.
# -1 marks an invalid hex digit. Indexed directly by ord(ch); covers both
# upper- and lowercase so decode() does a single lookup per character.
_HEX_VALUES: tuple[int, ...] = tuple(
    [
        -1
        if i < ord("0")
        else (i - ord("0"))
        if i <= ord("9")
        else -1
        if i < ord("A")
        else (i - ord("A") + 10)
        if i <= ord("F")
        else -1
        if i < ord("a")
        else (i - ord("a") + 10)
        if i <= ord("f")
        else -1
        for i in range(256)
    ]
)

# ASCII whitespace bytes, per str.isspace() for the 0-127 range. We use a
# frozenset of byte values so decode() can check membership in O(1) without
# allocating a set per call.
_WHITESPACE: frozenset[int] = frozenset(b" \t\n\r\x0b\x0c")


def encode(data: bytes) -> str:
    """Encode bytes to a lowercase hexadecimal string.

    Returns a str, not bytes, because hex output is text: it gets printed,
    logged, compared, and pasted into configs. Returning bytes.hex() would
    force every caller to decode again.

    >>> encode(b"\\x00\\xff")
    '00ff'
    """
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError(
            f"encode() expects bytes-like, got {type(data).__name__}"
        )
    # bytes.hex() is implemented in C, handles the full range, and emits
    # lowercase. There is no point reimplementing it.
    return bytes(data).hex()


def decode(text: str) -> bytes:
    """Decode a hexadecimal string to bytes.

    Whitespace is ignored so wrapped blobs round-trip. An odd number of hex
    digits after stripping whitespace is an error: we will not guess whether
    the missing nibble was on the high or low end. Non-hex characters are an
    error; we do not strip '0x', ':', or '-' because silent punctuation
    stripping turns typos into valid data.

    Both upper- and lowercase hex are accepted. encode() always emits
    lowercase; decode() is permissive because uppercase hex is common in the
    wild (certificate fingerprints, MAC addresses, etc.).

    >>> decode("00ff")
    b'\\x00\\xff'
    >>> decode("00 FF\\n")
    b'\\x00\\xff'
    """
    if not isinstance(text, str):
        raise TypeError(f"decode() expects str, got {type(text).__name__}")

    # Fast path: if there's no whitespace and the length is even, we can
    # decode directly without building an intermediate list. This covers the
    # common case where encode()'s output is fed straight back in.
    has_whitespace = False
    for ch in text:
        # We check via the byte value because _HEX_VALUES is indexed by byte
        # value. str.isascii() keeps us in the 0-127 range; non-ASCII chars
        # are caught below as invalid hex.
        if ord(ch) < 128 and ord(ch) in _WHITESPACE:
            has_whitespace = True
            break

    if not has_whitespace:
        if len(text) % 2 != 0:
            raise DecodeError(
                f"odd number of hex digits ({len(text)}): cannot split into pairs"
            )
        try:
            return bytes.fromhex(text)
        except ValueError as exc:
            # bytes.fromhex raises ValueError with a message like
            # "non-hexadecimal number found in fromhex() arg at position N".
            # We re-raise as DecodeError to keep the exception type stable
            # for callers, but preserve the original message for debugging.
            raise DecodeError(str(exc)) from exc

    # Slow path: strip whitespace, then decode. We build a list of kept
    # characters and join at the end — faster than repeated string
    # concatenation and avoids re-scanning.
    kept: list[str] = []
    for ch in text:
        o = ord(ch)
        if o < 128 and o in _WHITESPACE:
            continue
        if o >= len(_HEX_VALUES) or _HEX_VALUES[o] == -1:
            raise DecodeError(
                f"invalid hex character {ch!r} at index {_position(text, ch, kept)}"
            )
        kept.append(ch)

    if len(kept) % 2 != 0:
        raise DecodeError(
            f"odd number of hex digits ({len(kept)}) after stripping whitespace: "
            "cannot split into pairs"
        )

    cleaned = "".join(kept)
    try:
        return bytes.fromhex(cleaned)
    except ValueError as exc:
        # Should not happen — we validated above — but fromhex could still
        # reject in some build. Guard anyway.
        raise DecodeError(str(exc)) from exc


def _position(text: str, ch: str, kept: list[str]) -> int:
    """Find the index in the original text of the invalid character.

    kept is the list of valid characters collected so far; we use its length
    to skip ahead past already-consumed characters. This is only used for
    error messages, so correctness matters more than speed.
    """
    # We scan from the start each time an error is reported. Errors are
    # exceptional, so O(n) here is fine.
    consumed = len(kept)
    seen = 0
    for i, c in enumerate(text):
        o = ord(c)
        if o < 128 and o in _WHITESPACE:
            continue
        if seen == consumed:
            return i
        seen += 1
    return -1
