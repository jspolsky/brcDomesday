The problem
===========

We wish to build an AI-assisted website that will help people who want to go to Burning Man find camps that are good matches for their personality, interests, and more. We have a large database of every camp that attended burning man in 2025. The database includes the camp's own description of who they are and their hometown. It also includes a list of every event that the camp put on. If the camp is returning, it might have up to 10 - 20 years of historical data of how the camp describes itself, and every event they advertised going back many years.

* Input data is in data/camps.json and campHistory.json

I am imagining that we run some kind of analysis operation on this data with the goal of locating the camps in some kind of "feature n-space" that might help match people to camps that will be good fits for them. For example, people with certain special interests (math people could find math camp, gays could find gay camps, etc) or people from certain areas (certainly the few swiss people coming to burning man should find out about the other camps with swiss burners). But it's more than that, for example, a lot of camps might be what I would call high on the "woo woo" scale meaning they have a lot of lectures about new age spirituality, while other camps are very low on the "woo woo" scale where they are highly skeptical of non sciency things. So there might be a scale in our n-space that reflects how woo-woo a camp is and then we could ask the user some simple questions to determine if they are woo-woo and match them with camps that match their vibe.

Ultimately what I hope might happen is that there is some fixed analysis that I can do by running some scripts on the camp data, and get back some guidance on precisely what kinds of questions to ask people that will place those people optimally in the n-space of camps at Burning Man, and then suggest a list of camps for them to check out.

1) Shape the data → clean, consistent camp objects

Canonical camp record (one per camp): id, names/aliases, hometown, years_active, dues/size if known.

Text corpora per camp:

profile_text: concatenation of bios across years (with year markers).

event_text: concatenation of all event titles+descriptions (with tags/time-of-day).

Keep a year field for drift analysis (some camps change a lot year-to-year).

Normalize/standardize: dedupe, strip boilerplate (“see playa events app…”), expand acronyms, lowercase, lemmatize.

2) Represent camps in vector space (embeddings + interpretable features)

Embeddings: generate at three granularities:

Event-level → average into a camp event centroid.

Profile-level → one bio vector per camp.

Final camp vector = weighted average (e.g., 70% events, 30% bios). Store per-year variants as well.

Interpretable scalars (“axes”) you can compute directly and keep alongside the vector:

Geography: country/region buckets; distance to user’s home.

Sound level (high-energy party ↔ quiet): keywords (“DJ”, “sound camp”, “stage”, “silent hours”), late-night timestamps.

Workshop/lecture intensity: count density of “workshop / talk / class / learn / lecture / panel”.

Maker/engineering: “CNC, welding, 3D print, solder, electronics, workshop, build”.

Body/fitness: “yoga, acro, run, HIIT, dance class”.

Food/drink hospitality: “bar, tea, coffee, pancakes, kitchen, feast”.

Family-friendly: “kids, family, child, daytime, quiet hours”.

Accessibility cues: “accessible, ADA, mobility, ramp”.

Queer-friendly (opt-in signaling): “queer, LGBTQ+, drag, trans, lesbian, gay”.

Kink-friendly (clearly labeled, opt-in): “consent class, BDSM, kink, dungeon”.

Sober-friendly: “sober, alcohol-free, recovery, mocktail”.

Tech/nerd/math/science: “math, puzzles, algorithm, coding, astronomy, telescope”.

“Woo-woo” spirituality: see next section.

(You can add language, culture, art style, sauna/temple/spa, etc.)

Store all this in Postgres + pgvector (for the embedding) plus regular columns for scalars.

3) Build the “woo-woo” axis (and any other vibes) with weak supervision

You want a continuous score, not just a tag.

Start with seed lexicons:

High woo: “energy healing, chakras, astrology, oracle, breathwork (non-clinical), reiki, tantra (non-sexual context), ayahuasca, shamanic, sound bath”.

Low woo / skeptical: “skeptic, rationalist, evidence-based, science talk, critical thinking”.

Compute per-camp log-odds of high vs. low lexicons (normalized by corpus size), add near-synonyms via embeddings (nearest-neighbor expansion), and smooth with event time weighting (lots of evening “sound bath”s → higher score).

