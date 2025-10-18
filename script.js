// Canvas and rendering setup
const demomode = true;
const canvas = document.getElementById('mapCanvas');
const ctx = canvas.getContext('2d');
const loadingStatus = document.getElementById('loadingStatus');

// Data storage
let campOutlines = null;
let campNames = null;
let showNames = true;
let showOutlines = true;
let allCampNames = []; // For autocomplete

// Camp highlighting
let highlightedCamp = null;
let lastDiagnostic = '';

// Camp naming system
let campNamingMode = false;
let currentNamingFID = 1;
let campMappings = {}; // FID -> camp name mapping
let allFIDs = []; // Array of all FID numbers from the data

// View settings
let viewport = {
    centerX: -119.22, // Approximate center of Black Rock City
    centerY: 40.782,
    scale: 5000, // Adjust this for initial zoom level
    offsetX: 0,
    offsetY: 0
};

// Geographic bounds for Black Rock City area
const BRC_BOUNDS = {
    minLon: -119.26,
    maxLon: -119.19,
    minLat: 40.78,
    maxLat: 40.79
};

// Resize canvas to match container
function resizeCanvas() {
    const container = document.getElementById('mapContainer');
    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;
    redraw();
}

// Convert geographic coordinates to canvas coordinates
function geoToCanvas(lon, lat) {
    // Convert longitude/latitude to canvas coordinates
    // Account for the fact that latitude needs to be scaled differently due to Earth's projection
    const latScale = Math.cos(viewport.centerY * Math.PI / 180); // Mercator-like adjustment

    const x = canvas.width / 2 + (lon - viewport.centerX) * viewport.scale * latScale;
    const y = canvas.height / 2 - (lat - viewport.centerY) * viewport.scale;

    return { x, y };
}

// Convert canvas coordinates back to geographic coordinates
function canvasToGeo(canvasX, canvasY) {
    const latScale = Math.cos(viewport.centerY * Math.PI / 180);

    const lon = viewport.centerX + (canvasX - canvas.width / 2) / (viewport.scale * latScale);
    const lat = viewport.centerY - (canvasY - canvas.height / 2) / viewport.scale;

    return { lon, lat };
}

