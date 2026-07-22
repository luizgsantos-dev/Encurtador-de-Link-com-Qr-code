import io

import qrcode
import qrcode.image.svg


def generate_qrcode_png(data: str) -> bytes:
    img = qrcode.make(data, box_size=10, border=2)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def generate_qrcode_svg(data: str) -> bytes:
    factory = qrcode.image.svg.SvgPathImage
    img = qrcode.make(data, image_factory=factory, box_size=10, border=2)
    buffer = io.BytesIO()
    img.save(buffer)
    return buffer.getvalue()
