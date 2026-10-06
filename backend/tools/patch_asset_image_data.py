"""
Patch a Dataverse asset record and set the dystudio_image_data field to a small generated PNG (base64).
Usage: python backend/tools/patch_asset_image_data.py <asset_id>

This script uses the same DataverseService to PATCH the asset. It's a quick way to populate image_data for testing.
"""
import sys
import base64
import io
from PIL import Image

from backend.core.dataverse_service import DataverseService


def make_test_png_bytes(color=(100, 150, 200), size=(64, 64)):
    img = Image.new("RGBA", size, color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def main():
    if len(sys.argv) < 2:
        print("Usage: python backend/tools/patch_asset_image_data.py <asset_id>")
        return
    asset_id = sys.argv[1]
    print(f"Patching asset {asset_id} with test PNG...")

    b = make_test_png_bytes()
    b64 = base64.b64encode(b).decode("utf-8")

    svc = DataverseService()
    # First attempt: try to update the Dataverse record with image_data.
    updates = {
        "image_data": b64,
        "content_type": "image/png",
        "size": len(b),
    }

    try:
        res = svc.update_asset_metadata(asset_id, media_type="image", updates=updates)
        print("Patch result:")
        print(res)
        return
    except Exception as e:
        print("Dataverse rejected image_data property, falling back to local file and metadata update:", e)

    # Fallback: write file locally and update metadata without image_data
    try:
        image_dir = svc._environment_url and None  # dummy to reference svc for potential side-effects
    except Exception:
        pass

    # Write to configured static images directory
    from backend.core.config import settings
    image_dir = settings.IMAGE_DIR
    import os
    os.makedirs(image_dir, exist_ok=True)
    _, ext = os.path.splitext("test.png")
    local_filename = f"{asset_id}{ext}"
    local_path = os.path.join(image_dir, local_filename)
    try:
        with open(local_path, "wb") as f:
            f.write(b)
    except Exception as write_exc:
        print("Failed to write local fallback file:", write_exc)
        return

    updates2 = {
        "container": "local",
        "url": f"/{image_dir.rstrip('/')}/{local_filename}",
        "content_type": "image/png",
        "size": len(b),
    }

    try:
        res = svc.update_asset_metadata(asset_id, media_type="image", updates=updates2)
        print("Patch result (fallback metadata update):")
        print(res)
    except Exception as e:
        print("Failed to update metadata with local fallback:", e)


if __name__ == "__main__":
    main()
