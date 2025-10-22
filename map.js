// HTML escaping utility to prevent XSS injection
function escapeHtml(text) {
    if (text == null) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Canvas and rendering setup
const canvas = document.getElementById('mapCanvas');
const ctx = canvas.getContext('2d');
const loadingStatus = document.getElementById('loadingStatus');

// Data storage
let campOutlines = null;
let campFidMappings = null; // Maps FID to camp name
let campsData = null; // Full camp data from camps.json
let campHistory = null; // Historical camp data
let showOutlines = false; // Don't display outlines, but keep for hit testing

// Background map image
let backgroundImage = null;
let showBackgroundImage = true;

// Background image alignment settings - adjust these to align the image with the GeoJSON data
const BACKGROUND_IMAGE_SETTINGS = {
    // Geographic coordinates where the background image center should be placed
    centerLon: -119.22,
    centerLat: 40.782,

    // Scale factor for the background image (pixels per degree)
    // Adjust this to make the background image larger or smaller
    scale: 99010,

    // Fine-tune offsets in pixels (after rotation and scaling)
    offsetX: 1385,
    offsetY: 737,

    // Rotation offset in degrees (if the image needs additional rotation beyond the main 45°)
    rotationOffset: 45
};

// Camp highlighting
let highlightedCamp = null;
let currentPopupCampName = null; // Track which camp is currently shown in popup
let currentSidebarCampName = null; // Track which camp is in sidebar
let fullCampInfoOpen = false; // Track if full camp info is open
let currentFullCampName = null; // Track which camp is in full info mode

// Map rotation - 45 degrees clockwise to show 12:00 pointing up
const ROTATION_ANGLE = -45 * Math.PI / 180; // -45 degrees in radians (negative = clockwise)
const COS_ROTATION = Math.cos(ROTATION_ANGLE);
const SIN_ROTATION = Math.sin(ROTATION_ANGLE);

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

    // Calculate position relative to viewport center
    const dx = (lon - viewport.centerX) * viewport.scale * latScale;
    const dy = -(lat - viewport.centerY) * viewport.scale;

    // Apply rotation around center (clockwise by 45 degrees to put 12:00 up)
    const rotatedX = dx * COS_ROTATION - dy * SIN_ROTATION;
    const rotatedY = dx * SIN_ROTATION + dy * COS_ROTATION;

    // Translate to canvas position
    const x = canvas.width / 2 + rotatedX;
    const y = canvas.height / 2 + rotatedY;

    return { x, y };
}

