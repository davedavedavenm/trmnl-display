import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__)

BASE_DIR = Path(__file__).parent
IMAGE_DIR = BASE_DIR / "images"
IMAGE_DIR.mkdir(exist_ok=True)

CONFIG_PATH = BASE_DIR / "config.json"
DEFAULT_PORT = 4567
DEFAULT_REFRESH = 300

config = {
    "refresh_rate": DEFAULT_REFRESH,
    "timezone": "America/New_York",
    "playlist": ["test", "weather", "calendar", "todo"],
    "plugins_dir": str(BASE_DIR / "plugins"),
}

if CONFIG_PATH.exists():
    with open(CONFIG_PATH) as f:
        saved = json.load(f)
        config.update(saved)

_last_hash = ""
_counter = 0


def generate_test_image():
    from PIL import Image, ImageDraw, ImageFont

    width, height = 800, 480
    image = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(image)

    draw.rectangle([0, 0, width - 1, height - 1], outline=0, width=3)
    draw.line([(0, 40), (width, 40)], fill=0, width=2)

    draw.rectangle([(10, 10), (30, 30)], fill=0)
    draw.text((40, 8), "InkyPi BYOS", fill=0)
    draw.text((40, 22), "TRMNL Local Server", fill=128)

    now = datetime.now()
    date_str = now.strftime("%A, %B %d, %Y")
    time_str = now.strftime("%I:%M %p")
    draw.text((width - 200, 8), date_str, fill=0)
    draw.text((width - 100, 22), time_str, fill=0)

    y = 60
    draw.text((30, y), "TRMNL BYOS Server Active", fill=0)
    y += 30
    draw.text((30, y), f"Device: Pimoroni Inky Impression 7.3\"", fill=128)
    y += 20
    draw.text((30, y), f"Resolution: {width}x{height}", fill=128)
    y += 20
    draw.text((30, y), f"Server: http://0.0.0.0:{DEFAULT_PORT}", fill=128)
    y += 20
    draw.text((30, y), f"Refresh: every {config['refresh_rate']}s", fill=128)

    y += 40
    draw.line([(20, y), (width - 20, y)], fill=200, width=1)
    y += 15
    draw.text((30, y), "Playlist:", fill=0)
    y += 25
    for i, plugin in enumerate(config["playlist"]):
        marker = ">" if i == 0 else " "
        fill = 0 if i == 0 else 128
        draw.text((50, y), f"{marker} {plugin}", fill=fill)
        y += 22

    y += 20
    draw.line([(20, y), (width - 20, y)], fill=200, width=1)
    y += 15
    draw.text((30, y), "Status: OK - Ready for plugins", fill=0)
    y += 25
    draw.text((30, y), "Next: Add InkyPi plugins as recipes", fill=128)

    gray_blocks = [(0, 64, 128, 192, 255)]
    bx = 600
    for i, g in enumerate(gray_blocks[0]):
        draw.rectangle([(bx + i * 38, 420), (bx + i * 38 + 30, 460)], fill=g, outline=0)
        draw.text((bx + i * 38 + 5, 462), str(g), fill=0)

    ts = now.strftime("%Y%m%d_%H%M%S")
    filename = f"screen_{ts}.png"
    filepath = IMAGE_DIR / filename
    image.save(filepath)
    return filename


def cleanup_old_images(keep=10):
    files = sorted(IMAGE_DIR.glob("screen_*.png"), key=os.path.getmtime, reverse=True)
    for f in files[keep:]:
        f.unlink()


@app.route("/api/display", methods=["GET"])
def get_display():
    global _last_hash, _counter

    device_id = request.headers.get("ID", "default")
    _counter += 1

    filename = generate_test_image()
    cleanup_old_images()

    host = request.host or f"localhost:{DEFAULT_PORT}"
    scheme = request.scheme or "http"
    image_url = f"{scheme}://{host}/images/{filename}"

    content_hash = hashlib.md5(filename.encode()).hexdigest()[:12]
    _last_hash = content_hash

    return jsonify({
        "image_url": image_url,
        "filename": content_hash,
        "refresh_rate": config["refresh_rate"],
        "update_firmware": False,
        "firmware_url": None,
        "reset_firmware": False,
        "special_function": "",
    })


@app.route("/api/setup", methods=["GET"])
def get_setup():
    return jsonify({
        "api_key": "byos-inky-pi-local",
        "friendly_id": "INKYPI",
        "image_url": f"http://localhost:{DEFAULT_PORT}/images/setup.bmp",
        "message": "InkyPi BYOS Server",
    })


@app.route("/api/log", methods=["POST"])
def post_log():
    return "", 204


@app.route("/images/<path:filename>")
def serve_image(filename):
    return send_from_directory(str(IMAGE_DIR), filename)


@app.route("/api/config", methods=["GET"])
def get_config():
    return jsonify(config)


@app.route("/api/config", methods=["POST"])
def update_config():
    global config
    data = request.get_json(force=True)
    if data:
        config.update(data)
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)
    return jsonify(config)


@app.route("/health")
def health():
    return jsonify({"status": "ok", "counter": _counter, "uptime": time.time()})


if __name__ == "__main__":
    print(f"Starting TRMNL BYOS Server on port {DEFAULT_PORT}")
    print(f"Image directory: {IMAGE_DIR}")
    print(f"API endpoint: http://0.0.0.0:{DEFAULT_PORT}/api/display")
    app.run(host="0.0.0.0", port=DEFAULT_PORT)