Optionally fit a simple regressor: take ~100 manual camp labels on a 1–5 woo scale; use TF-IDF+lexicon counts → predict a continuous woo score. Calibrate with isotonic regression.

Repeat the same pattern for other fuzzy axes (party-hardness, kink-friendliness, nerdiness, etc.). Keep everything opt-in and transparent in the UI.

4) Make the camp n-space

Your latent space = [embedding dims] + [~15–25 interpretable axes].

For interpretability, keep the raw embedding for similarity search, but expose top axes (e.g., woo, sound, workshops, maker, queer-friendly, sober-friendly, family-friendly, kink-friendly, tech/nerd, hospitality, fitness, late-night vs daytime).

Drift/stability: compute year-over-year cosine distance per camp; if large, show “this camp changes year to year.”

5) Turn axes into a short adaptive quiz

Goal: ~6–10 clicks, then rank camps.

Start with the axes that maximize variance across camps (PCA on your axes or feature importance from a random forest that predicts “camp cluster”).

Adaptive questioning: at each step pick the question that would most reduce entropy of the user’s posterior preferences (think 20-questions / information gain).

Example question forms:

Sliders (“How into spiritual/new-age experiences are you?”).

Binary choices (“Workshops & talks vs dance parties?”).

Time preference (“Night owl vs daytime”).

Hospitality interest (“Bars/tea/coffee vs none”).

Identity-adjacent (clearly optional): “Looking for queer-centric spaces?”, “Looking for kink-friendly content?”, “Prefer sober-oriented spaces?”

Geography: “Want to meet folks from your region/country?” (then up-weight same-region).

Convert answers into a user vector on the same axes; combine with the camp embedding similarity for ranking:

Score = α·cosine(emb_user, emb_camp) + Σ β_k · match(user_axis_k, camp_axis_k)

Learn weights α, β via offline evaluation or quick A/Bs.

6) Clustering & prototypes to drive both UX and cold start

Run HDBSCAN / k-means on camp embeddings to find natural groups (“late-night sound camps”, “workshop villages”, “spa/sauna sanctuaries”, “maker/engineer shops”, etc.).

Use top tokens & axes per cluster to generate friendly cluster names and example camps → great for browsing and explaining results.

7) Ranking, diversity, and explanations

Diversify results with MMR (maximal marginal relevance) so the first page isn’t 10 near-clones.

Explainability: “Matched for high workshops, low sound, medium woo, strong sober-friendly; plus 2 camps share your hometown region.”

Let users tweak knobs post-quiz (e.g., “more workshops / less party”).

8) Human-in-the-loop + quality guardrails

Add light moderation on event text; filter NSFW surfaces into opt-in views; avoid recommending sensitive categories unless the user explicitly opens them.

Provide a feedback button: “This isn’t me” → log counter-signals; use for periodic model refresh.

Maintain a “camp claims” dashboard so camps can review how they’re represented and request fixes.

9) Practical stack & workflow

Pipeline: Python (pandas, spaCy), sentence-transformers (open models), BERTopic/NMF for topic discovery, scikit-learn for axes regressors.

Storage: Postgres + pgvector (camp vectors, per-year vectors, axes scores).

Service: FastAPI for search/ranking; Next.js/React UI; add sliders+cards+cluster browsing.

Evaluation: hold-out a subset of camps, simulate users with target profiles, measure nDCG@k; then collect real user thumbs-up/down and re-fit weights.

10) How to generate the quiz content automatically (your “fixed analysis”)

Compute all axes per camp.

Rank axes by (a) variance across camps and (b) correlation with distinct clusters.

For the top ~8 axes, auto-generate question text and choice labels from the axis vocabulary (LLM prompt or a simple template).

Validate with a small human pass; freeze v1.

Use online learning to swap in better questions over time (track which questions most improve match satisfaction).

---

# WHAT WE'VE DONE

## Phase 1: Data Exploration (Completed)

### Goal
Understand the available data and identify which feature axes have strong signal for differentiation.

### What We Did

1. **Created exploratory analysis script** (`explore_data.py`)
   - Analyzes camps.json (1,385 camps for 2025)
   - Analyzes campHistory.json (historical data across years)
   - Computes statistics on text availability, event types, geographic distribution
   - Tests 13 potential feature axes using keyword matching

