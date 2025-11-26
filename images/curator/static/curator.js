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
const newImagesSectionEl = document.getElementById('new-images-section');
const newImagesGridEl = document.getElementById('new-images-grid');
const curatedImagesSectionEl = document.getElementById('curated-images-section');
const curatedImagesGridEl = document.getElementById('curated-images-grid');
const submitBtn = document.getElementById('submit-btn');
const submitBtnBottom = document.getElementById('submit-btn-bottom');
const rejectAllBtn = document.getElementById('reject-all-btn');
const rejectAllBtnBottom = document.getElementById('reject-all-btn-bottom');
const rejectAllNewBtn = document.getElementById('reject-all-new-btn');
const rejectAllNewBtnBottom = document.getElementById('reject-all-new-btn-bottom');
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

        // Initialize decisions from existing curation_result or default to approved
        data.images.forEach(img => {
            if (img.curation_result) {
                imageDecisions[img.filename] = img.curation_result;
            } else {
                imageDecisions[img.filename] = 'approved';
            }
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

    // Clear both grids
    newImagesGridEl.innerHTML = '';
    curatedImagesGridEl.innerHTML = '';

    // Separate images into new and previously curated
    const newImages = [];
    const curatedImages = [];

    camp.images.forEach(img => {
        if (img.curation_result) {
            curatedImages.push(img);
        } else {
            newImages.push(img);
        }
    });

    // Populate new images section
    if (newImages.length > 0) {
        newImagesSectionEl.style.display = 'block';
        newImages.forEach(img => {
            const imageItem = createImageItem(img, camp.camp_name);
            newImagesGridEl.appendChild(imageItem);
        });
    } else {
        newImagesSectionEl.style.display = 'none';
    }

    // Populate curated images section
    if (curatedImages.length > 0) {
        curatedImagesSectionEl.style.display = 'block';
        curatedImages.forEach(img => {
            const imageItem = createImageItem(img, camp.camp_name);
            curatedImagesGridEl.appendChild(imageItem);
        });
    } else {
        curatedImagesSectionEl.style.display = 'none';
    }
}

// Create an image item element
function createImageItem(img, campName) {
    const div = document.createElement('div');
    div.className = 'image-item';
    div.dataset.filename = img.filename;

    // Set initial state based on existing curation result
    const currentDecision = imageDecisions[img.filename];
    if (currentDecision === 'rejected') {
        div.classList.add('rejected');
    } else if (currentDecision === 'approved') {
        div.classList.add('approved');
    }

    // Image element
    const imgEl = document.createElement('img');
    imgEl.src = `/candidates/${encodeURIComponent(campName)}/${encodeURIComponent(img.filename)}`;
    imgEl.alt = img.filename;
    imgEl.loading = 'lazy';

    // Reject badge (red X)
    const rejectBadge = document.createElement('div');
    rejectBadge.className = 'reject-badge';
    rejectBadge.innerHTML = '<div class="badge-circle badge-reject">✕</div>';

    // Approve badge (green check)
    const approveBadge = document.createElement('div');
    approveBadge.className = 'approve-badge';
    approveBadge.innerHTML = '<div class="badge-circle badge-approve">✓</div>';

    // Image info
    const info = document.createElement('div');
    info.className = 'image-info';

    const filename = document.createElement('div');
    filename.className = 'filename';
    filename.textContent = img.filename;

    const dimensions = document.createElement('div');
    dimensions.className = 'dimensions';
    dimensions.textContent = `${img.width} × ${img.height}`;

    // Year and photographer (if available)
    let creditEl = null;
    if (img.photographer || img.year) {
        creditEl = document.createElement('div');
        creditEl.className = 'image-credit';
        let creditText = '';
        if (img.photographer && img.year) {
            creditText = `Photo by ${img.photographer} (${img.year})`;
        } else if (img.photographer) {
            creditText = `Photo by ${img.photographer}`;
        } else if (img.year) {
            creditText = `Photo from ${img.year}`;
        }
        creditEl.textContent = creditText;
    }

    // Title (if available)
    let titleEl = null;
    if (img.title) {
        titleEl = document.createElement('div');
        titleEl.className = 'image-title';
        titleEl.textContent = img.title;
    }

    // Caption (if available)
    let captionEl = null;
    if (img.caption) {
        captionEl = document.createElement('div');
        captionEl.className = 'image-caption';
        captionEl.textContent = img.caption;
    }

    const source = document.createElement('div');
    source.className = 'source';
    const sourceLink = document.createElement('a');
    const sourceUrl = img.source_page_url || img.image_url;
    sourceLink.href = sourceUrl;
    sourceLink.target = '_blank';
    sourceLink.rel = 'noopener';
    // Extract domain name from URL
    try {
        const url = new URL(sourceUrl);
        sourceLink.textContent = url.hostname;
    } catch (e) {
        sourceLink.textContent = 'Source';
    }
    sourceLink.onclick = (e) => e.stopPropagation(); // Prevent toggle when clicking link
    source.appendChild(sourceLink);

    info.appendChild(filename);
    info.appendChild(dimensions);
    if (creditEl) info.appendChild(creditEl);
    if (titleEl) info.appendChild(titleEl);
    if (captionEl) info.appendChild(captionEl);
    info.appendChild(source);

    div.appendChild(imgEl);
    div.appendChild(rejectBadge);
    div.appendChild(approveBadge);
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
        imageItem.classList.remove('approved');
        imageItem.classList.add('rejected');

        // If we're in hiding mode, change button to "Rehide Rejected"
        if (rejectedHidden) {
            toggleRejectedBtn.textContent = 'Rehide Rejected';
            toggleRejectedBtnBottom.textContent = 'Rehide Rejected';
        }
    } else {
        imageDecisions[filename] = 'approved';
        imageItem.classList.remove('rejected');
        imageItem.classList.add('approved');
    }
}

// Reject all images
function rejectAll() {
    Object.keys(imageDecisions).forEach(filename => {
        imageDecisions[filename] = 'rejected';
    });

    document.querySelectorAll('.image-item').forEach(item => {
        item.classList.remove('approved');
        item.classList.add('rejected');
    });
}

// Reject all new images (leave previously curated images unchanged)
function rejectAllNew() {
    if (!currentCamp) return;

    // Find images that are new (no curation_result)
    const newImageFilenames = currentCamp.images
        .filter(img => !img.curation_result)
        .map(img => img.filename);

    // Update decisions for new images only
    newImageFilenames.forEach(filename => {
        imageDecisions[filename] = 'rejected';
    });

    // Update DOM for new images only
    document.querySelectorAll('.image-item').forEach(item => {
        const filename = item.dataset.filename;
        if (newImageFilenames.includes(filename)) {
            item.classList.remove('approved');
            item.classList.add('rejected');
        }
    });
}

// Accept all images
function acceptAll() {
    Object.keys(imageDecisions).forEach(filename => {
        imageDecisions[filename] = 'approved';
    });

    document.querySelectorAll('.image-item').forEach(item => {
        item.classList.remove('rejected');
        item.classList.add('approved');
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
rejectAllNewBtn.addEventListener('click', rejectAllNew);
rejectAllNewBtnBottom.addEventListener('click', rejectAllNew);
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
