# Reading the OBIS Visayas notebook — a walkthrough for non-specialists

**What this document is.** The notebook is well built, but it assumes you already know what DBSCAN is, what "richness" means in ecology, and why clustering is the right move. This guide reads the notebook the way a curious classmate would: what you see on the screen, what it means, and why the analyst did it that way. It follows `Philippines_Marine_Biodiversity_POC.ipynb` from the title to the end, including every figure in `outputs/`.

**How to use it.** Skim the "What you should be thinking" lines. They are the ones that carry the argument. The rest is detail you only need when a question comes at you in the Q&A.

---

## The short version, before you open anything

Someone took every fish occurrence record that scientists have ever uploaded for a rectangle of ocean off the Visayas (122–125° E, 9–12° N), cleaned it up, and asked: **do the sea areas where the most species have been recorded form distinct geographic patches, or is that an illusion created by where people happened to look?**

They found seven patches — but also found that the map of "where species are" is mostly a map of "where people went looking." Both halves of that sentence are the finding.

Three ideas carry the whole project. If you understand nothing else, understand these:

1. **Recorded richness is not fish abundance, and an empty map cell is unknown, not empty.** The data says "a fish of this species was recorded here." It never says how many, and it says nothing at all about places nobody visited.
2. **Effort drives the pattern.** Cells with more survey records also have more recorded species — correlation of 0.969 on a 0–1 scale. That is the single most important number in the notebook.
3. **"Noise" is an answer, not a failure.** DBSCAN is allowed to say "this one rich cell stands alone, and I will not pretend it has neighbors." Forcing everything into a cluster would have hidden that.

---

## Before you start: three numbers to have in your head

| Number | What it means | Why it matters |
|---|---|---|
| **38,865** | Clean occurrence records | The evidence base. All of it public volunteer and museum data. |
| **2,237** | Distinct species identified | The richness ceiling in this window. |
| **0.969** | Correlation between survey effort and recorded richness | The reason the notebook keeps insisting you separate *recorded* from *real*. |

If a grader asks "what's your dataset," those three sentences answer it.

---

## 1. The title page and the opening claim

**What you see.** The title asks *"Where has the Visayas actually been surveyed? Recorded fish richness from OBIS."* Then it opens with the line that sets up the whole story: the Visayas is called the center of Philippine marine biodiversity, but that reputation rests on **what has been recorded** — and recording is uneven.

**What you should be thinking.** Notice that the framing is careful from the first line. This is not a paper claiming "we found the biodiversity hotspots of the Visayas." It is a paper claiming "we mapped the *record*, and we will keep telling you where the record and reality might diverge." That framing is doing real work: it is what makes the results defensible rather than overclaimed.

The scope box is also deliberate. It says out loud what the project is **not**: not an official maritime boundary, not a nationwide inventory, sharks and rays excluded. Reviewers reward projects that name their own boundaries. A pilot that admits it is a pilot reads as more competent, not less.

The pipeline line — *occurrences → cleaning → grid → DBSCAN → composition → sensitivity* — is your map of the notebook. Every arrow is a section you will meet.

**A natural question here:** "Why ray-finned fish only?" Because they are numerous, well sampled, and taxonomically messy in a *useful* way — the project can show you exactly where it relies on database identifiers versus names.

---

## 2. "Question and method" — why DBSCAN, and not something else

**What you see.** A bulleted comparison of four clustering techniques, then a paragraph arguing for DBSCAN.

**What you should be thinking.** This is the section that earns the most credit under the "alignment of technique with dataset and research question" criterion, and it works because it *rejects* alternatives instead of just praising one. The reasoning, in plain terms:

- **K-means** needs you to tell it how many clusters to find *before* it runs, and it forces groups to be roughly round and roughly equal in size. Real marine patches follow coastlines and reef edges. They are lumpy and lopsided. Also, nobody knows how many patches to expect — that is the actual research question.
- **EM clustering** (a fancier k-means that models each cluster as a fuzzy blob) inherits the same round-cluster assumption and the same need to fix the count up front.
- **SLINK** (single-linkage hierarchical clustering) merges anything that has *any* nearby neighbor, and keeps merging. Two genuinely distinct ecosystems 30 km apart get welded together because a few records sit between them. That is called chaining, and it would have produced a confident, wrong map.
- **DBSCAN** asks a local question per cell: "are there enough neighbors within a reasonable distance?" It lets shapes be irregular, and — the key point — it does not force isolated cells into a group. It calls them **noise**.

**Why the analyst chose it:** the question is "do rich areas clump into a few patches, and is any of them standing alone?" DBSCAN is the only one of the four that can honestly answer both halves. The other three would have to invent an answer for the second half.

**The detail that shows care:** they cluster **grid-cell centers**, not individual fish sightings. Clustering 38,865 raw points would just re-derive the sampling map. Aggregating first means DBSCAN is answering the ecological question — *do areas clump* — not the trivial one — *are there many points here*.

---

## 3. "Data source and reproducibility"

**What you see.** OBIS (the Ocean Biodiversity Information System) as the source. Cursor pagination through **all** matching records rather than a first page. Provider licenses, a file hash, provenance JSON.

**What you should be thinking.** Two things.

First, *why all the records matters*. OBIS is a live API, so the tempting shortcut is to grab the first 1,000 rows. That would be a sample chosen by API response order — arbitrary, biased toward whatever the server ranks first, and unreproducible. Paging through everything costs minutes and makes the finding a statement about the whole snapshot.

Second, the licensing sentence is not boilerplate to skim. About half the contributing datasets here are **noncommercial (CC BY-NC)**, and the largest contributor is iNaturalist — volunteer observations, dual-licensed. The notebook explicitly declines to relicense the data and warns against republishing it commercially. For a class project this is exactly right, and it is the kind of detail that separates a data science project from a data science assignment.

If a grader asks "is this reproducible?", the answer is: bundled snapshot runs offline, `download_data.py` refreshes it, provenance JSON records the query and retrieval time, and the snapshot's SHA-256 is printed. That is a complete answer.

---

## 4. "Data preparation" — the cleaning audit

**What you see.** Rules for keeping records, then a printed table showing what each rule removed.

The audit reads roughly:

| Rule | Removed | Left |
|---|---|---|
| Valid, nonmissing coordinates | 0 | 42,032 |
| Inside study rectangle | 0 | 42,032 |
| Presence records only | 0 | 42,032 |
| Exclude OBIS dropped records | 0 | 42,032 |
| Taxon explicitly flagged marine | 181 | 41,851 |
| Identified species required | 2,986 | 38,865 |

**What you should be thinking.** Look at the two non-zero rows — the rest are honest zeros, and showing them is a quiet kind of rigor (it proves you checked and found nothing to remove, rather than not checking).

The 2,986 removals are mostly records with no species name. Dropping them matters more than it looks: an unidentified specimen at a location does not tell you anything about species richness, and counting it as one "species" would inflate every richness number downstream.

Then come the two judgment calls, and they are the most interesting part:

- **The marine flag describes the taxon, not the place.** A fish can be *a marine species* and still have been recorded on a beach, in a river mouth, or with a typo'd coordinate. So "marine" ≠ "at sea," and the notebook says so.
- **The `flags` field came back empty.** OBIS normally returns quality flags that would let you drop dubious records automatically. This snapshot requested specific fields and did not include flags, so **no flag-based exclusions were possible.** Rather than quietly ignoring that, the notebook states it in bold.

**The decision that shows maturity:** they **keep** repeated records of the same species at the same coordinates. That looks like sloppy deduplication until you realize a museum specimen and a diver sighting at the same spot are two independent observations. Over-deduplicating would have thrown away evidence.