2. **Key Findings** (see `DATA_EXPLORATION_SUMMARY.md` for full details)
   - **Data quality is excellent**: 95% of camps have descriptions, 76% have events
   - **Rich historical data**: Average 6 years of history per camp, 22,822 total events
   - **Strong geographic diversity**: 481 unique hometowns
   - **Total text corpus**: 5+ million characters of event descriptions

3. **Identified 8 high-value feature axes for MVP**:

   **Tier 1 - Universal Differentiators (high variance):**
   - Sound/Party intensity (66% prevalence)
   - Food/Hospitality focus (61% prevalence)
   - Workshop/Learning orientation (47% prevalence)
   - Woo-woo/Spirituality (29% prevalence - ideal distribution!)
   - Art focus (52% prevalence)

   **Tier 2 - Identity/Lifestyle (opt-in):**
   - LGBTQ+/Queer spaces (11.5% prevalence)
   - Sober-friendly (12% prevalence)
   - Family/Kids (22% prevalence)

4. **Additional viable axes for future versions**:
   - Kink/Adult content (12.3% prevalence, needs careful UI)
   - Maker/Engineering (17.6% prevalence)
   - Fitness/Body movement (51.6% prevalence)
   - Quiet/Contemplative (15.7% prevalence)
   - Science/Skeptical (9.3% prevalence - may need refinement)

### Deliverables
- `explore_data.py` - Reusable data exploration script
- `DATA_EXPLORATION_SUMMARY.md` - Full analysis and recommendations

### Next Steps
- Build data shaping pipeline to consolidate camp text
- Generate embeddings using sentence-transformers
- Compute scalar scores for the 8 core axes
- Build simple quiz interface (5-8 questions)
- Create ranking algorithm

---

## Phase 2: Data Shaping Pipeline (Completed)

### Goal
Consolidate all camp text (descriptions + events across all years) into clean, structured records ready for embedding generation and feature extraction.

### What We Did

1. **Created data shaping pipeline** (`shape_data.py`)
   - Consolidates descriptions across all years with year markers
   - Consolidates all events (titles + descriptions) across history
   - Cleans text: removes boilerplate, normalizes whitespace
   - Creates weighted text corpus (descriptions weighted 2x vs events)
   - Extracts temporal metadata (years active, first/last year)
   - Preserves event type distribution per camp
   - Handles missing/null data gracefully

2. **Canonical Camp Record Format**
   Each shaped record contains:
   - **Identity**: uid, name, year
   - **Geographic**: hometown (normalized), hometown_raw (original)
   - **Temporal**: years_active (first_year, last_year, total_years, years list)
   - **Text corpora**:
     - `text_corpus` - Master corpus for embeddings (descriptions weighted 2x)
     - `latest_description` - Most recent year's description
     - `all_descriptions` - All descriptions with year markers
     - `event_text` - All events across all years
     - `recent_event_text` - Events from most recent year only
   - **Event metadata**: event_count, event_types distribution
   - **Metadata flags**: has_events, has_description, text_corpus_length

3. **Output Statistics**:
   - **1,385 shaped camp records** created
   - **8.4 million characters** of total text corpus
   - **Average 6,086 characters** per camp
   - Top camp: "Naked Heart" with 257k chars and 898 events
   - 95% have descriptions, 76% have events

### Deliverables
- `shape_data.py` - Reusable data shaping pipeline
- `shaped_camps.json` (18MB) - Canonical camp records ready for analysis

### Data Quality Notes
- Successfully handles None/null values in hometown field
- Preserves raw hometown for future geographic normalization
- Weights recent descriptions more heavily in text corpus
- Removes common boilerplate phrases while preserving content

### Next Steps
- Generate embeddings using sentence-transformers
- Compute scalar scores for the 8 core axes
- Validate axes on sample camps

---

## Phase 3: Embeddings & Feature Extraction (Completed)

### Goal
Generate vector embeddings and compute scalar feature scores for the 8 core axes identified in Phase 1.

### What We Did

