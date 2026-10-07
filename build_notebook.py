"""Build and execute an explanatory notebook without additional notebook tooling."""
from pathlib import Path
import base64
import contextlib
import hashlib
import io
import json
import textwrap
import traceback

ROOT = Path(__file__).resolve().parent
cells = []


def md(source):
    cells.append({'cell_type': 'markdown', 'metadata': {}, 'source': textwrap.dedent(source).strip() + '\n'})


def code(source):
    cells.append({'cell_type': 'code', 'metadata': {}, 'source': textwrap.dedent(source).strip() + '\n', 'execution_count': None, 'outputs': []})


md('''
# Analysis of Recorded Marine Fish Richness in the Visayas

**Course:** CS365 – Applied Artificial Intelligence | Midterm Project  
**Authors:** Gian Cedrick G. Epilan & Jahzeel Lanz N. Mercado  
**Date:** October 2026  

The Visayas is often called the center of Philippine marine biodiversity. That reputation rests on what has been *recorded* — and recording is uneven. This project asks a focused research question:

*Do neighboring areas with high recorded species richness form geographically coherent clusters?*

Scope: ray-finned fish (Actinopterygii) in a rectangle covering 122–125° E, 9–12° N — parts of Negros, Cebu, Bohol and surrounding waters. It is an empirical pilot window, not an official boundary or a national inventory, and sharks and rays are outside the taxonomic scope.

Pipeline: real occurrences → cleaning → grid richness and sampling effort → high-richness cells → haversine DBSCAN → cluster composition and sensitivity. Richness counts distinct recorded species, not fish abundance. An area with few records is *unknown*, not poor.
''')
md('''
## 1. Question and method

Each 0.1° grid cell gets a richness count (unique species) and an effort count (records, datasets, years). The question is spatial: do cells that are rich *and* near each other group into coherent patches?

Candidate techniques, and why they were accepted or rejected:

- **K-means** needs the number of clusters up front and favors equal-sized spherical groups — the wrong shape for patches that follow coastlines.
- **EM clustering** (Gaussian mixture) also assumes blob-like clusters and a fixed k.
- **SLINK** (single-linkage hierarchical) chains distant cells together through intermediate points.
- **DBSCAN** groups neighbors within a distance, allows irregular shapes, and labels isolated cells as noise instead of forcing them into a cluster.

DBSCAN fits the question: we do not know how many patches exist, we expect irregular geography, and "no cluster" is a meaningful answer for a lone high-richness cell. We cluster **grid-cell centers**, not individual observations, using haversine (great-circle) distance. Section 7 shows how the radius was chosen; Section 8 tests how much the answer depends on it.
''')
md('''
## 2. Data source and reproducibility

Occurrence data was queried directly from the Ocean Biodiversity Information System (OBIS) API (`https://api.obis.org/v3/occurrence`) using a custom data retrieval pipeline (`download_data.py`). The full snapshot is cached locally in `data/` for complete reproducibility.

Source: [OBIS data access](https://obis.org/data/access/), [OBIS API](https://api.obis.org/), [OBIS manual](https://manual.obis.org/access.html). The download uses cursor pagination through **all matching records** — not an arbitrary first-page sample. Query parameters, retrieval timestamp, counts, and cryptographic hashes are recorded in `data/provenance.json`.

Provider datasets and original licenses are retained in `data/dataset_metadata.json`, the raw JSON, and `data/dataset_attribution.csv`. Map outline geometry is sourced from [Natural Earth](https://www.naturalearthdata.com/about/terms-of-use/).
''')
code('''
from pathlib import Path
import hashlib
import json
import platform
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import sklearn
from sklearn.cluster import DBSCAN
from sklearn.neighbors import NearestNeighbors

ROOT = Path.cwd()
assert (ROOT / 'data' / 'obis_visayas_raw.json').exists(), 'Start Jupyter in the project folder.'
DATA = ROOT / 'data'
OUTPUT = ROOT / 'outputs'
OUTPUT.mkdir(exist_ok=True)
GRID_SIZE = 0.1  # degrees; roughly 11 km north–south
RICHNESS_QUANTILE = 0.80
MIN_SAMPLES = 3  # includes the candidate cell itself
EARTH_RADIUS_KM = 6371.0088
BOUNDS = (122.0, 9.0, 125.0, 12.0)  # west, south, east, north
EPS_OVERRIDE_KM = None  # set a positive value to explore another radius
plt.rcParams.update({'figure.dpi': 120, 'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})

provenance = json.loads((DATA / 'provenance.json').read_text(encoding='utf-8'))
raw = pd.DataFrame(json.loads((DATA / 'obis_visayas_raw.json').read_text(encoding='utf-8')))
print(json.dumps(provenance, indent=2, ensure_ascii=False))
print('Raw snapshot SHA-256:', hashlib.sha256((DATA / 'obis_visayas_raw.json').read_bytes()).hexdigest())
print('Versions:', {'Python': platform.python_version(), 'pandas': pd.__version__, 'numpy': np.__version__, 'matplotlib': matplotlib.__version__, 'sklearn': sklearn.__version__})
print('Raw shape:', raw.shape)
print('Available fields:', ', '.join(raw.columns))
''')
code('''
attribution = raw.groupby('dataset_id').agg(records=('id', 'size')).reset_index()
for field in ['datasetName', 'license', 'rightsHolder', 'accessRights']:
    if field in raw:
        values = raw.groupby('dataset_id')[field].agg(lambda s: ' | '.join(sorted(set(s.dropna().astype(str)))))
        attribution[field] = attribution['dataset_id'].map(values)
attribution['source_url'] = 'https://obis.org/dataset/' + attribution['dataset_id']
attribution.to_csv(DATA / 'dataset_attribution.csv', index=False)
print(attribution.sort_values('records', ascending=False).to_string(index=False))
''')
md('''
## 3. Data preparation

We keep explicit marine presences with usable coordinates and an identified species (OBIS `speciesid`, with a species-name fallback; unidentified genera do not count as species). We drop repeated OBIS IDs and repeated provider occurrence IDs within a dataset, and we **keep** repeated records of the same species at the same coordinates — separate surveys or specimens can legitimately look identical. Duplicates across providers cannot always be resolved.

Key preprocessing considerations: The marine flag describes the taxon, not the record's location, and **this API snapshot did not return a `flags` field, so no flag-based exclusions were applied**. Depth is optional in OBIS; invalid or missing depths are treated as missing, not fatal. The audit table below makes every removal visible. Coordinate, habitat, and flag checks remain for the final study.
''')
code('''
df = raw.copy()
audit = []
def keep(mask, reason):
    global df
    before = len(df)
    df = df.loc[mask].copy()
    audit.append({'rule': reason, 'removed': before - len(df), 'remaining': len(df)})

for col in ['decimalLatitude', 'decimalLongitude', 'speciesid', 'year', 'minimumDepthInMeters', 'maximumDepthInMeters']:
    if col not in df:
        df[col] = np.nan
    df[col] = pd.to_numeric(df[col], errors='coerce')
keep(df.decimalLatitude.between(-90, 90) & df.decimalLongitude.between(-180, 180), 'Valid, nonmissing coordinates')
w, s, e, n = BOUNDS
keep(df.decimalLongitude.between(w, e) & df.decimalLatitude.between(s, n), 'Inside study rectangle')
keep(df.get('absence', pd.Series(False, index=df.index)).fillna(False).eq(False), 'Presence records only')
keep(df.get('dropped', pd.Series(False, index=df.index)).fillna(False).eq(False), 'Exclude OBIS dropped records')
keep(df.get('marine', pd.Series(False, index=df.index)).eq(True), 'Taxon explicitly flagged marine')
df['species'] = df.get('species', pd.Series(pd.NA, index=df.index)).astype('string').str.strip()
keep(df.species.notna() & df.species.ne(''), 'Identified species required')
keep(~df['id'].duplicated(), 'Unique OBIS record ID')
if 'occurrenceID' in df:
    provider_id = df['occurrenceID'].astype('string').str.strip()
    repeated = provider_id.notna() & provider_id.ne('') & df.duplicated(['dataset_id', 'occurrenceID'])
    keep(~repeated, 'Unique nonempty provider occurrence ID within dataset')
df['species_key'] = ['aphia:' + str(int(i)) if pd.notna(i) else 'name:' + name for i, name in zip(df.speciesid, df.species)]
df.loc[~df.year.between(1500, pd.Timestamp(provenance['retrieved_utc']).year), 'year'] = np.nan
for col in ['minimumDepthInMeters', 'maximumDepthInMeters']:
    df.loc[~df[col].between(0, 11000), col] = np.nan
reversed_depth = df.minimumDepthInMeters > df.maximumDepthInMeters
df.loc[reversed_depth, ['minimumDepthInMeters', 'maximumDepthInMeters']] = np.nan
df['depth_m'] = df[['minimumDepthInMeters', 'maximumDepthInMeters']].mean(axis=1)
cleaning_audit = pd.DataFrame(audit)
cleaning_audit.to_csv(OUTPUT / 'cleaning_audit.csv', index=False)
print(cleaning_audit.to_string(index=False))
print('Depth ranges invalidated:', int(reversed_depth.sum()))
print('Species-name fallbacks:', int(df.speciesid.isna().sum()))
print('Top retained OBIS quality flags:')
print(df['flags'].explode().value_counts().head(12).to_string() if 'flags' in df else 'No flags field')
if 'coordinateUncertaintyInMeters' in df:
    uncertainty = pd.to_numeric(df.coordinateUncertaintyInMeters, errors='coerce')
    print(f'Coordinate uncertainty supplied for {100*uncertainty.notna().mean():.1f}% of retained records; {int((uncertainty > 10000).sum())} exceed 10 km.')
if 'basisOfRecord' in df:
    print('Record types:')
    print(df.basisOfRecord.value_counts(dropna=False).to_string())
cols = ['id', 'occurrenceID', 'dataset_id', 'species', 'species_key', 'genus', 'family', 'class', 'decimalLatitude', 'decimalLongitude', 'year', 'depth_m']
df[[c for c in cols if c in df]].to_csv(DATA / 'obis_visayas_clean.csv', index=False)
assert len(df) > 0 and df.species_key.notna().all()
assert df['id'].is_unique
''')
md('''
## 4. Descriptive statistics

Before any clustering: what does the snapshot look like? Four things matter — how records spread across datasets and families, how coverage changed over time, how deep the observations are, and how complete the optional fields are.

Family and dataset bars count **records**, not fish. Annual totals describe database coverage; they are not a population trend. Depth is reported for only about a tenth of records, so its distribution is a partial view.
''')
code('''
summary = pd.Series({'clean_records': len(df), 'recorded_species': df.species_key.nunique(), 'recorded_families': df.family.nunique(), 'contributing_datasets': df.dataset_id.nunique(), 'years_with_records': df.year.nunique(), 'earliest_year': df.year.min(), 'latest_year': df.year.max(), 'year_completeness_pct': 100 * df.year.notna().mean(), 'depth_completeness_pct': 100 * df.depth_m.notna().mean()})
print(summary.round(2).to_string())
print('\\nDepth (m), where reported:')
print(df.depth_m.describe().round(1).to_string())
share5 = 100 * df.dataset_id.value_counts().head(5).sum() / len(df)
top_family = df.family.value_counts().iloc[0]
print(f'\\nTop 5 datasets hold {share5:.1f}% of records; the most-recorded family is {df.family.value_counts().index[0]} with {int(top_family):,} records ({100*top_family/len(df):.1f}%).')
print('\\nRecord types (% of retained records):')
print((100 * df.basisOfRecord.value_counts(dropna=False) / len(df)).round(1).to_string())

fig, axes = plt.subplots(2, 2, figsize=(12, 9), layout='constrained')
ds_counts = df.dataset_id.value_counts().head(10).sort_values()
named = attribution.dropna(subset=['datasetName'])
name_map = dict(zip(named.dataset_id, named.datasetName))
ds_labels = [name_map.get(d, str(d))[:38] for d in ds_counts.index]
ds_counts.plot.barh(ax=axes[0, 0], color='#168a83')
axes[0, 0].set_yticklabels(ds_labels, fontsize=7)
axes[0, 0].set(title='Records by contributing dataset (top 10)', xlabel='Occurrence records')
df.family.value_counts().head(10).sort_values().plot.barh(ax=axes[0, 1], color='#168a83')
axes[0, 1].set(title='Most frequently recorded families', xlabel='Occurrence records', ylabel='Family')
annual = df.dropna(subset=['year']).groupby('year').agg(records=('id', 'size'), species=('species_key', 'nunique'))
axes[1, 0].plot(annual.index, annual.records, label='Records', color='#176b8a')
axes[1, 0].plot(annual.index, annual.species, label='Unique species', color='#d07825')
axes[1, 0].set(title='Annual database coverage', xlabel='Year', ylabel='Count')
axes[1, 0].legend()
axes[1, 1].hist(df.depth_m.dropna(), bins=40, color='#168a83', edgecolor='white')
axes[1, 1].set(title=f'Depth distribution ({100*df.depth_m.notna().mean():.0f}% of records report depth)', xlabel='Depth (m)', ylabel='Records')
fig.savefig(OUTPUT / '01_descriptive_statistics.png', bbox_inches='tight')
plt.show()
''')
md('''
## 5. Aggregate records into geographic grid cells

A fixed grid origin sits at the southwest corner of the rectangle. The 0.1° pilot grid is about 11 km north–south; longitude widths shrink with latitude. It is an exploratory scale, not an optimized ecological unit; 0.25° and 0.5° grids are tested in Section 8. Only **occupied cells** enter the richness distribution — unsampled cells are unknown, not zero.

Within a cell, richness is the number of unique species identifiers. Cluster-level richness is recomputed as the union of species across member cells, because summing cell richness would count some species more than once.
''')
code('''
def aggregate_grid(records, step):
    tagged = records.copy()
    west, south, east, north = BOUNDS
    nx, ny = int(np.ceil((east-west)/step)), int(np.ceil((north-south)/step))
    tagged['ix'] = np.floor((tagged.decimalLongitude-west)/step).astype(int).clip(0, nx-1)
    tagged['iy'] = np.floor((tagged.decimalLatitude-south)/step).astype(int).clip(0, ny-1)
    tagged['cell_id'] = tagged.ix.astype(str) + ':' + tagged.iy.astype(str)
    grid = tagged.groupby('cell_id').agg(ix=('ix', 'first'), iy=('iy', 'first'), observation_count=('id', 'size'), unique_species=('species_key', 'nunique'), unique_families=('family', 'nunique'), years_sampled=('year', 'nunique'), dataset_count=('dataset_id', 'nunique'), median_depth_m=('depth_m', 'median')).reset_index()
    grid['center_lon'] = west + (grid.ix + 0.5) * step
    grid['center_lat'] = south + (grid.iy + 0.5) * step
    grid['species_per_record'] = grid.unique_species / grid.observation_count
    assert grid.observation_count.sum() == len(records)
    assert (grid.unique_species <= grid.observation_count).all()
    return tagged, grid

tagged, grid = aggregate_grid(df, GRID_SIZE)
threshold = grid.unique_species.quantile(RICHNESS_QUANTILE)
candidates = grid.loc[grid.unique_species >= threshold].copy()
print(f'{len(grid)} occupied cells; richness threshold = {threshold:.2f}; {len(candidates)} candidate cells ({100*len(candidates)/len(grid):.1f}%).')
print('Ties at the threshold can make the selected fraction exceed 20%.')
print(grid.sort_values('unique_species', ascending=False).head(12).to_string(index=False))
grid.to_csv(OUTPUT / 'grid_metrics.csv', index=False)
''')
code('''
outline = json.loads((DATA / 'philippines_outline.geojson').read_text(encoding='utf-8'))
def map_background(ax):
    for feature in outline['features']:
        geom = feature['geometry']
        polygons = geom['coordinates'] if geom['type'] == 'MultiPolygon' else [geom['coordinates']]
        for polygon in polygons:
            ring = np.array(polygon[0])
            ax.fill(ring[:, 0], ring[:, 1], facecolor='#ecebe4', edgecolor='#aaa99e', linewidth=0.45, zorder=0)
    ax.set(xlim=(BOUNDS[0], BOUNDS[2]), ylim=(BOUNDS[1], BOUNDS[3]), xlabel='Longitude (°E)', ylabel='Latitude (°N)')
    ax.set_aspect(1/np.cos(np.deg2rad(10.5)))
    ax.grid(alpha=0.15)

fig, axes = plt.subplots(1, 3, figsize=(15, 5), layout='constrained')
for ax in axes:
    map_background(ax)
axes[0].scatter(df.decimalLongitude, df.decimalLatitude, s=2, alpha=0.15, color='#176b8a', rasterized=True)
axes[0].set_title('Cleaned occurrence locations: sampling footprint')
for ax, column, title in [(axes[1], 'observation_count', 'Sampling effort: records per occupied cell'), (axes[2], 'unique_species', 'Recorded species richness per occupied cell')]:
    points = ax.scatter(grid.center_lon, grid.center_lat, c=grid[column], norm=matplotlib.colors.LogNorm(vmin=1, vmax=max(2, grid[column].max())), s=34, marker='s', cmap='viridis')
    ax.set_title(title)
    fig.colorbar(points, ax=ax, label='Count (log color scale)', shrink=0.7)
fig.savefig(OUTPUT / '02_sampling_and_richness_maps.png', bbox_inches='tight')
plt.show()
''')
md('''
## 6. Select high-richness cells and examine sampling effort

The candidate rule is **at or above the 80th percentile of richness among occupied cells** — a transparent, relative cutoff, not a significance test. The histogram shows the threshold; the scatter plot asks whether rich cells are simply well-sampled cells. The rank correlation describes association, not cause.

Species-per-record is an exploratory ratio: it can spike in tiny samples and is not an effort correction. Coverage-based rarefaction would need a defensible definition of sampling units, which these mixed records do not provide.
''')
code('''
fig, axes = plt.subplots(1, 2, figsize=(12, 4), layout='constrained')
axes[0].hist(grid.unique_species, bins=25, color='#168a83', edgecolor='white')
axes[0].axvline(threshold, color='#ba4b35', linestyle='--', label=f'80th percentile: {threshold:.1f}')
axes[0].set(title='Richness among occupied cells', xlabel='Unique recorded species', ylabel='Grid cells')
axes[0].legend()
pts = axes[1].scatter(grid.observation_count, grid.unique_species, c=grid.dataset_count, cmap='plasma', alpha=0.8, edgecolors='white', linewidth=0.4)
axes[1].set(xscale='log', yscale='log', title='Sampling effort versus recorded richness', xlabel='Occurrence records (log)', ylabel='Unique species (log)')
fig.colorbar(pts, ax=axes[1], label='Contributing datasets')
rho = grid.observation_count.rank().corr(grid.unique_species.rank())
print(f'Spearman rank correlation: {rho:.3f}')
print('High-richness candidates with the fewest records (exploratory, not adjusted richness):')
print(candidates.sort_values('observation_count').head(8)[['cell_id','unique_species','observation_count','dataset_count','years_sampled','species_per_record']].to_string(index=False))
fig.savefig(OUTPUT / '03_threshold_and_sampling_bias.png', bbox_inches='tight')
plt.show()
''')
md('''
## 7. Choose a DBSCAN distance and inspect sensitivity

`eps` is converted from kilometers to radians using the mean Earth radius. For `min_samples=3`, the sorted distance to the third-nearest point (counting the point itself) is the standard diagnostic, and the elbow suggests a starting radius. It is a heuristic that fails when no elbow exists, so Section 8 sweeps the parameter space instead of trusting the knee. With fewer than three candidate cells, the pilot would need a different scope or grid.
''')
code('''
assert len(candidates) >= MIN_SAMPLES, 'Too few candidate cells for this min_samples.'
coords_rad = np.deg2rad(candidates[['center_lat', 'center_lon']].to_numpy())
distances, _ = NearestNeighbors(n_neighbors=MIN_SAMPLES, metric='haversine', algorithm='ball_tree').fit(coords_rad).kneighbors(coords_rad)
kdist_km = np.sort(distances[:, -1] * EARTH_RADIUS_KM)
x = np.linspace(0, 1, len(kdist_km))
y = (kdist_km - kdist_km.min()) / max(float(np.ptp(kdist_km)), 1e-12)
knee_index = int(np.argmax(x - y))
suggested_eps = max(0.1, float(kdist_km[knee_index]))
EPS_KM = suggested_eps if EPS_OVERRIDE_KM is None else float(EPS_OVERRIDE_KM)
assert EPS_KM > 0
fig, ax = plt.subplots(figsize=(8, 4), layout='constrained')
ax.plot(np.arange(1, len(kdist_km)+1), kdist_km, color='#176b8a')
ax.axhline(EPS_KM, color='#ba4b35', linestyle='--', label=f'Pilot eps = {EPS_KM:.2f} km')
ax.scatter(knee_index+1, suggested_eps, c='#ba4b35')
ax.set(title='Sorted third-neighbor distances (includes self)', xlabel='Sorted candidate cell', ylabel='Distance (km)')
ax.legend()
fig.savefig(OUTPUT / '04_k_distance.png', bbox_inches='tight')
plt.show()

def run_dbscan(cells, eps_km, min_samples):
    if len(cells) == 0:
        return np.array([], dtype=int)
    radians = np.deg2rad(cells[['center_lat', 'center_lon']].to_numpy())
    return DBSCAN(eps=eps_km/EARTH_RADIUS_KM, min_samples=min_samples, metric='haversine', algorithm='ball_tree').fit_predict(radians)

def label_stats(labels):
    return {'clusters': len(set(labels) - {-1}), 'noise_cells': int((labels == -1).sum()), 'clustered_cells': int((labels >= 0).sum())}

candidates['cluster'] = run_dbscan(candidates, EPS_KM, MIN_SAMPLES)
trials = []
for radius in sorted(set([15.0, 25.0, 40.0, round(EPS_KM, 5)])):
    for minimum in [3, 4, 5]:
        labels = run_dbscan(candidates, radius, minimum)
        trials.append({'eps_km': radius, 'min_samples': minimum, **label_stats(labels)})
sensitivity = pd.DataFrame(trials)
print(f'Elbow suggestion: {suggested_eps:.2f} km; actual pilot eps: {EPS_KM:.2f} km')
print(sensitivity.to_string(index=False))
sensitivity.to_csv(OUTPUT / 'dbscan_parameter_sensitivity.csv', index=False)
candidates.to_csv(OUTPUT / 'candidate_cell_clusters.csv', index=False)
''')
md('''
## 8. Map and characterize clusters

On the map, colored points are clustered high-richness cells, grey crosses are high-richness cells DBSCAN called noise, and pale dots are other occupied cells. Noise means "isolated under these settings," not "unimportant." Label numbers are arbitrary identifiers.

Cluster richness is the distinct species union in member candidate cells — the same definition used for records and family composition. Family proportions summarize recorded occurrences and inherit dataset methods. The sensitivity views show how cluster counts respond to radius, `min_samples`, grid size, and the richness cutoff; matching membership across settings would be a stronger stability check for the final project.
''')
code('''
fig, ax = plt.subplots(figsize=(8, 7), layout='constrained')
map_background(ax)
ax.scatter(grid.center_lon, grid.center_lat, s=12, color='#d5d9df', label='Other occupied cells')
cluster_ids = sorted(set(candidates.cluster) - {-1})
palette = plt.get_cmap('tab20')
for i, cluster_id in enumerate(cluster_ids):
    part = candidates[candidates.cluster == cluster_id]
    ax.scatter(part.center_lon, part.center_lat, s=55, color=palette(i % 20), edgecolors='black', linewidth=0.35, label=f'Cluster {cluster_id}')
noise = candidates[candidates.cluster == -1]
if len(noise):
    ax.scatter(noise.center_lon, noise.center_lat, s=42, color='#555555', marker='x', label='High-richness noise')
ax.set_title(f'High recorded richness clusters | eps={EPS_KM:.1f} km, min_samples={MIN_SAMPLES}')
ax.legend(loc='upper left', fontsize=8)
fig.savefig(OUTPUT / '05_dbscan_cluster_map.png', bbox_inches='tight')
plt.show()

cluster_records = tagged.merge(candidates[['cell_id', 'cluster']], on='cell_id', how='inner', validate='many_to_one')
cluster_summary = cluster_records[cluster_records.cluster >= 0].groupby('cluster').agg(total_records=('id', 'size'), unique_species=('species_key', 'nunique'), unique_families=('family', 'nunique'), datasets=('dataset_id', 'nunique'), years_sampled=('year', 'nunique'), median_depth_m=('depth_m', 'median'))
cell_summary = candidates[candidates.cluster >= 0].groupby('cluster').agg(grid_cells=('cell_id', 'size'), mean_cell_richness=('unique_species', 'mean'))
cluster_summary = cluster_summary.join(cell_summary)
cluster_summary.to_csv(OUTPUT / 'cluster_summary.csv')
print('Cluster summaries (species union, not summed richness):')
print(cluster_summary.round(2).to_string())
print('Noise candidate cells:', len(noise))
if len(cluster_summary):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4), layout='constrained')
    cluster_summary.unique_species.plot.bar(ax=axes[0], color='#168a83', rot=0)
    axes[0].set(title='Distinct recorded species in clustered candidate cells', xlabel='Cluster', ylabel='Unique species')
    families = cluster_records.loc[cluster_records.cluster >= 0, 'family'].value_counts().head(6).index
    composition = pd.crosstab(cluster_records.loc[cluster_records.cluster >= 0, 'cluster'], cluster_records.loc[cluster_records.cluster >= 0, 'family'])
    totals = cluster_records.loc[cluster_records.cluster >= 0].groupby('cluster').size()
    shares = composition.reindex(columns=families, fill_value=0).div(totals, axis=0)
    shares['Other / missing'] = (1 - shares.sum(axis=1)).clip(lower=0)
    shares.plot.bar(stacked=True, ax=axes[1], colormap='tab20', rot=0)
    axes[1].set(title='Family composition of records', xlabel='Cluster', ylabel='Share of occurrence records')
    axes[1].legend(loc='upper left', bbox_to_anchor=(1, 1), fontsize=8)
    shares.to_csv(OUTPUT / 'cluster_family_record_shares.csv')
    fig.savefig(OUTPUT / '06_cluster_richness_and_composition.png', bbox_inches='tight')
    plt.show()
else:
    print('No spatial cluster at these settings. That is a valid outcome; inspect sensitivity instead of forcing clusters.')
''')
md('''
The table below changes the grid scale and the candidate percentile while holding the pilot `eps` and `min_samples` fixed. A wider grid also changes cell spacing, so these comparisons demonstrate that no single setting is universally optimal.
''')
code('''
scale_trials = []
for step in [0.1, 0.25, 0.5]:
    _, cells_at_scale = aggregate_grid(df, step)
    for quantile in [0.7, 0.8, 0.9]:
        cut = cells_at_scale.unique_species.quantile(quantile)
        selected = cells_at_scale[cells_at_scale.unique_species >= cut]
        labels = run_dbscan(selected, EPS_KM, MIN_SAMPLES)
        scale_trials.append({'grid_degrees': step, 'quantile': quantile, 'occupied_cells': len(cells_at_scale), 'richness_cutoff': cut, 'candidate_cells': len(selected), **label_stats(labels)})
scale_sensitivity = pd.DataFrame(scale_trials)
print(scale_sensitivity.round(2).to_string(index=False))
scale_sensitivity.to_csv(OUTPUT / 'grid_threshold_sensitivity.csv', index=False)
fig, axes = plt.subplots(1, 2, figsize=(12, 4), layout='constrained')
matrix = sensitivity.pivot(index='min_samples', columns='eps_km', values='clusters')
im = axes[0].imshow(matrix, cmap='YlGnBu', aspect='auto')
axes[0].set_xticks(range(len(matrix.columns)), [f'{v:.1f}' for v in matrix.columns])
axes[0].set_yticks(range(len(matrix.index)), matrix.index)
axes[0].set(title='Cluster count: radius and neighbor requirement', xlabel='eps (km)', ylabel='min_samples')
for iy in range(matrix.shape[0]):
    for ix in range(matrix.shape[1]):
        value = matrix.iloc[iy, ix]
        label_color = 'white' if value > (matrix.to_numpy().max() + matrix.to_numpy().min()) / 2 else 'black'
        axes[0].text(ix, iy, str(value), ha='center', va='center', color=label_color)
fig.colorbar(im, ax=axes[0], label='Clusters')
for step, subset in scale_sensitivity.groupby('grid_degrees'):
    axes[1].plot(subset['quantile'], subset.clusters, marker='o', label=f'{step}° grid')
axes[1].set(title='Cluster count: grid and richness threshold', xlabel='Candidate richness quantile', ylabel='Clusters', xticks=[0.7, 0.8, 0.9])
axes[1].legend()
fig.savefig(OUTPUT / '07_sensitivity.png', bbox_inches='tight')
plt.show()
''')
md('''
## 9. Findings

The numbers below describe the bundled snapshot; the cell that follows prints the live values so you can check them after any rerun. Geographic locations are identified by spatial coordinates and verified against local coastal landmarks.

**F1 — A broad but thin record.** 38,865 records cover 2,237 species in 179 families from 28 datasets spanning 1885–2016, spread over 358 occupied cells. The median cell holds 6 species; the richest holds 643 — a strongly right-skewed distribution.

**F2 — Recording is concentrated.** Five of 28 datasets supply 88.8% of records, and iNaturalist research-grade observations alone supply 53%. Pomacentridae, Labridae, and Gobiidae are the most-recorded families. The map largely shows where a handful of projects worked.

**F3 — Richness tracks effort.** Records per cell and species per cell correlate at Spearman ρ = 0.969. Several candidate cells reach 31+ species on fewer than 45 records from a single dataset: high richness on thin evidence.

**F4 — High-richness cells form coherent clusters.** 73 cells clear the 80th-percentile threshold (≥ 31 species). At eps = 15.63 km and min_samples = 3, DBSCAN returns 7 clusters plus 17 isolated cells. Cluster 0 dominates: 23 cells, 1,524 species, 16 datasets, and 51 years of recording at a median depth of 2.4 m — a broad, long-sampled coastal concentration in the south-central window (around 123.3° E, 9.3° N). Cluster 4 sits apart at a median depth of 333 m: a deeper-water group. Cluster 5 rests on one dataset in a single year (359 records, 163 species) — a single-survey signal until verified.

**F5 — Boundaries move with the settings.** Tested radii and neighbor requirements yield 3–7 clusters, and coarser grids shift the count again. The stable claim is that high-richness cells concentrate in a few patches; the exact edges are exploratory.

**F6 — Gaps cap what the record can say.** 58% of records lack a year and 89% lack depth; 2,048 records carry coordinate uncertainty above 10 km, close to the grid width. Nothing here measures abundance, and annual totals describe database coverage, not fish populations.
''')
code('''
print(f'The cleaned Visayas-window snapshot contains {len(df):,} marine ray-finned fish records and {df.species_key.nunique():,} recorded species across {len(grid)} occupied {GRID_SIZE}° cells.')
print(f'{len(candidates)} cells meet the {RICHNESS_QUANTILE:.0%} richness quantile threshold ({threshold:.1f} species). At eps={EPS_KM:.2f} km and min_samples={MIN_SAMPLES}, DBSCAN identifies {len(cluster_ids)} clusters and {len(noise)} isolated candidate cells.')
print(f'Record count and cell richness have rank correlation {rho:.3f}.')
if len(cluster_summary):
    richest = cluster_summary.unique_species.idxmax()
    row = cluster_summary.loc[richest]
    top_families = cluster_records.loc[cluster_records.cluster == richest, 'family'].value_counts().head(3)
    print(f'Cluster {richest} has the largest species union: {int(row.unique_species):,} species from {int(row.total_records):,} records in {int(row.grid_cells)} candidate cells, contributed by {int(row.datasets)} datasets over {int(row.years_sampled)} years, median depth {row.median_depth_m:.1f} m.')
    print('Its most frequently recorded families:', ', '.join(f'{name} ({count:,} records)' for name, count in top_families.items()))
    for cluster_id in cluster_summary.index:
        subset = cluster_records[cluster_records.cluster == cluster_id]
        family_counts = subset.family.value_counts()
        if len(family_counts):
            dominant = family_counts.index[0]
            share = 100 * family_counts.iloc[0] / len(subset)
            print(f'Cluster {cluster_id}: most frequently recorded family is {dominant} ({share:.1f}% of its records).')
print(f'Tested parameter combinations produce {sensitivity.clusters.min()}–{sensitivity.clusters.max()} clusters.')
print(f'Year coverage: {100*df.year.notna().mean():.1f}%; depth coverage: {100*df.depth_m.notna().mean():.1f}%.')
if 'coordinateUncertaintyInMeters' in df:
    uncertainty = pd.to_numeric(df.coordinateUncertaintyInMeters, errors='coerce')
    print(f'{int((uncertainty > 10000).sum()):,} records have reported coordinate uncertainty above 10 km, close to the pilot grid width.')
''')
md('''
## 10. Limitations

- **Sampling bias.** Records mix surveys, specimens, methods, and historical periods. Dataset count and years indicate coverage, not standardized effort; presence-only data cannot estimate true richness without stronger assumptions.
- **Spatial quality.** The rectangle is a pilot window; a marine taxon flag does not validate habitat or coordinates. Coarse, repeated, on-land, or uncertain coordinates can create artificial concentrations, and the missing `flags` field ruled out flag-based exclusions.
- **Taxonomy.** The pilot relies on OBIS identifiers; name fallbacks and cross-provider duplicates deserve review. Ray-finned fish are one component of marine biodiversity.
- **Scale.** Richness depends on cell size; the percentile cutoff, `eps`, and `min_samples` are exploratory choices, not tuned against ecological labels. The elbow is a diagnostic, not a proof of optimal parameters.
- **Time.** Species accumulated over decades need not coexist today.
- **Interpretation.** These are clusters of **high recorded richness**. Unsampled cells are unknown, noise cells may still matter, and no conservation priority or definitive hotspot is established here.
''')
md('''
## 11. Route to the final project

Before the final term submission, this exploratory pilot will be expanded across several key areas:
1. **Sampling Effort Correction:** Implement coverage-based rarefaction or sample-based standardization to separate genuine biodiversity hotspots from dive-tourism and research concentrations.
2. **Data Quality Enhancement:** Ingest full OBIS data quality flags to programmatically filter records with large positional uncertainty.
3. **Ecological and Depth Stratification:** Conduct vertical depth stratification (shallow reef vs. bathyal zones) and incorporate environmental covariates (such as sea surface temperature and bathymetry).
4. **Scale and Sensitivity Validation:** Assess cluster membership stability across multiple spatial resolutions and validate boundaries against designated Philippine Marine Protected Areas (MPAs).
''')


