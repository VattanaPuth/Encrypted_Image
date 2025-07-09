from flask import Flask, request, send_file, render_template, jsonify
from werkzeug.utils import secure_filename
from flask_cors import CORS
from celery import Celery
import os, zipfile, uuid, io
from PIL import Image, ImageEnhance
import numpy as np
import logging

# ========== Flask App Setup ==========
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, template_folder="../templates", static_folder="../static")
CORS(app)

# ========== Celery Setup ==========
app.config.update(
    broker_url='redis://localhost:6379/0',  
    result_backend='redis://localhost:6379/0'
)

def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=app.config['result_backend'],
        broker=app.config['broker_url']
    )
    celery.conf.update(app.config)
    
    class ContextTask(celery.Task):
        """Make celery tasks work with Flask app context."""
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery

celery = make_celery(app)

# ========== Directories ==========
UPLOAD_FOLDER = os.path.join(BASE_DIR, "temp")
ENCRYPTED_FOLDER = os.path.join(BASE_DIR, "encrypted")
DECRYPTED_FOLDER = os.path.join(BASE_DIR, "decrypted")
# STATIC_FOLDER = os.path.join(BASE_DIR, "static")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ENCRYPTED_FOLDER, exist_ok=True)
os.makedirs(DECRYPTED_FOLDER, exist_ok=True)
# os.makedirs(STATIC_FOLDER, exist_ok=True)

# ========== Logging Setup ==========
logging.basicConfig(level=logging.INFO)

# ========== RSA Functions ==========
def gcd(a, b):
    while b:
        a, b = b, a % b
    return a

