# North End Gentrification Map

An interactive demographic dashboard visualizing gentrification in Boston's North End from **1950 to 2000**.

**[Live site →](https://joshuarobins.github.io/north-end-gentrification-map/)**

## Overview

This project maps census tract-level data across six decades to track the displacement of the North End's Italian-American community and the broader forces of neighborhood gentrification. Users can explore a custom gentrification index composed of weighted occupation, income, and rent metrics, rendered as a choropleth heatmap over historic tract boundaries.

## Features

- **Decade slider** — step through census years: 1950, 1960, 1970, 1980, 1990, 2000
- **Custom index weights** — adjust the relative contribution of occupation (% white-collar), median family income, and median rent to the gentrification index in real time
- **Choropleth heatmap** — tracts colored on a normalized 0–1 scale (global min/max across all decades)
- **Hover tooltips** — per-tract breakdown of population, Italian demographic groups, economic indicators, and normalized scores
- **Summary stats panel** — neighborhood-wide aggregates that update with the active year and weights

## Gentrification Index

The index is a weighted average of three normalized metrics (global 0–1 scale across all tracts and years):

```
index = (w_occ × Norm_Pct_White_Collar + w_inc × Norm_Median_Family_Income + w_rent × Norm_Median_Rent)
        ──────────────────────────────────────────────────────────────────────────────────────────────
                                    w_occ + w_inc + w_rent
```

Weights are adjustable via the sidebar sliders (0–10).

## Works Cited

Hawkins, Jason, et al. "Measuring the Process of Urban Gentrification: A Composite Measure of the Gentrification Process in Toronto." *Cities*, vol. 126, 2022, article 103708. — Argues that gentrification must be measured as a composite of demographic, real estate, and commercial indicators, and highlights the aggregation bias inherent in fixed census tract boundaries.

Pasto, James S., and Donna R. Gabaccia. "Immigrants and Ethnics: Post–World War II Italian Immigration and Boston's North End (1945–2016)." *New Italian Migrations to the United States: Politics and History since 1945*, vol. 1, University of Illinois Press, 2017, pp. 105–131. — Traces post-WWII Italian immigration to the North End through demographic changes, institutional developments, and housing transactions, providing the historical baseline for interpreting quantitative findings.

Schroeder, Jonathan, et al. *IPUMS National Historical Geographic Information System: Version 20.0*. IPUMS, 2025. — Provides the decennial census tract data — population, income, rent, and occupational variables — that forms the empirical foundation of this project.

## Limitations

- **Italian-origin proxy (1950–1970):** The census did not track Italian ancestry directly in this period. Italian demographic figures are estimated using foreign-born stock data (country of birth of self or parents), which overestimates the true Italian-American population and cannot distinguish later generations.
- **Tract boundary changes:** The North End used F-series tracts in 1950–1960 and shifted to numeric tracts from 1970 onward. These are separate geographies and direct tract-to-tract comparison across the boundary change is not meaningful.
- **Modeled income (1950):** Median family income for 1950 is modeled from occupational class distributions rather than directly observed, as tract-level income data were not published at that geography.
- **Three-metric index:** The gentrification index captures only occupation, income, and rent. Other meaningful signals — educational attainment, housing age, commercial transformation, in-migration rates — are not included due to data availability constraints across all six decades.

## License

MIT