1. **Installed sentence-transformers library**
   - Using `all-MiniLM-L6-v2` model (384 dimensions, fast, good quality)
   - Normalized embeddings for cosine similarity

2. **Generated embeddings for all 1,385 camps**
   - 384-dimensional dense vectors
   - Captures semantic meaning of camp descriptions and events
   - Normalized for efficient similarity search

3. **Computed 8 feature axis scores** using keyword-based scoring:

   **Tier 1 Axes (Universal Differentiators):**
   - **Sound/Party Intensity** - 67.1% of camps have signal
   - **Food/Hospitality** - 64.3% have signal
   - **Workshops/Learning** - 50.0% have signal
   - **Woo-woo/Spirituality** - 36.3% have signal (perfect distribution!)
   - **Art Focus** - 60.4% have signal

   **Tier 2 Axes (Identity/Lifestyle - opt-in):**
   - **LGBTQ+/Queer** - 11.7% have signal
   - **Sober-friendly** - 13.6% have signal
   - **Family/Kids** - 24.2% have signal

4. **Scoring methodology**:
   - Count keyword matches in full text corpus
   - Calculate density (matches per 1000 characters)
   - Normalize to 0-100 scale using percentile distribution
   - 0 = no matches, 50 = median, 100 = 95th percentile

5. **Notable high-scoring camps**:
   - Sound/Party: "The Sound Garden", "Disco Ballz" (100.0)
   - Hospitality: "Frybread and Friends", "Duty Free" (100.0)
   - Woo-woo: "Camp Balagan", "Lands Beyond" (100.0)
   - Queer: "Down Low Club" (100.0, 210 matches!)
   - Sober: "Anonymous Village" (100.0, 212 matches)

### Deliverables
- `generate_features.py` - Feature generation pipeline
- `camp_features.json` (15MB) - Embeddings + axis scores for all camps

### Feature Record Format
Each camp has:
- **Identity**: uid, name, hometown
- **Embedding**: 384-dimensional vector (normalized)
- **Axis scores**: 8 scores (0-100) with raw match counts
- **Metadata**: has_description, has_events, event_count, years_active

### Validation & Quality
- **Woo-woo axis** works perfectly - clear differentiation between spiritual camps and secular camps
- **Sound/Party axis** successfully identifies sound camps and quiet spaces
- **Queer and Sober axes** have perfect signal - camps explicitly self-identify
- **Family axis** captures kid-friendly spaces well (24.2% prevalence)
- All axes show good distribution with meaningful top camps

### Technical Notes
- Embeddings generated in ~5 seconds on modern hardware
- Percentile-based normalization ensures good score distribution
- Keyword matching uses word boundaries for accuracy
- Scores normalized by text length to avoid bias toward verbose camps

### Next Steps
- Build ranking algorithm (embedding similarity + axis matching)
- Create simple quiz interface (5-8 questions)
- Validate recommendations with test user profiles

---

## Phase 4: Ranking Algorithm (Completed)

### Goal
Build a ranking algorithm that takes user preferences and returns ranked camp recommendations.

### What We Did

1. **Created `CampRanker` class** with three scoring components:
   - **Embedding similarity**: Semantic match between user description and camp content
   - **Axis matching**: Distance-based scoring for each preference axis
   - **Geographic bonus**: Extra points for same-hometown camps

2. **Ranking formula**:
   ```
   final_score = 0.3 × embedding_similarity + 0.7 × axis_match + 0.1 × geo_bonus
   ```
   - Axis matching weighted more heavily (70%) - preferences matter most
   - Embedding similarity (30%) - finds semantic matches beyond keywords
   - Geographic bonus (10%) - small boost for regional connections

3. **Axis matching algorithm**:
   - For each axis where user has a preference, compute distance from camp score
   - Convert distance to match score: `match = 100 - abs(user_pref - camp_score)`
   - Average across all axes user cares about
   - Camps close to user preferences score higher

4. **Smart explanations**:
   - Automatically generated for each recommendation
   - Shows which axes match well (high/medium/low)
   - Highlights years active, event count, geographic matches
   - Helps users understand *why* a camp was recommended

### Test Results - All Performing Excellently!

