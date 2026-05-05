# Blindspot Reduction Plan

## Objective
Close coverage gaps in Baltimore calendar sources across Maslow needs and community sectors, while reducing over-reliance on Meetup/Eventbrite and improving classification quality.

## Baseline (as of 2026-05-05)
- Total sources: 94
- Maslow undercoverage: Survival & Health, Water, Food, Housing/Shelter, Clothing
- Sector undercoverage: Faith, Environment, Makerspace, Politics, Finance (relative)
- Classification gaps in `community_sectors.json`: `Safety & Stability`, `Education`, `Science`, `Lifelong Learning`, `Youth Education`
- Platform concentration: Meetup (39) + Eventbrite (26)

## Success Criteria
- Every active tag used in `baltimore/event_sources.py` maps to a community sector.
- Add at least 3 net-new sources per major Maslow blindspot:
  - Food
  - Housing/Shelter
  - Survival & Health
  - Water/Environment
- Add at least 2 net-new sources for each thin sector:
  - Faith
  - Environment
  - Makerspace
  - Politics
  - Finance
- Reduce platform concentration by adding at least 12 direct institutional/non-platform sources.
- No syntax or ingestion regressions.

## Workstreams

### 1) Taxonomy and Mapping Hardening
1. Update `data/category_maps/community_sectors.json`:
   - Add `Safety & Stability` to `Environment` or create a dedicated `Civic Resilience` sector.
   - Map `Education`, `Science`, `Lifelong Learning`, `Youth Education` to a sector (recommended: `Technology` or new `Education` sector).
2. Confirm tag compatibility with `city_source_taxonomy.py` Maslow mappings.
3. Add a validation script/check that flags tags present in city sources but missing in sector mappings.

Deliverables:
- Updated `data/category_maps/community_sectors.json`
- Validation command documented in repo

### 2) Maslow Gap Expansion

#### Food
Target sources:
- Baltimore food access nonprofits with public event calendars
- Mutual aid/community pantry event feeds
- Urban agriculture/community kitchen organizations

Tag strategy:
- `Food`, `Community`, optional `Community Organizing`

#### Housing / Shelter
Target sources:
- Housing justice/legal aid org events
- Tenant unions and homeless services calendars
- City housing and neighborhood revitalization event pages

Tag strategy:
- `Housing` or `Shelter + Habitat`, `Safety & Stability`, `Community`

#### Survival & Health
Target sources:
- Hospital community outreach calendars
- Behavioral health, recovery, chronic illness support orgs
- Preventive care/screening series

Tag strategy:
- `Health`, `Wellness`, `Community`, optional `Community Organizing`

#### Water / Environment
Target sources:
- Watershed/environmental nonprofits
- Climate resilience and conservation programs
- City sustainability/public works community events

Tag strategy:
- `Water`, `Climate & Energy`, `Infrastructure`, `Community`

Deliverables:
- Net-new entries in `baltimore/event_sources.py`
- Balanced tags aligned with Maslow mapper

### 3) Sector Gap Expansion

#### Faith
- Add interfaith service orgs and congregations with active public calendars.
- Prioritize groups with community service programming (not only worship schedules).

#### Environment
- Add environmental justice groups, watershed councils, clean energy community programs.

#### Makerspace
- Add additional labs/fabrication groups beyond current makerspace set.

#### Politics
- Add civic engagement organizations with recurring public policy events.

#### Finance
- Add local personal finance, investing education, and fintech meetups/calendars.
- Keep `Crypto & Web3` balanced with non-crypto finance programming.

Deliverables:
- Minimum 2 new sources per thin sector

### 4) Platform Blindspot Reduction
1. Prioritize first-party calendars from:
   - City agencies
   - Hospitals and universities
   - Nonprofits and coalitions
   - Professional associations
2. Add source diversity guardrail:
   - No more than 60% of newly added sources from Meetup/Eventbrite.
3. Track source host distribution after each batch.

Deliverables:
- Host distribution report before/after
- At least 12 direct institutional/non-platform sources added

### 5) Quality Control and Ingestion Safety
1. For each candidate source:
   - Verify URL is active and event-oriented.
   - Confirm recurrence or ongoing updates.
   - Assign 2-4 high-signal tags.
2. Run checks after each batch:
   - `python -m py_compile baltimore/event_sources.py`
   - JSON validation for category maps
   - Optional local ingest dry run if available
3. De-duplicate near-identical sources.

Deliverables:
- Clean compile/validation logs
- Reduced scrape errors and fewer dead sources over time

## Execution Phases

### Phase 1 (Day 1)
- Fix taxonomy and sector mapping gaps.
- Add validation query/script for unmapped tags.

### Phase 2 (Days 1-2)
- Add Maslow critical blindspot sources: Food, Housing, Health, Water.
- Minimum 12 new sources, at least 6 non-Meetup/Eventbrite.

### Phase 3 (Days 2-3)
- Fill thin sector gaps: Faith, Environment, Makerspace, Politics, Finance.
- Minimum 10 new sources.

### Phase 4 (Day 3)
- Run coverage recount and host distribution analysis.
- Prune dead or redundant sources.
- Finalize with updated counts and residual gaps.

## Metrics Dashboard (to update after implementation)
- Source totals by sector
- Source totals by Maslow bucket
- Unmapped tag count (target: 0)
- Host distribution (Meetup/Eventbrite vs direct sources)
- New sources added by gap category

## Risks and Mitigations
- Risk: stale event links.
  - Mitigation: prefer organizational calendars over one-off event pages.
- Risk: over-tagging causes noisy filters.
  - Mitigation: cap to 2-4 primary tags per source.
- Risk: imbalance persists after additions.
  - Mitigation: enforce per-gap minimum additions before adding to saturated sectors.

## Immediate Next Actions
1. Patch `community_sectors.json` for currently unmapped tags.
2. Add first batch of non-platform sources for Food/Housing/Water/Health.
3. Recompute coverage and publish delta.
