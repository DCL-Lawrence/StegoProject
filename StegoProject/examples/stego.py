"""
stego.py — a clean calling interface on top of StegoTool.

It does NOT replace StegoTool's engine (Graph / Audio / Stream). It is a thin
facade that makes the three carriers behave the same way and removes the
boilerplate the original API forced onto every caller.

--------------------------------------------------------------------------
WHY  (what the old calling style made you write)
--------------------------------------------------------------------------
    from StegoTool import Graph

    data = "I have a pen."
    d = ""
    for i in range(len(data)):            # 1. hand-roll text -> bitstring
        d += bin(ord(data[i]))[2:].zfill(8)

    img = Graph("pic.png")
    img.select("R:2 / G:1 / B:2")         # 2. select() DSL differs per carrier
    img.create("12", d)                   # 3. "12" hopping-order is required
    img.save_image("Newpic.png")          # 4. save name differs per carrier

    bits = img.get("12")                  # 5. returns the WHOLE carrier's bits
    #     -> you must already know the length to slice the message back out,
    #        then hand-decode bits -> text yourself.

--------------------------------------------------------------------------
NOW  (same thing, every carrier, no boilerplate)
--------------------------------------------------------------------------
    import stego

    stego.Image("pic.png").using("R:2 G:1 B:2").hide("I have a pen.").save("Newpic.png")
    msg = stego.Image("Newpic.png").using("R:2 G:1 B:2").reveal()
    #     -> "I have a pen."   (exact message, decoded, nothing trailing)

    # or the one-liners:
    stego.hide("pic.png", "I have a pen.", out="Newpic.png", channels="R:2 G:1 B:2")
    msg = stego.reveal("Newpic.png", channels="R:2 G:1 B:2")

The same four calls work for Audio and Network:

    stego.Audio("in.wav").using("1 2 1").hide(secret).save("out.wav")
    stego.Audio("out.wav").using("1 2 1").reveal()

    stego.Network("in.pcap").using("IPv6(hlim:8, plen:16)").hide(secret).save("out.pcap")
    stego.Network("out.pcap").using("IPv6(hlim:8, plen:16)").reveal()

What the facade adds:
  * hide() accepts str or bytes; reveal() returns str (or bytes) — no manual
    bit juggling.
  * a 32-bit length header is embedded automatically, so reveal() returns
    exactly the message and stops, instead of the whole carrier's low bits.
  * one consistent verb set: using() -> hide() -> save(), and reveal().
  * the channel hopping order is optional (defaults to natural order 1..N).
  * Audio's multi-file quirk is handled for you by save()/reveal().
"""

from __future__ import annotations

import os
import re
import sys
from typing import List, Union

# Make the StegoTool engine importable whether it sits next to this file or one
# folder up (this file ships inside examples/, with StegoTool/ in the parent).
for _p in (os.path.dirname(os.path.abspath(__file__)),
           os.path.dirname(os.path.dirname(os.path.abspath(__file__)))):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from StegoTool import Graph as _Graph
from StegoTool import Audio as _Audio
from StegoTool import Stream as _Stream

Message = Union[str, bytes, bytearray]

_HEADER_BITS = 32  # unsigned big-endian byte-length prefix


class StegoError(Exception):
    """Raised for configuration / capacity / extraction problems."""


# --------------------------------------------------------------------------- #
# payload encoding: <32-bit length><message bytes>  <-> bitstring
# --------------------------------------------------------------------------- #
def _bytes_to_bits(data: bytes) -> str:
    return "".join(f"{b:08b}" for b in data)


def _bits_to_bytes(bits: str) -> bytes:
    usable = len(bits) - (len(bits) % 8)
    return bytes(int(bits[i:i + 8], 2) for i in range(0, usable, 8))


def _encode_payload(message: Message) -> str:
    if isinstance(message, str):
        data = message.encode("utf-8")
    elif isinstance(message, (bytes, bytearray)):
        data = bytes(message)
    else:
        raise TypeError("message must be str or bytes")
    if len(data) >= (1 << _HEADER_BITS):
        raise StegoError("message too large to length-prefix")
    return f"{len(data):0{_HEADER_BITS}b}" + _bytes_to_bits(data)


def _decode_payload(bits: str, as_text: bool = True) -> Message:
    if len(bits) < _HEADER_BITS:
        raise StegoError("no stego header found in carrier")
    n = int(bits[:_HEADER_BITS], 2)
    body = bits[_HEADER_BITS:_HEADER_BITS + n * 8]
    if len(body) < n * 8:
        raise StegoError(
            f"carrier truncated: header claims {n} bytes but only "
            f"{len(body) // 8} are present"
        )
    data = _bits_to_bytes(body)
    if as_text:
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data  # fall back to raw bytes for non-text payloads
    return data


