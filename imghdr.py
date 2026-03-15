from io import BytesIO
from PIL import Image


def what(file, h=None):
    try:
        if h is not None:
            data = h
        elif isinstance(file, (bytes, bytearray)):
            data = file
        elif hasattr(file, "read"):
            pos = file.tell() if hasattr(file, "tell") else None
            data = file.read()
            if pos is not None and hasattr(file, "seek"):
                file.seek(pos)
        elif isinstance(file, str):
            with open(file, "rb") as f:
                data = f.read()
        else:
            return None
        with Image.open(BytesIO(data)) as img:
            fmt = (img.format or "").upper()
        mapping = {
            "JPEG": "jpeg",
            "JPG": "jpeg",
            "PNG": "png",
            "GIF": "gif",
            "BMP": "bmp",
            "TIFF": "tiff",
            "WEBP": "webp"
        }
        return mapping.get(fmt, fmt.lower() or None)
    except Exception:
        return None