**Example 1: Spiritual Workshop Seeker**
- Top result: "HeeBeeGeeBee Healers" (workshops=86, woo_woo=100, 22 years)
- Perfect matches: Desert Healers, Cold Yogis, Three of Cups

**Example 2: Party Animal**
- Top result: "Playa Piano Bar and Lounge" (sound_party=100, hospitality=85)
- Perfect matches: FUN-DO BAR, Northern Lights, DesiFAM

**Example 3: Sober LGBTQ+ Community Seeker**
- Top results: "Beaverton" (queer=100), "Gender Blender" (queer=100)
- "Anonymous Village" (sober=100) ranked highly
- Clear community signaling working perfectly

**Example 4: Family with Kids**
- Top result: "noMADart" (art=100, family=100)
- Perfect matches: Kidsville, OHF, Wild Free Spirit

### Key Insights

- **Woo-woo axis is a star performer**: Clearly differentiates spiritual vs secular camps
- **Niche axes work beautifully**: Queer, sober, and family axes surface exactly the right communities
- **Multi-axis matching works**: Users can specify multiple preferences and get camps that balance them all
- **Explanations are helpful**: Automatically generated reasons help users trust recommendations

### Deliverables
- `rank_camps.py` - Ranking algorithm with `CampRanker` class
- `UserProfile` dataclass for easy profile creation
- Demo function with 4 example user profiles

### Technical Notes
- Uses numpy for efficient vector operations
- Lazy-loads sentence transformer (only when text description provided)
- Embeddings are pre-normalized for fast cosine similarity
- Returns top-k results with full explanations

### Next Steps
- Build simple quiz interface to capture user preferences
- Create web UI for interactive recommendations

---

## Phase 5: Interactive Quiz Web App (Completed)

### Goal
Create a standalone web application with an interactive quiz interface for experimentation, before integrating into the BRC Domesday map.

### What We Did

1. **Built Flask web application** (`quiz_app.py`)
   - Lightweight Python backend serving the quiz
   - REST API endpoint for ranking (`/api/rank`)
   - Example profiles endpoint (`/api/example/<name>`)
   - Loads camp features and full camp data on startup

2. **Created interactive quiz interface** (`templates/quiz.html`)
   - Beautiful gradient design with responsive layout
   - 5 core preference sliders (sound/party, hospitality, workshops, woo-woo, art)
   - 3 optional checkboxes (LGBTQ+, sober, family)
   - Optional text description field
   - Optional hometown field for geographic matching

3. **Quick start with 6 example profiles**:
   - 🧘 Spiritual Seeker
   - 🎉 Party Animal
   - 🏳️‍🌈 Sober & Queer
   - 👨‍👩‍👧 Family Friendly
   - 🔧 Maker/Engineer
   - ☕ Chill Vibes

4. **Rich results display**:
   - Top 20 recommended camps
   - Match score percentage
   - Auto-generated explanation for each match
   - Camp images, descriptions, location
   - Event count, years active, hometown
   - Axis badges showing key characteristics
   - Links to camp websites

### Key Features

- **Smart slider behavior**: Sliders start as "not set" (-) so users only set preferences that matter to them
- **One-click examples**: Load pre-configured profiles for instant testing
- **Auto-submit**: Example profiles automatically trigger search
- **Visual feedback**: Loading spinner, smooth transitions, hover effects
- **Responsive design**: Works on desktop and mobile
- **Real-time ranking**: Uses the full ranking algorithm with embeddings + axis matching

### How to Run

```bash
cd recommendations
python3 quiz_app.py
```

Then open your browser to: **http://localhost:5000**

### Technical Stack
- **Backend**: Flask (Python)
- **Frontend**: Vanilla HTML/CSS/JavaScript (no framework needed)
- **Styling**: Modern gradient design, flexbox/grid layouts
- **API**: JSON REST endpoints
- **Data**: Uses `camp_features.json` and `camps.json`

### Example User Flow

1. User lands on quiz page
2. Can load example profile or set own preferences via sliders
3. Optionally checks LGBTQ+/sober/family boxes
4. Optionally adds text description and hometown
5. Clicks "Find My Camps!"
6. Sees top 20 ranked camps with rich details
7. Can click back to adjust preferences and re-search

