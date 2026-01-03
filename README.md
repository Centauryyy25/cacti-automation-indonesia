# 🌵 Cacti Automation Indonesia

Otomatisasi scraping dan OCR untuk data traffic dari Cacti NMS.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0+-green?logo=flask)

---

## 📸 Screenshot

<p align="center">
  <img src="static/download.jpg" alt="Dashboard Preview" width="600">
</p>

---

## ⚡ Quick Start (3 Langkah!)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Setup Environment
```bash
cp .env.example .env
# Edit .env dengan data Anda
```

### 3. Jalankan!
```bash
python -m web.app
```

Buka browser: **http://localhost:5000** ✅

---

## 🔧 Konfigurasi (.env)

Edit file `.env` dengan data berikut:

```env
# WAJIB - Data Login Cacti
CACTI_USERNAME=username_anda
CACTI_PASSWORD=password_anda
CACTI_BASE_URL=https://your-cacti-server.com/

# OPTIONAL - untuk keamanan
CACTI_ALLOWED_URLS=https://your-cacti-server.com/

# OPTIONAL - Mode Headless (tanpa tampilan browser)
SELENIUM_HEADLESS=true
```

---

## 🖥️ Cara Pakai Web Dashboard

1. **Buka browser** → `http://localhost:5000`
2. **Isi form:**
   - **Target URL:** URL Cacti Anda
   - **Username & Password:** Login Cacti
   - **Usernames:** List device (pisahkan dengan koma)
   - **Date Range:** Pilih rentang waktu
3. **Klik "Run Pipeline"**
4. **Tunggu proses selesai**
5. **Download hasil:** Pilih format (Original/Mbps/Kbps)

---

## 📁 Hasil Output

Setelah pipeline selesai, hasil disimpan di folder `output/<timestamp>/`:

```
output/2026-01-03_14-30-00/
├── raw_screenshots/        # Gambar yang di-scrape
├── processed_output/       # Hasil OCR (JSON)
├── hasil_original_*.csv    # Data asli
├── hasil_mbps_*.csv        # Data dalam Mbps
├── hasil_kbps_*.csv        # Data dalam Kbps
└── summary.json            # Ringkasan run
```

---

## 🐳 Docker (Opsional)

```bash
# Build dan jalankan
docker-compose up -d

# Buka di browser
http://localhost:5000
```

---

## 📋 Requirements

- **Python 3.10+**
- **Chrome/Chromium** (untuk Selenium)
- **ChromeDriver** (otomatis via `webdriver-manager`)

### Install Chrome di Linux:
```bash
# Ubuntu/Debian
sudo apt install chromium-browser

# Atau download dari:
# https://www.google.com/chrome/
```

---

## 🛠️ Troubleshooting

### Error: "ChromeDriver not found"
```bash
pip install webdriver-manager
```

### Error: "Module not found"
```bash
pip install -r requirements.txt
```

### Error: "Connection refused"
- Pastikan URL Cacti benar
- Cek username/password
- Cek firewall/network

---

## 📂 Struktur Folder

```
cacti-automation/
├── web/                 # Flask web app
├── scraping/            # Selenium scraper
├── cleaning/            # Data cleaning & CSV
├── ocr/                 # EasyOCR processing
├── templates/           # HTML templates
├── static/              # CSS, images
├── output/              # Hasil scraping
└── tests/               # Unit tests
```

---

## 🧪 Testing

```bash
# Jalankan semua tests
python -m pytest

# Dengan coverage
python -m pytest --cov
```

---

## 📝 License

MIT License - Bebas digunakan dan dimodifikasi.

---

## ❓ FAQ

<details>
<summary><b>Q: Bagaimana cara menambah device baru?</b></summary>
<p>Masukkan nama device di field "Usernames", pisahkan dengan koma.
Contoh: <code>device1, device2, device3</code></p>
</details>

<details>
<summary><b>Q: Format tanggal yang benar?</b></summary>
<p>Gunakan format datetime picker di browser. Contoh: <code>2025-01-01 00:00</code></p>
</details>

<details>
<summary><b>Q: Hasil OCR tidak akurat?</b></summary>
<p>Pastikan gambar grafik cukup jelas. OCR bekerja lebih baik dengan resolusi tinggi.</p>
</details>

---

**Made with ❤️ in Indonesia** 🇮🇩
