// Current camp data
let currentCamp = null;
let imageDecisions = {}; // filename -> 'approved' or 'rejected'
let rejectedHidden = false; // Track whether rejected images are hidden

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
const rejectAllBtnBottom = document.getElementById('reject-all-btn-bottom');
const acceptAllBtn = document.getElementById('accept-all-btn');
const acceptAllBtnBottom = document.getElementById('accept-all-btn-bottom');
const toggleRejectedBtn = document.getElementById('toggle-rejected-btn');
const toggleRejectedBtnBottom = document.getElementById('toggle-rejected-btn-bottom');

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
        rejectedHidden = false;
        toggleRejectedBtn.textContent = 'Hide Rejected';
        toggleRejectedBtnBottom.textContent = 'Hide Rejected';

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

        // If we're in hiding mode, change button to "Rehide Rejected"
        if (rejectedHidden) {
            toggleRejectedBtn.textContent = 'Rehide Rejected';
            toggleRejectedBtnBottom.textContent = 'Rehide Rejected';
        }
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

// Toggle visibility of rejected images
function toggleRejectedVisibility() {
    const currentButtonText = toggleRejectedBtn.textContent;

    // If button says "Rehide Rejected", just hide all rejected images
    // and change back to "Show Rejected" without toggling rejectedHidden
    if (currentButtonText === 'Rehide Rejected') {
        document.querySelectorAll('.image-item').forEach(item => {
            if (item.classList.contains('rejected')) {
                item.style.display = 'none';
            }
        });
        toggleRejectedBtn.textContent = 'Show Rejected';
        toggleRejectedBtnBottom.textContent = 'Show Rejected';
        // rejectedHidden remains true
        return;
    }

    // Normal toggle behavior
    rejectedHidden = !rejectedHidden;

    document.querySelectorAll('.image-item').forEach(item => {
        if (item.classList.contains('rejected')) {
            if (rejectedHidden) {
                item.style.display = 'none';
            } else {
                item.style.display = 'inline-block';
            }
        }
    });

    // Update button text
    toggleRejectedBtn.textContent = rejectedHidden ? 'Show Rejected' : 'Hide Rejected';
    toggleRejectedBtnBottom.textContent = rejectedHidden ? 'Show Rejected' : 'Hide Rejected';
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
rejectAllBtnBottom.addEventListener('click', rejectAll);
acceptAllBtn.addEventListener('click', acceptAll);
acceptAllBtnBottom.addEventListener('click', acceptAll);
toggleRejectedBtn.addEventListener('click', toggleRejectedVisibility);
toggleRejectedBtnBottom.addEventListener('click', toggleRejectedVisibility);

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Enter to submit (only with Cmd/Ctrl modifier to avoid conflicts)
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        submitCuration();
    }
});

// Start the app
init();