// Point-in-polygon test using ray casting algorithm
function isPointInPolygon(lon, lat, coordinates) {
    let inside = false;
    const x = lon;
    const y = lat;

    for (let i = 0, j = coordinates.length - 1; i < coordinates.length; j = i++) {
        const xi = coordinates[i][0];
        const yi = coordinates[i][1];
        const xj = coordinates[j][0];
        const yj = coordinates[j][1];

        if (((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi)) {
            inside = !inside;
        }
    }

    return inside;
}

// Find which camp contains the given geographic coordinate (with diagnostics)
function findCampAtLocation(lon, lat) {
    lastDiagnostic = ''; // Reset diagnostic message

    if (!campOutlines) {
        lastDiagnostic = 'No camp outline data loaded';
        return null;
    }

    let totalFeatures = 0;
    let lineStringFeatures = 0;
    let validLengthFeatures = 0;
    let closedPolygons = 0;
    let testedFeatures = [];

    for (const feature of campOutlines.features) {
        totalFeatures++;

        if (feature.geometry.type === 'LineString') {
            lineStringFeatures++;
            const coordinates = feature.geometry.coordinates;

            // Check if the coordinates form a closed polygon
            if (coordinates.length > 3) {
                validLengthFeatures++;
                const first = coordinates[0];
                const last = coordinates[coordinates.length - 1];
                const tolerance = 0.000001;
                const isClosed = Math.abs(first[0] - last[0]) < tolerance &&
                    Math.abs(first[1] - last[1]) < tolerance;

                if (isClosed) {
                    closedPolygons++;

                    // Test if point is inside this polygon
                    if (isPointInPolygon(lon, lat, coordinates)) {
                        return feature; // Found it!
                    }

                    // For debugging, track some tested features
                    if (testedFeatures.length < 3) {
                        const fid = feature.properties ? feature.properties.fid : 'unknown';
                        testedFeatures.push(fid);
                    }
                }
            }
        }
    }

    // Generate diagnostic message
    const parts = [];
    parts.push(`${totalFeatures} total features`);
    parts.push(`${lineStringFeatures} LineStrings`);
    parts.push(`${validLengthFeatures} valid length`);
    parts.push(`${closedPolygons} closed polygons`);

    if (testedFeatures.length > 0) {
        parts.push(`tested: ${testedFeatures.join(', ')}`);
    }

    lastDiagnostic = `No match found: ${parts.join(', ')}`;
    return null;
}

// Draw a LineString feature
function drawLineString(coordinates, color, lineWidth = 1) {
    if (coordinates.length < 2) return;

    ctx.strokeStyle = color;
    ctx.lineWidth = lineWidth;
    ctx.beginPath();

    const startPoint = geoToCanvas(coordinates[0][0], coordinates[0][1]);
    ctx.moveTo(startPoint.x, startPoint.y);

    for (let i = 1; i < coordinates.length; i++) {
        const point = geoToCanvas(coordinates[i][0], coordinates[i][1]);
        ctx.lineTo(point.x, point.y);
    }

    ctx.stroke();
}

// Draw a filled polygon
function fillPolygon(coordinates, color) {
    if (coordinates.length < 3) return;

    ctx.fillStyle = color;
    ctx.beginPath();

    const startPoint = geoToCanvas(coordinates[0][0], coordinates[0][1]);
    ctx.moveTo(startPoint.x, startPoint.y);

    for (let i = 1; i < coordinates.length; i++) {
        const point = geoToCanvas(coordinates[i][0], coordinates[i][1]);
        ctx.lineTo(point.x, point.y);
    }

    ctx.closePath();
    ctx.fill();
}

// Calculate the centroid (geometric center) of a polygon
function calculateCentroid(coordinates) {
    if (coordinates.length === 0) return null;

    let sumLon = 0;
    let sumLat = 0;

    for (const coord of coordinates) {
        sumLon += coord[0];
        sumLat += coord[1];
    }

    return [sumLon / coordinates.length, sumLat / coordinates.length];
}

// Draw a star marker at a geographic location
function drawStarMarker(lon, lat, color = 'red', size = 12) {
    const canvasPoint = geoToCanvas(lon, lat);

    // Only draw if the point is visible on canvas
    if (canvasPoint.x >= 0 && canvasPoint.x <= canvas.width &&
        canvasPoint.y >= 0 && canvasPoint.y <= canvas.height) {

        ctx.font = `${size}px Arial`;
        ctx.fillStyle = color;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('⭐', canvasPoint.x, canvasPoint.y);
    }
}

// Render all data
function redraw() {
    // Clear canvas
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw camp outlines in light blue
    if (campOutlines && showOutlines) {
        campOutlines.features.forEach(feature => {
            if (feature.geometry.type === 'LineString') {
                const coordinates = feature.geometry.coordinates;

                // Fill highlighted camp with yellow background
                if (highlightedCamp && feature === highlightedCamp) {
                    fillPolygon(coordinates, 'rgba(255, 255, 0, 0.3)');
                }

                // Draw the outline
                const color = (highlightedCamp && feature === highlightedCamp) ? 'orange' : 'lightblue';
                const lineWidth = (highlightedCamp && feature === highlightedCamp) ? 3 : 2;
                drawLineString(coordinates, color, lineWidth);
            }
        });
    }

    // Mark unclosed polygons with red stars
    if (campOutlines && showOutlines) {
        campOutlines.features.forEach(feature => {
            if (feature.geometry.type === 'LineString') {
                const coordinates = feature.geometry.coordinates;

                // Check if this polygon is unclosed
                if (coordinates.length > 3) {
                    const first = coordinates[0];
                    const last = coordinates[coordinates.length - 1];
                    const tolerance = 0.000001;
                    const isClosed = Math.abs(first[0] - last[0]) < tolerance &&
                        Math.abs(first[1] - last[1]) < tolerance;

                    // If not closed, draw a red star at the centroid
                    if (!isClosed) {
                        const centroid = calculateCentroid(coordinates);
                        if (centroid) {
                            drawStarMarker(centroid[0], centroid[1], 'red', 16);
                        }
                    }
                }
            }
        });
    }

    // Draw camp names in black
    if (campNames && showNames) {
        campNames.features.forEach(feature => {
            if (feature.geometry.type === 'LineString') {
                drawLineString(feature.geometry.coordinates, 'black', 1);
            }
        });
    }
}

// Load GeoJSON data
async function loadGeoJSON(url) {
    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`Failed to load ${url}:`, error);
        return null;
    }
}

