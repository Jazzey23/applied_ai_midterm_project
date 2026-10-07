
slide 1

    Hello everyone, our mini data science research is Analysis of Recorded Marine Fish Richness in the Visayas.
    
    I am Gian Cedrick G. Epilan, and alongside Jahzeel Lanz N. Mercado.

    The Visayas is internationally celebrated as the global epicenter of marine biodiversity. But here’s the reality: that reputation comes from what has actually been recorded by humans—and where humans look is notoriously uneven.
    Our project investigates the real data behind that reputation: does high recorded fish biodiversity actually form connected geographic corridors along our coastlines, or is it simply a coincidence of where dive boats and scientists happened to visit?

slide 2

    Our research question is: "Do neighboring areas in the Visayas with high recorded species richness form geographically coherent clusters?"
    Why does this matter? Because in marine conservation, if biodiversity exists in isolated pockets, you manage individual coral heads. But if rich areas form connected clusters, local governments need to protect entire continuous straits and corridors.

    To answer this, we defined a strict pilot window: a geographic rectangle covering the Central and Eastern Visayas—122 to 125 degrees East and 9 to 12 degrees North—focusing on marine ray-finned fish.

    We explicitly defined this boundary as an empirical pilot study, giving us a bounded area to test real-world spatial clustering.

slide 3
    To get this data, we queried the Ocean Biodiversity Information System (OBIS)—the global, UNESCO-backed repository for marine life occurrences.

    We wrote a Python script to hit the OBIS API directly, setting a spatial boundary polygon over the Visayas—between 122 to 125 degrees East and 9 to 12 degrees North, covering Cebu, Bohol, Negros, and Leyte.

    We used cursor-based pagination to exhaustively pull every matching occurrence record in that area—capturing coordinates, species names, sampling years, and provider metadata.

slide 4

    That got us this initial dataset of 42,032 OBIS records across 30 datasets.

    BUT:

    We couldn’t just download all marine organisms into one bucket. If we wanted meaningful clusters, we needed a biological group that shares the same coastal waters and was recorded at similar spatial scales.

    So how did we find that group?

slide 5

    We explored what was actually available in the regional database, comparing different marine groups:
    - Groups like sharks and marine mammals had far too few sightings across the Visayas to detect any geographic patterns.
    - Invertebrates like corals and sponges were rarely identified down to the exact species level.
    - But when we looked at water depth and the most recorded families on this chart, we saw a clear pattern: sightings were heavily concentrated in shallow coral reefs—averaging around 7 meters deep—dominated by families like Pomacentridae (damselfishes and clownfishes), Labridae (wrasses), and Gobiidae (gobies).
    
    
slide 6

    All of these families belong to the scientific class Actinopterygii—marine ray-finned fish.
    This group checked every box for our research:

    - It gave us over 42,000 observations representing 2,237 confirmed species.

    - Over half came from verified citizen-science dive photos (iNaturalist) sharing the same shallow reef habitat.

    Choosing ray-finned fish gave us a rich, consistent baseline where every observation is directly comparable across the entire Visayas.

slide 7

    Once we pulled the 42,032 records, we ran an explicit data cleaning audit across eight validation rules.

    First, we removed 181 non-marine records, These were freshwater or brackish fish caught near river mouths that bled into our coastal 
    boundary. (diko sure sa technicality pero lets go with that lang).

    Second, we removed 2,986 records that lacked a confirmed species name: Many museum specimens were only identified to the family or genus 
    level—like just labeling a fish 'Goby' or 'Snapper'. If you don't know the exact species, counting it would falsely inflate the area's 
    species richness.

    That left us with 38,865 high-confidence, clean observations representing 2,237 distinct species ready for spatial analysis.

slide 8

    slide 8 [Visual: 02_sampling_and_richness_maps.png - The 3 Maps]

    Now, when we plotted our clean data across the Visayas, here is what we saw across three steps:

    Map 1 on the far left shows the raw sightings footprint.
       Every individual dot is a GPS coordinate. You can already see dense clusters right along coastlines and popular dive sites like Dauin, Mactan, and Southern Leyte—with huge blank gaps in the open water.

    Map 2 in the middle summarizes survey effort.
       We grouped those sightings into 11-kilometer grid squares. Brighter yellow squares mean hundreds or thousands of sightings were recorded there, while dark purple means only one or two.

    3. Map 3 on the far right shows recorded species richness—how many different species were found in each square.


    [--- THE BIG COMPARISON ---]

    Now, compare the middle map (effort) directly against the right map (richness).

    The color patterns and shapes are almost identical. In fact, there is an almost perfect correlation of 0.97 between them.

slide 9

    wait what? a 0.97 correlation?

slide 10 [Visual: 03_threshold_and_sampling_bias.png - Scatter Plot]
    A 0.97 correlation between survey effort and recorded species richness. 

    What does it mean?

    Areas look "species-rich" largely because humans have spent decades surveying them. In our data, places like Apo Island and Dauin have records spanning 51 different years of marine expeditions, while blank areas simply mean nobody went there to look.

    our map shows where biodiversity has been recorded, but it also directly mirrors where people have spent time looking.    

    so What does that actually imply?

    It implies three critical things:

    1. First: "Richness" is driven by visits, not just biology.
       If you want to predict which area in the Visayas has the highest recorded fish species, you don't need ocean depth or reef health data. You just need to know: "How many times did a dive boat or research team go there?"
    2. Second: Blank areas are UNKNOWN, not EMPTY.
       When you see an empty square on our map, it does not mean there are no fish in that water. It just means nobody dropped an anchor and took photos. Absence of evidence is not evidence of absence.
    3. Third: Why we can't just use standard clustering algorithms.
       Because the data is so uneven, algorithms like K-Means would fail—they would just draw circles around popular dive resorts. 
       
       We needed an algorithm that looks at density, respects natural coastlines, and isn't afraid to call isolated spots "noise." And that brings us to DBSCAN.