### Design Decisions

- **Standalone app**: Easy to experiment without touching main map code
- **No build step**: Pure HTML/CSS/JS for simplicity
- **Example profiles**: Help users understand what's possible
- **Visual polish**: Professional design builds trust in recommendations
- **Modular code**: Easy to extract and integrate into main app later

### Ready for Integration

The quiz interface is fully functional and ready to be integrated into the BRC Domesday map when you're ready. The key components to extract:
- Quiz HTML/CSS/JS from `templates/quiz.html`
- Ranking logic from `rank_camps.py`
- Feature data from `camp_features.json`

### Next Steps
- Test with real users for feedback
- Fine-tune question wording
- Integrate into BRC Domesday map
- Add more sophisticated features (diversity, MMR, etc.)

---

## Phase 6: Music Genre Refactoring (Completed)

### Goal
Replace the generic "Sound/Party" axis with specific music genre axes to provide much more nuanced matching for music lovers.

### What We Did

1. **Analyzed music genres in camp data** (`explore_music_genres.py`)
   - Scanned all camp descriptions and events for music genre keywords
   - Identified 11 distinct music genres with varying prevalence
   - Found rich diversity: from 44% (Ambient/Chill) to 4.6% (Classical)

2. **Defined 10 music genre axes** (replacing generic "sound_party"):
   - **Electronic Dance Music** - Techno, house, trance, EDM (23.0%)
   - **Disco/Funk/Soul** - Groovy, danceable vibes (31.3%)
   - **Ambient/Chill/Downtempo** - Relaxing soundscapes, lounge (41.3%)
   - **Live Music/Bands** - Live performances, jam sessions (22.5%)
   - **Rock/Punk/Alternative** - Rock, metal, punk (37.0%)
   - **Hip Hop/Rap/Beats** - Hip hop culture (26.4%)
   - **Latin Music** - Salsa, cumbia, reggaeton (5.5%)
   - **World/Tribal/Ethnic** - World music, reggae, folk (11.9%)
   - **Jazz/Blues** - Jazz, blues, swing (14.7%)
   - **Classical/Orchestra** - Classical, choirs, opera (4.6%)
   - **Bass/Sound Systems** - Heavy bass culture (10.0%)

3. **Regenerated all camp features** with 17 total axes:
   - 10 music genre axes
   - 7 other axes (hospitality, workshops, woo-woo, art, queer, sober, family)
   - Each camp now has nuanced music profile instead of generic "sound/party" score

4. **Updated ranking algorithm** to be flexible:
   - `UserProfile` now accepts any axis via `**kwargs`
   - Works with any number/type of axes
   - Backward compatible

5. **Added music-focused example profiles**:
   - 🎷 Jazz Lover - Finds Playa Jazz Cafe (195 jazz mentions!)
   - 🎧 Techno Raver - Electronic + bass systems
   - 💃 Latin Dancer - Salsa, cumbia, reggaeton
   - 🎸 Live Music Fan - Bands and jam sessions
   - 🎻 Classical Fan - Finds Playa Choir (76 classical mentions!)

### Key Results

**Perfect niche matching**:
- Jazz lovers find **Playa Jazz Cafe** (jazz score: 100, 195 mentions)
- Classical fans find **Playa Choir** (classical score: 100, 76 mentions)
- Latin dancers find **Yeah Man!**, **Camposanto**, **Tierra Bomba** (all latin: 100)
- Techno ravers find **Ofosho**, **Buddha Lounge**, **Bubbles and Bass** (electronic: 100)

**Much better than generic "sound/party"**:
- Before: "Bag o' Dicks" = sound/party: 45
- After: "Bag o' Dicks" = hiphop: 85.6, jazz: 61.7, art: 45.8

### Technical Implementation

- **Keyword-based scoring**: Each genre has 10-20 relevant keywords
- **Percentile normalization**: Scores normalized to 0-100 scale
- **Multi-genre camps supported**: Camps can score high on multiple genres
- **Flexible architecture**: Easy to add more genres or axes in future

