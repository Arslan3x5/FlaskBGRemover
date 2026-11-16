import io
import os

from flask import Flask, jsonify, render_template, request, send_file
from PIL import Image, ImageOps, UnidentifiedImageError
from rembg import new_session, remove

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # reject uploads over 10 MB

MAX_SIDE = 3000  # longest side in pixels; keeps memory use and time reasonable

# Load the model once at startup instead of on every request (much faster).
session = new_session("u2net")


def remove_background(file_storage):
    """Return PNG bytes of the uploaded image with its background removed."""
    image = Image.open(file_storage.stream)
    image = ImageOps.exif_transpose(image).convert("RGBA")
    image.thumbnail((MAX_SIDE, MAX_SIDE))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return remove(buffer.getvalue(), session=session)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/remove", methods=["POST"])
def api_remove():
    file = request.files.get("image")
    if not file or not file.filename:
        return jsonify(error="Please choose an image."), 400
    try:
        result = remove_background(file)
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError):
        return jsonify(error="That file is not a valid image."), 400
    return send_file(
        io.BytesIO(result),
        mimetype="image/png",
        download_name="background_removed.png",
    )


@app.errorhandler(413)
def too_large(_error):
    return jsonify(error="Image is too large. Maximum size is 10 MB."), 413


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
