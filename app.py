import pandas as pd
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from sklearn.preprocessing import MinMaxScaler
from sklearn.neural_network import MLPRegressor
from sklearn.model_selection import train_test_split
import joblib
import random
import time
import numpy as np

app = Flask(__name__, static_folder='templates/static')
socketio = SocketIO(app)

# Konfigurasi database MySQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root@localhost/hasilprediksi'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Model untuk tabel hasilprediksi
class HasilPrediksi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    suhu = db.Column(db.Float)
    kelembaban_udara = db.Column(db.Float)
    tekanan_udara = db.Column(db.Float)
    arah_angin = db.Column(db.Float)
    kecepatan_angin = db.Column(db.Float)
    curah_hujan = db.Column(db.Float)

# Memuat model dari file joblib
mlp_regressor_model = joblib.load('mlp_regressor_model.joblib')
xgb_model = joblib.load('xgb_bpnnmodel.joblib')
scaler_X = joblib.load('scaler_X.joblib')
scaler_y = joblib.load('scaler_y.joblib')

def make_prediction(input_data):
    # Prediksi menggunakan model MLPRegressor
    input_scaled = scaler_X.transform([input_data])
    prediction_mlp = mlp_regressor_model.predict(input_scaled)
    
    # Gabungkan prediksi MLPRegressor ke dalam input untuk XGBoost
    input_with_mlp = np.hstack((input_scaled, prediction_mlp.reshape(-1, 1)))
    
    # Prediksi menggunakan model XGBoost
    prediction_xgb = xgb_model.predict(input_with_mlp)
    
    # Denormalisasi hasil prediksi XGBoost
    prediction_denormalized = scaler_y.inverse_transform(prediction_xgb.reshape(-1, 1))
    
    return prediction_denormalized.flatten()[0]

@app.route('/get_prediction_data')
def get_prediction_data():
    # Ambil data prediksi dari basis data
    data = HasilPrediksi.query.all()

    # Format data untuk dikirim sebagai respons JSON
    formatted_data = [
        {
            'id': hasil.id,
            'suhu': hasil.suhu,
            'kelembaban_udara': hasil.kelembaban_udara,
            'tekanan_udara': hasil.tekanan_udara,
            'arah_angin': hasil.arah_angin,
            'kecepatan_angin': hasil.kecepatan_angin,
            'curah_hujan': hasil.curah_hujan
        }
        for hasil in data
    ]

    return jsonify(formatted_data)

# Endpoint API yang akan memberikan data curah hujan
@app.route('/api/data')
def get_data():
    data = {'timestamp': time.time(), 'rainfall': random.randint(1, 10)}
    socketio.emit('update', data)
    return data

# Route untuk halaman utama
@app.route('/')
def index():
    return render_template('rainfallprediction.html')

@app.route('/predict', methods=['POST'])
def predict():
    if request.method == 'POST':
        # Ambil nilai input dari form
        suhu = float(request.form['suhu'])
        kelembaban_udara = float(request.form['kelembaban_udara'])
        tekanan_udara = float(request.form['tekanan_udara'])
        arah_angin = float(request.form['arah_angin'])
        kecepatan_angin = float(request.form['kecepatan_angin'])

        # Susun input data untuk model (5 fitur yang digunakan untuk prediksi)
        input_data = [suhu, kelembaban_udara, tekanan_udara, arah_angin, kecepatan_angin]

        # DEBUG: Cek panjang input_data
        print(f"Panjang input_data: {len(input_data)}")

        # Lakukan prediksi menggunakan model yang sudah dimuat
        hasilprediksi = make_prediction(input_data)

        # Format hasil prediksi ke dua angka desimal
        hasilprediksi_formatted = "{:.2f}".format(hasilprediksi)

        # Memastikan nilai prediksi tidak negatif
        hasilprediksi_formatted = max(float(hasilprediksi_formatted), 0.00)
        hasilprediksi_formatted = "{:.2f}".format(hasilprediksi_formatted)  # Reformat jika ada perubahan

        # Simpan hasil prediksi ke dalam database
        prediksi_baru = HasilPrediksi(
            suhu=suhu,
            kelembaban_udara=kelembaban_udara,
            tekanan_udara=tekanan_udara,
            arah_angin=arah_angin,
            kecepatan_angin=kecepatan_angin,
            curah_hujan=hasilprediksi
        )

        db.session.add(prediksi_baru)
        db.session.commit()

        # Logika kondisi cuaca berdasarkan hasil prediksi
        kondisi_cuaca, icon = determine_weather_condition(float(hasilprediksi_formatted))

        # Return hasil prediksi dan kondisi cuaca
        return render_template('rainfallprediction.html', prediction=hasilprediksi_formatted, kondisi_cuaca=kondisi_cuaca, icon=icon)


def determine_weather_condition(pred):
    if pred == 0:
        return 'Cerah', 'clear-day-fill'
    elif 0.5 <= pred < 20:
        return 'Hujan ringan', 'overcast-night-rain'
    elif 20 <= pred < 50:
        return 'Hujan sedang', 'cloud-rain-fill'
    elif 50 <= pred < 100:
        return 'Hujan lebat', 'cloud-showers-heavy-fill'
    elif 100 <= pred < 150:
        return 'Hujan sangat lebat', 'cloud-hail-fill'
    else:
        return 'Hujan ekstrem', 'cloud-showers-heavy-fill'

if __name__ == '__main__':
    socketio.run(app, debug=True)
