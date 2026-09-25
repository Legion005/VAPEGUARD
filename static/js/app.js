const productForm = document.getElementById('productForm');
const serialInput = document.getElementById('serialInput');
const productResult = document.getElementById('productResult');
const productStatusLight = document.getElementById('productStatusLight');

const video = document.getElementById('video');
const startCameraBtn = document.getElementById('startCameraBtn');
const checkAgeBtn = document.getElementById('checkAgeBtn');
const cameraStatus = document.getElementById('cameraStatus');
const ageResult = document.getElementById('ageResult');

let stream = null;
let modelsLoaded = false;

function setProductResult(type, message) {
  productResult.className = `result-box ${type}`;
  productResult.textContent = message;
}

function setAgeResult(type, message) {
  ageResult.className = `result-box ${type}`;
  ageResult.innerHTML = message;
}

productForm.addEventListener('submit', async (event) => {
  event.preventDefault();

  const serial = serialInput.value.trim();
  if (!serial) {
    setProductResult('error', 'Nomor seri tidak boleh kosong.');
    productStatusLight.style.background = '#f87171';
    return;
  }

  try {
    const response = await fetch('/api/verify-product', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ serial }),
    });

    const data = await response.json();

    if (data.valid) {
      const details = data.product;
      setProductResult(
        'success',
        `${data.message} Produk ${details.name} dengan batch ${details.batch} dan produsen ${details.manufacturer} telah terverifikasi.`
      );
      productStatusLight.style.background = '#34d399';
      productStatusLight.style.boxShadow = '0 0 18px rgba(52, 211, 153, 0.9)';
    } else {
      setProductResult('error', data.message);
      productStatusLight.style.background = '#f87171';
      productStatusLight.style.boxShadow = '0 0 18px rgba(248, 113, 113, 0.8)';
    }
  } catch (error) {
    setProductResult('error', 'Gagal memeriksa produk. Silakan coba lagi.');
    productStatusLight.style.background = '#f87171';
    productStatusLight.style.boxShadow = '0 0 18px rgba(248, 113, 113, 0.8)';
  }
});

async function loadModels() {
  if (modelsLoaded) {
    return;
  }

  const MODEL_URL = 'https://cdn.jsdelivr.net/npm/@vladmandic/face-api@1.7.13/weights';

  await Promise.all([
    faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL),
    faceapi.nets.faceLandmark68Net.loadFromUri(MODEL_URL),
    faceapi.nets.ageGenderNet.loadFromUri(MODEL_URL),
  ]);

  modelsLoaded = true;
}

async function startCamera() {
  try {
    await loadModels();
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'user' },
      audio: false,
    });

    video.srcObject = stream;
    await video.play();
    cameraStatus.textContent = 'Kamera aktif dan siap mendeteksi wajah.';
    startCameraBtn.textContent = 'Kamera Aktif';
  } catch (error) {
    cameraStatus.textContent = 'Kamera tidak dapat diakses. Pastikan izin kamera sudah diberikan.';
    console.error(error);
  }
}

async function checkAge() {
  if (!stream) {
    setAgeResult('error', 'Aktifkan kamera terlebih dahulu untuk memulai verifikasi wajah.');
    return;
  }

  try {
    const detection = await faceapi
      .detectSingleFace(video, new faceapi.TinyFaceDetectorOptions())
      .withFaceLandmarks()
      .withAgeAndGender();

    if (!detection) {
      setAgeResult('error', 'Wajah tidak terdeteksi. Pastikan wajah Anda berada di depan kamera dan pencahayaan cukup.');
      return;
    }

    const age = Math.round(detection.age);
    const gender = detection.gender === 'male' ? 'Laki-laki' : 'Perempuan';
    const isEligible = age >= 18;

    const message = `
      <strong>Hasil Deteksi:</strong><br>
      Umur diperkirakan: <strong>${age} tahun</strong><br>
      Jenis kelamin: <strong>${gender}</strong><br>
      Status: <strong>${isEligible ? 'Memenuhi syarat umur pembelian' : 'Belum memenuhi syarat umur pembelian'}</strong>
    `;

    setAgeResult(isEligible ? 'success' : 'error', message);

    if (isEligible) {
      const response = await fetch('/api/verify-age', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ age, serial: serialInput.value.trim() || '-' }),
      });

      const data = await response.json();
      cameraStatus.textContent = data.message;
    } else {
      cameraStatus.textContent = 'Verifikasi umur gagal karena usia belum memenuhi syarat minimal.';
    }
  } catch (error) {
    setAgeResult('error', 'Proses deteksi wajah gagal. Coba lagi dalam beberapa detik.');
    console.error(error);
  }
}

startCameraBtn.addEventListener('click', startCamera);
checkAgeBtn.addEventListener('click', checkAge);