slide 11 [Visual: DBSCAN on neighboring high-richness cells]
    To run DBSCAN, we had to define two things: 
    Which cells count as "biodiversity hotspots", and how close do they need to be to form a cluster?

    1. First, selecting Candidate Cells:
       We didn't cluster the entire ocean. We filtered for cells at or above the 80th percentile of species richness—meaning 31 species or more. That narrowed our map down to the 73 richest candidate cells.

    2. Second, our neighborhood settings:
       We set the minimum requirement to 3 cells—meaning a cell needs at least two rich neighbors to form a cluster. And we calculated spatial 
       separation using Haversine geographic distance on Earth's curved surface.

    3. Choosing the radius (The graph on the right):
       How far should our search radius be? 
       This graph sorts all 73 candidate cells by the distance to their 3rd nearest neighbor. 
       - For the first 35 cells, distance is flat at around 11 km—meaning they are touching immediate neighbors.
       - The natural mathematical "elbow" sits right at 15.63 kilometers (the dashed orange line).
       - Beyond that, the curve spikes sharply upward to 50 and 70 kilometers. 
    Any cell on that steep upward spike is simply too far from other rich areas. And rather than forcing them into awkward groups, DBSCAN honestly classifies them as isolated noise.

slide 12

    At 15.6 km, DBSCAN found 7 clusters and left 17 rich cells as isolated noise (the grey crosses).

    Cluster 0 in dark blue is our anchor: 23 connected cells and 1,524 species across Apo Island and Siquijor.
    Cluster 4 in the north is unique, sitting in deep water at 333 meters.
    And Cluster 5 in the southeast comes from just a single survey expedition.

    This shows high-richness areas do cluster along coastlines, but the map also reflects where scientists surveyed.

slide 13 [Visual: Sampling coverage shapes the comparisons]

    This slide proves why you cannot compare clusters using raw numbers alone.
    Look at the comparison between Cluster 2 and Cluster 6:

    - Cluster 6 recorded 84% of the species that Cluster 2 found, but with only one-third of the records (944 vs 2,869).
    - It was also dominated by an entirely different family: Apogonidae (cardinalfishes) instead of the usual damselfishes.
    Does this mean Cluster 6 is inherently richer? 

    Not necessarily. It means different teams used different survey methods—some logging tons of duplicate photos, others sampling more efficiently.

    Because our overall record-richness correlation is so high (0.97), you cannot rank these biodiversity areas fairly without first standardizing for survey effort.

    If we already see survey differences between C2 and C6 within the same fish class, imagine the chaos if we hadn't filtered for ray-finned fish in the first place! Restricting to Actinopterygii was essential to make these areas comparable, but as C2 and C6 prove, future work must still standardize for survey effort before declaring true ecological winners."

slide 14 [Visual: Results depend on the DBSCAN settings]
    Here is the honest test of our model: How much does our answer depend on our choices?
    We tested 12 different parameter combinations—varying the search radius from 15 to 40 kilometers, and the minimum neighbor rule from 3 to 5 cells.
    Notice what happens:
    - As the search radius grows wider to 40 km, neighboring clusters naturally merge together.
    - And as we demand more neighbors, smaller clusters drop out.
    Across all 12 settings, we consistently find between 3 to 7 clusters.
    This proves our core finding is robust: high-richness cells definitely concentrate into a few distinct geographic patches across the Visayas—even if the exact borders shift depending on where you draw the line.

slide 15 [Visual: Coordinate uncertainty changes the result]
    Finally, we audited spatial accuracy: What happens when GPS coordinates are fuzzy?
    Our grid cells are 11 kilometers wide, but 2,048 historical records carry coordinate uncertainties greater than 10 kilometers—meaning they could belong to an adjacent cell.
    Look at what happens when we filter them out:
    - In the middle map, removing those 2,048 coarse records drops our clusters from 7 to 6. Cluster 1 completely dissolves, proving it was partly an artifact of fuzzy coordinates.
    - In the right map, demanding strict modern GPS accuracy leaves only 10 datasets and 4 core clusters.
    The key takeaway: Core clusters like Cluster 0 around Apo Island remain rock solid, but spatial precision directly shapes the boundaries of smaller clusters.


slide 16 [Visual: Findings, Limitations, Next Steps]

    To bring our entire project together:

    Did we find biodiversity clusters?
    Yes. High-richness areas definitely form coherent geographic corridors along Visayan coastlines—ranging between 3 to 7 clusters depending on your parameters, including a unique deep-water community at 333 meters.

    That 0.97 correlation between survey effort and species richness is a massive flashing warning sign for decision-makers.
    If a policymaker looked at our map naively, they might say: 

    "Let’s put all our conservation funding and marine reserves in Cluster 0, and ignore the dark blank spaces."

    That would be a dangerous mistake. 
    
    A 0.97 correlation means our map is predicting human survey visits, not necessarily raw biological truth. Those dark, empty waters aren't 
    devoid of life—they simply represent unstudied reefs that might be in desperate need of protection, but lack tourists and researchers to 
    document them.

Slide 17:
    Anyways thats allll

    Thank you for listening!