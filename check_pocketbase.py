#!/usr/bin/env python

import pocketbase

print("PocketBase module version:", pocketbase.__version__)
print("\nContents of pocketbase module:")
for item in dir(pocketbase):
    if not item.startswith("__"):
        print(f"- {item}")

print("\nChecking PocketBase class:")
client = pocketbase.PocketBase("http://127.0.0.1:8090")
print("\nMethods of PocketBase client:")
for item in dir(client):
    if not item.startswith("__"):
        print(f"- {item}")
