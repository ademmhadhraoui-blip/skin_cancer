from flask import Flask, render_template, request, redirect, flash, url_for, session
import mysql.connector
import os
import uuid
import numpy as np
from werkzeug.utils import secure_filename
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
import gdown
import os
from dotenv import load_dotenv

load_dotenv()



app = Flask(__name__)
app.secret_key = "dermascan_secret_key_2025"


UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ── Connexion DB (fonction pour éviter les déconnexions) ─────────────────────
def get_db():
    mysql_port = os.environ.get("MYSQLPORT") or "3306"
    return mysql.connector.connect(
        host=os.environ.get("MYSQLHOST"),
        user=os.environ.get("MYSQLUSER"),
        password=os.environ.get("MYSQLPASSWORD"),
        database=os.environ.get("MYSQLDATABASE"),
        port=int(mysql_port)
    )
# ── Chargement du modèle (une seule fois au démarrage) ────────────────────────

MODEL_DIR = "model"
MODEL_PATH = os.path.join(MODEL_DIR, "best_vgg16_skin.keras")

def download_model():
    os.makedirs(MODEL_DIR, exist_ok=True)

    if not os.path.exists(MODEL_PATH):
        model_url = os.environ.get("MODEL_URL")

        if not model_url:
            raise Exception("MODEL_URL environment variable is missing")

        print("Downloading model from Google Drive...")
        gdown.download(model_url, MODEL_PATH, quiet=False)

        if not os.path.exists(MODEL_PATH):
            raise Exception("Model download failed")

        print("Model downloaded successfully.")

download_model()
model = load_model(MODEL_PATH)

class_names = [
    "actinic keratosis",
    "basal cell carcinoma",
    "dermatofibroma",
    "melanoma",
    "nevus",
    "pigmented benign keratosis",
    "seborrheic keratosis",
    "squamous cell carcinoma",
    "vascular lesion"
]


# ── Fonction de prédiction ────────────────────────────────────────────────────
def predict_skin_cancer(img_path):
    img = image.load_img(img_path, target_size=(224, 224))
    img_array = image.img_to_array(img) / 255.0
    img_array = np.expand_dims(img_array, axis=0)

    prediction = model.predict(img_array)[0]

    predicted_index = np.argmax(prediction)
    confidence = float(np.max(prediction))
    result = class_names[predicted_index]

    # Top 3 prédictions
    top3_indices = np.argsort(prediction)[::-1][:3]
    top3 = [
        {
            "classe": class_names[i],
            "confiance": round(float(prediction[i]) * 100, 2)
        }
        for i in top3_indices
    ]

    return result, confidence, top3


# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM users WHERE username=%s AND password=%s",
            (username, password)
        )
        user = cursor.fetchone()
        cursor.close()
        db.close()

        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("dashboard"))

        flash("Username ou password incorrect", "danger")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template("dashboard.html")


@app.route("/predict", methods=["GET", "POST"])
def predict():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        name = request.form.get("name")
        age = request.form.get("age")
        file = request.files.get("image")

        if not name or not age:
            flash("Veuillez remplir le nom et l'âge", "danger")
            return redirect(url_for("predict"))

        if file is None or file.filename == "":
            flash("Veuillez choisir une image", "danger")
            return redirect(url_for("predict"))

        original_filename = secure_filename(file.filename)
        extension = os.path.splitext(original_filename)[1].lower()

        if extension not in [".jpg", ".jpeg", ".png", ".webp"]:
            flash("Veuillez choisir une image valide : JPG, JPEG, PNG ou WEBP", "danger")
            return redirect(url_for("predict"))

        filename = f"{uuid.uuid4().hex[:10]}{extension}"
        image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(image_path)

        image_path_for_web = "/" + image_path.replace("\\", "/")

        result, probability, top3 = predict_skin_cancer(image_path)

        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            """
            INSERT INTO patients (name, age, result, probability, image_path)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (name, age, result, probability, image_path_for_web)
        )
        db.commit()
        cursor.close()
        db.close()

        return render_template(
            "result.html",
            result=result,
            prob=round(probability * 100, 2),
            img=image_path_for_web,
            top3=top3
        )

    return render_template("predict.html")


@app.route("/patients")
def patients():
    if "user_id" not in session:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM patients ORDER BY created_at DESC")
    patients_list = cursor.fetchall()
    cursor.close()
    db.close()

    return render_template("patients.html", patients=patients_list)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    print("Modèle chargé avec succès")
    app.run(debug=True)