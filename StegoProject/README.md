# StegoTool

## Introduction
This is a function library that implements image, audio and network-header
steganography. Add the package to the project you want to use it in. Each
carrier type has its own class — `Graph` (image), `Audio` (audio) and
`Stream` (network headers).

There are two ways to call it:

- **`stego` (recommended)** — a small, uniform wrapper. Every carrier is
  driven the same way: `using()` → `hide()` → `save()`, and `reveal()`.
  It takes `str`/`bytes` directly and gives the exact message back.
- **`StegoTool` (low level)** — the underlying engine classes, if you need
  fine-grained control. Documented further down.

------

## Files in this package
```
StegoTool/          the engine (original code, only comment typos fixed)
  Graph.py            image steganography
  Audio.py            audio steganography
  Stream.py           network-header steganography
  Analysis.py         Chi-square + R/S steganalysis
  __init__.py
setup.py            packaging metadata (unchanged original)
README.md           this file
examples/           everything you need to run it, kept together
  stego.py            NEW: the clean wrapper API (recommended entry point)
  Gtest.py            test script, image   — rewritten to use stego.py
  Atest.py            test script, audio   — rewritten to use stego.py
  Ptest.py            test script, network — rewritten to use stego.py
  demo_new_api.py     runnable demo of all three carriers + one-liners
  pic.png             sample cover image
  svega.wav           sample cover audio
  P2300.pcap          sample cover capture
  secret.txt          sample secret message
```
Run a test straight away (from the `examples/` folder):
```bash
cd examples
python Gtest.py pic.png secret.txt
python Atest.py svega.wav secret.txt
python Ptest.py P2300.pcap secret.txt
python demo_new_api.py
```
`stego.py` locates the `StegoTool/` engine in the parent folder automatically,
so the scripts run from `examples/` without any extra setup.

Requires: `opencv-python`, `scapy`, `scipy`, `numpy`.

------

## Quick start (the `stego` wrapper)

```python
import stego

# Hide, then read back — identical calls for all three carriers.
stego.Image("pic.png").using("R:2 G:1 B:2").hide("I have a pen.").save("Newpic.png")
msg = stego.Image("Newpic.png").using("R:2 G:1 B:2").reveal()        # -> "I have a pen."

stego.Audio("in.wav").using("1 2 1").hide("I have a pen.").save("out.wav")
stego.Audio("out.wav").using("1 2 1").reveal()

stego.Network("in.pcap").using("IPv6(hlim:8, plen:16)").hide("I have a pen.").save("out.pcap")
stego.Network("out.pcap").using("IPv6(hlim:8, plen:16)").reveal()
```

One-liners for the simple case:

```python
stego.hide("pic.png", "I have a pen.", out="Newpic.png", channels="R:2 G:1 B:2")
stego.reveal("Newpic.png", channels="R:2 G:1 B:2")                   # -> "I have a pen."
```

Notes:
- `hide()` accepts a `str` or `bytes`; `reveal()` returns a `str` (or `bytes`
  for non-text payloads, or when you pass `reveal(as_text=False)`).
- A length header is embedded automatically, so `reveal()` returns exactly the
  message — no trailing garbage.
- The channel hopping order defaults to natural order `1..N`. Pass
  `order="121"` (etc.) to customise it.

### Channel / bit specification
- **Image:** `"R:2 G:1 B:2"` — last 2 bits of red, 1 bit of green, 2 bits of
  blue. Separators are flexible (`"R2/G1/B2"` also works). Max 2 bits each.
- **Audio:** `"1 2 1"` — 1 bit on channel 1, 2 bits on channel 2, 1 bit on
  channel 3. Max 2 bits each.
- **Network:** `"IPv6(hlim:8, plen:16)"` — 8 bits in Hop Limit, 16 bits in
  Payload Length of the IPv6 header.

------

## Low-level API (`StegoTool` classes)

Use these only if you need direct control; otherwise prefer `stego` above.

### Import
```python
from StegoTool import Graph    # image
from StegoTool import Audio    # audio
from StegoTool import Stream   # network header
```

### Initialization
Declare a variable for each method. The constructor argument is a file path of
the matching type (`.png`, `.wav`, `.pcap`).
```python
image  = Graph("in.png")
audio  = Audio("in.wav")
stream = Stream("in.pcap")
```

### Select target channels and bits
```python
image.select("R:2 / G:1 / B:1")        # last 2 bits of red, 1 bit of green/blue
audio.select("121")                    # 1/2/1 bits on channels 1/2/3
stream.select("IPv6(hlim:8, plen:16)") # 8 bits Hop Limit, 16 bits Payload Length
```

### Hide data
The low-level `create()` expects a **binary string** and a channel hopping
sequence. (The `stego` wrapper does this encoding for you.)
```python
bits = "".join(f"{b:08b}" for b in b"I have a pen.")   # text -> bit string
image.create("12", bits)                               # hop channel 1, 2, 1, 2, ...
audio.create("213", bits)
stream.create("12", bits)
```

### Export stego files
```python
image.save_image("out.png")
audio.save_audio("out.wav")
stream.save_pcap("out.pcap")
```

### Extract data
`get()` returns the raw bit string read across the whole carrier, so you must
know the message length to slice it back out and decode it yourself.
```python
bits = image.get("12")
bits = stream.get("12")

# Audio also needs the exported channel file list before extracting:
audio.select_audio_list(["out1.wav", "out2.wav", "out3.wav"])
bits = audio.get("213")
```

------

## Steganalysis tools
StegoTool also provides steganalysis APIs to detect the existence of hidden
data. The current version includes the Chi-square test and the Rescaled Range
(R/S) test.
```python
from StegoTool import ChiSquare, RS
```