### Files Modified
- `generate_features.py` - Updated FEATURE_AXES with 10 music genres
- `rank_camps.py` - Made UserProfile flexible to accept any axes
- `quiz_app.py` - Updated backend to handle new axes dynamically
- `camp_features.json` - Regenerated with 17 axes (15MB)

### Quiz UI Updates

6. **Updated quiz interface** (`templates/quiz.html`) with music genre support:
   - Replaced old "Sound/Party Intensity" slider with music genre checkbox grid
   - Added 11 music genre checkboxes in responsive grid layout
   - Updated `updateMusicCheckbox()` to track checkbox state
   - Updated `loadExample()` to load music genre preferences from example profiles
   - Updated `submitQuiz()` to collect music genre checkbox values
   - Updated `resetForm()` to reset music genre checkboxes
   - Music checkboxes set to value of 90 when checked (consistent with other checkboxes)
   - Genre icons: 🎧 Electronic, 🎷 Jazz, 🎻 Classical, 💃 Latin, etc.

**Music Genre Checkbox Layout**:
```
🎧 Electronic/Techno/House     🕺 Disco/Funk/Soul        ☕ Ambient/Chill
🎸 Live Music/Bands            🤘 Rock/Punk/Metal        🎤 Hip Hop/Rap
💃 Latin Music                 🌍 World/Tribal          🎷 Jazz/Blues
🎻 Classical/Orchestra         🔊 Bass/Sound Systems
```

### Testing
- Test profiles include 5 music-focused examples
- Example profiles automatically check relevant music genres
- Submit flow works with music genre preferences
- Results show camps matching specific music tastes

### Ranking Logic Improvements

7. **Fixed axis matching logic** to properly handle preferences:
   - **Previous behavior**: Used absolute distance, penalized camps for being "too high"
     - User wants jazz=90, Camp has jazz=100 → distance=10 → match=90
     - User wants jazz=90, Camp has jazz=80 → distance=10 → match=90
   - **New behavior**: Rewards camps that meet or exceed preferences
     - User wants jazz=90, Camp has jazz=100 → match=110 (100 base + 10 bonus)
     - User wants jazz=90, Camp has jazz=80 → match=80 (penalized for being below)
   - **Result**: Playa Jazz Cafe (jazz score: 100) now ranks in top 10 for jazz lovers
   - **Bonus system**: Camps get up to +10 points for exceeding user preference

### Results
- ✅ Music genre checkboxes working in quiz UI
- ✅ Quick Start buttons include all 11 example profiles (6 general + 5 music)
- ✅ Jazz/Blues checkbox finds jazz camps (Playa Jazz Cafe, Black Rock French Quarter, etc.)
- ✅ Perfect jazz camps (score 100) rank higher than good jazz camps (score 80-90)
- ✅ Axis matching logic rewards camps that exceed user preferences

### Keyword Search Enhancement

8. **Improved text field for keyword-based niche search**:
   - Changed label from "Describe your ideal camp" to "Anything else you're looking for?"
   - Updated placeholder with concrete examples: "cola, breathwork, coffee, tea, massage, poetry"
   - **Dynamic weight adjustment**: When keywords are provided, automatically switches weighting:
     - With keywords: 70% embedding similarity, 30% axis matching
     - Without keywords: 30% embedding similarity, 70% axis matching
   - **Results**: Keyword search successfully finds niche camps
     - "cola" → finds **Hack-a-Cola** as #1 match
     - "breathwork" → finds camps focused on breathwork practices
     - Works well for any specific interest not covered by checkboxes/sliders

### Hard Filters for Critical Axes

9. **Implemented hard filtering for LGBTQ+, Sober, and Family-Friendly**:
   - These are treated as **requirements**, not preferences
   - If a checkbox is checked, **only camps scoring >= 60** on that axis are shown
   - **No results** message if no camps meet all filter criteria
   - Prevents showing inappropriate camps (e.g., party camps to sober seekers)

   **Filter Statistics**:
   - Sober spaces: 43 camps (3.1% of total)
   - LGBTQ+ affirming: 32 camps (2.3% of total)
   - Family-friendly: 74 camps (5.3% of total)
   - Sober + LGBTQ+: 1 camp (LuvClub)
   - All three: 0 camps (impossible combination)

   **Implementation**:
   - Filters applied before ranking
   - Filtered camps get score of -infinity (never shown)
   - User gets clear message when combination is impossible
   - Back button returns to quiz to adjust filters

