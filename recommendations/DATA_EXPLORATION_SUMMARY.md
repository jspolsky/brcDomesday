# Data Exploration Summary

## Dataset Overview

**Great news**: We have rich, comprehensive data to work with!

- **1,385 camps** in 2025, all with historical data
- **Average 6 years of history** per camp (median: 5 years)
- One camp has **26 years** of continuous attendance!
- **95%** have descriptions
- **76%** have hosted events (22,822 total events across all years)
- **97%** have hometown data

## Text Corpus Quality

We have substantial text to work with:
- **Average description**: 343 characters (median: 305)
- **Average event**: 220 characters
- **Total event text**: 5+ million characters
- **URL availability**: 43% for 2025, 49% historically

This is plenty of text for embedding generation and feature extraction.

## Geographic Distribution

Strong representation from:
1. **San Francisco** (192 camps)
2. **Los Angeles** (100 camps)
3. **Reno** (81 camps)
4. **Oakland** (41 camps)
5. **Seattle** (31 camps)

**481 unique hometowns** total - excellent geographic diversity for matching people by region.

## Event Type Distribution

The most common event types reveal camp characteristics:
1. **Class/Workshop** (31.1%) - huge learning community
2. **Music/Party** (22.3%) - vibrant nightlife
3. **Food** (7.8%) - strong hospitality culture
4. **Mature Audiences** (4.9%) - adult-oriented content
5. **Games** (4.4%)

## Feature Axes Analysis - Key Findings

We tested 13 potential feature axes. Here's what has **strong signal**:

### High-Variance Axes (Good for differentiation)

**1. Sound / Party** (66.2% of camps)
- Very common, but still 34% of camps DON'T emphasize this
- Keywords: dance, party, music, dj, beats
- **Good axis**: High variance in intensity

**2. Food / Hospitality** (60.9%)
- Bar culture is huge (2,667 mentions)
- Tea (1,608) and coffee (1,346) very popular
- **Good axis**: Clear hospitality vs non-hospitality split

**3. Fitness / Body** (51.6%)
- Yoga dominates (2,112 mentions)
- Dance overlaps with party axis (4,087)
- **Good axis**: Active vs contemplative

**4. Art** (51.6%)
- Widespread but not universal
- **Good axis**: Art-focused vs other focus

**5. Workshops / Learning** (47.0%)
- Strong educational component
- **Good axis**: Learning-oriented vs experience-oriented

**6. Woo-woo / Spirituality** (29.2%)
- Perfect distribution! Not too common, not too rare
- Meditation (1,123), healing (1,031), breathwork (290)
- **Excellent axis**: Clear differentiation possible

### Niche Axes (Lower prevalence but high specificity)

**7. Family / Kids** (21.9%)
- **Good niche axis**: Important for families, clear signal

**8. Maker / Engineering** (17.6%)
- **Good niche axis**: Specific community

**9. Quiet / Contemplative** (15.7%)
- **Good axis**: Sanctuary spaces vs high-energy

**10. Kink / Adult** (12.3%)
- **Important niche axis**: Consent-focused, clear opt-in needed
- 1,364 total mentions despite only 171 camps

**11. Sober** (12.1%)
- **Critical niche axis**: Important for recovery community
- "Clean" is overloaded (258 mentions) - may need refinement

**12. LGBTQ+ / Queer** (11.5%)
- **Important identity axis**: Clear community signaling
- Queer (350), gay (235), trans (189), drag (188)

**13. Science / Skeptical** (9.3%)
- **Lower signal but valid**: Counterbalance to woo-woo
- May want to combine or refine this

## Recommended MVP Feature Set

Based on this analysis, I recommend starting with **8 core axes**:

### Tier 1: Universal Differentiators (ask everyone)
1. **Sound / Party intensity** - 66% prevalence, high variance
2. **Hospitality focus** (bar/food/beverages) - 61% prevalence
3. **Workshop / Learning orientation** - 47% prevalence
4. **Woo-woo / Spirituality** - 29% prevalence, perfect distribution
5. **Art focus** - 52% prevalence

### Tier 2: Identity & Lifestyle (optional/opt-in questions)
6. **LGBTQ+ / Queer spaces** - 11.5% prevalence, important signal
7. **Sober-friendly** - 12% prevalence, critical for some users
8. **Family / Kids** - 22% prevalence, binary need

### Tier 3: Consider for V2
- **Kink / Adult content** (needs careful UI/consent handling)
- **Maker / Engineering** (good niche axis)
- **Fitness / Body movement** (may correlate with other axes)
- **Quiet / Contemplative** (may be inverse of party axis)
- **Geographic proximity** (use hometown data)

## Data Quality Notes

### Strengths
- Excellent historical depth (avg 6 years)
- High description coverage (95%)
- Rich event data (22k+ events)
- Good geographic diversity (481 hometowns)

### Limitations
- URL availability moderate (43-49%)
- Some camps have minimal history (193 are first-timers)
- Event type categories are somewhat coarse
- Need to handle year-to-year camp changes

## Next Steps for MVP

1. **Build data shaping pipeline**:
   - Consolidate description + event text per camp
   - Clean and normalize text (remove boilerplate)
   - Create per-camp text corpus

2. **Generate embeddings**:
   - Use sentence-transformers (e.g., `all-MiniLM-L6-v2`)
   - Create camp-level embeddings from consolidated text

3. **Compute scalar axes**:
   - Start with 5 Tier 1 axes using keyword scoring
   - Validate manually on sample camps
   - Add Tier 2 axes as needed

4. **Build simple quiz**:
   - 5-8 questions mapping to the axes
   - Sliders or binary choices
   - Output ranked camp list

5. **Create ranking algorithm**:
   - Weighted combination of embedding similarity + axis matching
   - Add geographic bonus if user provides hometown

## Validation Ideas

- **Sanity check**: Manually review top/bottom camps for each axis
- **Cluster analysis**: See if camps naturally group by our axes
- **Test cases**: Create synthetic user profiles, verify recommendations make sense
- **Real user testing**: Get 5-10 burners to try the quiz and review their results
