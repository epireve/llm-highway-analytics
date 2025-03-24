#!/usr/bin/env python

import pocketbase

print("Checking pocketbase.errors module:")
for item in dir(pocketbase.errors):
    if not item.startswith("__"):
        print(f"- {item}")

# Try to import all error classes
for error_class in dir(pocketbase.errors):
    if not error_class.startswith("__"):
        print(f"\nDetails for {error_class}:")
        error_obj = getattr(pocketbase.errors, error_class)
        print(f"  Type: {type(error_obj)}")
        if hasattr(error_obj, "__doc__"):
            print(f"  Doc: {error_obj.__doc__}")
