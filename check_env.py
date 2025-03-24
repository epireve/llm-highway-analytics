#!/usr/bin/env python

import os
from dotenv import load_dotenv

# Try loading the .env file
load_dotenv()

# Print all environment variables that start with POCKETBASE
print("Environment variables:")
for key, value in os.environ.items():
    if key.startswith("POCKETBASE"):
        # Mask password for security
        if "PASSWORD" in key:
            value = "*" * len(value)
        print(f"{key}: {value}")

# Try direct access using os.getenv
print("\nDirect access with os.getenv:")
email = os.getenv("POCKETBASE_ADMIN_EMAIL")
password = os.getenv("POCKETBASE_ADMIN_PASSWORD")
url = os.getenv("POCKETBASE_URL")

print(f"POCKETBASE_ADMIN_EMAIL: {email}")
print(f"POCKETBASE_ADMIN_PASSWORD: {'*' * len(password) if password else None}")
print(f"POCKETBASE_URL: {url}")

# Open and print the .env file content for comparison
print("\n.env file content:")
try:
    with open(".env", "r") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#"):
                print(line)
                continue

            # Mask passwords
            if "PASSWORD" in line:
                key, value = line.split("=", 1)
                print(f"{key}={'*' * len(value)}")
            else:
                print(line)
except Exception as e:
    print(f"Error reading .env file: {str(e)}")
