# Preprocessing and training handoff

This is a technical handoff, not submission/report prose. Start training from `data/processed/training_handoff/development.csv`. The task is count regression: poster X in year t predicts China's number of active parent militarized interstate disputes in year t+1.

## Files to use

| File | Purpose |
| --- | --- |
| `data/processed/poster_x_features_v1.csv` | 4,752 poster rows, 57 columns, including identifiers and audit fields; these are not 57 model predictors. |
| `data/processed/annual_x_features_v1.csv` | 65 annual observations, poster years 1949–2013; means, valid denominators and missing ratios. |
| `data/processed/training_handoff/annual_model_table.csv` | Validated one-to-one X_t/Y_(t+1) join and fixed split labels. |
| `data/processed/training_handoff/{development,embargo,test}.csv` | Separate annual partitions: 51, 1 and 13 rows. |
| `data/processed/training_handoff/annual_column_dictionary.csv` | Column meanings and feature-set membership. |
| `data/processed/feature_sets_v1.json` | Candidate feature sets; use explicitly selected mean columns, not every numeric column. |
| `results/split_manifest.json` | Frozen year assignments. |
| `results/preprocessing_handoff_validation.json` | Validation counts and SHA256 hashes of principal tables. |
| `figures/selected_x/x_overview_five_panels.png` | Five-panel development-only X overview; SVG and PDF also supplied. |
| `src/notebooks/` | Saved collection, preprocessing and military notebook source snapshots with outputs removed. |

## Collection and eligibility

The collection run saved 5,619 unique poster IDs with no reported collection failures. Image validation reported no errors. This is coverage of the chosen catalogue crawl, not proof of every work ever produced or every website entry. Of all dates, 4,052 parsed to month precision, 790 to year precision, and 777 remained unresolved. The final eligible 1949–2013 subset has 4,752 posters. Unresolved/ambiguous dates are excluded rather than assigned guessed years. There were no exact image-hash duplicate groups in the eligible subset; near-duplicate works have not been established.

The raw metadata snapshot is shared at `data/raw/posters_learning/metadata_full.json`; images, HTML and per-record download checkpoints remain local. Image-based preprocessing requires those images or recollection. The metadata JSON preserves image URLs, paths and hashes. Collection implementation: `src/collect.py`; interactive workflow: `src/notebooks/poster_data.ipynb`.

## X definitions

### Visual and physical properties

- Color extraction uses the first displayed image, full image region, EXIF orientation and ICC conversion to sRGB when available. Missing profiles assume sRGB and are recorded. Scans, paper aging, borders and digitization can influence measurements.
- Red fraction: HSV hue within 15 degrees of red, saturation >= 0.4 and value >= 0.15. This is a color threshold, not a verified political-symbol detector; some orange/skin pixels may qualify.
- RGB channel means and saturation are on a 0–1 scale. Lightness is CIELAB L* with D65, 2-degree observer; mean, standard deviation and p90-minus-p10 are retained.
- Printed dimensions are in cm, independent of image pixels. Short/long sides, area in cm² and long/short ratio are retained. Explicit formatting typos are normalized with an audit trail. Unsupported unitless or multi-panel formats and unknown entries remain missing. Large parsed sizes are not automatically removed. Short/long ratio does not preserve portrait/landscape orientation.
- Frozen color configuration: `data/processed/color_v1/config.json`. Size normalization: `data/processed/poster_size_features_v2.csv` and notebook functions.

### Title, designers and publishers

- Chinese-title availability and Han-character count are retained. No OCR is used.
- The tested 19-term threat lexicon matched zero eligible titles and is excluded from model features; the audit is retained in `title_dictionary_check.json`. Do not reintroduce it as a useful score without separate justification.
- Designer counts refer to identified named entities, which can be people or organizations. `multi_designer` marks multiple identified entities, not multiple confirmed people. Unknown/partially identified cases can remain missing.
- Automated designer organization/collective wording and publisher press/party/military/education wording are regex markers. They are not verified entity classifications, affiliations, or mutually exclusive categories. No exhaustive manual classification was performed. Missing/unknown identity must not become a negative class.

