# Semantic Search Implementation

This document explains how to build and use the semantic search feature for BRC Domesday.

## Overview

The semantic search system uses machine learning embeddings to enable intelligent camp searching beyond simple keyword matching. Users can search for concepts (like "jazz music" or "meditation") and find relevant camps even if those exact words don't appear in the camp name.

## Architecture

- **Build time**: Pre-compute embeddings for all camps using `transformers.js`
- **Runtime**: Load search index and ML model client-side (lazy loading)
- **No server required**: All processing happens in the browser

## Building the Search Index

### Prerequisites

1. Install Node.js (version 18 or higher)
2. Install dependencies:

```bash
npm install
```

### Generate the Index

Run the build script:

```bash
npm run build-search-index
```

This will:
1. Load camp data from `data/` directory
2. Extract searchable content from each camp (name, description, events, history)
3. Generate embeddings using the `Xenova/all-MiniLM-L6-v2` model
4. Create two files:
   - `data/search-index.json` - Full JSON with embeddings
   - `data/search-index-compressed.json` - Compressed version (base64-encoded)

**Build time**: ~5-10 minutes for 1000 camps

**Output size**:
- Full: ~2-3 MB
- Compressed: ~1.5-2 MB

### What Gets Indexed?

For each camp, the following content is extracted and weighted:

- **Camp name** (2x weight)
- **Current description** (2025)
- **Recent history** (2023-2024 descriptions)
- **Event titles and descriptions** (all events, prioritized by most recent years first)

Content is truncated to ~500 tokens to fit model limits. Events are prioritized by year (newest first), so if a camp has many events, the most recent ones will be indexed first.

## How It Works

### Client-Side Flow

1. **User starts typing**: Search remains keyword-based initially
2. **First search**: Semantic search initializes in background
   - Downloads ~23MB ML model (cached permanently)
   - Loads ~1.5MB search index
   - Takes ~3-5 seconds on first use
3. **Subsequent searches**: Fast semantic search (~100-200ms per query)

### Search Scoring

The system uses **hybrid scoring**:

```javascript
finalScore = (semanticScore × 0.7) + (keywordScore × 0.3)
```

- **Semantic score**: Cosine similarity between query and camp embeddings
- **Keyword score**: Exact/prefix/substring matching on camp names

This ensures:
- Exact name matches still rank high
- Semantic relevance is primary factor
- Keyword stuffing doesn't dominate results

### Example Queries

**Semantic understanding**:
- Query: "acoustic music" → Finds camps with "jazz", "folk", "guitar"
- Query: "meditation" → Finds "mindfulness", "yoga", "zen" camps
- Query: "art workshops" → Finds camps offering painting, sculpture, crafts

**Exact matches still work**:
- Query: "village" → Camps with "village" in the name rank highest
- Query: "center" → Exact substring matches boosted

## Files

### Source Files

```
scripts/
  build-search-index.js     # Build script to generate index

semantic-search.js          # Client-side search module
map.js                      # Updated with search integration
```

### Generated Files

```
data/
  search-index.json              # Full search index
  search-index-compressed.json   # Compressed version (used by frontend)
```

### Configuration

```
package.json              # Node dependencies
```

## Deployment

1. Build the search index locally:
   ```bash
   npm run build-search-index
   ```

2. Commit the generated index to git:
   ```bash
   git add data/search-index-compressed.json
   git commit -m "Update search index"
   ```

3. Deploy the app - the search index will be loaded on-demand

## Performance

### Build Time
- Initial build: ~5-10 minutes (downloads model)
- Subsequent builds: ~3-5 minutes (model cached)

### Runtime Performance
- **First search**: 3-5 seconds (one-time initialization)
- **Subsequent searches**: 100-200ms per query
- **Model download**: ~23MB (one-time, cached in browser)
- **Index download**: ~1.5MB (one-time per session)

### Browser Compatibility

Works in all modern browsers that support:
- ES6 modules
- WebAssembly (for transformers.js)
- Async/await

Tested on:
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Customization

### Adjust Search Weights

In `semantic-search.js`, modify the hybrid search weights:

```javascript
async search(query, options = {}) {
  const {
    semanticWeight = 0.7,  // Adjust: 0-1
    keywordWeight = 0.3    // Should sum to 1.0
  } = options;
  // ...
}
```

### Change Minimum Score

Lower minScore to show more results (may include less relevant):

```javascript
const results = await semanticSearch.search(query, {
  minScore: 0.1  // Default: 0.2
});
```

### Modify Indexed Content

In `build-search-index.js`, edit the `buildSearchableText()` function to change what content is indexed and how it's weighted.

## Troubleshooting

### Search not working

1. Check browser console for errors
2. Verify `data/search-index-compressed.json` exists
3. Check that `semantic-search.js` loads as ES6 module

### Slow initial load

The first search downloads a 23MB ML model. This is normal and only happens once (then cached).

### Results not relevant

1. Rebuild the index with updated camp data
2. Adjust semantic/keyword weights
3. Lower minScore threshold

### Build script fails

- Check Node.js version (need 18+)
- Run `npm install` to ensure dependencies are installed
- Check that data files exist in `data/` directory

## Future Enhancements

Possible improvements:

1. **Query expansion**: Automatically expand queries with synonyms
2. **Filters**: Filter by location, camp type, year active
3. **Personalization**: Learn from user's search history
4. **Image search**: Search based on camp images
5. **Voice search**: Use speech recognition for queries
6. **Multi-language**: Support non-English queries

## Cost Analysis

**One-time build cost**: Free (uses local transformers.js)

**Runtime cost**: Zero
- No API calls
- No server backend
- All processing client-side

**Alternative (OpenAI-based)**:
- Build: ~$0.10 (one-time)
- Runtime: ~$0.00002 per search query
- Requires API key and proxy endpoint

## Credits

Built with:
- [transformers.js](https://github.com/xenova/transformers.js) - Run transformers in the browser
- [all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) - Sentence embedding model
