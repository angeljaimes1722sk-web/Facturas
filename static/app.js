// ================= TABS =================
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
    });
});

// ================= DROPZONE helper =================
function setupDropzone(dropzoneId, fileInputId, listId) {
    const dropzone = document.getElementById(dropzoneId);
    const fileInput = document.getElementById(fileInputId);
    const listContainer = document.getElementById(listId);

    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
    });

    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('dragover');
    });

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        const files = e.dataTransfer.files;
        const dt = new DataTransfer();
        for (let f of files) {
            if (f.name.endsWith('.pdf') || f.name.endsWith('.xlsx') || f.name.endsWith('.xls')) {
                dt.items.add(f);
            }
        }
        fileInput.files = dt.files;
        updateFileList(fileInput.files, listContainer);
    });

    fileInput.addEventListener('change', () => {
        updateFileList(fileInput.files, listContainer);
    });
}

function updateFileList(files, container) {
    container.innerHTML = '';
    for (let f of files) {
        const div = document.createElement('div');
        div.textContent = '📄 ' + f.name;
        container.appendChild(div);
    }
}

// ================= SETUP DROPZONES =================
setupDropzone('dropzone-codigos', 'file-codigos', 'files-codigos');
setupDropzone('dropzone-grupos', 'file-grupos', 'files-grupos');

// Excel dropzone (single file)
const dropzoneExcel = document.getElementById('dropzone-excel');
const fileExcelInput = document.getElementById('file-excel');
const excelName = document.getElementById('file-excel-name');

dropzoneExcel.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzoneExcel.classList.add('dragover');
});

dropzoneExcel.addEventListener('dragleave', () => {
    dropzoneExcel.classList.remove('dragover');
});

dropzoneExcel.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzoneExcel.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) {
        const f = e.dataTransfer.files[0];
        if (f.name.endsWith('.xlsx') || f.name.endsWith('.xls')) {
            const dt = new DataTransfer();
            dt.items.add(f);
            fileExcelInput.files = dt.files;
            excelName.textContent = '📊 ' + f.name;
        }
    }
});

fileExcelInput.addEventListener('change', () => {
    if (fileExcelInput.files.length > 0) {
        excelName.textContent = '📊 ' + fileExcelInput.files[0].name;
    }
});

// ================= BUSCAR POR CÓDIGOS =================
let pdfGlobalBase64 = null;

document.getElementById('btn-buscar-codigos').addEventListener('click', async () => {
    const codigos = document.getElementById('codigos-input').value.trim();
    const files = document.getElementById('file-codigos').files;

    if (!codigos) {
        alert('Ingresa al menos un código de factura');
        return;
    }

    if (files.length === 0) {
        alert('Sube al menos un archivo PDF');
        return;
    }

    const btn = document.getElementById('btn-buscar-codigos');
    btn.disabled = true;
    btn.textContent = '🔄 Buscando...';

    const formData = new FormData();
    formData.append('codigos', codigos);
    for (let f of files) {
        formData.append('pdfs', f);
    }

    try {
        const res = await fetch('/buscar-codigos', {
            method: 'POST',
            body: formData
        });

        const data = await res.json();

        pdfGlobalBase64 = data.pdf_global || null;

        const container = document.getElementById('resultados-codigos');
        container.classList.remove('hidden');

        const resumen = document.getElementById('resumen-codigos');
        resumen.innerHTML = `
            <span class="resumen-item encontradas">✅ Encontradas: ${data.encontradas.length}</span>
            <span class="resumen-item no-encontradas">❌ No encontradas: ${data.no_encontradas.length}</span>
        `;

        const listaEncontradas = document.getElementById('lista-encontradas');
        listaEncontradas.innerHTML = '<h4>Facturas encontradas:</h4>';
        if (data.encontradas.length > 0) {
            for (let f of data.encontradas) {
                const tag = document.createElement('span');
                tag.className = 'encontrada-tag';
                tag.textContent = f;
                listaEncontradas.appendChild(tag);
            }
        } else {
            listaEncontradas.innerHTML += '<p style="color:#666">Ninguna</p>';
        }

        const listaNo = document.getElementById('lista-no-encontradas');
        if (data.no_encontradas.length > 0) {
            listaNo.innerHTML = `
                <div class="no-encontradas-section">
                    <h4>❌ No encontradas:</h4>
                    ${data.no_encontradas.map(f => `<div class="no-factura">${f}</div>`).join('')}
                </div>
            `;
        } else {
            listaNo.innerHTML = '';
        }

        const btnDownload = document.getElementById('btn-descargar-pdf');
        if (pdfGlobalBase64) {
            btnDownload.classList.remove('hidden');
        }

    } catch (err) {
        alert('Error: ' + err.message);
    } finally {
        btn.disabled = false;
        btn.textContent = '🔍 Buscar';
    }
});

