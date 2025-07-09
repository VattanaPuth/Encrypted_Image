// =========================
// CONFIGURATION
// =========================
const CONFIG = {
    MAX_FILE_SIZE: 100 * 1024 * 1024, // 100MB
    ALLOWED_TYPES: ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/bmp', 'image/tiff'],
    HEALTH_CHECK_INTERVAL: 30000,
    API_BASE_URL: 'http://127.0.0.1:5000'
};

// =========================
// INITIALIZATION
// =========================
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
    switchTab('encryptImage'); // Default tab
});

function initializeApp() {
    setupEventListeners();
    setupDragAndDrop();
    startHealthCheck();
}

// 👇 Make sure this function exists
function setupEventListeners() {
    const imageFileInput = document.getElementById('imageFile');
    const zipFileInput = document.getElementById('zipFile');

    if (imageFileInput) imageFileInput.addEventListener('change', handleImageFileSelect);
    if (zipFileInput) zipFileInput.addEventListener('change', handleZipFileSelect);

    document.addEventListener('dragover', e => e.preventDefault());
    document.addEventListener('drop', e => e.preventDefault());
}

// =========================
// FILE VALIDATION
// =========================
function validateImageFile(file) {
    if (!file) return false;
    if (file.size > CONFIG.MAX_FILE_SIZE) {
        showMessage('encryptMessage', 'File too large (max 50MB)', 'error');
        return false;
    }
    if (!CONFIG.ALLOWED_TYPES.includes(file.type)) {
        showMessage('encryptMessage', 'Unsupported image type.', 'error');
        return false;
    }
    return true;
}

function validateZipFile(file) {
    if (!file) return false;
    if (file.size > CONFIG.MAX_FILE_SIZE) {
        showMessage('decryptMessage', 'File too large (max 50MB)', 'error');
        return false;
    }
    if (file.type !== 'application/zip' && !file.name.endsWith('.zip')) {
        showMessage('decryptMessage', 'Only ZIP files are accepted.', 'error');
        return false;
    }
    return true;
}

// =========================
// FILE SELECTION HANDLERS
// =========================
function handleImageFileSelect(e) {
    const file = e.target.files[0];
    if (!file || !validateImageFile(file)) {
        resetFileInput('imageFile');
        return;
    }
    enableButton('encryptBtn');
    showFileInfo(file, 'encrypt');
    updateUploadArea('encryptUploadArea', file);
}

function handleZipFileSelect(e) {
    const file = e.target.files[0];
    if (!file || !validateZipFile(file)) {
        resetFileInput('zipFile');
        return;
    }
    enableButton('decryptBtn');
    showFileInfo(file, 'decrypt');
    updateUploadArea('decryptUploadArea', file);
}

// =========================
// FILE UPLOAD DISPLAY
// =========================
function updateUploadArea(areaId, file) {
    const area = document.getElementById(areaId);
    area.querySelector('.upload-icon').textContent = '✅';
    area.querySelector('.upload-text').textContent = `Selected: ${file.name}`;
    area.querySelector('.upload-subtext').textContent = `Size: ${formatFileSize(file.size)} • Ready`;
    area.style.borderColor = '#10b981';
    area.style.backgroundColor = 'rgba(16, 185, 129, 0.1)';
}

function formatFileSize(bytes) {
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
}

function showFileInfo(file, type) {
    const resultArea = document.getElementById(`${type}Result`);
    const fileInfoHTML = `
        <h3>📁 File Information</h3>
        <div class="file-info-grid">
            <div class="file-info-item"><span class="file-info-label">Filename:</span><span>${file.name}</span></div>
            <div class="file-info-item"><span class="file-info-label">Size:</span><span>${formatFileSize(file.size)}</span></div>
            <div class="file-info-item"><span class="file-info-label">Type:</span><span>${file.type}</span></div>
            <div class="file-info-item"><span class="file-info-label">Modified:</span><span>${new Date(file.lastModified).toLocaleString()}</span></div>
        </div>`;
    document.getElementById(`${type}FileInfo`).innerHTML = fileInfoHTML;
    resultArea.classList.add('show');
}

function resetFileInput(inputId) {
    const input = document.getElementById(inputId);
    if (input) input.value = '';

    const btnId = inputId === 'imageFile' ? 'encryptBtn' : 'decryptBtn';
    const areaId = inputId === 'imageFile' ? 'encryptUploadArea' : 'decryptUploadArea';
    const defaultIcon = inputId === 'imageFile' ? '📸' : '📦';
    const defaultText = inputId === 'imageFile' ? 'Drop your image here or click to select' : 'Drop encrypted package here or click to select';

    disableButton(btnId);

    const area = document.getElementById(areaId);
    area.querySelector('.upload-icon').textContent = defaultIcon;
    area.querySelector('.upload-text').textContent = defaultText;
    area.querySelector('.upload-subtext').textContent = '';
    area.style.borderColor = '';
    area.style.backgroundColor = '';
}