// Load camp names database for autocomplete
async function loadCampNamesDatabase() {
    try {
        const response = await fetch('data/camps.json');
        if (response.ok) {
            const camps = await response.json();
            allCampNames = camps.map(camp => camp.name).filter(name => name && name.trim());
            // Remove duplicates and sort
            allCampNames = [...new Set(allCampNames)].sort();
            console.log(`Loaded ${allCampNames.length} camp names for autocomplete`);
            return allCampNames;
        }
    } catch (error) {
        console.log('Could not load camp names database:', error);
    }
    return [];
}

// Load existing FID mappings if available
async function loadCampMappings() {

    if (!demomode) {

        // First try to load from data/camp_fid_mappings.json (preferred)
        try {
            const response = await fetch('data/camp_fid_mappings.json');
            if (response.ok) {
                const mappings = await response.json();
                campMappings = mappings;
                const loadedCount = Object.keys(mappings).length;
                console.log(`Loaded ${loadedCount} existing camp mappings from file`);

                // Update status to show mappings were loaded
                if (loadedCount > 0) {
                    loadingStatus.textContent = `Loaded ${loadedCount} existing camp mappings from file`;
                    setTimeout(() => {
                        loadingStatus.textContent = 'Ready';
                    }, 2000);
                }

                return mappings;
            }
        } catch (error) {
            console.log('No camp mappings file found, checking browser storage...');
        }
    }

    // Fallback: try localStorage
    try {
        const storedMappings = localStorage.getItem('brc_camp_mappings');
        if (storedMappings) {
            const mappings = JSON.parse(storedMappings);
            campMappings = mappings;
            const loadedCount = Object.keys(mappings).length;
            console.log(`Loaded ${loadedCount} existing camp mappings from browser storage`);

            if (loadedCount > 0) {
                loadingStatus.textContent = `Loaded ${loadedCount} camp mappings from browser storage`;
                setTimeout(() => {
                    loadingStatus.textContent = 'Ready';
                }, 2000);
            }

            return mappings;
        }
    } catch (error) {
        console.log('No browser storage mappings found');
    }

    console.log('Starting fresh - no existing mappings found');
    return {};
}

// Initialize the application
async function init() {
    loadingStatus.textContent = 'Loading camp outlines...';

    // Load camp outlines
    campOutlines = await loadGeoJSON('data/camp_outlines_2025.geojson');
    if (campOutlines) {
        document.getElementById('outlinesCount').textContent =
            `Camp Outlines: ${campOutlines.features.length}`;
    }

    loadingStatus.textContent = 'Loading camp names...';

    // Load camp names (this is the large file, so it might take a moment)
    campNames = await loadGeoJSON('data/camp_names_2025.geojson');
    if (campNames) {
        document.getElementById('namesCount').textContent =
            `Camp Names: ${campNames.features.length}`;
    }

    loadingStatus.textContent = 'Loading camp names database...';

    // Load camp names for autocomplete
    await loadCampNamesDatabase();

    loadingStatus.textContent = 'Loading existing camp mappings...';

    // Load existing camp FID mappings if available
    await loadCampMappings();

    // Extract all FIDs from camp outlines for progress tracking
    if (campOutlines) {
        allFIDs = campOutlines.features.map(f => f.properties.fid).sort((a, b) => a - b);
        console.log(`Found ${allFIDs.length} total camps for naming`);
    }

    // Update progress display with loaded mappings
    updateNamingProgress();

    const mappedCount = Object.keys(campMappings).length;
    if (mappedCount > 0) {
        console.log(`Found ${mappedCount} existing camp name mappings`);
    }

    loadingStatus.style.display = 'none';

    // Initial render
    resizeCanvas();
    zoomToFit();
}

