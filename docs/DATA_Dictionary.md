# Data Dictionary: Selected Annual Features

## Dataset structure

The unit of observation is a poster year. Features aggregated from posters
published in year t are matched to the number of active militarized
interstate disputes involving China in year t+1.

The annual dataset contains 65 observations:
- Development: 51 observations, poster years 1949–1999.
- Embargo: 1 observation, poster year 2000.
- Test: 13 observations, poster years 2001–2013.

This dictionary describes the 12 selected predictors and the accompanying
target and indexing fields. Earlier preprocessing outputs contain additional
candidate features that are not included in this selection.

## Aggregation and missing values

Annual feature means are calculated from available poster-level values.
Each poster with a nonmissing value receives equal weight within its year.

For binary poster-level indicators, the annual mean is the proportion of
nonmissing records coded as 1. Unknown values are not automatically coded
as 0. An annual feature remains missing if no valid observations are
available for that feature in that year.

Missing-value imputation and statistical scaling must be fitted within
training folds.

## Selected predictors

| Category | Column | Data type | Unit or range | Description |
| --- | --- | --- | --- | --- |
| Visual | red_ratio_mean | Continuous | Proportion, 0–1 | Annual mean of poster-level red-pixel fractions. Red pixels satisfy hue within 15 degrees of red, HSV saturation >= 0.4, and value >= 0.15. |
| Visual | saturation_mean_mean | Continuous | Unitless, 0–1 | Annual mean of each poster's mean HSV saturation. Higher values indicate more saturated colors. |
| Visual | lightness_mean_mean | Continuous | CIELAB L*, nominally 0–100 | Annual mean of each poster's mean pixel lightness. Higher values indicate lighter images. |
| Visual | lightness_std_mean | Continuous | CIELAB L* units | Annual mean of within-image pixel lightness standard deviations. Higher values indicate greater lightness variation. |
| Visual | size_area_cm2_mean | Continuous | Square centimeters (cm²) | Annual mean of successfully parsed printed poster areas. This measures physical size, not image resolution. |
| Visual | size_aspect_ratio_mean | Continuous | Unitless, >= 1 | Annual mean of the longer printed side divided by the shorter printed side. Does not distinguish portrait from landscape orientation. |
| Metadata | title_han_count_mean | Continuous, derived from counts | Han characters per poster title | Annual mean number of Han characters in the recorded Chinese title field. This is not an OCR-derived count of all text printed on the poster. |
| Metadata | designer_has_identified_mean | Continuous proportion | 0–1 | Proportion of posters with at least one identified designer entity. Entities may be individuals or organizations. |
| Metadata | designer_org_name_marker_mean | Continuous proportion | 0–1 | Proportion of nonmissing designer-marker records matching predefined organizational wording. Does not establish verified organizational authorship. |
| Metadata | publisher_military_name_marker_mean | Continuous proportion | 0–1 | Proportion of nonmissing publisher-marker records matching predefined military-related wording. Does not establish verified military affiliation. |
| Archive | archive_theme_military_mean | Continuous proportion | 0–1 | Proportion of posters with available theme metadata matching People's Liberation Army or People's Militia. |
| Archive | archive_tag_military_personnel_mean | Continuous proportion | 0–1 | Proportion of posters with available tag metadata matching soldier, People's Liberation Army, or 解放军. |

## Target and indexing fields

| Role | Column | Data type | Unit, range, or categories | Description |
| --- | --- | --- | --- | --- |
| Index | poster_year | Integer calendar year | 1949–2013 | Publication year used to aggregate poster features. Not included in the selected predictor list. |
| Index | target_year | Integer calendar year | 1950–2014 | Outcome year, equal to poster_year + 1. Not included in the selected predictor list. |
| Target | y_active_mid_count | Discrete count | Nonnegative integer; distinct parent disputes per year | Number of distinct parent MID dispute identifiers involving China that are active in target_year. A continuing dispute contributes to each active year. Measures participation frequency, not initiation or severity. |
| Partition | split | Categorical, nominal | development; embargo; test | Fixed chronological assignment. Development is used for model development, embargo is excluded from fitting and evaluation, and test is reserved for final evaluation. Not a predictor. |

## Interpretation notes

- Name-based markers identify wording, not verified identities or affiliations.
- Archive themes and tags are retrospective website annotations. Their
  availability at the historical prediction date is uncertain, so archive
  features should be evaluated separately from the main forecasting features.
- Annual averages describe the collected archive sample, not all posters
  historically produced in China.
- None of the selected predictors is ordinal.
- The saved annual tables may also include unselected candidate columns,
  n_posters, valid-value counts, and missingness ratios. Those columns are
  outside this selected-feature dictionary and are not automatically model
  inputs.