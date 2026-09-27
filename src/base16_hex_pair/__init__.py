"""Base16 Hex Pair: encode bytes to hex, decode hex pairs to bytes."""

from base16_hex_pair.core import encode, decode, DecodeError

__all__ = ["encode", "decode", "DecodeError"]