// Calculate bounds from actual data
function calculateDataBounds() {
    let minLon = Infinity, maxLon = -Infinity;
    let minLat = Infinity, maxLat = -Infinity;

    // Check camp outlines
    if (campOutlines) {
        campOutlines.features.forEach(feature => {
            if (feature.geometry.type === 'LineString') {
                feature.geometry.coordinates.forEach(coord => {
                    const [lon, lat] = coord;
                    minLon = Math.min(minLon, lon);
                    maxLon = Math.max(maxLon, lon);
                    minLat = Math.min(minLat, lat);
                    maxLat = Math.max(maxLat, lat);
                });
            }
        });
    }

    // Check camp names for more comprehensive bounds
    if (campNames) {
        campNames.features.forEach(feature => {
            if (feature.geometry.type === 'LineString') {
                feature.geometry.coordinates.forEach(coord => {
                    const [lon, lat] = coord;
                    minLon = Math.min(minLon, lon);
                    maxLon = Math.max(maxLon, lon);
                    minLat = Math.min(minLat, lat);
                    maxLat = Math.max(maxLat, lat);
                });
            }
        });
    }

    return { minLon, maxLon, minLat, maxLat };
}

// Fit all data in the viewport
function zoomToFit() {
    // Calculate bounds from actual loaded data
    const bounds = calculateDataBounds();

    // Fall back to predefined bounds if no data is loaded
    if (!isFinite(bounds.minLon)) {
        bounds.minLon = BRC_BOUNDS.minLon;
        bounds.maxLon = BRC_BOUNDS.maxLon;
        bounds.minLat = BRC_BOUNDS.minLat;
        bounds.maxLat = BRC_BOUNDS.maxLat;
    }

    // Calculate the scale needed to fit the bounds in the canvas
    const latRange = bounds.maxLat - bounds.minLat;
    const lonRange = bounds.maxLon - bounds.minLon;

    const latScale = Math.cos(((bounds.maxLat + bounds.minLat) / 2) * Math.PI / 180);

    const scaleX = (canvas.width * 0.9) / (lonRange * latScale);
    const scaleY = (canvas.height * 0.9) / latRange;

    viewport.scale = Math.min(scaleX, scaleY);
    viewport.centerX = (bounds.maxLon + bounds.minLon) / 2;
    viewport.centerY = (bounds.maxLat + bounds.minLat) / 2;

    redraw();
}

// Toggle functions
function toggleNames() {
    showNames = !showNames;
    redraw();
}

function toggleOutlines() {
    showOutlines = !showOutlines;
    redraw();
}

// Camp naming system functions
function startCampMapping() {
    if (!campOutlines) {
        alert('Please wait for camp data to load first.');
        return;
    }

    // Extract all FIDs from the data
    allFIDs = campOutlines.features.map(feature => feature.properties.fid).sort((a, b) => a - b);

    campNamingMode = true;
    currentNamingFID = findNextUnnamedCamp();

    document.getElementById('campNamingSection').style.display = 'block';
    updateNamingProgress();

    if (currentNamingFID !== -1) {
        zoomToCamp(currentNamingFID);
    } else {
        alert('All camps have been named!');
        stopCampMapping();
    }
}

function stopCampMapping() {
    campNamingMode = false;
    document.getElementById('campNamingSection').style.display = 'none';
    highlightedCamp = null;
    redraw();
}

