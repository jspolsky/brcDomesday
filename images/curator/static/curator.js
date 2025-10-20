// Current camp data
let currentCamp = null;
let imageDecisions = {}; // filename -> 'approved' or 'rejected'

// DOM elements
const statusEl = document.getElementById('status');
const completeMessageEl = document.getElementById('complete-message');
const campContentEl = document.getElementById('camp-content');
const campNameEl = document.getElementById('camp-name');
const campUrlEl = document.getElementById('camp-url');
const campDescriptionEl = document.getElementById('camp-description');
const imageGridEl = document.getElementById('image-grid');
const submitBtn = document.getElementById('submit-btn');
const submitBtnBottom = document.getElementById('submit-btn-bottom');
const rejectAllBtn = document.getElementById('reject-all-btn');
const acceptAllBtn = document.getElementById('accept-all-btn');

// Initialize
async function init() {
    await loadNextCamp();
}

// Load the next camp that needs curation
async function loadNextCamp() {
    try {
        statusEl.textContent = 'Loading next camp...';

        const response = await fetch('/api/next-camp');
        const data = await response.json();

        if (data.status === 'complete') {
            // All camps curated
            campContentEl.style.display = 'none';
            completeMessageEl.style.display = 'block';
            statusEl.textContent = 'All camps curated!';
            return;
        }

        currentCamp = data;
        imageDecisions = {};

        // Initialize all images as approved
        data.images.forEach(img => {
            imageDecisions[img.filename] = 'approved';
        });

        displayCamp(data);
        statusEl.textContent = `Curating: ${data.camp_name}`;

    } catch (error) {
        console.error('Error loading next camp:', error);
        statusEl.textContent = 'Error loading camp: ' + error.message;
    }
}

// Display camp information and images
function displayCamp(camp) {
    campContentEl.style.display = 'block';
    completeMessageEl.style.display = 'none';

    // Set camp header
    campNameEl.textContent = camp.camp_name;
    campUrlEl.href = camp.url || '#';
    if (!camp.url) {
        campUrlEl.style.display = 'none';
    } else {
        campUrlEl.style.display = 'inline';
    }

    // Set description
    campDescriptionEl.textContent = camp.description || 'No description available.';

    // Clear and populate image grid
    imageGridEl.innerHTML = '';

    camp.images.forEach(img => {
        const imageItem = createImageItem(img, camp.camp_name);
        imageGridEl.appendChild(imageItem);
    });
}

// Create an image item element
function createImageItem(img, campName) {
    const div = document.createElement('div');
    div.className = 'image-item';
    div.dataset.filename = img.filename;

    // Image element
    const imgEl = document.createElement('img');
    imgEl.src = `/candidates/${encodeURIComponent(campName)}/${encodeURIComponent(img.filename)}`;
    imgEl.alt = img.filename;
    imgEl.loading = 'lazy';

    // Reject badge
    const badge = document.createElement('div');
    badge.className = 'reject-badge';
    badge.textContent = '🚫';

    // Image info
    const info = document.createElement('div');
    info.className = 'image-info';

    const filename = document.createElement('div');
    filename.className = 'filename';
    filename.textContent = img.filename;

    const dimensions = document.createElement('div');
    dimensions.className = 'dimensions';
    dimensions.textContent = `${img.width} × ${img.height}`;

    const source = document.createElement('div');
    source.className = 'source';
    const sourceLink = document.createElement('a');
    sourceLink.href = img.source_page_url || img.image_url;
    sourceLink.target = '_blank';
    sourceLink.rel = 'noopener';
    sourceLink.textContent = 'Source';
    sourceLink.onclick = (e) => e.stopPropagation(); // Prevent toggle when clicking link
    source.appendChild(sourceLink);

    info.appendChild(filename);
    info.appendChild(dimensions);
    info.appendChild(source);

    div.appendChild(imgEl);
    div.appendChild(badge);
    div.appendChild(info);

    // Click handler to toggle rejection
    div.addEventListener('click', () => {
        toggleImageRejection(div, img.filename);
    });

    return div;
}

// Toggle image rejection state
function toggleImageRejection(imageItem, filename) {
    const currentDecision = imageDecisions[filename];

    if (currentDecision === 'approved') {
        imageDecisions[filename] = 'rejected';
        imageItem.classList.add('rejected');
    } else {
        imageDecisions[filename] = 'approved';
        imageItem.classList.remove('rejected');
    }
}

// Reject all images
function rejectAll() {
    Object.keys(imageDecisions).forEach(filename => {
        imageDecisions[filename] = 'rejected';
    });

    document.querySelectorAll('.image-item').forEach(item => {
        item.classList.add('rejected');
    });
}

// Accept all images
function acceptAll() {
    Object.keys(imageDecisions).forEach(filename => {
        imageDecisions[filename] = 'approved';
    });

    document.querySelectorAll('.image-item').forEach(item => {
        item.classList.remove('rejected');
    });
}

// Submit curation decisions
async function submitCuration() {
    if (!currentCamp) return;

    try {
        statusEl.textContent = 'Saving curation decisions...';
        submitBtn.disabled = true;
        submitBtnBottom.disabled = true;

        const response = await fetch('/api/curate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                camp_name: currentCamp.camp_name,
                decisions: imageDecisions
            })
        });

        const result = await response.json();

        if (result.status === 'ok') {
            statusEl.textContent = 'Saved! Loading next camp...';
            // Load next camp after short delay
            setTimeout(() => {
                loadNextCamp();
                submitBtn.disabled = false;
                submitBtnBottom.disabled = false;
            }, 500);
        } else {
            throw new Error(result.message || 'Failed to save curation');
        }

    } catch (error) {
        console.error('Error submitting curation:', error);
        statusEl.textContent = 'Error saving: ' + error.message;
        submitBtn.disabled = false;
        submitBtnBottom.disabled = false;
    }
}

// Event listeners
submitBtn.addEventListener('click', submitCuration);
submitBtnBottom.addEventListener('click', submitCuration);
rejectAllBtn.addEventListener('click', rejectAll);
acceptAllBtn.addEventListener('click', acceptAll);

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Enter to submit
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
        submitCuration();
    }
    // R to reject all
    if (e.key === 'r' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        rejectAll();
    }
    // A to accept all
    if (e.key === 'a' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        acceptAll();
    }
});

// Start the app
init();
