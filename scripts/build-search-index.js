#!/usr/bin/env node

/**
 * Build semantic search index for BRC Domesday
 *
 * This script:
 * 1. Loads camp data, mappings, and history
 * 2. Extracts searchable content from each camp
 * 3. Generates embeddings using transformers.js
 * 4. Outputs a compressed search index
 *
 * Usage: node scripts/build-search-index.js
 */

import { pipeline } from '@xenova/transformers';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const DATA_DIR = path.join(__dirname, '..', 'data');

// Load data files
function loadJSON(filename) {
    const filepath = path.join(DATA_DIR, filename);
    return JSON.parse(fs.readFileSync(filepath, 'utf-8'));
}

const campFidMappings = loadJSON('camp_fid_mappings.json');
const campsData = loadJSON('camps.json');
const campHistory = loadJSON('campHistory.json');

// Create a map for faster camp lookup
const campsMap = new Map();
campsData.forEach(camp => {
    campsMap.set(camp.name, camp);
});

/**
 * Extract searchable text for a camp
 */
function buildSearchableText(campName, campData, history) {
    const parts = [];

    // Camp name (repeated for higher weight)
    if (campName) {
        parts.push(campName);
        parts.push(campName);
    }

    // Current description
    if (campData?.description) {
        parts.push(campData.description);
    }

    // Recent history descriptions (last 2 years)
    if (history?.history) {
        const recentHistory = history.history
            .filter(h => h.year >= 2023 && h.year < 2025)
            .map(h => h.description)
            .filter(Boolean);
        parts.push(...recentHistory);
    }

    // Event titles and descriptions (prioritize recent years)
    // Sort by year descending so we get most recent events first
    if (history?.history) {
        const sortedHistory = [...history.history].sort((a, b) => b.year - a.year);

        sortedHistory.forEach(yearEntry => {
            if (yearEntry.events && yearEntry.events.length > 0) {
                yearEntry.events.forEach(event => {
                    // For events, prioritize name and type over description for token efficiency
                    const eventText = [
                        event.event_name,
                        event.event_type,
                        // Include description but make it optional if we're running long
                        event.description
                    ].filter(Boolean).join('. ');
                    if (eventText) {
                        parts.push(eventText);
                    }
                });
            }
        });
    }

    // Combine all parts
    let searchText = parts.join('. ');

    // Truncate if too long (to avoid token limits)
    // all-MiniLM-L6-v2 has a 512 token limit
    // Rough estimate: 1 token ≈ 4 characters
    // Being conservative to leave room for tokenization overhead
    const MAX_CHARS = 2000; // ~500 tokens, close to the limit
    if (searchText.length > MAX_CHARS) {
        // Smart truncation: try to end at a sentence boundary
        const truncated = searchText.substring(0, MAX_CHARS);
        const lastPeriod = truncated.lastIndexOf('. ');
        searchText = lastPeriod > MAX_CHARS * 0.8 ? truncated.substring(0, lastPeriod + 1) : truncated;
    }

    return searchText;
}

/**
 * Create a short snippet for display
 */
function createSnippet(campData) {
    if (!campData?.description) return '';

    const desc = campData.description;
    const MAX_LENGTH = 150;

    if (desc.length <= MAX_LENGTH) return desc;

    // Truncate at word boundary
    const truncated = desc.substring(0, MAX_LENGTH);
    const lastSpace = truncated.lastIndexOf(' ');
    return truncated.substring(0, lastSpace) + '...';
}

/**
 * Calculate camp statistics
 */
function calculateStats(campName, history) {
    const stats = {
        hasEvents: false,
        yearsActive: 0,
        hasImages: false
    };

    if (!history) return stats;

    // Years active (excluding 2025)
    const historicalYears = history.history.filter(h => h.year !== 2025);
    stats.yearsActive = historicalYears.length;

    // Has events
    const hasEvents = history.history.some(h => h.events && h.events.length > 0);
    stats.hasEvents = hasEvents;

    // Has images
    stats.hasImages = history.images && history.images.length > 0;

    return stats;
}

/**
 * Main function to build the search index
 */
async function buildSearchIndex() {
    console.log('🚀 Building semantic search index...\n');

    // Initialize the embedding pipeline
    console.log('📦 Loading embedding model (this may take a minute on first run)...');
    const embedder = await pipeline(
        'feature-extraction',
        'Xenova/all-MiniLM-L6-v2'
    );
    console.log('✅ Model loaded\n');

    const index = {
        version: '1.0',
        model: 'Xenova/all-MiniLM-L6-v2',
        dimensions: 384,
        created: new Date().toISOString(),
        camps: []
    };

    const campEntries = Object.entries(campFidMappings);
    let processed = 0;

    console.log(`Processing ${campEntries.length} camps...\n`);

    for (const [fid, campName] of campEntries) {
        processed++;

        // Get camp data
        const campData = campsMap.get(campName);
        const history = campHistory[campName];

        // Skip camps that have neither current data nor historical data
        // These are likely old camp outlines that no longer exist
        if (!campData && !history) {
            console.log(`⚠️  Skipping ${campName} (no current or historical data)`);
            continue;
        }

        // Build searchable text
        const searchText = buildSearchableText(campName, campData, history);

        if (!searchText.trim()) {
            console.log(`⚠️  Skipping ${campName} (no searchable content)`);
            continue;
        }

        // Generate embedding
        const output = await embedder(searchText, {
            pooling: 'mean',
            normalize: true
        });

        // Extract the embedding array
        const embedding = Array.from(output.data);

        // Add to index
        index.camps.push({
            fid: fid,
            name: campName,
            embedding: embedding,
            snippet: createSnippet(campData),
            location: campData?.location_string || '',
            stats: calculateStats(campName, history)
        });

        // Progress indicator
        if (processed % 50 === 0) {
            console.log(`✓ Processed ${processed}/${campEntries.length} camps`);
        }
    }

    console.log(`\n✅ Processed all ${index.camps.length} camps\n`);

    // Write the index file
    const outputPath = path.join(DATA_DIR, 'search-index.json');
    fs.writeFileSync(outputPath, JSON.stringify(index, null, 2));

    const stats = fs.statSync(outputPath);
    const sizeMB = (stats.size / 1024 / 1024).toFixed(2);

    console.log(`💾 Search index saved to: ${outputPath}`);
    console.log(`📊 File size: ${sizeMB} MB`);
    console.log(`🎯 Total camps indexed: ${index.camps.length}`);

    // Also create a compressed version
    console.log('\n📦 Creating compressed version...');
    const compressedPath = path.join(DATA_DIR, 'search-index-compressed.json');

    // Create compressed version with float32 arrays stored more efficiently
    const compressedIndex = {
        ...index,
        camps: index.camps.map(camp => ({
            ...camp,
            // Store embedding as base64-encoded Float32Array for smaller size
            embedding: Buffer.from(new Float32Array(camp.embedding).buffer).toString('base64')
        }))
    };

    fs.writeFileSync(compressedPath, JSON.stringify(compressedIndex));
    const compressedStats = fs.statSync(compressedPath);
    const compressedSizeMB = (compressedStats.size / 1024 / 1024).toFixed(2);
    console.log(`💾 Compressed index saved to: ${compressedPath}`);
    console.log(`📊 Compressed size: ${compressedSizeMB} MB`);

    console.log('\n✨ Done!');
}

// Run the script
buildSearchIndex().catch(error => {
    console.error('❌ Error building search index:', error);
    process.exit(1);
});