function findNextUnnamedCamp() {
    for (const fid of allFIDs) {
        if (!campMappings[fid]) {
            return fid;
        }
    }
    return -1; // All camps named
}

function zoomToCamp(fid) {
    const camp = campOutlines.features.find(f => f.properties.fid === fid);
    if (!camp) return;

    // Calculate camp bounds
    const coords = camp.geometry.coordinates;
    let minLon = Infinity, maxLon = -Infinity;
    let minLat = Infinity, maxLat = -Infinity;

    coords.forEach(coord => {
        minLon = Math.min(minLon, coord[0]);
        maxLon = Math.max(maxLon, coord[0]);
        minLat = Math.min(minLat, coord[1]);
        maxLat = Math.max(maxLat, coord[1]);
    });

    // Center on the camp
    viewport.centerX = (minLon + maxLon) / 2;
    viewport.centerY = (minLat + maxLat) / 2;

    // Zoom in to show the camp clearly
    const latRange = maxLat - minLat;
    const lonRange = maxLon - minLon;
    const latScale = Math.cos(viewport.centerY * Math.PI / 180);

    const scaleX = (canvas.width * 0.3) / (lonRange * latScale);
    const scaleY = (canvas.height * 0.3) / latRange;
    viewport.scale = Math.min(scaleX, scaleY);

    // Highlight the camp
    highlightedCamp = camp;

    // Update UI
    document.getElementById('currentFID').textContent = fid;
    document.getElementById('campNameInput').value = '';
    document.getElementById('campNameInput').focus();

    redraw();
}

function submitCampName() {
    const campName = document.getElementById('campNameInput').value.trim();
    if (!campName) {
        alert('Please enter a camp name.');
        return;
    }

    // Save the mapping
    campMappings[currentNamingFID] = campName;
    console.log(`Mapped FID ${currentNamingFID} -> "${campName}"`);

    // Auto-save to localStorage as backup
    localStorage.setItem('brc_camp_mappings', JSON.stringify(campMappings));

    // Move to next camp
    moveToNextCamp();
}

function skipCamp() {
    // Mark as skipped (empty string)
    campMappings[currentNamingFID] = '';
    console.log(`Skipped FID ${currentNamingFID}`);

    // Move to next camp
    moveToNextCamp();
}

function moveToNextCamp() {
    currentNamingFID = findNextUnnamedCamp();
    updateNamingProgress();

    if (currentNamingFID !== -1) {
        zoomToCamp(currentNamingFID);
    } else {
        alert('All camps have been processed! You can now save the mappings.');
        stopCampMapping();
    }
}

function updateNamingProgress() {
    const named = Object.keys(campMappings).length;
    const total = allFIDs.length;
    const percentage = total > 0 ? Math.round((named / total) * 100) : 0;

    let progressText = `Progress: ${named} / ${total} camps processed (${percentage}%)`;
    if (named > 0) {
        progressText += ` • ${named} camps named`;
    }

    document.getElementById('campProgress').textContent = progressText;
}

function saveMappings() {
    const dataStr = JSON.stringify(campMappings, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });

    const link = document.createElement('a');
    link.href = URL.createObjectURL(dataBlob);
    link.download = 'camp_fid_mappings.json';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    console.log('Camp mappings saved:', campMappings);

    // Show instructions for persistence
    const mappedCount = Object.keys(campMappings).length;
    alert(`Mappings downloaded! (${mappedCount} camps)\n\nTo make these mappings load automatically next time:\n1. Move the downloaded 'camp_fid_mappings.json' file\n2. From your Downloads folder\n3. To: data/camp_fid_mappings.json\n\nThe app will then load your mappings automatically on next visit.`);
}

// Autocomplete functionality
let selectedAutocompleteIndex = -1;

