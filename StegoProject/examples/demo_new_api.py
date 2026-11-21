"""Round-trip demo of the stego.py API on the bundled sample files.

Run from this folder:  python demo_new_api.py
"""
import stego

SECRET = "I have a pen."

print("== Image ==")
stego.Image("pic.png").using("R:2 G:1 B:2").hide(SECRET).save("out_pic.png")
print(" reveal:", repr(stego.Image("out_pic.png").using("R:2 G:1 B:2").reveal()))

print("== Image (one-liner + custom order) ==")
stego.hide("pic.png", SECRET, out="out_pic2.png", channels="R:2 G:1 B:2", order="121")
print(" reveal:", repr(stego.reveal("out_pic2.png", channels="R:2 G:1 B:2", order="121")))

print("== Audio ==")
f = stego.Audio("svega.wav").using("1 2 1").hide(SECRET).save("out_svega.wav")
print(" wrote:", f)
print(" reveal:", repr(stego.Audio("out_svega.wav").using("1 2 1").reveal()))

print("== Network ==")
stego.Network("P2300.pcap").using("IPv6(hlim:8, plen:16)").hide(SECRET).save("out_P2300.pcap")
print(" reveal:", repr(stego.Network("out_P2300.pcap").using("IPv6(hlim:8, plen:16)").reveal()))

print("== bytes payload (non-text) ==")
blob = bytes(range(16))
stego.Image("pic.png").using("R:2 G:1 B:2").hide(blob).save("out_blob.png")
got = stego.Image("out_blob.png").using("R:2 G:1 B:2").reveal(as_text=False)
print(" match:", got == blob)