def mod_inverse(e, phi):
    def extended_gcd(a, b):
        if a == 0:
            return b, 0, 1
        gcd, x1, y1 = extended_gcd(b % a, a)
        x = y1 - (b // a) * x1
        y = x1
        return gcd, x, y
    
    gcd, x, _ = extended_gcd(e, phi)
    if gcd != 1:
        raise ValueError("Modular inverse does not exist")
    return x % phi

def generate_keypair(keysize=8):
    import random
    
    def is_prime(n):
        if n < 2:
            return False
        for i in range(2, int(n**0.5) + 1):
            if n % i == 0:
                return False
        return True
    
    def generate_prime(keysize):
        while True:
            num = random.getrandbits(keysize)
            if is_prime(num):
                return num
    
    p = generate_prime(keysize // 2)
    q = generate_prime(keysize // 2)
    n = p * q
    phi = (p - 1) * (q - 1)
    
    e = 65537
    while gcd(e, phi) != 1:
        e += 2
    
    d = mod_inverse(e, phi)
    return (e, n), (d, n)

def quantized_matrix_to_image(matrices, dims, step, output_path):
    w, h = dims
    img = Image.new("RGB", (w, h))
    pixels = []
    
    for y in range(h):
        for x in range(w):
            r = int(matrices[0][y][x] * step)
            g = int(matrices[1][y][x] * step)
            b = int(matrices[2][y][x] * step)
            pixels.append((r, g, b))
    
    img.putdata(pixels)
    
    if img.mode != "RGB":
        img = img.convert("RGB")
        
    if img.size != (w, h):
        img = img.resize((w, h), Image.LANCZOS)
        
    enhancer_contrast = ImageEnhance.Contrast(img)
    img = enhancer_contrast.enhance(1.2)
    
    enhancer_sharpness = ImageEnhance.Sharpness(img)
    img = enhancer_sharpness.enhance(1.0)

    img.save(output_path)

# ========== Celery Task (Asynchronous Encryption) ==========
@celery.task(bind=True, name='RSA.app.app.process_encryption')
def process_encryption(self, file_path):
    """
    Task to process encryption asynchronously.
    """
    try:
        logging.info(f"Starting encryption for {file_path}")
        
        # Load and process the image
        img = Image.open(file_path)
        logging.warning(f"Image {file_path} loaded successfully.")
        
        # Convert to RGB and get dimensions
        img = img.convert("RGB")
        w, h = img.size
        
        # Convert image to matrices
        pixels = list(img.getdata())
        r_matrix = [[pixels[y * w + x][0] for x in range(w)] for y in range(h)]
        g_matrix = [[pixels[y * w + x][1] for x in range(w)] for y in range(h)]
        b_matrix = [[pixels[y * w + x][2] for x in range(w)] for y in range(h)]
        
        # Generate RSA keys
        public_key, private_key = generate_keypair()
        e, n = public_key
        
        # Quantization and encryption
        step = 8
        quantized_r = [[r_matrix[y][x] // step for x in range(w)] for y in range(h)]
        quantized_g = [[g_matrix[y][x] // step for x in range(w)] for y in range(h)]
        quantized_b = [[b_matrix[y][x] // step for x in range(w)] for y in range(h)]
        
        # Encrypt matrices
        encrypted_r = [[pow(quantized_r[y][x], e, n) for x in range(w)] for y in range(h)]
        encrypted_g = [[pow(quantized_g[y][x], e, n) for x in range(w)] for y in range(h)]
        encrypted_b = [[pow(quantized_b[y][x], e, n) for x in range(w)] for y in range(h)]
        
        # Save encrypted data to zip
        encrypted_filename = f"encrypted_{uuid.uuid4().hex}.zip"
        static_file_path = os.path.join(BASE_DIR, "encrypted", encrypted_filename)
        
        with open(static_file_path, "wb") as f:
            with zipfile.ZipFile(f, "w") as zip_file:
                zip_file.writestr("r.npy", np.array(encrypted_r).tobytes())
                zip_file.writestr("g.npy", np.array(encrypted_g).tobytes())
                zip_file.writestr("b.npy", np.array(encrypted_b).tobytes())
                zip_file.writestr("meta.txt", f"{w} {h} {step}")
        
        logging.info(f"Encryption completed. File saved at {static_file_path}")
        return static_file_path
        
    except Exception as e:
        logging.error(f"Error during encryption task: {str(e)}")
        raise Exception(f"Error in encryption task: {str(e)}")

# ========== Routes ==========
@app.route("/")
def index():
    return render_template("index.html")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg'}

@app.route("/encrypt", methods=["POST"])
def encrypt_image():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"error": "Invalid file type. Only PNG, JPG, JPEG allowed."}), 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(file_path)
        
        # Validate image
        try:
            with Image.open(file_path) as img:
                img.verify()
            logging.info(f"Valid image file: {file_path}")
        except Exception:
            os.remove(file_path)
            return jsonify({"error": "Invalid image file"}), 400
        
        # Start asynchronous task
        task = process_encryption.delay(file_path)
        return jsonify({"task_id": task.id, "status": "Processing..."}), 202

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route("/status/<task_id>", methods=["GET"])
def task_status(task_id):
    task = celery.AsyncResult(task_id)
    if task.state == 'PENDING':
        return jsonify({"status": "Pending..."}), 200
    elif task.state == 'SUCCESS':
        encrypted_file_path = task.result
        filename = os.path.basename(encrypted_file_path)
        return jsonify({"status": "Complete", "file_url": f"/download/encrypted/{filename}"}), 200
    elif task.state == 'FAILURE':
        return jsonify({"status": "Failed", "error": str(task.info)}), 500

@app.route("/decrypt", methods=["POST"])
def decrypt_image():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not file.filename.endswith('.zip'):
            return jsonify({"error": "Please upload a .zip file"}), 400
        
        # Read zip file content
        zip_content = io.BytesIO(file.read())
        
        with zipfile.ZipFile(zip_content, 'r') as zip_ref:
            # Load encrypted matrices
            r = np.frombuffer(zip_ref.read("r.npy"), dtype=np.int64)
            g = np.frombuffer(zip_ref.read("g.npy"), dtype=np.int64)
            b = np.frombuffer(zip_ref.read("b.npy"), dtype=np.int64)
            
            # Load private key and metadata
            private_key_data = zip_ref.read("private_key.txt").decode().split(',')
            d, n = int(private_key_data[0]), int(private_key_data[1])
            
            w, h, step = map(float, zip_ref.read("meta.txt").decode().split())
            dims = (int(w), int(h))
            
            # Reshape matrices
            r = r.reshape((int(h), int(w)))
            g = g.reshape((int(h), int(w)))
            b = b.reshape((int(h), int(w)))
            
            # Decrypt matrices
            decrypted_r = [[pow(int(r[y][x]), d, n) for x in range(int(w))] for y in range(int(h))]
            decrypted_g = [[pow(int(g[y][x]), d, n) for x in range(int(w))] for y in range(int(h))]
            decrypted_b = [[pow(int(b[y][x]), d, n) for x in range(int(w))] for y in range(int(h))]
        
        output_filename = f"decrypted_{uuid.uuid4().hex}.png"
        output_path = os.path.join(BASE_DIR, "decrypted", output_filename)
        quantized_matrix_to_image([decrypted_r, decrypted_g, decrypted_b], dims, step, output_path)

        return jsonify({"image_url": f"/download/decrypted/{output_filename}"}), 200

    except Exception as e:
        return jsonify({"error": f"Decryption failed: {str(e)}"}), 500

# ========== Download Routes ==========
@app.route("/download/encrypted/<filename>")
def download_encrypted(filename):
    """Serve encrypted files from the encrypted folder"""
    try:
        file_path = os.path.join(ENCRYPTED_FOLDER, filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({"error": "File not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Error serving file: {str(e)}"}), 500

@app.route("/download/decrypted/<filename>")
def download_decrypted(filename):
    """Serve decrypted files from the decrypted folder"""
    try:
        file_path = os.path.join(DECRYPTED_FOLDER, filename)
        if os.path.exists(file_path):
            return send_file(file_path)
        else:
            return jsonify({"error": "File not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Error serving file: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)