function showAutocomplete(matches) {
    const dropdown = document.getElementById('autocompleteDropdown');
    dropdown.innerHTML = '';

    if (matches.length === 0) {
        dropdown.style.display = 'none';
        return;
    }

    // If there's exactly one match, auto-fill the input and select the untyped portion
    if (matches.length === 1) {
        const input = document.getElementById('campNameInput');
        const currentValue = input.value;
        const matchValue = matches[0];

        // Set the full match as the value
        input.value = matchValue;

        // Select the portion the user didn't type
        // Find where the user's input appears in the match (case-insensitive)
        const userInput = currentValue.toLowerCase();
        const matchLower = matchValue.toLowerCase();
        const matchIndex = matchLower.indexOf(userInput);

        if (matchIndex !== -1) {
            // Select from the end of user's input to the end of the match
            const selectionStart = matchIndex + currentValue.length;
            input.setSelectionRange(selectionStart, matchValue.length);
        } else {
            // Fallback: select everything after the current input length
            input.setSelectionRange(currentValue.length, matchValue.length);
        }

        dropdown.style.display = 'none';
        selectedAutocompleteIndex = -1;
        return;
    }

    matches.slice(0, 10).forEach((match, index) => { // Show max 10 matches
        const item = document.createElement('div');
        item.textContent = match;
        item.style.padding = '8px';
        item.style.cursor = 'pointer';
        item.style.borderBottom = '1px solid #eee';

        item.addEventListener('mouseenter', () => {
            clearAutocompleteSelection();
            item.style.backgroundColor = '#e9ecef';
            selectedAutocompleteIndex = index;
        });

        item.addEventListener('mouseleave', () => {
            item.style.backgroundColor = '';
        });

        item.addEventListener('click', () => {
            document.getElementById('campNameInput').value = match;
            dropdown.style.display = 'none';
            selectedAutocompleteIndex = -1;
        });

        dropdown.appendChild(item);
    });

    dropdown.style.display = 'block';
}

function clearAutocompleteSelection() {
    const dropdown = document.getElementById('autocompleteDropdown');
    Array.from(dropdown.children).forEach(child => {
        child.style.backgroundColor = '';
    });
}

function selectAutocompleteItem(direction) {
    const dropdown = document.getElementById('autocompleteDropdown');
    const items = dropdown.children;

    if (items.length === 0) return;

    clearAutocompleteSelection();

    if (direction === 'down') {
        selectedAutocompleteIndex = (selectedAutocompleteIndex + 1) % items.length;
    } else if (direction === 'up') {
        selectedAutocompleteIndex = selectedAutocompleteIndex <= 0 ? items.length - 1 : selectedAutocompleteIndex - 1;
    }

    if (selectedAutocompleteIndex >= 0) {
        items[selectedAutocompleteIndex].style.backgroundColor = '#e9ecef';
    }
}

function applySelectedAutocomplete() {
    const dropdown = document.getElementById('autocompleteDropdown');
    const items = dropdown.children;

    if (selectedAutocompleteIndex >= 0 && selectedAutocompleteIndex < items.length) {
        const selectedText = items[selectedAutocompleteIndex].textContent;
        document.getElementById('campNameInput').value = selectedText;
        dropdown.style.display = 'none';
        selectedAutocompleteIndex = -1;
        return true;
    }
    return false;
}

// Allow Enter key to submit camp name and handle autocomplete navigation
document.addEventListener('DOMContentLoaded', () => {
    const campNameInput = document.getElementById('campNameInput');

    // Handle input changes for autocomplete
    campNameInput.addEventListener('input', (e) => {
        const query = e.target.value.trim().toLowerCase();

        if (query.length < 2) {
            document.getElementById('autocompleteDropdown').style.display = 'none';
            return;
        }

        // Find matching camp names
        const matches = allCampNames.filter(name =>
            name.toLowerCase().includes(query)
        ).slice(0, 10);

        showAutocomplete(matches);
        selectedAutocompleteIndex = -1;
    });

    // Handle keyboard navigation
    campNameInput.addEventListener('keydown', (e) => {
        const dropdown = document.getElementById('autocompleteDropdown');

        if (dropdown.style.display === 'none') {
            if (e.key === 'Enter') {
                submitCampName();
            }
            return;
        }

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                selectAutocompleteItem('down');
                break;
            case 'ArrowUp':
                e.preventDefault();
                selectAutocompleteItem('up');
                break;
            case 'Enter':
                e.preventDefault();
                if (!applySelectedAutocomplete()) {
                    submitCampName();
                }
                break;
            case 'Escape':
                dropdown.style.display = 'none';
                selectedAutocompleteIndex = -1;
                break;
        }
    });

    // Hide dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (!campNameInput.contains(e.target) && !document.getElementById('autocompleteDropdown').contains(e.target)) {
            document.getElementById('autocompleteDropdown').style.display = 'none';
        }
    });
});