**If asked "is your data clean?"** — say: 42,032 raw to 38,865 retained, every removal shown in an audit table, three records had impossible depth ranges, and one known gap (missing flags) is documented rather than papered over.

---

## 5. "Descriptive statistics" — Figure 1, the four-panel dashboard

**What you see.** `outputs/01_descriptive_statistics.png`, four panels:

- **(top left) Records by contributing dataset, top 10** — one enormous bar (iNaturalist, ~20,800 records), a second large bar (a museum consortium: AM, ANSP, CAS, CUMV, FMNH, KAUM…), then a rapid drop-off.
- **(top right) Most frequently recorded families** — Pomacentridae (~4,500), Labridae (~3,983), Gobiidae (~3,616), then a long tail of reef families.
- **(bottom left) Annual database coverage** — records and species per year, spiky, climbing hard after ~1970, peaking around 1987, and mostly empty before 1900.
- **(bottom right) Depth distribution** — a huge spike at the surface, a thin tail out to 1,700 m, and a title reminding you only 11% of records report depth.

**What you should be thinking.** *This figure is the honest core of the project.* Read the panels in this order:

The **dataset bar** is the most important panel in the entire notebook. Five of 28 datasets supply 88.8% of all records. One citizen-science platform supplies 53%. That means the "map of the Visayas" is substantially a map of iNaturalist observers and one museum network. Every downstream map inherits this.

The **family bars** say something true and something cautionary. True: reef-associated families dominate, which matches expectations for a shallow tropical region. Cautionous: these are *record counts*, so they reflect which families get photographed and which get collected. It is a measure of attention as much as of biology.

The **annual panel** looks like a population trend and is not one. Rising lines from 1900 to 1987 mean the **database** got better at recording fish, not that the water changed. This is the single most common misreading of biodiversity data, and the notebook heads it off in the caption.

The **depth histogram** is mostly a completeness chart. With 89% of records missing depth, that spike at the surface is as much about shallow surveys being easier as it is about fish living shallow.

**A line worth memorizing:** "Family and dataset bars count records, not fish."

---

## 6. "Aggregate records into grid cells" — Figure 2, and the project's central insight

**What you see.** `outputs/02_sampling_and_richness_maps.png`, three maps of the same rectangle:

1. **Occurrence locations** — a blue haze of tens of thousands of dots, dense around islands and coasts, empty offshore.
2. **Records per occupied cell** — a viridis-colored heatmap of survey effort.
3. **Recorded species richness per occupied cell** — a viridis-colored heatmap of species counts.

**What you should be thinking.** Put maps 2 and 3 side by side and compare the *shapes*. They are nearly the same shape.

That is the finding. High richness is concentrated exactly where sampling is concentrated. If someone showed you only map 3, you would report a marine biodiversity hotspot map. Having map 2 next to it is what turns that into an honest observation about **sampling**.

Notice also what the maps do *not* show: the empty blue water offshore and the interiors of Negros and Bohol. Those are **unknown**, not zero-richness. The notebook uses the phrase "occupied cells" precisely so the reader cannot mistake blank space for biological absence.

A nice piece of arithmetic in the text: the 0.1° grid is about 11 km north–south, and longitude cells get narrower toward the top of the map. Small detail, but it signals the analyst thought about the geometry instead of assuming a square grid is square everywhere.

**If asked "how do you know the clustering isn't just finding dense sampling?"** — that is Section 7's job, and it is the right next question. Ask it out loud; following it shows you followed the argument.

---

## 7. "Select high-richness cells and examine sampling effort" — Figure 3

**What you see.** `outputs/03_threshold_and_sampling_bias.png`:

- **Left:** a histogram of species counts per occupied cell, with a dashed line at 31 species labeled "80th percentile."
- **Right:** a log-log scatter of records versus species per cell, each dot colored by how many datasets contributed.

