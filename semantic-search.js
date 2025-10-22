/**
 * Semantic Search Module for BRC Domesday
 *
 * This module provides client-side semantic search using pre-computed embeddings
 * and transformers.js for query encoding.
 *
 * Features:
 * - Lazy loading of search index and ML model
 * - Cosine similarity ranking
 * - Hybrid keyword + semantic scoring
 */

class SemanticSearch {
    constructor() {
        this.searchIndex = null;
        this.embedder = null;
        this.isLoading = false;
        this.isReady = false;
    }

    /**
     * Initialize the search engine (loads index and model)
     */
    async initialize() {
        if (this.isReady) return;
        if (this.isLoading) {
            // Wait for existing initialization to complete
            while (this.isLoading) {
                await new Promise(resolve => setTimeout(resolve, 100));
            }
            return;
        }

        this.isLoading = true;

        try {
            console.log('🔍 Initializing semantic search...');

            // Load both in parallel
            const [indexResponse, embedderModule] = await Promise.all([
                // Load search index
                fetch('data/search-index-compressed.json')
                    .then(res => res.json()),

                // Load transformers.js dynamically
                import('https://cdn.jsdelivr.net/npm/@xenova/transformers@2.17.1')
            ]);

            console.log('📦 Search index loaded');

            // Decompress embeddings from base64
            this.searchIndex = {
                ...indexResponse,
                camps: indexResponse.camps.map(camp => ({
                    ...camp,
                    embedding: this._decompressEmbedding(camp.embedding)
                }))
            };

            console.log(`✅ Indexed ${this.searchIndex.camps.length} camps`);

            // Initialize the embedding pipeline
            console.log('🤖 Loading ML model (may take a moment)...');
            this.embedder = await embedderModule.pipeline(
                'feature-extraction',
                'Xenova/all-MiniLM-L6-v2'
            );

            console.log('✅ Semantic search ready!');
            this.isReady = true;
        } catch (error) {
            console.error('❌ Failed to initialize semantic search:', error);
            throw error;
        } finally {
            this.isLoading = false;
        }
    }

    /**
     * Decompress base64-encoded Float32Array
     */
    _decompressEmbedding(base64String) {
        const binaryString = atob(base64String);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i);
        }
        return Array.from(new Float32Array(bytes.buffer));
    }

    /**
     * Calculate cosine similarity between two vectors
     */
    _cosineSimilarity(vecA, vecB) {
        if (vecA.length !== vecB.length) {
            throw new Error('Vectors must have same dimensions');
        }

        let dotProduct = 0;
        let normA = 0;
        let normB = 0;

        for (let i = 0; i < vecA.length; i++) {
            dotProduct += vecA[i] * vecB[i];
            normA += vecA[i] * vecA[i];
            normB += vecB[i] * vecB[i];
        }

        if (normA === 0 || normB === 0) return 0;

        return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
    }

    /**
     * Calculate keyword match score for hybrid search
     */
    _keywordScore(query, campName) {
        const q = query.toLowerCase().trim();
        const n = campName.toLowerCase();

        if (n === q) return 1.0;           // Exact match
        if (n.startsWith(q)) return 0.8;   // Starts with
        if (n.includes(q)) return 0.5;     // Contains

        // Check for word boundaries
        const words = q.split(/\s+/);
        const nameWords = n.split(/\s+/);

        let matchedWords = 0;
        words.forEach(word => {
            if (nameWords.some(nw => nw.includes(word))) {
                matchedWords++;
            }
        });

        if (matchedWords === words.length) return 0.4;  // All words present
        if (matchedWords > 0) return 0.2;                // Some words present

        return 0;
    }

    /**
     * Search for camps matching the query
     */
    async search(query, options = {}) {
        const {
            limit = 10,
            minScore = 0.2,
            semanticWeight = 0.7,  // 70% semantic, 30% keyword
            keywordWeight = 0.3
        } = options;

        if (!this.isReady) {
            throw new Error('Search engine not initialized. Call initialize() first.');
        }

        if (!query || query.trim().length === 0) {
            return [];
        }

        const startTime = performance.now();

        // Generate embedding for the query
        const queryEmbedding = await this._embedQuery(query);

        // Score all camps
        const results = this.searchIndex.camps.map(camp => {
            // Semantic similarity
            const semanticScore = this._cosineSimilarity(queryEmbedding, camp.embedding);

            // Keyword match
            const keywordScore = this._keywordScore(query, camp.name);

            // Hybrid score
            const finalScore = (semanticScore * semanticWeight) + (keywordScore * keywordWeight);

            return {
                fid: camp.fid,
                name: camp.name,
                snippet: camp.snippet,
                location: camp.location,
                stats: camp.stats,
                score: finalScore,
                semanticScore: semanticScore,
                keywordScore: keywordScore
            };
        });

        // Sort by score (descending)
        results.sort((a, b) => b.score - a.score);

        // Filter by minimum score
        const filteredResults = results.filter(r => r.score >= minScore);

        // Limit results
        const limitedResults = filteredResults.slice(0, limit);

        const endTime = performance.now();
        const searchTime = (endTime - startTime).toFixed(2);

        console.log(`🔍 Search completed in ${searchTime}ms, found ${limitedResults.length} results`);

        return limitedResults;
    }

    /**
     * Generate embedding for a query string
     */
    async _embedQuery(query) {
        const output = await this.embedder(query, {
            pooling: 'mean',
            normalize: true
        });

        return Array.from(output.data);
    }

    /**
     * Get a preview of indexed camps (for debugging)
     */
    getIndexInfo() {
        if (!this.searchIndex) {
            return null;
        }

        return {
            version: this.searchIndex.version,
            model: this.searchIndex.model,
            dimensions: this.searchIndex.dimensions,
            totalCamps: this.searchIndex.camps.length,
            created: this.searchIndex.created,
            sampleCamps: this.searchIndex.camps.slice(0, 5).map(c => c.name)
        };
    }
}

// Create singleton instance
const semanticSearch = new SemanticSearch();

// Export the instance
export default semanticSearch;