// =========================
// DRAG & DROP
// =========================
function setupDragAndDrop() {
    document.querySelectorAll('.upload-area').forEach(area => {
        area.addEventListener('dragover', e => {
            e.preventDefault();
            area.classList.add('dragover');
        });
        area.addEventListener('dragleave', e => {
            e.preventDefault();
            area.classList.remove('dragover');
        });
        area.addEventListener('drop', e => {
            e.preventDefault();
            area.classList.remove('dragover');
            const file = e.dataTransfer.files[0];
            if (!file) return;
            if (area.id === 'encryptUploadArea' && validateImageFile(file)) {
                document.getElementById('imageFile').files = e.dataTransfer.files;
                handleImageFileSelect({ target: { files: [file] } });
            } else if (area.id === 'decryptUploadArea' && validateZipFile(file)) {
                document.getElementById('zipFile').files = e.dataTransfer.files;
                handleZipFileSelect({ target: { files: [file] } });
            }
        });
    });
}

// =========================
// UPLOAD + API CALLS
// =========================
async function encryptImage() {
    const fileInput = document.getElementById('imageFile');
    const file = fileInput?.files[0];

    if (!file) {
        showMessage('encryptMessage', 'Please select an image to encrypt.', 'error');
        return;
    }

    disableButton('encryptBtn');
    showLoadingOverlay('Encrypting Image...', 'Processing image...');
    showProgress('encrypt', true, 'Encrypting...');

    const formData = new FormData();
    formData.append('file', file);

    try {
        await sleep(1000); // simulate pre-encryption preparation delay

        const res = await fetch(`${CONFIG.API_BASE_URL}/encrypt`, {
            method: 'POST',
            body: formData
        });

        if (!res.ok) {
            const data = await res.json().catch(() => ({}));
            throw new Error(data.error || 'Encryption failed.');
        }

        await sleep(1000); // simulate processing time after response

        const blob = await res.blob();

        if (blob.size === 0) {
            showMessage('encryptMessage', 'Received empty ZIP file. Something went wrong.', 'error');
            return;
        }

        await sleep(1000); // simulate post-processing before download

        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'encrypted_package.zip';
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);

        showMessage('encryptMessage', 'Encryption successful! ZIP file downloaded.', 'success');
        resetFileInput('imageFile');
        disableButton('encryptBtn');

    } catch (err) {
        console.error('Encryption error:', err);
        showMessage('encryptMessage', `${err.message}`, 'error');
        enableButton('encryptBtn');
    }

    hideLoadingOverlay();
    showProgress('encrypt', false);
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}


async function decryptImage() {
    const file = document.getElementById('zipFile')?.files[0];
    if (!file) return;

    disableButton('decryptBtn');
    showLoadingOverlay('Decrypting...', 'Rebuilding the image...');
    showProgress('decrypt', true, 'Decrypting...');

    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch(`${CONFIG.API_BASE_URL}/decrypt`, {
            method: 'POST',
            body: formData
        });

        if (!res.ok) {
            const data = await res.json();
            throw new Error(data.error || 'Decryption failed.');
        }

        const data = await res.json();
        if (data.image_url) {
            document.getElementById('decryptedImageContainer').innerHTML =
                `<img src="${data.image_url}" class="preview-image" alt="Decrypted Image">`;
            showMessage('decryptMessage', 'Image decrypted successfully.', 'success');
            resetFileInput('zipFile');
        } else {
            throw new Error('No image URL returned.');
        }
    } catch (err) {
        console.error('Decrypt error:', err);
        showMessage('decryptMessage', err.message, 'error');
    }

    hideLoadingOverlay();
    showProgress('decrypt', false);
    enableButton('decryptBtn');
}


// =========================
// UTILITIES
// =========================
function showMessage(id, msg, type = 'info') {
    const el = document.getElementById(id);
    const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
    el.textContent = `${icons[type]} ${msg}`;
    el.className = `status-message status-${type}`;
    el.parentElement.classList.add('show');
}

function showLoadingOverlay(title, subtitle) {
    document.getElementById('loadingOverlay').style.display = 'flex';
    document.getElementById('loadingTitle').textContent = title;
    document.getElementById('loadingSubtext').textContent = subtitle;
    document.body.style.overflow = 'hidden';
}

function hideLoadingOverlay() {
    document.getElementById('loadingOverlay').style.display = 'none';
    document.body.style.overflow = '';
}

function showProgress(type, show, text = 'Processing...') {
    const bar = document.getElementById(`${type}Progress`);
    const label = document.getElementById(`${type}ProgressText`);
    if (bar && label) {
        bar.style.display = show ? 'block' : 'none';
        label.textContent = text;
    }
}

function disableButton(id) {
    const btn = document.getElementById(id);
    if (btn) btn.disabled = true;
}

function enableButton(id) {
    const btn = document.getElementById(id);
    if (btn) btn.disabled = false;
}

function switchTab(tabName) {
    document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

    document.querySelector(`[onclick="switchTab('${tabName}')"]`).classList.add('active');
    document.getElementById(`${tabName}-tab`).classList.add('active');

    resetFileInput(tabName === 'encryptImage' ? 'imageFile' : 'zipFile');
}

// =========================
// SYSTEM CHECK
// =========================
function startHealthCheck() {
    const indicator = document.getElementById('healthIndicator');

    const check = async () => {
        try {
            const res = await fetch(`${CONFIG.API_BASE_URL}/`);
            indicator.style.backgroundColor = res.ok ? '#10b981' : '#f59e0b';
            indicator.title = res.ok ? 'System Healthy' : 'Server Unreachable';
        } catch {
            indicator.style.backgroundColor = '#ef4444';
            indicator.title = 'Server Down';
        }
    };

    check(); // run once on load
    setInterval(check, CONFIG.HEALTH_CHECK_INTERVAL);
}
