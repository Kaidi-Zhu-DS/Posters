"""Build the validated annual training handoff and five-panel X-only figure."""
from pathlib import Path
import json
import hashlib
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/processed'
OUT = DATA / 'training_handoff'
FIG = ROOT / 'figures/selected_x'
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)
poster = pd.read_csv(DATA / 'poster_x_features_v1.csv')
annual = pd.read_csv(DATA / 'annual_x_features_v1.csv')
target = pd.read_csv(DATA / 'military/annual_military_target.csv')
manifest = json.loads((ROOT / 'results/split_manifest.json').read_text())
sets = json.loads((DATA / 'feature_sets_v1.json').read_text())
assert poster.poster_id.is_unique and len(poster) == 4752
assert annual.poster_year.is_unique and target.year.is_unique
assert (annual.target_year == annual.poster_year + 1).all()
assert set(annual.poster_year) == set(range(1949, 2014))
for columns in sets.values():
    assert set(columns).issubset(annual.columns)
joined = annual.merge(target, left_on='target_year', right_on='year',
                      how='left', validate='one_to_one', indicator=True)
assert joined['_merge'].eq('both').all()
assert joined.y_active_mid_count.notna().all()
assert (joined.y_active_mid_count >= 0).all()
assert (joined.y_active_mid_count % 1 == 0).all()
joined = joined.drop(columns=['year', '_merge'])
joined['split'] = ''
for split, key in [('development', 'development_poster_years'),
                   ('embargo', 'embargo_poster_years'), ('test', 'test_poster_years')]:
    joined.loc[joined.poster_year.isin(manifest[key]), 'split'] = split
assert joined.split.ne('').all()
assert joined.split.value_counts().to_dict() == {'development': 51, 'test': 13, 'embargo': 1}
joined.to_csv(OUT / 'annual_model_table.csv', index=False)
for split in ['development', 'embargo', 'test']:
    joined.loc[joined.split.eq(split)].to_csv(OUT / f'{split}.csv', index=False)

# Audit annual means and denominators against poster-level inputs.
for column in [c for c in annual if c.endswith('_mean')]:
    base = column[:-5]
    if base not in poster:
        continue
    grouped = poster.groupby('poster_year')[base]
    expected = grouped.mean().reindex(annual.poster_year).to_numpy()
    assert np.allclose(annual[column], expected, equal_nan=True), column
    assert np.array_equal(annual[base + '_n_valid'], grouped.count().reindex(annual.poster_year)), base

dictionary = []
for column in annual:
    if column.endswith('_missing_ratio'):
        meaning = 'Fraction of eligible posters with unavailable feature in that year.'
    elif column.endswith('_n_valid'):
        meaning = 'Number of nonmissing poster-level values used in the annual mean.'
    elif column.endswith('_mean'):
        meaning = 'Mean of available poster-level values; binary features become shares among known records.'
    else:
        meaning = {'poster_year':'Year of poster production used for X.',
                   'target_year':'Outcome year: poster_year + 1.',
                   'n_posters':'Retained archive catalogue records in this poster year.'}.get(column, '')
    dictionary.append({'column':column, 'meaning':meaning,
                       'feature_sets':';'.join(k for k,v in sets.items() if column in v)})
dictionary.extend([
    {'column':'y_active_mid_count','meaning':'Distinct parent MID disno values involving China active in target_year.','feature_sets':''},
    {'column':'split','meaning':'Fixed chronological development/embargo/test assignment; never an input feature.','feature_sets':''}])
pd.DataFrame(dictionary).to_csv(OUT / 'annual_column_dictionary.csv', index=False)

dev = poster.loc[poster.poster_year.isin(manifest['development_poster_years'])]
years = manifest['development_poster_years']
plt.rcParams.update({'font.size':10, 'axes.spines.top':False, 'axes.spines.right':False})
fig = plt.figure(figsize=(17, 15), layout='constrained')
grid = fig.add_gridspec(3, 2)
axes = [fig.add_subplot(grid[0,0]), fig.add_subplot(grid[0,1]),
        fig.add_subplot(grid[1,:]), fig.add_subplot(grid[2,0]), fig.add_subplot(grid[2,1])]
