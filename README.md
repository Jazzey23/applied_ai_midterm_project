# Marine biodiversity proof of concept

Open `Philippines_Marine_Biodiversity_POC.ipynb` in Jupyter, VS Code, or another notebook viewer. It contains executed outputs, explanatory text, and seven exported figures based on real OBIS data.

The notebook follows a report arc: research question and method (including why DBSCAN over K-means, EM, or SLINK) → data source and reproducibility → data preparation with a cleaning audit → descriptive statistics (dataset concentration, family and annual coverage, depth) → grid aggregation → high-richness candidate selection → DBSCAN radius choice → cluster results and sensitivity → written findings (F1–F6) → limitations → route to the final project with a 5–10 minute presentation outline.

This draft studies marine ray-finned fish in a Visayas-region rectangle (122–125° E, 9–12° N), not the whole Philippines or an official maritime boundary. It measures recorded species richness and compares it with sampling coverage before applying DBSCAN to high-richness grid cells.

## Run

From this project folder, using Python 3.12 or a compatible environment:

```text
python -m pip install -r requirements.txt
python -m jupyterlab
```

Open the notebook and run all cells. The supplied data snapshot supports offline analysis after installing dependencies. Internet access is required only to refresh the dataset:

```text
python download_data.py
```

`build_notebook.py` rebuilds and executes the draft notebook using the four core analysis libraries; it is a development helper, not required to open the notebook.

## Files

- `data/obis_visayas_raw.json`: original selected OBIS API fields with provider rights. The API did not return the requested quality flags; that limitation is explicit in the notebook.
- `data/provenance.json`: retrieval time, full filter, pagination and count information.
- `data/dataset_metadata.json` and `data/dataset_attribution.csv`: contributing providers and attribution.
- `data/obis_visayas_clean.csv`: cleaned records used in the analysis.
- `data/philippines_outline.geojson`: Natural Earth public-domain map geometry.
- `outputs/`: seven PNG figures, audit and analysis CSVs, and execution versions.

OBIS source: https://obis.org/data/access/ and https://manual.obis.org/access.html. The occurrence data retain their original provider licenses; some have noncommercial restrictions. Review dataset metadata and record-level terms before redistribution. The notebook does not assign a new license to the source records.

Results describe recorded richness under uneven sampling. They do not establish true biodiversity, fish abundance, biological time trends, or definitive ecological hotspots.

The executed pilot downloads all 42,032 matching API records, retains 38,865 records representing 2,237 recorded species, and identifies seven clusters at a suggested radius of 15.63 km with `min_samples=3`. The results change with the parameters. The snapshot also has 2,048 retained records with reported coordinate uncertainty above 10 km, requiring further spatial quality review before a final study.
