"""Network-header steganography test — new stego.py API.

Usage:  python Ptest.py <cover.pcap> <secret_file>
"""
import sys
import stego

cover, secret_path = sys.argv[1], sys.argv[2]
secret = open(secret_path, "rb").read()

CHANNELS = "IPv6(hlim:8, plen:16)"               # 8 bits Hop Limit, 16 bits Payload Len
ORDER = "12"                                     # hop field 1, 2, 1, 2, ...

stego.Network(cover).using(CHANNELS, order=ORDER).hide(secret).save("New" + cover)

recovered = stego.Network("New" + cover).using(CHANNELS, order=ORDER).reveal(as_text=False)
print("hidden :", len(secret), "bytes")
print("match  :", recovered == secret)
print("as text:", recovered.decode("utf-8", "replace"))
