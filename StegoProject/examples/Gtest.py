"""Image steganography test — new stego.py API.

Usage:  python Gtest.py <cover.png> <secret_file>
"""
import sys
import stego

cover, secret_path = sys.argv[1], sys.argv[2]
secret = open(secret_path, "rb").read()          # hide the raw bytes

CHANNELS = "R:2 G:1 B:2"                          # last 2/1/2 bits of R/G/B
ORDER = "12"                                      # hop R, G, R, G, ...

stego.Image(cover).using(CHANNELS, order=ORDER).hide(secret).save("New" + cover)

recovered = stego.Image("New" + cover).using(CHANNELS, order=ORDER).reveal(as_text=False)
print("hidden :", len(secret), "bytes")
print("match  :", recovered == secret)
print("as text:", recovered.decode("utf-8", "replace"))
