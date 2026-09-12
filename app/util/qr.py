# SPDX-License-Identifier: MIT
# Copyright (c) 2024 Collegiate Cyber Defense Club
import io

import segno


def membership_qr_png(user_id: str) -> bytes:
    """
    Render a member's QR code as a PNG.

    Encodes the bare membership UUID, exactly like the profile page and the
    wallet passes, so the door scanner accepts it unchanged.
    """
    buf = io.BytesIO()
    segno.make(user_id, error="m").save(buf, kind="png", scale=8, border=2)
    return buf.getvalue()