// Mouse panning state
let isPanning = false;
let lastMousePos = { x: 0, y: 0 };

// Mouse event handlers for panning
canvas.addEventListener('mousedown', (e) => {
    isPanning = true;
    const rect = canvas.getBoundingClientRect();
    lastMousePos.x = e.clientX - rect.left;
    lastMousePos.y = e.clientY - rect.top;
    canvas.style.cursor = 'grabbing';
});

canvas.addEventListener('mousemove', (e) => {
    const rect = canvas.getBoundingClientRect();
    const canvasX = e.clientX - rect.left;
    const canvasY = e.clientY - rect.top;

    if (isPanning) {
        // Calculate the difference in mouse position
        const deltaX = canvasX - lastMousePos.x;
        const deltaY = canvasY - lastMousePos.y;

        // Convert canvas pixel movement to geographic coordinate movement
        const latScale = Math.cos(viewport.centerY * Math.PI / 180);
        const deltaLon = -deltaX / (viewport.scale * latScale);
        const deltaLat = deltaY / viewport.scale;

        // Update viewport center
        viewport.centerX += deltaLon;
        viewport.centerY += deltaLat;

        // Update last mouse position
        lastMousePos.x = canvasX;
        lastMousePos.y = canvasY;

        // Redraw the map
        redraw();
    }

    // Update coordinate display and camp detection
    const geo = canvasToGeo(canvasX, canvasY);
    document.getElementById('coordinates').textContent =
        `Mouse: ${geo.lon.toFixed(6)}, ${geo.lat.toFixed(6)}`;

    // Check if mouse is over a camp (only when not panning)
    if (!isPanning) {
        const newHighlightedCamp = findCampAtLocation(geo.lon, geo.lat);

        if (newHighlightedCamp !== highlightedCamp) {
            highlightedCamp = newHighlightedCamp;

            // Update camp display and diagnostic information
            const campDisplay = document.getElementById('currentCamp');
            const diagnosticDisplay = document.getElementById('diagnostic');

            if (highlightedCamp && highlightedCamp.properties && highlightedCamp.properties.fid) {
                const fid = highlightedCamp.properties.fid;
                const campName = campMappings[fid];

                if (campName) {
                    campDisplay.textContent = `Camp: ${fid} - "${campName}"`;
                } else {
                    campDisplay.textContent = `Camp: ${fid} (unnamed)`;
                }
                diagnosticDisplay.style.display = 'none';
            } else {
                campDisplay.textContent = 'Camp: None';
                if (lastDiagnostic) {
                    diagnosticDisplay.textContent = lastDiagnostic;
                    diagnosticDisplay.style.display = 'inline-block';
                } else {
                    diagnosticDisplay.style.display = 'none';
                }
            }

            redraw();
        }
    }
});

canvas.addEventListener('mouseup', (e) => {
    isPanning = false;
    canvas.style.cursor = 'crosshair';
});

// Handle mouse leaving the canvas area
canvas.addEventListener('mouseleave', (e) => {
    isPanning = false;
    canvas.style.cursor = 'crosshair';

    // Clear camp highlighting when mouse leaves
    if (highlightedCamp) {
        highlightedCamp = null;
        document.getElementById('currentCamp').textContent = 'Camp: None';
        document.getElementById('diagnostic').style.display = 'none';
        redraw();
    }
});

