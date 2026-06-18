let selectedFile = null;

function updateCharCount() {
    const text = document.getElementById('textInput').value;
    document.getElementById('charCount').innerText = `${text.length} characters`;
}

function handleFileSelect() {
    const fileInput = document.getElementById('fileInput');
    const fileLabel = document.getElementById('fileLabel');
    const clearFileBtn = document.getElementById('clearFileBtn');

    if (fileInput.files.length > 0) {
        selectedFile = fileInput.files[0];
        fileLabel.innerText = selectedFile.name;
        clearFileBtn.classList.remove('hidden');
    } else {
        selectedFile = null;
        fileLabel.innerText = "Choose .txt, .docx, or .pdf file";
        clearFileBtn.classList.add('hidden');
    }
}

function clearFile() {
    selectedFile = null;
    document.getElementById('fileInput').value = '';
    document.getElementById('fileLabel').innerText = "Choose .txt, .docx, or .pdf file";
    document.getElementById('clearFileBtn').classList.add('hidden');
}

async function runScan() {
    const textInput = document.getElementById('textInput').value;
    const scanBtn = document.getElementById('scanBtn');
    const placeholderCard = document.getElementById('placeholderCard');
    const resultsArea = document.getElementById('resultsArea');
    const scoreBadge = document.getElementById('scoreBadge');
    const verdictText = document.getElementById('verdictText');
    const suggestionList = document.getElementById('suggestionList');

    if (!textInput.trim() && !selectedFile) {
        alert("Please paste some text or upload a file before scanning.");
        return;
    }

    scanBtn.innerHTML = `
        <svg class="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg> Scanning...`;
    scanBtn.disabled = true;

    try {
        const formData = new FormData();

        // File takes priority over pasted text, matching backend behavior
        if (selectedFile) {
            formData.append('file', selectedFile);
        } else {
            formData.append('text', textInput);
        }

        const response = await fetch('http://127.0.0.1:8000/detect', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errBody = await response.json().catch(() => null);
            throw new Error(errBody?.detail || "Server connection error");
        }

        const result = await response.json();

        placeholderCard.classList.add('hidden');
        resultsArea.classList.remove('hidden');

        scoreBadge.innerText = `${result.percentage}%`;

        if (result.percentage >= 50) {
            scoreBadge.className = "text-4xl font-black tracking-tight text-rose-600";
            verdictText.innerText = "High Risk Level";
            verdictText.className = "text-sm font-bold text-rose-600 mt-0.5";
        } else if (result.percentage >= 20) {
            scoreBadge.className = "text-4xl font-black tracking-tight text-amber-500";
            verdictText.innerText = "Moderate Variation";
            verdictText.className = "text-sm font-bold text-amber-500 mt-0.5";
        } else {
            scoreBadge.className = "text-4xl font-black tracking-tight text-emerald-600";
            verdictText.innerText = "Clear Safe Margin";
            verdictText.className = "text-sm font-bold text-emerald-600 mt-0.5";
        }

        suggestionList.innerHTML = '';
        let advice = [];

        if (result.percentage >= 50) {
            advice.push("⚠️ <b>Vary sentence rhythm:</b> Try mixing shorter, direct sentences with your longer compound phrases.");
            advice.push("💡 <b>Inject contextual evidence:</b> Add specific examples or personal arguments to disrupt predictable text styles.");
        } else if (result.percentage >= 20) {
            advice.push("🔄 <b>Flip structural perspectives:</b> Try rewriting passive voice sections into an active voice.");
            advice.push("✍️ <b>Rethink text connectors:</b> Change heavy academic connectors like <i>'Furthermore'</i> or <i>'Consequently'</i> to simpler transitions.");
        } else {
            advice.push("✨ <b>Strong individual flow:</b> The text patterns look highly organic and well-varied.");
        }

        advice.forEach(text => {
            const li = document.createElement('li');
            li.className = "border-l-2 border-cyan-500/40 pl-3 py-0.5";
            li.innerHTML = text;
            suggestionList.appendChild(li);
        });

    } catch (err) {
        alert(err.message || "Could not connect to the backend server.");
        console.error(err);
    } finally {
        scanBtn.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4">
                <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.602 10.602z" />
            </svg> Analyze Writing Cadence`;
        scanBtn.disabled = false;
    }
}