// Convert canvas coordinates back to geographic coordinates
function canvasToGeo(canvasX, canvasY) {
    const latScale = Math.cos(viewport.centerY * Math.PI / 180);

    // Get canvas position relative to center
    const canvasDx = canvasX - canvas.width / 2;
    const canvasDy = canvasY - canvas.height / 2;

    // Apply inverse rotation (counter-clockwise by 45 degrees)
    // Inverse rotation matrix: transpose of rotation matrix (since rotation is orthogonal)
    const unrotatedX = canvasDx * COS_ROTATION + canvasDy * SIN_ROTATION;
    const unrotatedY = -canvasDx * SIN_ROTATION + canvasDy * COS_ROTATION;

    // Convert back to geographic coordinates
    const lon = viewport.centerX + unrotatedX / (viewport.scale * latScale);
    const lat = viewport.centerY - unrotatedY / viewport.scale;

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

// Find which camp contains the given geographic coordinate
function findCampAtLocation(lon, lat) {

    if (!campOutlines) {
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

// Draw the background map image
function drawBackgroundImage() {
    if (!backgroundImage || !showBackgroundImage) return;

    // Save the current canvas state
    ctx.save();

    // Use viewport's latScale for consistency
    const latScale = Math.cos(viewport.centerY * Math.PI / 180);

    // Calculate the scale factor for the image
    // The image scale is relative to the viewport scale, using latScale for consistency
    const imageScaleFactor = (viewport.scale * latScale) / BACKGROUND_IMAGE_SETTINGS.scale;

    // Calculate offset adjustments - scale them with the zoom level
    const scaledOffsetX = BACKGROUND_IMAGE_SETTINGS.offsetX * imageScaleFactor;
    const scaledOffsetY = BACKGROUND_IMAGE_SETTINGS.offsetY * imageScaleFactor;

    // Rotate the scaled offsets to apply them in the correct direction
    const rotatedOffsetX = scaledOffsetX * COS_ROTATION - scaledOffsetY * SIN_ROTATION;
    const rotatedOffsetY = scaledOffsetX * SIN_ROTATION + scaledOffsetY * COS_ROTATION;

    // Calculate position relative to viewport center (in pixels before rotation)
    const dx = (BACKGROUND_IMAGE_SETTINGS.centerLon - viewport.centerX) * viewport.scale * latScale + rotatedOffsetX;
    const dy = -(BACKGROUND_IMAGE_SETTINGS.centerLat - viewport.centerY) * viewport.scale + rotatedOffsetY;

    // Apply rotation around viewport center
    const rotatedX = dx * COS_ROTATION - dy * SIN_ROTATION;
    const rotatedY = dx * SIN_ROTATION + dy * COS_ROTATION;

    // Calculate the final canvas position for the image center
    const imageCenterX = canvas.width / 2 + rotatedX;
    const imageCenterY = canvas.height / 2 + rotatedY;

    // Move to the image center position
    ctx.translate(imageCenterX, imageCenterY);

    // Apply rotation (main rotation + any additional offset)
    const totalRotation = ROTATION_ANGLE + (BACKGROUND_IMAGE_SETTINGS.rotationOffset * Math.PI / 180);
    ctx.rotate(totalRotation);

    // Scale the image
    ctx.scale(imageScaleFactor, imageScaleFactor);

    // Draw the image centered at the origin (which is now at the transformed position)
    ctx.drawImage(
        backgroundImage,
        -backgroundImage.width / 2,
        -backgroundImage.height / 2,
        backgroundImage.width,
        backgroundImage.height
    );

    // Restore the canvas state
    ctx.restore();
}

// Render all data
function redraw() {
    // Clear canvas
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw background image first (behind everything)
    drawBackgroundImage();

    // Draw highlighted camp only (if mouse is hovering over one)
    if (highlightedCamp && campOutlines) {
        const coordinates = highlightedCamp.geometry.coordinates;

        // Fill highlighted camp with yellow background
        fillPolygon(coordinates, 'rgba(255, 255, 0, 0.3)');

        // Draw the outline in orange
        drawLineString(coordinates, 'orange', 3);
    }

    // Optionally draw all camp outlines in light blue (toggle with button)
    if (campOutlines && showOutlines) {
        campOutlines.features.forEach(feature => {
            if (feature.geometry.type === 'LineString') {
                const coordinates = feature.geometry.coordinates;

                // Skip the highlighted camp (already drawn above)
                if (highlightedCamp && feature === highlightedCamp) {
                    return;
                }

                // Draw the outline
                drawLineString(coordinates, 'lightblue', 2);
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

// Load JSON data (generic)
async function loadJSON(url) {
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

// Initialize the application
async function init() {
    loadingStatus.textContent = 'Loading background map image...';

    // Load background image
    backgroundImage = new Image();
    backgroundImage.src = 'data/BRCMapAdj.png';
    await new Promise((resolve, reject) => {
        backgroundImage.onload = resolve;
        backgroundImage.onerror = () => {
            console.error('Failed to load background image');
            resolve(); // Continue even if image fails to load
        };
    });

    loadingStatus.textContent = 'Loading camp data...';

    // Load camp FID to name mappings
    campFidMappings = await loadJSON('data/camp_fid_mappings.json');

    // Load full camp data
    campsData = await loadJSON('data/camps.json');

    // Load camp history
    campHistory = await loadJSON('data/campHistory.json');

    // Load camp outlines
    campOutlines = await loadGeoJSON('data/camp_outlines_2025.geojson');

    loadingStatus.style.display = 'none';

    // Initialize search
    initializeSearch();

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

    // Account for sidebar when calculating visible area
    const sidebar = document.getElementById('campSidebar');
    let availableWidth = canvas.width;
    if (sidebar && window.getComputedStyle(sidebar).display !== 'none') {
        availableWidth = canvas.width - sidebar.offsetWidth;
    }

    const scaleX = (availableWidth * 0.9) / (lonRange * latScale);
    const scaleY = (canvas.height * 0.9) / latRange;

    viewport.scale = Math.min(scaleX, scaleY);
    viewport.centerX = (bounds.maxLon + bounds.minLon) / 2;
    viewport.centerY = (bounds.maxLat + bounds.minLat) / 2;

    // Adjust for sidebar covering part of the canvas
    if (sidebar && window.getComputedStyle(sidebar).display !== 'none') {
        const sidebarWidth = sidebar.offsetWidth;
        // Sidebar is on the left, so we need to shift the view right by half the sidebar width
        // This shift is in canvas space, but we need to account for the 45-degree rotation
        // when converting to geographic coordinate adjustments

        // Desired shift in rotated canvas space: right by sidebarWidth/2 (positive X direction)
        // Apply inverse rotation to get the shift needed in geographic space
        const latScale = Math.cos(viewport.centerY * Math.PI / 180);
        const canvasShiftX = sidebarWidth / 2;  // Positive because shifting right
        const canvasShiftY = 0;  // No vertical shift needed in canvas space

        // Apply inverse rotation: use transpose of rotation matrix
        const geoShiftX = (canvasShiftX * COS_ROTATION + canvasShiftY * SIN_ROTATION) / (viewport.scale * latScale);
        const geoShiftY = (-canvasShiftX * SIN_ROTATION + canvasShiftY * COS_ROTATION) / viewport.scale;

        // Apply the geographic shifts (note: these shift the viewport, which moves the image oppositely)
        viewport.centerX -= geoShiftX;
        viewport.centerY += geoShiftY;
    }

    redraw();
}

// Toggle functions
function toggleOutlines() {
    showOutlines = !showOutlines;
    redraw();
}

// Info button handler (placeholder)
function showInfo() {
    window.open('https://github.com/jspolsky/brcDomesday/blob/main/README.md', '_blank');
}

// Find camp data by name
function findCampDataByName(campName) {
    if (!campsData || !campName) return null;

    // Try exact match first
    let camp = campsData.find(c => c.name === campName);
    if (camp) return camp;

    // Try case-insensitive match
    const lowerCampName = campName.toLowerCase();
    camp = campsData.find(c => c.name && c.name.toLowerCase() === lowerCampName);

    return camp;
}

// Show camp popup
function showCampPopup(campName, mouseX, mouseY) {
    const popup = document.getElementById('campPopup');
    const campData = findCampDataByName(campName);

    // Only update content if switching to a different camp
    if (currentPopupCampName !== campName) {
        currentPopupCampName = campName;

        // Update popup content - show camp name even if no data found
        document.getElementById('campPopupName').textContent = campData ? (campData.name || campName) : campName;
        document.getElementById('campPopupLocation').textContent = campData ? (campData.location_string || '') : '';

        // Update image
        const img = document.getElementById('campPopupImage');

        // Special case for First Camp - use local image
        if (campName === 'First Camp') {
            img.src = '';
            img.src = 'firstcamp.jpg';
            img.style.display = 'block';
        } else if (campData && campData.images && campData.images.length > 0 && campData.images[0].thumbnail_url) {
            // Clear the current image first to show purple placeholder while loading
            img.src = '';
            // Then set the new image URL
            img.src = campData.images[0].thumbnail_url;
            img.style.display = 'block';
        } else {
            img.src = '';
            img.style.display = 'none';
        }
    }

    // Position the popup
    popup.style.display = 'block';

    // Get popup dimensions after making it visible
    const popupRect = popup.getBoundingClientRect();
    const canvasRect = canvas.getBoundingClientRect();

    // Calculate position - offset from mouse to avoid blocking the camp
    const offset = 20;
    let left = mouseX + offset;
    let top = mouseY + offset;

    // Adjust horizontal position if popup would go off right edge
    if (left + popupRect.width > canvasRect.width) {
        left = mouseX - popupRect.width - offset;
    }

    // Adjust vertical position based on which half of screen we're in
    if (mouseY < canvasRect.height / 2) {
        // Top half - show below mouse
        top = mouseY + offset;
    } else {
        // Bottom half - show above mouse
        top = mouseY - popupRect.height - offset;
    }

    // Ensure popup stays within canvas bounds
    left = Math.max(0, Math.min(left, canvasRect.width - popupRect.width));
    top = Math.max(0, Math.min(top, canvasRect.height - popupRect.height));

    popup.style.left = left + 'px';
    popup.style.top = top + 'px';
}

// Hide camp popup
function hideCampPopup() {
    document.getElementById('campPopup').style.display = 'none';
    currentPopupCampName = null;
}

// Update sidebar content with camp information
function updateSidebarCampInfo(campName) {
    const campData = findCampDataByName(campName);
    currentSidebarCampName = campName;

    // Update text content
    document.getElementById('sidebarCampName').textContent = campData ? (campData.name || campName) : campName;
    document.getElementById('sidebarCampLocation').textContent = campData ? (campData.location_string || '') : '';
    document.getElementById('sidebarCampDescription').textContent = campData ? (campData.description || 'No description available.') : 'No description available.';

    // Calculate statistics for the hint
    const stats = calculateCampStats(campName);
    const hintElement = document.getElementById('sidebarHint');

    if (stats.hasData) {
        let hintText = 'Click for ';
        const parts = [];

        if (stats.yearsOfHistory > 0) {
            parts.push(`${stats.yearsOfHistory} year${stats.yearsOfHistory !== 1 ? 's' : ''} of history`);
        }

        if (stats.totalEvents > 0) {
            parts.push(`${stats.totalEvents} event${stats.totalEvents !== 1 ? 's' : ''}`);
        }

        if (stats.imageCount > 0) {
            parts.push(`${stats.imageCount} photo${stats.imageCount !== 1 ? 's' : ''}`);
        }

        if (parts.length > 0) {
            // Join with commas and "and" for the last item
            if (parts.length === 1) {
                hintText += parts[0];
            } else if (parts.length === 2) {
                hintText += parts[0] + ' and ' + parts[1];
            } else {
                hintText += parts.slice(0, -1).join(', ') + ', and ' + parts[parts.length - 1];
            }
        } else {
            hintText = 'Click for more information about this camp.';
        }

        hintElement.textContent = hintText;
    } else {
        hintElement.textContent = 'Click for more information about this camp.';
    }

    // Update image
    const img = document.getElementById('sidebarCampImage');

    // Special case for First Camp - use local image
    if (campName === 'First Camp') {
        img.src = '';
        img.src = 'firstcamp.jpg';
        img.style.display = 'block';
    } else if (campData && campData.images && campData.images.length > 0 && campData.images[0].thumbnail_url) {
        const thumbnailUrl = campData.images[0].thumbnail_url;

        // First load the thumbnail
        img.src = '';
        img.src = thumbnailUrl;
        img.style.display = 'block';

        // Then load high-res version by removing query string
        const highResUrl = thumbnailUrl.split('?')[0];
        if (highResUrl !== thumbnailUrl) {
            // Create a new image to preload the high-res version
            const highResImg = new Image();
            highResImg.onload = () => {
                // Only update if we're still showing the same camp
                if (currentSidebarCampName === campName) {
                    img.src = highResUrl;
                }
            };
            highResImg.src = highResUrl;
        }
    } else {
        img.src = '';
        img.style.display = 'none';
    }
}

// Calculate statistics about camp history, events, and images
function calculateCampStats(campName) {
    const stats = {
        yearsOfHistory: 0,
        totalEvents: 0,
        imageCount: 0,
        hasData: false
    };

    if (!campHistory || !campHistory[campName]) {
        return stats;
    }

    const history = campHistory[campName].history;

    // Count years of history (excluding 2025)
    const historicalYears = history.filter(h => h.year !== 2025);
    stats.yearsOfHistory = historicalYears.length;

    // Count total events across all years
    history.forEach(yearEntry => {
        if (yearEntry.events && yearEntry.events.length > 0) {
            stats.totalEvents += yearEntry.events.length;
        }
    });

    // Count images
    if (campHistory[campName].images && campHistory[campName].images.length > 0) {
        stats.imageCount = campHistory[campName].images.length;
    }

    // Check if we have any data to show
    stats.hasData = stats.yearsOfHistory > 0 || stats.totalEvents > 0 || stats.imageCount > 0;

    return stats;
}

// Update sidebar with camp details
function updateSidebarWithCamp(campName) {
    if (currentSidebarCampName === campName || fullCampInfoOpen) return;
    updateSidebarCampInfo(campName);
    hideCampPopup();
}

// Tooltip state management
let tooltipHideTimer = null;
let currentTooltipTarget = null;

// Build the camp history section
function buildCampEventsSection(campName) {
    const eventsContainer = document.getElementById('fullCampEvents');

    if (!campHistory || !campHistory[campName]) {
        eventsContainer.innerHTML = '';
        return;
    }

    const history = campHistory[campName].history;

    // Find the 2025 entry
    const entry2025 = history.find(h => h.year === 2025);

    // Check if there are any historical events (before checking 2025 events)
    const historicalEntries = history.filter(h => h.year !== 2025 && h.events && h.events.length > 0);

    // If no 2025 events AND no historical events, don't show the section at all
    if ((!entry2025 || !entry2025.events || entry2025.events.length === 0) && historicalEntries.length === 0) {
        eventsContainer.innerHTML = '';
        return;
    }

    // Build events HTML
    let eventsHTML = `
        <hr style="margin: 20px 0; border: none; border-top: 1px solid #444;">
        <h2>2025 Events</h2>
    `;

    if (entry2025 && entry2025.events && entry2025.events.length > 0) {
        eventsHTML += `<div class="events-year-group">`;

        entry2025.events.forEach(event => {
            const eventType = event.event_type ? ` (${escapeHtml(event.event_type)})` : '';
            eventsHTML += `
                <div class="event-item">
                    <div>
                        <span class="event-title">${escapeHtml(event.title)}</span><span class="event-type">${eventType}</span>
                    </div>
                    <div class="event-description">${escapeHtml(event.description)}</div>
                </div>
            `;
        });

        eventsHTML += `</div>`;
    } else {
        // No 2025 events
        eventsHTML += `<div style="color: #aaaaaa; font-style: italic; margin-bottom: 15px;">No events listed for 2025</div>`;
    }

    // Add "Show older events" button if there are historical events
    if (historicalEntries.length > 0) {
        // Add "Show older events" button
        eventsHTML += `
            <div style="margin-top: 15px;">
                <button id="toggleOlderEventsBtn" onclick="toggleOlderEvents('${escapeHtml(campName).replace(/'/g, "\\'")}')">Show older events</button>
            </div>
            <div id="olderEventsContainer" style="display: none; margin-top: 15px;">
        `;

        // Build historical events HTML (sorted by year descending)
        historicalEntries.sort((a, b) => b.year - a.year);

        historicalEntries.forEach(yearEntry => {
            eventsHTML += `<h3 style="font-size: 16px; color: #ffffff; margin-top: 20px; margin-bottom: 10px;">${yearEntry.year} Events</h3>`;
            eventsHTML += `<div class="events-year-group">`;

            yearEntry.events.forEach(event => {
                const eventType = event.event_type ? ` (${escapeHtml(event.event_type)})` : '';
                eventsHTML += `
                    <div class="event-item">
                        <div>
                            <span class="event-title">${escapeHtml(event.title)}</span><span class="event-type">${eventType}</span>
                        </div>
                        <div class="event-description">${escapeHtml(event.description)}</div>
                    </div>
                `;
            });

            eventsHTML += `</div>`;
        });

        eventsHTML += `</div>`;
    }

    eventsContainer.innerHTML = eventsHTML;
}

function toggleOlderEvents(campName) {
    const olderEventsContainer = document.getElementById('olderEventsContainer');
    const toggleBtn = document.getElementById('toggleOlderEventsBtn');

    if (olderEventsContainer.style.display === 'none') {
        olderEventsContainer.style.display = 'block';
        toggleBtn.textContent = 'Hide older events';
    } else {
        olderEventsContainer.style.display = 'none';
        toggleBtn.textContent = 'Show older events';
    }
}

function buildCampHistorySection(campName) {
    const historyContainer = document.getElementById('fullCampHistory');

    if (!campHistory || !campHistory[campName]) {
        historyContainer.innerHTML = '';
        return;
    }

    const history = campHistory[campName].history;

    // Check if this is a new camp (only appears in 2025)
    if (history.length === 1 && history[0].year === 2025) {
        historyContainer.innerHTML = `
            <hr style="margin: 20px 0; border: none; border-top: 1px solid #ddd;">
            <div style="color: #666; font-style: italic;">This camp was new in 2025</div>
        `;
        return;
    }

    // Camp has history - build the year list (excluding 2025)
    const historicalYears = history.filter(h => h.year !== 2025);

    if (historicalYears.length === 0) {
        historyContainer.innerHTML = `
            <hr style="margin: 20px 0; border: none; border-top: 1px solid #ddd;">
            <div style="color: #666; font-style: italic;">This camp was new in 2025</div>
        `;
        return;
    }

    // Build HTML with hoverable years
    let historyHTML = `
        <hr style="margin: 20px 0; border: none; border-top: 1px solid #ddd;">
        <div style="margin-top: 20px;">
            <strong>Camp History:</strong>
    `;

    historicalYears.forEach((yearData, index) => {
        historyHTML += `<span class="history-year" data-year-info='${JSON.stringify(yearData).replace(/'/g, "&#39;")}'>${yearData.year}</span>`;
        if (index < historicalYears.length - 1) {
            historyHTML += ' ';
        }
    });

    historyHTML += '</div>';
    historyContainer.innerHTML = historyHTML;

    // Add event listeners for hover
    const yearSpans = historyContainer.querySelectorAll('.history-year');
    yearSpans.forEach(span => {
        span.addEventListener('mouseenter', showHistoryTooltip);
        span.addEventListener('mouseleave', startTooltipHideTimer);
    });
}

// Show history tooltip
function showHistoryTooltip(event) {
    // Cancel any pending hide timer
    if (tooltipHideTimer) {
        clearTimeout(tooltipHideTimer);
        tooltipHideTimer = null;
    }

    const tooltip = document.getElementById('historyTooltip');
    const target = event.target;

    // If tooltip is already showing for this target, don't recreate it
    if (currentTooltipTarget === target && tooltip.style.display === 'block') {
        return;
    }

    currentTooltipTarget = target;
    const yearData = JSON.parse(target.getAttribute('data-year-info'));

    let tooltipContent = `<strong>${yearData.year}</strong><br>`;

    if (yearData.location_string) {
        tooltipContent += `<strong>Location:</strong> ${escapeHtml(yearData.location_string)}<br>`;
    }

    if (yearData.description) {
        // Truncate long descriptions
        const desc = yearData.description.length > 1000
            ? yearData.description.substring(0, 1000) + '...'
            : yearData.description;
        tooltipContent += `<strong>Description:</strong> ${escapeHtml(desc)}<br>`;
    }

    if (yearData.url) {
        // Create Wayback Machine URL for August 1st of the year
        const waybackDate = `${yearData.year}0801`;
        const escapedUrl = escapeHtml(yearData.url);
        const waybackUrl = `https://web.archive.org/web/${waybackDate}/${encodeURIComponent(yearData.url)}`;
        tooltipContent += `<strong>Web Archive URL:</strong> <a href="${escapeHtml(waybackUrl)}" target="_blank" style="color: #66aaff;" title="View on Wayback Machine (Aug 1, ${yearData.year})">${escapedUrl}</a>`;
    }

    tooltip.innerHTML = tooltipContent;
    tooltip.style.display = 'block';

    // Position the tooltip below the year pill
    positionTooltip(target, tooltip);

    // Add hover listeners to the tooltip itself so it stays open when mouse moves to it
    tooltip.onmouseenter = cancelTooltipHide;
    tooltip.onmouseleave = startTooltipHideTimer;
}

// Position tooltip below the target element
function positionTooltip(target, tooltip) {
    const targetRect = target.getBoundingClientRect();
    const tooltipRect = tooltip.getBoundingClientRect();
    const offsetY = 8; // Gap between target and tooltip

    // Start with tooltip below the target, centered
    let left = targetRect.left + (targetRect.width / 2) - (tooltipRect.width / 2);
    let top = targetRect.bottom + offsetY;

    // Adjust if tooltip would go off right edge
    if (left + tooltipRect.width > window.innerWidth - 10) {
        left = window.innerWidth - tooltipRect.width - 10;
    }

    // Adjust if tooltip would go off left edge
    if (left < 10) {
        left = 10;
    }

    // Adjust if tooltip would go off bottom edge - show above instead
    if (top + tooltipRect.height > window.innerHeight - 10) {
        top = targetRect.top - tooltipRect.height - offsetY;
    }

    // Add scroll offset since we're using absolute positioning
    tooltip.style.left = (left + window.scrollX) + 'px';
    tooltip.style.top = (top + window.scrollY) + 'px';
}

// Start timer to hide tooltip
function startTooltipHideTimer() {
    // Clear any existing timer
    if (tooltipHideTimer) {
        clearTimeout(tooltipHideTimer);
    }

    // Set a delay before hiding (500ms gives time to move mouse to tooltip)
    tooltipHideTimer = setTimeout(() => {
        hideHistoryTooltip();
    }, 300);
}

// Cancel tooltip hide
function cancelTooltipHide() {
    if (tooltipHideTimer) {
        clearTimeout(tooltipHideTimer);
        tooltipHideTimer = null;
    }
}

// Hide history tooltip
function hideHistoryTooltip() {
    const tooltip = document.getElementById('historyTooltip');
    tooltip.style.display = 'none';
    currentTooltipTarget = null;

    // Remove event listeners
    tooltip.onmouseenter = null;
    tooltip.onmouseleave = null;
}

// Build the camp gallery section
function buildCampGallerySection(campName) {
    const galleryContainer = document.getElementById('fullCampGallery');

    if (!campHistory || !campHistory[campName] || !campHistory[campName].images || campHistory[campName].images.length === 0) {
        galleryContainer.innerHTML = '';
        return;
    }

    const images = campHistory[campName].images;

    // Build gallery HTML
    let galleryHTML = `
        <hr style="margin: 20px 0; border: none; border-top: 1px solid #444;">
        <h2 style="font-size: 18px; color: #ffffff; margin-bottom: 15px;">Camp Images</h2>
        <div class="gallery-container">
    `;

    images.forEach(image => {
        const escapedUrl = escapeHtml(image.url);
        const escapedSourceUrl = escapeHtml(image.source_page_url);

        galleryHTML += `
            <div class="gallery-item">
                <a href="${escapedSourceUrl}" target="_blank" rel="noopener noreferrer">
                    <img src="${escapedUrl}"
                         alt="Camp image"
                         loading="lazy"
                         width="${image.width}"
                         height="${image.height}">
                </a>
            </div>
        `;
    });

    galleryHTML += `</div>`;
    galleryContainer.innerHTML = galleryHTML;
}

// Open full camp information mode
function openFullCampInfo(campName) {
    const campData = findCampDataByName(campName);
    const overlay = document.getElementById('mapOverlay');
    const fullInfo = document.getElementById('fullCampInfo');

    fullCampInfoOpen = true;
    currentFullCampName = campName;

    // Update content
    document.getElementById('fullCampName').textContent = campData ? (campData.name || campName) : campName;
    document.getElementById('fullCampLocation').textContent = campData ? (campData.location_string || '') : '';
    document.getElementById('fullCampDescription').textContent = campData ? (campData.description || 'No description available.') : 'No description available.';

    // Build additional details
    let details = '';
    if (campData) {
        if (campData.hometown) {
            details += `<strong>Hometown:</strong> ${escapeHtml(campData.hometown)}<br><br>`;
        }
        if (campData.url) {
            const escapedUrl = escapeHtml(campData.url);
            details += `<strong>Website:</strong> <a href="${escapedUrl}" target="_blank" style="color: #66aaff;">${escapedUrl}</a><br><br>`;
        }
        if (campData.contact_email) {
            details += `<strong>Contact:</strong> ${escapeHtml(campData.contact_email)}<br><br>`;
        }
        if (campData.landmark) {
            details += `<strong>Landmark:</strong> ${escapeHtml(campData.landmark)}<br><br>`;
        }
        if (campData.location && campData.location.dimensions) {
            details += `<strong>Dimensions:</strong> ${escapeHtml(campData.location.dimensions)}<br><br>`;
        }
    }
    document.getElementById('fullCampDetails').innerHTML = details;

    // Build events section
    buildCampEventsSection(campName);

    // Build history section
    buildCampHistorySection(campName);

    // Build image gallery section
    buildCampGallerySection(campName);

    // Update image
    const img = document.getElementById('fullCampImage');
    if (campName === 'First Camp') {
        img.src = '';
        img.src = 'firstcamp.jpg';
        img.style.display = 'block';
    } else if (campData && campData.images && campData.images.length > 0 && campData.images[0].thumbnail_url) {
        const thumbnailUrl = campData.images[0].thumbnail_url;
        img.src = '';
        img.src = thumbnailUrl;
        img.style.display = 'block';

        // Load high-res version
        const highResUrl = thumbnailUrl.split('?')[0];
        if (highResUrl !== thumbnailUrl) {
            const highResImg = new Image();
            highResImg.onload = () => {
                if (currentFullCampName === campName && fullCampInfoOpen) {
                    img.src = highResUrl;
                }
            };
            highResImg.src = highResUrl;
        }
    } else {
        img.style.display = 'none';
    }

    // Show overlay and full info
    overlay.classList.remove('overlay-hidden');
    fullInfo.classList.remove('fullcamp-hidden');

    // Reset scroll position to top
    fullInfo.scrollTop = 0;
}

// Close full camp information mode
function closeFullCampInfo() {
    const overlay = document.getElementById('mapOverlay');
    const fullInfo = document.getElementById('fullCampInfo');

    overlay.classList.add('overlay-hidden');
    fullInfo.classList.add('fullcamp-hidden');

    fullCampInfoOpen = false;
    currentFullCampName = null;
}

// Mouse panning state
let isPanning = false;
let lastMousePos = { x: 0, y: 0 };
let mouseDownPos = { x: 0, y: 0 }; // Track where mouse was pressed for click detection
let lastClickTime = 0; // Track last click time for double-click detection
let lastClickedCamp = null; // Track last clicked camp for double-click detection
let singleClickTimer = null; // Timer for delayed single-click action

// Mouse event handlers for panning
canvas.addEventListener('mousedown', (e) => {
    const rect = canvas.getBoundingClientRect();
    const canvasX = e.clientX - rect.left;
    const canvasY = e.clientY - rect.top;

    // Track mouse down position for click detection
    mouseDownPos.x = canvasX;
    mouseDownPos.y = canvasY;

    isPanning = true;
    lastMousePos.x = canvasX;
    lastMousePos.y = canvasY;
    canvas.style.cursor = 'grabbing';
});

canvas.addEventListener('mousemove', (e) => {
    const rect = canvas.getBoundingClientRect();
    const canvasX = e.clientX - rect.left;
    const canvasY = e.clientY - rect.top;

    if (isPanning) {
        // Calculate the difference in mouse position (in canvas pixels)
        const deltaX = canvasX - lastMousePos.x;
        const deltaY = canvasY - lastMousePos.y;

        // Apply inverse rotation to the pixel movement to get unrotated deltas
        // This accounts for the 45-degree rotation of the display
        const unrotatedDeltaX = deltaX * COS_ROTATION + deltaY * SIN_ROTATION;
        const unrotatedDeltaY = -deltaX * SIN_ROTATION + deltaY * COS_ROTATION;

        // Convert unrotated canvas pixel movement to geographic coordinate movement
        const latScale = Math.cos(viewport.centerY * Math.PI / 180);
        const deltaLon = -unrotatedDeltaX / (viewport.scale * latScale);
        const deltaLat = unrotatedDeltaY / viewport.scale;

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
        `${geo.lat.toFixed(6)}, ${geo.lon.toFixed(6)}`;



    // Check if mouse is over a camp (only when not panning)
    if (!isPanning) {
        const newHighlightedCamp = findCampAtLocation(geo.lon, geo.lat);

        if (newHighlightedCamp !== highlightedCamp) {
            highlightedCamp = newHighlightedCamp;

            // Update camp display
            const campDisplay = document.getElementById('currentCamp');

            if (highlightedCamp && highlightedCamp.properties && highlightedCamp.properties.fid) {
                const fid = highlightedCamp.properties.fid;
                const campName = campFidMappings && campFidMappings[fid] ? campFidMappings[fid] : `FID ${fid}`;
                campDisplay.textContent = campName;

                // Update sidebar with camp info
                updateSidebarWithCamp(campName);
            } else {
                campDisplay.textContent = '';
            }

            redraw();
        }
    }
});

canvas.addEventListener('mouseup', (e) => {
    const rect = canvas.getBoundingClientRect();
    const canvasX = e.clientX - rect.left;
    const canvasY = e.clientY - rect.top;

    // Check if this was a click (mouse didn't move much) vs a drag
    const dx = canvasX - mouseDownPos.x;
    const dy = canvasY - mouseDownPos.y;
    const distanceMoved = Math.sqrt(dx * dx + dy * dy);

    // If mouse moved less than 5 pixels, treat it as a click
    if (distanceMoved < 5) {
        // Check if clicking on a camp
        const geo = canvasToGeo(canvasX, canvasY);
        const clickedCamp = findCampAtLocation(geo.lon, geo.lat);

        if (clickedCamp && clickedCamp.properties && clickedCamp.properties.fid) {
            const fid = clickedCamp.properties.fid;
            const campName = campFidMappings && campFidMappings[fid] ? campFidMappings[fid] : `FID ${fid}`;

            // Click on any camp opens full info
            openFullCampInfo(campName);
        }
    }

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
        document.getElementById('currentCamp').textContent = '';
        hideCampPopup();
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
    const rect = canvas.getBoundingClientRect();

    if (e.touches.length === 1) {
        // Single finger - start panning
        const touch = e.touches[0];
        const canvasX = touch.clientX - rect.left;
        const canvasY = touch.clientY - rect.top;

        mouseDownPos.x = canvasX;
        mouseDownPos.y = canvasY;
        isPanning = true;
        lastMousePos.x = canvasX;
        lastMousePos.y = canvasY;

        e.preventDefault();
    } else if (e.touches.length === 2) {
        // Two fingers - start pinch zoom
        isPanning = false; // Stop panning when two fingers touch

        const touch1 = e.touches[0];
        const touch2 = e.touches[1];

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
    const rect = canvas.getBoundingClientRect();

    if (e.touches.length === 1 && isPanning) {
        // Single finger panning
        const touch = e.touches[0];
        const canvasX = touch.clientX - rect.left;
        const canvasY = touch.clientY - rect.top;

        // Calculate the difference in position (same logic as mouse panning)
        const deltaX = canvasX - lastMousePos.x;
        const deltaY = canvasY - lastMousePos.y;

        // Apply inverse rotation to the pixel movement
        const unrotatedDeltaX = deltaX * COS_ROTATION + deltaY * SIN_ROTATION;
        const unrotatedDeltaY = -deltaX * SIN_ROTATION + deltaY * COS_ROTATION;

        // Convert to geographic coordinate movement
        const latScale = Math.cos(viewport.centerY * Math.PI / 180);
        const deltaLon = -unrotatedDeltaX / (viewport.scale * latScale);
        const deltaLat = unrotatedDeltaY / viewport.scale;

        // Update viewport center
        viewport.centerX += deltaLon;
        viewport.centerY += deltaLat;

        // Update last position
        lastMousePos.x = canvasX;
        lastMousePos.y = canvasY;

        // Redraw the map
        redraw();

        e.preventDefault();
    } else if (e.touches.length === 2 && lastTouchDistance > 0) {
        // Two finger pinch zoom
        const touch1 = e.touches[0];
        const touch2 = e.touches[1];

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
    const rect = canvas.getBoundingClientRect();

    if (e.touches.length === 0 && e.changedTouches.length > 0) {
        // Single finger was lifted - check if it was a tap or drag
        const touch = e.changedTouches[0];
        const canvasX = touch.clientX - rect.left;
        const canvasY = touch.clientY - rect.top;

        // Check if this was a tap (finger didn't move much) vs a drag
        const dx = canvasX - mouseDownPos.x;
        const dy = canvasY - mouseDownPos.y;
        const distanceMoved = Math.sqrt(dx * dx + dy * dy);

        // If finger moved less than 10 pixels, treat it as a tap (more lenient than mouse)
        if (distanceMoved < 10) {
            // Check if tapping on a camp
            const geo = canvasToGeo(canvasX, canvasY);
            const tappedCamp = findCampAtLocation(geo.lon, geo.lat);

            if (tappedCamp && tappedCamp.properties && tappedCamp.properties.fid) {
                const fid = tappedCamp.properties.fid;
                const campName = campFidMappings && campFidMappings[fid] ? campFidMappings[fid] : `FID ${fid}`;

                // On mobile (touch), always go directly to full-page view
                openFullCampInfo(campName);
            }
        }

        // End panning
        isPanning = false;
        lastTouchDistance = 0;
    } else if (e.touches.length < 2) {
        // Less than 2 fingers - end pinch zoom
        lastTouchDistance = 0;
    }
});

// Search functionality
let searchInput = null;
let searchAutocomplete = null;
let autocompleteResults = [];
let selectedAutocompleteIndex = -1;

function initializeSearch() {
    searchInput = document.getElementById('campSearch');
    searchAutocomplete = document.getElementById('searchAutocomplete');

    if (!searchInput || !searchAutocomplete) return;

    // Handle input changes
    searchInput.addEventListener('input', handleSearchInput);

    // Handle keyboard navigation
    searchInput.addEventListener('keydown', handleSearchKeydown);

    // Handle focus/blur
    searchInput.addEventListener('focus', handleSearchFocus);
    searchInput.addEventListener('blur', handleSearchBlur);
}

function handleSearchInput(e) {
    const query = e.target.value.trim().toLowerCase();

    if (query.length === 0) {
        hideAutocomplete();
        return;
    }

    // Get all camp names
    const campNames = Object.keys(campFidMappings || {}).map(fid => campFidMappings[fid]);

    // Filter camps that match the query
    autocompleteResults = campNames
        .filter(name => name.toLowerCase().includes(query))
        .sort((a, b) => {
            // Prioritize matches at the start of the name
            const aStarts = a.toLowerCase().startsWith(query);
            const bStarts = b.toLowerCase().startsWith(query);
            if (aStarts && !bStarts) return -1;
            if (!aStarts && bStarts) return 1;
            return a.localeCompare(b);
        })
        .slice(0, 10); // Limit to 10 results

    if (autocompleteResults.length > 0) {
        showAutocomplete(autocompleteResults, query);
    } else {
        hideAutocomplete();
    }
}

function handleSearchKeydown(e) {
    if (!searchAutocomplete || searchAutocomplete.style.display === 'none') {
        if (e.key === 'Enter' && autocompleteResults.length > 0) {
            // Search for the first result
            zoomToCamp(autocompleteResults[0]);
            searchInput.blur();
        }
        return;
    }

    if (e.key === 'ArrowDown') {
        e.preventDefault();
        selectedAutocompleteIndex = Math.min(selectedAutocompleteIndex + 1, autocompleteResults.length - 1);
        updateAutocompleteSelection();
    } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        selectedAutocompleteIndex = Math.max(selectedAutocompleteIndex - 1, -1);
        updateAutocompleteSelection();
    } else if (e.key === 'Enter') {
        e.preventDefault();
        if (selectedAutocompleteIndex >= 0) {
            zoomToCamp(autocompleteResults[selectedAutocompleteIndex]);
        } else if (autocompleteResults.length > 0) {
            zoomToCamp(autocompleteResults[0]);
        }
        searchInput.blur();
        hideAutocomplete();
    } else if (e.key === 'Escape') {
        hideAutocomplete();
        searchInput.blur();
    }
}

function handleSearchFocus() {
    // Select all text so user can easily type a new search
    searchInput.select();

    if (autocompleteResults.length > 0) {
        showAutocomplete(autocompleteResults, searchInput.value.trim().toLowerCase());
    }
}

function handleSearchBlur() {
    // Delay hiding to allow click events on autocomplete items
    setTimeout(() => {
        hideAutocomplete();
    }, 200);
}

function showAutocomplete(results, query) {
    searchAutocomplete.innerHTML = '';
    selectedAutocompleteIndex = -1;

    results.forEach((campName, index) => {
        const item = document.createElement('div');
        item.className = 'autocomplete-item';
        item.textContent = campName;
        item.setAttribute('data-index', index);

        // Highlight matching text
        const lowerName = campName.toLowerCase();
        const matchIndex = lowerName.indexOf(query);
        if (matchIndex >= 0) {
            const before = campName.substring(0, matchIndex);
            const match = campName.substring(matchIndex, matchIndex + query.length);
            const after = campName.substring(matchIndex + query.length);
            item.innerHTML = `${escapeHtml(before)}<strong>${escapeHtml(match)}</strong>${escapeHtml(after)}`;
        }

        item.addEventListener('mousedown', (e) => {
            e.preventDefault(); // Prevent blur
            zoomToCamp(campName);
            searchInput.value = campName;
            hideAutocomplete();
        });

        searchAutocomplete.appendChild(item);
    });

    searchAutocomplete.style.display = 'block';
}

function hideAutocomplete() {
    if (searchAutocomplete) {
        searchAutocomplete.style.display = 'none';
    }
    selectedAutocompleteIndex = -1;
}

function updateAutocompleteSelection() {
    const items = searchAutocomplete.querySelectorAll('.autocomplete-item');
    items.forEach((item, index) => {
        if (index === selectedAutocompleteIndex) {
            item.classList.add('selected');
        } else {
            item.classList.remove('selected');
        }
    });
}

function zoomToCamp(campName) {
    // Find the FID for this camp
    let targetFid = null;
    for (const fid in campFidMappings) {
        if (campFidMappings[fid] === campName) {
            targetFid = fid;
            break;
        }
    }

    if (!targetFid || !campOutlines) return;

    // Find the camp outline feature
    const feature = campOutlines.features.find(f => f.properties.fid === parseInt(targetFid));
    if (!feature || feature.geometry.type !== 'LineString') return;

    const coordinates = feature.geometry.coordinates;
    if (coordinates.length === 0) return;

    // Calculate bounding box
    let minLon = Infinity, maxLon = -Infinity;
    let minLat = Infinity, maxLat = -Infinity;

    coordinates.forEach(coord => {
        const [lon, lat] = coord;
        minLon = Math.min(minLon, lon);
        maxLon = Math.max(maxLon, lon);
        minLat = Math.min(minLat, lat);
        maxLat = Math.max(maxLat, lat);
    });

    // Calculate center
    const centerLon = (minLon + maxLon) / 2;
    const centerLat = (minLat + maxLat) / 2;

    // Calculate dimensions
    const lonSpan = maxLon - minLon;
    const latSpan = maxLat - minLat;

    // Zoom so the camp takes up about 30% of the screen
    const latScale = Math.cos(centerLat * Math.PI / 180);
    const scaleX = (canvas.width * 0.3) / (lonSpan * latScale);
    const scaleY = (canvas.height * 0.3) / latSpan;
    const targetScale = Math.min(scaleX, scaleY);

    // Animate to the new position, then highlight the camp
    animateViewport(centerLon, centerLat, targetScale, () => {
        // Highlight the camp after animation completes
        highlightedCamp = feature;
        redraw();
    });
}

function animateViewport(targetCenterX, targetCenterY, targetScale, onComplete) {
    const startCenterX = viewport.centerX;
    const startCenterY = viewport.centerY;
    const startScale = viewport.scale;

    const duration = 500; // milliseconds
    const startTime = Date.now();

    function animate() {
        const elapsed = Date.now() - startTime;
        const progress = Math.min(elapsed / duration, 1);

        // Ease in-out function
        const eased = progress < 0.5
            ? 2 * progress * progress
            : 1 - Math.pow(-2 * progress + 2, 2) / 2;

        viewport.centerX = startCenterX + (targetCenterX - startCenterX) * eased;
        viewport.centerY = startCenterY + (targetCenterY - startCenterY) * eased;
        viewport.scale = startScale + (targetScale - startScale) * eased;

        redraw();

        if (progress < 1) {
            requestAnimationFrame(animate);
        } else if (onComplete) {
            onComplete();
        }
    }

    animate();
}

// Handle window resize
window.addEventListener('resize', resizeCanvas);

// Handle ESC key to close full camp info, and typing to search
window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        if (fullCampInfoOpen) {
            closeFullCampInfo();
        }
    }

    // Don't interfere with keyboard navigation when full camp info is open
    if (fullCampInfoOpen) {
        return;
    }

    // If a letter/number is typed and search box is not focused, focus it and start searching
    if (searchInput && document.activeElement !== searchInput) {
        // Check if it's a single printable character (letter, number, space, etc.)
        if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
            // Focus the search box and clear it
            searchInput.value = '';
            searchInput.focus();
            // The character will be typed into the now-focused input naturally
        }
    }
});

// Start the application
init();
