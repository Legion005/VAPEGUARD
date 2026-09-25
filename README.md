# VapeGuard

Aplikasi validasi keaslian produk vape dan verifikasi usia menggunakan kamera browser.

## Fitur
- Validasi nomor seri produk
- Verifikasi usia dengan deteksi wajah (estimasi)
- Tombol buka kamera di browser
- Panel admin untuk melihat log verification dan data produk
- Database SQLite lokal

## Jalankan lokal
1. Masuk ke folder project
2. Install dependensi:
   pip install -r requirements.txt
3. Jalankan aplikasi:
   python app.py
4. Buka:
   http://127.0.0.1:5000

## Deploy ke Vercel
1. Buat repository GitHub baru
2. Push project ke GitHub
3. Masuk ke Vercel
4. Import project
5. Deploy

Catatan:
- Fitur kamera hanya berjalan di HTTPS atau localhost
- Deteksi usia adalah estimasi wajah untuk demo, bukan sistem identifikasi resmi

## Struktur utama
- app.py = aplikasi Flask
- api/index.py = entrypoint untuk serverless Vercel
- templates/ = halaman frontend
- static/ = CSS dan JavaScript
- vape_guard.db = database SQLite yang dibuat otomatis