**What you should be thinking.** The left panel shows a badly right-skewed distribution — most cells hold a handful of species, a few hold hundreds. The median cell has **6** species; the richest has **643**. A percentile cutoff is used rather than an absolute number like "50 species" precisely because the distribution is this lopsided.

Then the right panel delivers the punchline: **ρ = 0.969**. Nearly a perfect rank correlation between how many records a cell has and how many species it has. In plain terms: if you want to predict which cells look species-rich, the best predictor is not geography or habitat — it is simply **how much surveying happened there**.

Below the figure, the notebook prints the candidates that clear the threshold on the *thinnest* evidence: several cells reach 31–40 species on fewer than 45 records, some from a single dataset, one with zero recorded years. Those are the fragile claims in the map, and they are surfaced rather than hidden.

**The subtle honesty here:** "species per record" is called an exploratory ratio, not an index. It spikes in tiny samples — a cell with 3 records of 3 species scores 1.0, which looks perfect and means nothing. Knowing when your own ratio is meaningless is advanced statistical judgment.

---

## 8. "Choose a DBSCAN distance" — Figure 4

**What you see.** `outputs/04_k_distance.png`: an ascending curve of each candidate cell's distance to its third-nearest neighbor, with a dashed red line marking the chosen radius (15.63 km) and a dot on the knee.

**What you should be thinking.** DBSCAN has two knobs and the notebook is about to pick both. `min_samples` is set to 3 — "a cell needs itself plus two nearby high-richness cells to count as part of a cluster." `eps` is the distance radius, and *that* is what this figure chooses.

The method is standard: sort every cell by how far its third-nearest neighbor is, and look for the elbow — where the curve stops climbing gently and shoots up. Below the elbow, everything is close together and DBSCAN would merge the sea into one giant blob. Above it, everything is noise and DBSCAN finds nothing. The elbow is the compromise.

**The mature part:** the notebook immediately admits this is a heuristic that fails when no elbow exists — which is why Section 9 sweeps the whole parameter space instead of trusting the knee. A method presented as "the standard diagnostic" *and* immediately hedged shows the analyst knows their method's weak points.

---

## 9. "Map and characterize clusters" — Figures 5 and 6

**What you see.** Two more figures:

- **`05_dbscan_cluster_map.png`:** colored dots = clustered high-richness cells, grey crosses = high-richness cells DBSCAN called noise, pale grey dots = other occupied cells, with Natural Earth coastline behind.
- **`06_cluster_richness_and_composition.png`:** a bar chart of distinct species per cluster (Cluster 0 towering at 1,524) beside a stacked bar of family composition per cluster.

**What you should be thinking.** The cluster map is the money shot for the presentation, and it should be presented with the noise crosses visible. Seventeen cells cleared the richness bar and still could not find two neighbors within 15.63 km. Those are isolated high-richness cells, and they are part of the result.

Read the composition chart for **differences, not rankings**. Cluster 0 is dominated by Gobiidae (12.2% of its records); Clusters 1, 2, 3, and 5 lean Pomacentridae; Cluster 4 leans Labridae (11.0%); Cluster 6 is the most distinct, with Apogonidae (15.0%). That variation is interesting — but it is equally consistent with different survey methods, and the caption says so. Do not stand up and say "Cluster 6 has a unique fish community." Say "Cluster 6's recorded composition differs, and the next step is testing whether that survives effort correction."

**One more distinction the notebook insists on:** cluster richness is the **union** of species across member cells, never a sum. Summing would double-count every species found in two cells of the same cluster — inflating totals, sometimes enormously.

---

## 10. "Check grid and threshold dependence" — Figure 7

**What you see.** `outputs/07_sensitivity.png`: a heatmap of cluster counts across radius × `min_samples`, and a line chart of cluster counts across richness cutoffs for three grid sizes (0.1°, 0.25°, 0.5°).