# --------------------------------------------------------------------------- #
# shared behaviour
# --------------------------------------------------------------------------- #
class _Carrier:
    """Common fluent interface. Subclasses adapt one StegoTool engine."""

    def __init__(self, path: str):
        self.path = path
        self._engine = self._make_engine(path)
        self._order: str = ""
        self._nchan: int = 0
        self._configured = False

    # ---- to be provided by subclasses -----------------------------------
    def _make_engine(self, path: str):
        raise NotImplementedError

    def _configure(self, spec: str) -> int:
        """Call engine.select(...); return the number of channels/fields."""
        raise NotImplementedError

    def _save(self, path: str):
        raise NotImplementedError

    def _read_bits(self) -> str:
        return self._engine.get(self._order)

    # ---- fluent public API ----------------------------------------------
    def using(self, channels: str, order: str = None) -> "_Carrier":
        """Choose channels/bits, and optionally a hopping order (default 1..N)."""
        self._nchan = self._configure(channels)
        self._configured = True
        if order is None:
            order = "".join(str(i + 1) for i in range(self._nchan))
        self._validate_order(order)
        self._order = order
        return self

    def hide(self, message: Message) -> "_Carrier":
        self._require_config()
        bits = _encode_payload(message)
        try:
            self._engine.create(self._order, bits)
        except RuntimeError as exc:  # engine's "data too long" error
            raise StegoError(str(exc)) from None
        return self

    def reveal(self, as_text: bool = True) -> Message:
        self._require_config()
        return _decode_payload(self._read_bits(), as_text=as_text)

    def save(self, path: str):
        self._require_config()
        return self._save(path)

    # ---- helpers ---------------------------------------------------------
    def _require_config(self):
        if not self._configured:
            raise StegoError("call .using(...) before hide()/reveal()/save()")

    def _validate_order(self, order: str):
        if not order or not order.isdigit():
            raise StegoError(f"order must be digits, got {order!r}")
        if any(not (1 <= int(ch) <= self._nchan) for ch in order):
            raise StegoError(
                f"order {order!r} references a channel outside 1..{self._nchan}"
            )


# --------------------------------------------------------------------------- #
# Image
# --------------------------------------------------------------------------- #
class Image(_Carrier):
    """LSB steganography in an image (.png/.bmp/...). Wraps StegoTool.Graph."""

    def _make_engine(self, path):
        return _Graph(path)

    def _configure(self, spec: str) -> int:
        # Accept "R:2 G:1 B:2", "R2/G1/B2", "r:2, g:1, b:2" ...
        toks = re.findall(r"([RGBrgb])\D*([0-2])", spec)
        if not toks:
            raise StegoError("channel spec should look like 'R:2 G:1 B:2'")
        self._engine.select(" / ".join(f"{c.upper()}:{n}" for c, n in toks))
        return len(toks)

    def _save(self, path: str) -> str:
        self._engine.save_image(path)
        return path


# --------------------------------------------------------------------------- #
# Audio  (StegoTool.Audio writes one file per channel; handled here)
# --------------------------------------------------------------------------- #
class Audio(_Carrier):
    """LSB steganography in a .wav. Wraps StegoTool.Audio."""

    def _make_engine(self, path):
        return _Audio(path)

    def _configure(self, spec: str) -> int:
        digits = re.sub(r"\D", "", spec)  # "1 2 1" -> "121"
        if not digits:
            raise StegoError("audio spec should be per-channel bit counts, e.g. '1 2 1'")
        self._engine.select(digits)
        return len(digits)

    def _save(self, path: str) -> str:
        # StegoTool.Audio hides every channel into one shared sample buffer,
        # so a single .wav holds the whole message. We write one file (like the
        # image/network carriers) instead of leaking N near-identical files.
        from scipy.io import wavfile
        wavfile.write(path, self._engine.rate, self._engine.sounds[0])
        return path

    def reveal(self, as_text: bool = True, files: List[str] = None) -> Message:
        self._require_config()
        # feed the one saved file in for each selected channel
        files = files or [self.path] * self._nchan
        self._engine.select_audio_list(files)
        return _decode_payload(self._engine.get(self._order), as_text=as_text)


# --------------------------------------------------------------------------- #
# Network
# --------------------------------------------------------------------------- #
class Network(_Carrier):
    """Header steganography in a .pcap. Wraps StegoTool.Stream."""

    def _make_engine(self, path):
        return _Stream(path)

    def _configure(self, spec: str) -> int:
        self._engine.select(spec)  # e.g. "IPv6(hlim:8, plen:16)"
        if not self._engine.nbits:
            raise StegoError(f"no usable fields parsed from {spec!r}")
        return len(self._engine.nbits)

    def _save(self, path: str) -> str:
        self._engine.save_pcap(path)
        return path


# --------------------------------------------------------------------------- #
# one-liners
# --------------------------------------------------------------------------- #
_BY_EXT = {
    ".png": Image, ".bmp": Image, ".tif": Image, ".tiff": Image,
    ".jpg": Image, ".jpeg": Image,
    ".wav": Audio,
    ".pcap": Network, ".pcapng": Network,
}


def _open(path: str, kind: str = None) -> _Carrier:
    if kind:
        cls = {"image": Image, "audio": Audio, "network": Network}[kind.lower()]
    else:
        ext = re.search(r"(\.[A-Za-z0-9]+)$", path)
        cls = _BY_EXT.get(ext.group(1).lower()) if ext else None
        if cls is None:
            raise StegoError(f"cannot infer carrier type from {path!r}; pass kind=")
    return cls(path)


def hide(carrier: str, message: Message, out: str,
         channels: str, order: str = None, kind: str = None):
    """Hide `message` in `carrier` and write the stego file(s) to `out`."""
    return _open(carrier, kind).using(channels, order).hide(message).save(out)


def reveal(carrier: str, channels: str, order: str = None,
           kind: str = None, as_text: bool = True) -> Message:
    """Extract and return the message hidden in `carrier`."""
    return _open(carrier, kind).using(channels, order).reveal(as_text=as_text)