coverage = dev.groupby('poster_year').size().reindex(years, fill_value=0)
axes[0].bar(coverage.index, coverage.values, color='#526D82')
axes[0].set(title='A. Archive coverage varies across years', xlabel='Poster year', ylabel='Catalogue records')
axes[1].hist(dev.red_ratio.dropna()*100, bins=np.linspace(0,100,26), color='#B54A45', edgecolor='white')
axes[1].set(title='B. Most posters have limited red coverage', xlabel='Red pixels (%)', ylabel='Catalogue records', xlim=(0,100))
red = dev.groupby('poster_year').red_ratio.agg(median='median', q25=lambda s:s.quantile(.25), q75=lambda s:s.quantile(.75)).reindex(years)*100
axes[2].fill_between(red.index, red.q25, red.q75, color='#B54A45', alpha=.2, label='Interquartile range')
axes[2].plot(red.index, red['median'], color='#B54A45', label='Median')
axes[2].set(title='C. Red coverage varies between and within years', xlabel='Poster year', ylabel='Red pixels (%)')
axes[2].legend(frameon=False)
markers = {'designer_org_name_marker':'Designer: organization wording',
           'designer_collective_name_marker':'Designer: collective wording',
           'publisher_press_name_marker':'Publisher: press wording',
           'publisher_party_name_marker':'Publisher: party wording',
           'publisher_military_name_marker':'Publisher: military wording',
           'publisher_education_name_marker':'Publisher: education wording'}
marker = pd.DataFrame([{'feature':c,'label':l,'percent':100*dev[c].mean(),'n_valid':int(dev[c].count())} for c,l in markers.items()]).sort_values('percent')
bars = axes[3].barh(marker.label, marker.percent, color='#526D82')
axes[3].bar_label(bars, fmt='%.1f%%', padding=3, fontsize=9)
axes[3].set(title='D. Name markers are unevenly represented', xlabel='Matches among known records (%)', xlim=(0,100))
availability = pd.Series({
    'Description unavailable':100*(1-dev.archive_description_present.mean()),
    'Themes unavailable':100*(1-dev.archive_theme_present.mean()),
    'No identified designer':100*(1-dev.designer_has_identified.mean()),
    'Publisher name unavailable':100*(1-dev.publisher_has_name.mean()),
    'Chinese title unavailable':100*(1-dev.title_has_chinese.mean()),
    'Size unparsed or missing':100*dev.size_area_cm2.isna().mean(),
    'Tags unavailable':100*(1-dev.archive_tag_present.mean())}).sort_values()
bars = axes[4].barh(availability.index, availability.values, color='#8C6D62')
axes[4].bar_label(bars, fmt='%.1f%%', padding=3, fontsize=9)
axes[4].set(title='E. Metadata availability differs by source', xlabel='Development records (%)', xlim=(0,100))
fig.suptitle(f'Poster X overview | 1949–1999 | {len(dev):,} retained records', fontsize=19)
for extension in ['png','svg','pdf']:
    fig.savefig(FIG / f'x_overview_five_panels.{extension}', dpi=200, bbox_inches='tight')
plt.close(fig)
coverage.rename('n_posters').to_csv(FIG / 'coverage_data.csv')
red.to_csv(FIG / 'annual_red_data.csv')
marker.to_csv(FIG / 'marker_data.csv', index=False)
availability.rename('unavailable_percent').to_csv(FIG / 'availability_data.csv')
(FIG / 'README.md').write_text('''# Selected X overview

Five panels describe development-period X only (1949–1999). No Y values or test-period plots are used. Selection is for visualization, not model feature selection.

- A: retained catalogue records, not total historical production.
- B: full-image red-pixel fraction under the frozen HSV rule.
- C: median and 25th–75th percentiles across posters; shading is not a confidence interval. The annual model inputs use means, not these plotted medians.
- D: automated name-wording matches, not verified affiliations or person/collective classifications. Categories overlap; each denominator is the available values for that marker (see marker_data.csv).
- E: unavailable metadata or unsupported sizes; missing does not mean absence of historical content.

Generated by `python src/build_training_handoff.py`. PNG, SVG and PDF contain the same figure. Write submission captions independently according to course policy.
''', encoding='utf-8')
checks = {'poster_rows':len(poster),'annual_rows':len(annual),'development_poster_rows':len(dev),
          'split_counts':joined.split.value_counts().to_dict(),'annual_means_and_denominators_verified':True,
          'target_matching':'65/65 one-to-one','files':{}}
for path in [DATA/'poster_x_features_v1.csv', DATA/'annual_x_features_v1.csv', DATA/'military/annual_military_target.csv', OUT/'annual_model_table.csv']:
    checks['files'][str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
(ROOT / 'results/preprocessing_handoff_validation.json').write_text(json.dumps(checks, indent=2), encoding='utf-8')
print(json.dumps({k:v for k,v in checks.items() if k != 'files'}, indent=2))
