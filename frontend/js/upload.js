function initUpload() {
    // 1. Transaction CSV Dropzone
    const csvDropZone = document.getElementById('csv-drop-zone');
    const csvFileInput = document.getElementById('csv-file-input');
    const csvStatus = document.getElementById('csv-upload-status');

    if (csvDropZone && csvFileInput) {
        csvDropZone.addEventListener('click', () => csvFileInput.click());

        csvDropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            csvDropZone.classList.add('dragover');
        });

        csvDropZone.addEventListener('dragleave', () => csvDropZone.classList.remove('dragover'));

        csvDropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            csvDropZone.classList.remove('dragover');
            if (e.dataTransfer.files.length) {
                handleCSVUpload(e.dataTransfer.files[0]);
            }
        });

        csvFileInput.addEventListener('change', () => {
            if (csvFileInput.files.length) {
                handleCSVUpload(csvFileInput.files[0]);
            }
        });
    }

    // 2. Policy Document Dropzone
    const docDropZone = document.getElementById('doc-drop-zone');
    const docFileInput = document.getElementById('doc-file-input');
    const docStatus = document.getElementById('doc-upload-status');

    if (docDropZone && docFileInput) {
        docDropZone.addEventListener('click', () => docFileInput.click());

        docDropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            docDropZone.classList.add('dragover');
        });

        docDropZone.addEventListener('dragleave', () => docDropZone.classList.remove('dragover'));

        docDropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            docDropZone.classList.remove('dragover');
            if (e.dataTransfer.files.length) {
                handleDocUpload(e.dataTransfer.files[0]);
            }
        });

        docFileInput.addEventListener('change', () => {
            if (docFileInput.files.length) {
                handleDocUpload(docFileInput.files[0]);
            }
        });
    }

    async function handleCSVUpload(file) {
        if (!csvStatus) return;
        csvStatus.innerHTML = `<p class="text-muted"><i class="fa-solid fa-spinner fa-spin"></i> Uploading & parsing ${file.name}...</p>`;
        const formData = new FormData();
        formData.append('file', file);

        try {
            const compId = window.currentCompanyId || (window.currentUser ? window.currentUser.company_id : 1);
            const res = await fetch(`/api/upload/transactions?company_id=${compId}`, {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if (res.ok) {
                csvStatus.innerHTML = `<p class="kpi-sub positive"><i class="fa-solid fa-circle-check"></i> Success! Ingested ${data.added_transactions} transactions into database.</p>`;
                if (window.loadOverviewData) window.loadOverviewData();
            } else {
                csvStatus.innerHTML = `<p class="kpi-sub danger"><i class="fa-solid fa-triangle-exclamation"></i> Error: ${data.detail || 'Upload failed'}</p>`;
            }
        } catch (e) {
            csvStatus.innerHTML = `<p class="kpi-sub danger"><i class="fa-solid fa-triangle-exclamation"></i> Upload Error: ${e.message}</p>`;
        }
    }

    async function handleDocUpload(file) {
        if (!docStatus) return;
        docStatus.innerHTML = `<p class="text-muted"><i class="fa-solid fa-spinner fa-spin"></i> Indexing ${file.name} into RAG vector store...</p>`;
        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await fetch('/api/upload/document', {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if (res.ok) {
                docStatus.innerHTML = `<p class="kpi-sub positive"><i class="fa-solid fa-circle-check"></i> Success! Indexed ${data.indexed_chunks} text chunks into ChromaDB Vector Store.</p>`;
            } else {
                docStatus.innerHTML = `<p class="kpi-sub danger"><i class="fa-solid fa-triangle-exclamation"></i> Error: ${data.detail || 'Indexing failed'}</p>`;
            }
        } catch (e) {
            docStatus.innerHTML = `<p class="kpi-sub danger"><i class="fa-solid fa-triangle-exclamation"></i> Upload Error: ${e.message}</p>`;
        }
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initUpload);
} else {
    initUpload();
}