// Descargar PDF combinado
document.getElementById('btn-descargar-pdf').addEventListener('click', () => {
    if (!pdfGlobalBase64) return;
    const binary = atob(pdfGlobalBase64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
    }
    const blob = new Blob([bytes], { type: 'application/pdf' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'TODAS_LAS_FACTURAS.pdf';
    a.click();
    URL.revokeObjectURL(url);
});

// ================= BUSCAR POR GRUPOS =================
document.getElementById('btn-buscar-grupos').addEventListener('click', async () => {
    const excelFile = document.getElementById('file-excel').files[0];
    const pdfFiles = document.getElementById('file-grupos').files;

    if (!excelFile) {
        alert('Sube el archivo Excel');
        return;
    }

    if (pdfFiles.length === 0) {
        alert('Sube al menos un archivo PDF');
        return;
    }

    const btn = document.getElementById('btn-buscar-grupos');
    btn.disabled = true;
    btn.textContent = '🔄 Buscando...';

    const formData = new FormData();
    formData.append('excel', excelFile);
    for (let f of pdfFiles) {
        formData.append('pdfs', f);
    }

    try {
        const res = await fetch('/buscar-grupos', {
            method: 'POST',
            body: formData
        });

        const data = await res.json();

        const container = document.getElementById('resultados-grupos');
        container.classList.remove('hidden');

        const gruposKeys = Object.keys(data.grupos || {});

        document.getElementById('resumen-grupos').innerHTML = `
            <span class="resumen-item grupos">🏢 Grupos con facturas: ${gruposKeys.length}</span>
            <span class="resumen-item no-encontradas">❌ No encontradas: ${data.no_encontradas.length}</span>
        `;

        const listaGrupos = document.getElementById('lista-grupos');
        listaGrupos.innerHTML = '';

        if (gruposKeys.length === 0) {
            listaGrupos.innerHTML = '<p style="color:#666">No se encontraron facturas de grupos válidos</p>';
        } else {
            for (let grupo of gruposKeys) {
                const card = document.createElement('div');
                card.className = 'grupo-card';

                const facturas = data.grupos[grupo];
                let facturasHtml = facturas.map(f =>
                    `<div class="factura-item"><span>${f.codigo}</span> — pág. ${f.paginas.join(', ')}</div>`
                ).join('');

                card.innerHTML = `
                    <h4>🏢 ${grupo}</h4>
                    ${facturasHtml}
                `;
                listaGrupos.appendChild(card);
            }
        }

        if (data.no_encontradas.length > 0) {
            const noSection = document.createElement('div');
            noSection.className = 'no-encontradas-section';
            noSection.innerHTML = `
                <h4>❌ Facturas no encontradas:</h4>
                ${data.no_encontradas.map(f => `<div class="no-factura">${f}</div>`).join('')}
            `;
            listaGrupos.appendChild(noSection);
        }

    } catch (err) {
        alert('Error: ' + err.message);
    } finally {
        btn.disabled = false;
        btn.textContent = '🔍 Buscar';
    }
});
