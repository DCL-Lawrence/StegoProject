"""Audio steganography test — new stego.py API.

Usage:  python Atest.py <cover.wav> <secret_file>
"""
import sys
import stego

cover, secret_path = sys.argv[1], sys.argv[2]
secret = open(secret_path, "rb").read()

CHANNELS = "1 2 1"                                # 1/2/1 bits on three channels
ORDER = "213"                                     # hop channel 2, 1, 3, ...

stego.Audio(cover).using(CHANNELS, order=ORDER).hide(secret).save("New" + cover)

recovered = stego.Audio("New" + cover).using(CHANNELS, order=ORDER).reveal(as_text=False)
print("hidden :", len(secret), "bytes")
print("match  :", recovered == secret)
print("as text:", recovered.decode("utf-8", "replace"))