**What you should be thinking.** Read the heatmap across a row. At the chosen radius, raising `min_samples` from 3 to 5 collapses seven clusters down to five, and noise cells jump from 17 to 28. Across all twelve tested combinations the count ranges from **3 to 7**.

This is the section that makes the project honest rather than impressive-sounding. A pilot that only showed the 7-cluster map would be hiding that the number is a function of my choices. Showing the 3–7 range, plus the honest note that cluster *counts* are stable-ish but cluster *membership* is not yet tested, is what earns trust.

The grid comparison adds the same message at a different scale: change the grid from 0.1° to 0.5° and the answer changes again, because bigger cells mean different spacing between neighbors.

**The takeaway sentence for your presentation:** high-richness cells concentrate in a few patches; the exact number of patches and their boundaries depend on my parameter choices.

---

## 11. "Findings" — the six claims, in plain words

This is the section to actually memorize. Written findings (F1–F6) rather than printed output, with a code cell right after that prints the live values so anyone can verify them.

**F1 — A broad but thin record.** 38,865 records, 2,237 species, 179 families, 28 datasets, 1885–2016, spread over 358 occupied cells. The median cell has 6 species; the richest has 643.

> *What this means:* the window is well covered in species names and badly covered in places. Long time span, thin per-cell coverage.

**F2 — Recording is concentrated.** Five of 28 datasets = 88.8% of records; iNaturalist alone = 53%.

> *What this means:* the map is mostly a map of a few projects' footprints.

**F3 — Richness tracks effort.** ρ = 0.969. Several candidates reach 31+ species on under 45 records from one dataset.

> *What this means:* this is the load-bearing finding. It explains F1 and F2 and constrains every ecological claim.

**F4 — High-richness cells do form coherent clusters.** 73 cells clear the threshold; 7 clusters plus 17 isolated cells. Cluster 0: 23 cells, 1,524 species, 16 datasets, 51 years, median depth 2.4 m — a broad, long-sampled coastal concentration. Cluster 4 sits apart at median depth 333 m — a deeper-water group. Cluster 5: one dataset, one year, 359 records, 163 species.

> *What this means:* yes, there is real spatial structure — but Cluster 5 is a single survey's footprint, and Cluster 0's 51 years of coverage means its richness has had 51 years to accumulate. Both facts belong in the same breath as the cluster map.

**F5 — Boundaries move with the settings.** 3–7 clusters across tested parameters.

> *What this means:* report the range, not the headline number.

**F6 — Gaps cap what the record can say.** 58% of records lack a year, 89% lack depth, 2,048 records carry coordinate uncertainty above 10 km — comparable to the grid width.

> *What this means:* a fish "located" to within 10 km could be in the wrong cell entirely. Depth and trend analyses are off the table for now.

---

## 12. "Limitations" — six honest bullets

Sampling bias. Spatial quality (including the missing flags field). Taxonomy and cross-provider duplicates. Scale and parameter choice. Temporal pooling. Interpretation.

**What you should be thinking.** In a good project, limitations are not an apology — they are the section that shows you know exactly where your own claims stop. Read them as instructions for the *next* study: every bullet names a specific, fixable problem.

Notice the last one: these are clusters of **high recorded richness**, and no conservation priority or definitive hotspot is established. That sentence is the line to repeat whenever someone asks "so where should conservation money go?" — the honest answer is "not yet knowable from this data."

---

## 13. "Route to the final project" and the presentation plan

A concrete to-do list for the final assignment (fix the official study extent, audit suspicious coordinates, retrieve the missing OBIS flags, compare cluster membership across scales, add depth only when coverage allows) plus a timed 5–10 minute outline.

**What you should be thinking.** Use that outline literally when you rehearse. Seven beats, one to two minutes each:

1. The question and the pilot window (1 min)
2. The real dataset and what cleaning removed (2 min)
3. Descriptive statistics (1 min)
4. Sampling map beside richness map (1 min)
5. Method: grid, threshold, why DBSCAN, the elbow (1 min)
6. Results: cluster map, composition, sensitivity (2 min)
7. Findings, limitations, next steps (1–2 min)

