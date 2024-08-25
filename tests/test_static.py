# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
import os
import sys

from fastapi.testclient import TestClient

# Add the project root to the PYTHONPATH
import app.main
from app.main import app

client = TestClient(app)


def test_get_static():
    test_files = [
        "admin.js",
        "admin_logo.svg",
        "apple_wallet.svg",
        "favicon.ico",
        "favicon.svg",
        "form.js",
        "hackucf.css",
        "index.html",
        "lib/qr-scanner.umd.min.js",
        "lib/qr-scanner.min.js",
        "lib/qr-scanner-worker.min.js",
        "qr_hack_dark.svg",
        "qr_hack_light.svg",
    ]
    for file in test_files:
        get_static = client.get("/static/" + file)
        assert get_static.status_code == 200, f"Failed to retrieve file: {file}"
