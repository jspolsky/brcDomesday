// Canvas and rendering setup
const canvas = document.getElementById('mapCanvas');
const ctx = canvas.getContext('2d');
const loadingStatus = document.getElementById('loadingStatus');

// Data storage
let campOutlines = null;
let campFidMappings = null; // Maps FID to camp name
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

    // Load camp outlines
    campOutlines = await loadGeoJSON('data/camp_outlines_2025.geojson');

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
function toggleOutlines() {
    showOutlines = !showOutlines;
    redraw();
}

// Info button handler (placeholder)
function showInfo() {
    alert('BRC Domesday Book\n\nAn interactive map viewer for Burning Man 2025 camp locations.\n\nControls:\n- Click and drag to pan\n- Scroll to zoom\n- Hover over camps to see their names');
}

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
            } else {
                campDisplay.textContent = '';
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
        document.getElementById('currentCamp').textContent = '';
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