Beat 4 is the one to rehearse most — putting the effort map next to the richness map and saying "these are the same shape" is the moment the project stops being a technique demo and starts being an insight.

---

## Questions you might be asked, with short answers

**"So did you find the biodiversity hotspots of the Visayas?"**
Not established. We found where *recordings* cluster. With effort and richness correlated at 0.969, we cannot yet separate ecological pattern from sampling pattern.

**"Why DBSCAN?"**
Because we don't know how many clusters to expect, coastal patches are irregular rather than round, and DBSCAN can honestly label isolated cells as noise instead of forcing a cluster.

**"Why 0.1°? Why the 80th percentile? Why `min_samples=3`?"**
Exploratory choices, not tuned against ground truth. The percentile makes the selection transparent; the sensitivity tables show the answer's dependence on all three.

**"What's the biggest limitation?"**
Sampling effort. Everything else is downstream of it.

**"Is the deep cluster (Cluster 4, median 333 m) interesting?"**
Yes, and it's the clearest hypothesis in the project: a deeper-water assemblage recorded over few years. It needs effort-matched comparison before it means anything.

**"Why not sharks and rays?"**
Taxonomic scope for the pilot. Actinopterygii are numerous and well recorded; chondrichthyans would be a natural extension.

**"How would you make this stronger?"**
Effort-corrected richness (rarefaction or coverage-based standardization), a defensible maritime boundary, OBIS flags for quality filtering, and membership-stability testing across scales rather than just count stability.

---

## Vocabulary decoder

| Term | Plain meaning |
|---|---|
| **Occurrence record** | "A fish of species X was recorded at this spot, on this date, by this dataset." One line of evidence. |
| **Richness** | How many *different* species are recorded in an area. Never how many fish. |
| **Grid cell** | An imaginary ~11 km square used to summarize records. |
| **Occupied cell** | A cell with at least one record. Unoccupied cells are unknown, not empty. |
| **Cluster** | A group of nearby high-richness cells that DBSCAN judged connected. |
| **Noise** | A cell DBSCAN would not group. Not "worthless" — just isolated. |
| **`eps`** | How far apart cells can be and still be called neighbors (here 15.63 km). |
| **`min_samples`** | How many nearby cells a group needs to qualify (here 3 — which includes the cell itself, so it needs two real neighbors). |
| **Spearman ρ** | A rank correlation from −1 to 1 measuring whether two things move together, regardless of curve shape. 0.969 ≈ almost perfectly. |
| **Effort / coverage** | How much surveying happened in a cell. Records, datasets, and years are proxies for it. |
| **Percentile (80th)** | The value below which 80% of cells fall. A relative, transparent cutoff. |
| **Coordinate uncertainty** | How precisely a location is known. 10 km is comparable to a whole grid cell. |
| **OBIS** | The global archive where museums and citizen scientists deposit species records. |
| **OBIS flags** | Quality-control fields OBIS provides to mark dubious records. This snapshot's copy is empty. |
| **Provenance JSON** | A receipt: what was requested, when, how many records, and a file hash. |

---

## If you remember only five things

1. **The question is about the record, not the reef.** "Recorded" appears in the findings more than any other qualifier, and that is deliberate.
2. **Effort is the confounder.** 0.969. Put the effort map next to the richness map and say so out loud.
3. **The technique choice is argued, not assumed.** DBSCAN beats the alternatives *for this question* — irregular shapes, unknown cluster count, noise as a valid outcome.
4. **The results are reported with their uncertainty.** 7 clusters, but 3–7 depending on settings; Cluster 5 is one survey; 89% of records lack depth.
5. **Limitations point forward.** Each one names the concrete next step, which is exactly what a "route to the final project" section is for.