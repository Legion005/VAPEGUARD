const productAdminForm = document.getElementById('productAdminForm');
const adminProductMessage = document.getElementById('adminProductMessage');
const productTableBody = document.getElementById('productTableBody');
const adminLogsTable = document.getElementById('adminLogsTable');

async function loadProducts() {
  const response = await fetch('/api/products');
  const data = await response.json();

  productTableBody.innerHTML = data.products
    .map(
      (product) => `
        <tr>
          <td>${product.serial}</td>
          <td>${product.name}</td>
          <td>${product.batch}</td>
          <td>${product.manufacturer}</td>
        </tr>
      `
    )
    .join('');
}

async function loadLogs() {
  const response = await fetch('/api/admin/logs');
  const data = await response.json();

  adminLogsTable.innerHTML = data.logs
    .map(
      (log) => `
        <tr>
          <td>${log.product_serial}</td>
          <td>${log.age ?? '-'}</td>
          <td>${log.status}</td>
          <td>${new Date(log.created_at).toLocaleString('id-ID')}</td>
        </tr>
      `
    )
    .join('');
}

productAdminForm.addEventListener('submit', async (event) => {
  event.preventDefault();

  const payload = {
    serial: document.getElementById('adminSerial').value,
    name: document.getElementById('adminName').value,
    batch: document.getElementById('adminBatch').value,
    manufacturer: document.getElementById('adminManufacturer').value,
  };

  const response = await fetch('/api/admin/products', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  const data = await response.json();
  adminProductMessage.className = data.success ? 'result-box success' : 'result-box error';
  adminProductMessage.textContent = data.message;

  if (data.success) {
    productAdminForm.reset();
    loadProducts();
  }
});

loadProducts();
loadLogs();
setInterval(loadLogs, 5000);