def execute():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    namespace = {'__name__': '__main__'}
    counter = 0
    for cell in cells:
        if cell['cell_type'] != 'code':
            continue
        counter += 1
        cell['execution_count'] = counter
        captured_figures = []
        def show(*args, **kwargs):
            for num in plt.get_fignums():
                fig = plt.figure(num)
                buffer = io.BytesIO()
                fig.savefig(buffer, format='png', bbox_inches='tight')
                captured_figures.append(base64.b64encode(buffer.getvalue()).decode('ascii'))
                plt.close(fig)
        plt.show = show
        stream = io.StringIO()
        print(f'Executing cell {counter}', flush=True)
        with contextlib.redirect_stdout(stream):
            exec(compile(cell['source'], f'<notebook cell {counter}>', 'exec'), namespace)
        if stream.getvalue():
            cell['outputs'].append({'output_type': 'stream', 'name': 'stdout', 'text': stream.getvalue()})
        for encoded in captured_figures:
            cell['outputs'].append({'output_type': 'display_data', 'metadata': {}, 'data': {'image/png': encoded, 'text/plain': '<matplotlib figure>'}})
    versions = {key: namespace[key].__version__ for key in ['np', 'pd', 'matplotlib', 'sklearn']}
    (ROOT / 'outputs' / 'execution_versions.json').write_text(json.dumps(versions, indent=2), encoding='utf-8')


if __name__ == '__main__':
    execute()
    for index, cell in enumerate(cells):
        cell['id'] = f'pilot-{index:03d}'
    notebook = {'cells': cells, 'metadata': {'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'}, 'language_info': {'name': 'python', 'version': '3.12'}, 'title': 'Visayas recorded fish richness — OBIS pilot'}, 'nbformat': 4, 'nbformat_minor': 5}
    target = ROOT / 'Philippines_Marine_Biodiversity_POC.ipynb'
    target.write_text(json.dumps(notebook, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'Created executed notebook: {target}')