### Current State
- ✅ Music genre checkboxes working in quiz UI
- ✅ Quick Start buttons include all 11 example profiles (6 general + 5 music)
- ✅ Jazz/Blues checkbox finds jazz camps (Playa Jazz Cafe, Black Rock French Quarter, etc.)
- ✅ Perfect jazz camps (score 100) rank higher than good jazz camps (score 80-90)
- ✅ Axis matching logic rewards camps that exceed user preferences
- ✅ Keyword search for niche interests (cola, breathwork, etc.)
- ✅ Dynamic weighting prioritizes keywords when provided
- ✅ Hard filters for LGBTQ+, Sober, Family-Friendly (prevents showing wrong camps)
- ✅ Browser back button works to return from results to quiz

---

## Phase 7: Pivot to Personality-Based Matching (IN PROGRESS)

### The Problem
The recommendation engine was becoming too much like a "search engine" with hard requirements:
- If you search for "jazz", you expect to find THE jazz camp
- If you're sober, you expect 100% clean results
- Sets expectations that are hard to meet
- Feels like work (sliders, checkboxes, forms)
- Too literal and high-stakes

### The Solution: Personality Quiz
Shift from "what do you want" to "who are you":
- **Fun personality questions** like "Horoscope or science journal?"
- **BuzzFeed-style quiz** that's engaging to take
- **Lower stakes** - "Here are camps your personality might vibe with"
- **Discovery-oriented** - Find camps you didn't know you'd love
- **Personality-based** - Match on who you are, not what you're looking for

### New Personality Axes (16 total, 8 spectrums)

1. **Energy Level**: High Energy Social ↔️ Quiet Contemplative
   - Question: "Friday night - out dancing till dawn or cozy night with close friends?"

2. **Time of Day**: Night Owl ↔️ Early Bird
   - Question: "When do you feel most alive?"

3. **Participation Style**: Hands-On Maker ↔️ Observer Appreciator
   - Question: "At an art installation - build it or admire it?"

4. **Intellectual Style**: Deep Thinker ↔️ Playful Prankster
   - Question: "Philosophy salon or prank war?"

5. **Organization**: Structured Organized ↔️ Spontaneous Chaotic
   - Question: "Plan your whole week or see where the wind takes you?"

6. **Mystical vs Rational**: Mystical Spiritual ↔️ Rational Skeptical
   - Question: "Horoscope or science journal?"

7. **Social Style**: Generous Host ↔️ Social Butterfly
   - Question: "At a party - making sure everyone's fed or meeting new people?"

8. **Scale Preference**: Intimate Small Scale ↔️ Large Scale Spectacle
   - Question: "Dinner for 6 or festival for 600?"

### Implementation Progress

✅ **Phase 7a: Feature Generation**
- Created `explore_personality_axes.py` - analyzed 16 personality dimensions
- All 16 axes have good signal (>10% prevalence, up to 90%)
- Created `generate_personality_features.py`
- Generated `camp_personality_features.json` (16.6 MB, 16 personality axes per camp)

✅ **Phase 7b: Ranking Algorithm**
- Created `rank_camps_personality.py` with PersonalityProfile class
- Uses softer matching (similarity-based, not hard requirements)
- No more hard filters - everything is about vibe matching
- Demo results show excellent personality-based matching:
  - High-energy party type → Land of Monkey, Alternative Energy Zone
  - Quiet contemplative maker → Hibernaculum, Enchanted Booty Forest

🚧 **Phase 7c: Quiz UI Redesign (NEXT)**
- Redesign quiz to feel like a fun personality game
- 8 engaging questions with fun answer choices
- Remove sliders, make it more visual and interactive
- "Which are you?" style questions
- Results page emphasizes discovery ("camps your vibe might match")

### Next Steps
- Design fun, engaging personality quiz questions
- Redesign quiz UI to be more playful and game-like
- Update Flask backend to use personality-based ranking
- Test with real users - does it feel fun vs like work?