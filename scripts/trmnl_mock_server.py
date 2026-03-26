import os
from flask import Flask, jsonify, send_from_directory
from PIL import Image, ImageDraw
from datetime import datetime

app = Flask(__name__)
PORT = 8000
IMAGE_DIR = os.path.join(os.getcwd(), "trmnl_test_output")
if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

def generate_test_image():
    width, height = 800, 480
    image = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, width-1, height-1], outline="black", width=5)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text = "TRMNL MOCK SERVER\n\nHardware: Inky Impression 7.3\nResolution: 800x480\nTime: " + timestamp
    draw.text((50, 50), text, fill="black")
    draw.rectangle([50, 300, 150, 400], fill=(0, 0, 0))
    draw.rectangle([170, 300, 270, 400], fill=(85, 85, 85))
    draw.rectangle([290, 300, 390, 400], fill=(170, 170, 170))
    draw.rectangle([410, 300, 510, 400], fill=(255, 255, 255), outline="black")
    image_path = os.path.join(IMAGE_DIR, "test_display.png")
    image = image.convert("L")
    image.save(image_path)
    return "test_display.png"

@app.route("/api/display", methods=["GET"])
def get_display():
    filename = generate_test_image()
    time_str = datetime.now().strftime("%H%M%S")
    return jsonify({
        "status": 0,
        "image_url": "http://localhost:" + str(PORT) + "/images/" + filename,
        "image_name": "test-image-" + time_str,
        "update_firmware": False,
        "refresh_rate": 60,
        "reset_firmware": False
    })

@app.route("/images/<path:filename>")
def serve_image(filename):
    return send_from_directory(IMAGE_DIR, filename)

if __name__ == "__main__":
    print("Starting TRMNL Mock Server")
    generate_test_image()
    app.run(host="0.0.0.0", port=PORT)