### Retrospective archive extension

- Description availability and lengths, theme/tag availability and counts, and fixed exact-label indicators are included in a separate candidate feature set. See `archive_label_rules_v1.json` and `poster_group3_archive_features_v2.csv`.
- Website descriptions/themes/tags were assigned retrospectively. They are not demonstrated to have been observable before a historical prediction date, and could encode knowledge of later outcomes. Keep them separate from the main historical forecasting comparison; label their evaluation as retrospective.
- A missing metadata list does not mean a subject was absent. Categories overlap; label counts are website labels, not unique semantic concepts.

## Annual aggregation and outcome

Annual feature means use available values only. A binary feature's mean is a proportion among records with a known value. `_n_valid` and `_missing_ratio` preserve the denominator and availability. No imputation, scaling, target-informed feature selection or model training has been performed. `n_posters` describes archive sampling intensity, not national production volume.

Y comes from Dyadic MID 4.03: retain `statea == 710`, years 1950–2014, and count distinct parent `disno` per year. A continuing dispute contributes to each active year. Zero means no qualifying record within covered years, not missing/out-of-range coverage. This measures participation, not Chinese initiation, wars, military severity or number of opponents. Do not count directed dyad rows as separate parent disputes. `dyindex` alone was insufficient to identify opponent-specific dyads in these files; dyad audit IDs combine dyindex/statea/stateb. The military notebook preserves exploratory/earlier candidates; the final authoritative target is `annual_military_target.csv`.

## Training protocol

- Development: X1949–1999 -> Y1950–2000 (51 annual samples).
- Embargo: X2000 -> Y2001 (exclude from tuning and final test).
- Final test: X2001–2013 -> Y2002–2014 (13 annual samples).
- Use chronological/expanding-window validation within development; do not shuffle annual rows. Use a one-row gap if maintaining the one-year horizon separation between adjacent validation blocks.
- Fit imputation, scaling and any learned feature selection inside each training fold using a pipeline. Keep test data untouched until the analysis is locked. Some all-year descriptive inventories were inspected before this split was frozen; subsequent figures use development only.
- Exclude `poster_year`, `target_year`, `split` and `y_active_mid_count` from the default X input list. Year/time trends and archive counts require an explicitly documented baseline choice. Never use future-year Y as a predictor. A lagged-outcome baseline must use only outcomes available at each forecast origin.
- Annual sample size is 51 in development, not 4,752 independent training samples. Use a modest predictor set and regularization; avoid treating repeated annual targets at poster level as independent observations.
- Candidate sets are comparisons, not validated optimal feature selections. Correlation does not establish predictive usefulness or causation. Compare against simple count/persistence baselines under the same validation protocol.
- Course acceptance of externally supplied MID outcomes should be confirmed with the TA; downloadable external Y does not itself meet a web-collection requirement.

## Reproduce this handoff

Create the environment in `environment-preprocessing.yml`, then run from repository root:

```bash
python src/build_training_handoff.py
```

This rebuilds the annual joined tables, validates keys/coverage/means/denominators, writes hashes, and redraws the selected five-panel figure using saved poster-level data. It does not retrain models or access held-out outcomes for plotting. The notebooks document the upstream feature extraction; open the military notebook from repository root because it uses root-relative paths. Older v1 visual, preliminary joined tables, old archive v1 outputs and diplomacy work are superseded and are not part of this handoff.

Example loading for the training teammate:

```python
import json
import pandas as pd
from pathlib import Path

root = Path.cwd()  # Run from repository root.
dev = pd.read_csv(root / 'data/processed/training_handoff/development.csv')
sets = json.loads((root / 'data/processed/feature_sets_v1.json').read_text())
columns = sets['visual_baseline']
X = dev[columns]
y = dev['y_active_mid_count']
# Split chronologically and fit transformations only inside each training fold.
```
