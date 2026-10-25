# Preprocessing Notebooks

The project uses poster features in year t to predict the number of active militarized interstate disputes involving China in year t+1.

| Notebook | Main tasks | Main outputs |
| --- | --- | --- |
| `poster_data.ipynb` | Crawls ChinesePosters.net for images and metadata. Includes pilot and full collection, checkpoints, error logging, image validation, and missing-field checks. | Raw poster metadata, images, and audit files under `data/raw/posters_learning/`. |
| `military_data.ipynb` | Reads Dyadic MID 4.03, selects China for 1950-2014, checks duplicates, and counts distinct parent disputes per year. Explores alternative outcomes before saving the final count target. | `data/processed/military/annual_military_target.csv` and target documentation. |
| `poster_preprocessing.ipynb` | Parses dates; retains eligible posters; extracts color, physical-size, title, designer, publisher, and archive features; checks exact image duplicates; aggregates features annually; and generates X visualizations. | `data/processed/poster_x_features_v1.csv`, `annual_x_features_v1.csv`, feature-set definitions, and figures. |

## Running order

1. Run `poster_data.ipynb`, or use the existing saved collection.
2. Run `military_data.ipynb` to prepare Y.
3. Run `poster_preprocessing.ipynb` to prepare X. Its target-matching cells require the military target.
4. Run `python src/build_training_handoff.py` to rebuild and validate the final annual X/Y tables and selected overview figure.

Run from the repository root. Shared notebook snapshots are in `src/notebooks/`. Image extraction requires the downloaded images.

## Training data

The complete joined table is `data/processed/training_handoff/annual_model_table.csv`. Separate development, embargo, and test CSVs contain 51, 1, and 13 annual observations, respectively.

Missing X values are retained; imputation and scaling must be fitted within training folds. Preprocessing outputs include more candidate columns than the final selected feature set. Archive annotations are retrospective and should be evaluated separately.

`Diplomacy_data.ipynb` is earlier exploratory work and is not used in the current task.