// Zoom functionality
function zoomAtPoint(canvasX, canvasY, zoomFactor) {
    // Get the geographic coordinates at the mouse position before zooming
    const geoBeforeZoom = canvasToGeo(canvasX, canvasY);

    // Apply the zoom
    viewport.scale *= zoomFactor;

    // Constrain zoom levels to reasonable bounds
    const minScale = 100;   // Very zoomed out
    const maxScale = 500000; // Very zoomed in
    viewport.scale = Math.max(minScale, Math.min(maxScale, viewport.scale));

    // Get the geographic coordinates at the same canvas position after zooming
    const geoAfterZoom = canvasToGeo(canvasX, canvasY);

    // Adjust the viewport center to keep the mouse position fixed
    viewport.centerX += geoBeforeZoom.lon - geoAfterZoom.lon;
    viewport.centerY += geoBeforeZoom.lat - geoAfterZoom.lat;

    redraw();
}

// Mouse wheel zoom handler
canvas.addEventListener('wheel', (e) => {
    e.preventDefault(); // Prevent page scrolling

    const rect = canvas.getBoundingClientRect();
    const canvasX = e.clientX - rect.left;
    const canvasY = e.clientY - rect.top;

    // Calculate zoom factor from wheel delta
    // Normalize the wheel delta for cross-browser compatibility
    let deltaY = e.deltaY;
    if (e.deltaMode === 1) { // DOM_DELTA_LINE
        deltaY *= 40;
    } else if (e.deltaMode === 2) { // DOM_DELTA_PAGE
        deltaY *= 400;
    }

    // Smooth zoom factor calculation
    const zoomSpeed = 0.001;
    const zoomFactor = Math.exp(-deltaY * zoomSpeed);

    zoomAtPoint(canvasX, canvasY, zoomFactor);
}, { passive: false });

// Touch/trackpad gesture support for pinch-to-zoom
let lastTouchDistance = 0;
let touchCenter = { x: 0, y: 0 };

canvas.addEventListener('touchstart', (e) => {
    if (e.touches.length === 2) {
        // Calculate initial distance between two touches
        const touch1 = e.touches[0];
        const touch2 = e.touches[1];
        const rect = canvas.getBoundingClientRect();

        const dx = (touch1.clientX - touch2.clientX);
        const dy = (touch1.clientY - touch2.clientY);
        lastTouchDistance = Math.sqrt(dx * dx + dy * dy);

        // Calculate center point of the two touches
        touchCenter.x = (touch1.clientX + touch2.clientX) / 2 - rect.left;
        touchCenter.y = (touch1.clientY + touch2.clientY) / 2 - rect.top;

        e.preventDefault();
    }
}, { passive: false });

canvas.addEventListener('touchmove', (e) => {
    if (e.touches.length === 2 && lastTouchDistance > 0) {
        // Calculate current distance between two touches
        const touch1 = e.touches[0];
        const touch2 = e.touches[1];
        const rect = canvas.getBoundingClientRect();

        const dx = (touch1.clientX - touch2.clientX);
        const dy = (touch1.clientY - touch2.clientY);
        const currentDistance = Math.sqrt(dx * dx + dy * dy);

        // Calculate zoom factor from distance change
        const zoomFactor = currentDistance / lastTouchDistance;

        // Update center point
        touchCenter.x = (touch1.clientX + touch2.clientX) / 2 - rect.left;
        touchCenter.y = (touch1.clientY + touch2.clientY) / 2 - rect.top;

        zoomAtPoint(touchCenter.x, touchCenter.y, zoomFactor);

        lastTouchDistance = currentDistance;
        e.preventDefault();
    }
}, { passive: false });

canvas.addEventListener('touchend', (e) => {
    if (e.touches.length < 2) {
        lastTouchDistance = 0;
    }
});

// Handle window resize
window.addEventListener('resize', resizeCanvas);

// Start the application
init();