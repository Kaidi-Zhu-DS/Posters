# Selected Feature Documentation

All features are annual averages calculated from available poster-level observations.

| Category | Feature | Data Type / Unit | Description | Selection Rationale |
|---|---|---|---|---|
| Visual | red_ratio_mean | Continuous proportion, 0–1 | Mean proportion of red pixels | Captures red-color prevalence |
| Visual | saturation_mean_mean | Continuous, 0–1 | Mean color saturation | Measures color vividness |
| Visual | lightness_mean_mean | Continuous, CIELAB L* (0–100) | Mean image lightness | Represents overall brightness |
| Visual | lightness_std_mean | Continuous, CIELAB L* units | Mean within-image lightness standard deviation | Captures brightness variation |
| Visual | size_area_cm2_mean | Continuous, cm² | Mean printed area | Represents physical poster size |
| Visual | size_aspect_ratio_mean | Continuous ratio, ≥1 | Mean ratio of the longer side to the shorter side | Captures poster shape |
| Metadata | title_han_count_mean | Continuous mean count, Han characters | Mean Chinese character count in titles | Measures title length |
| Metadata | designer_has_identified_mean | Continuous proportion, 0–1 | Proportion with identified designer entities | Captures designer attribution |
| Metadata | designer_org_name_marker_mean | Continuous proportion, 0–1 | Proportion with organizational designer-name markers | Captures organizational wording |
| Metadata | publisher_military_name_marker_mean | Continuous proportion, 0–1 | Proportion with military publisher-name markers | Captures military-related wording |
| Archive | archive_theme_military_mean | Continuous proportion, 0–1 | Proportion with military-theme labels | Captures military-themed content |
| Archive | archive_tag_military_personnel_mean | Continuous proportion, 0–1 | Proportion with military-personnel tags | Captures military personnel references |

Note: Proportions use nonmissing records as their denominator. Name markers indicate wording rather than verified affiliations. Archive labels are retrospective website annotations.