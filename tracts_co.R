library(tigris)
library(sf)
library(leaflet)
library(htmlwidgets)

options(tigris_use_cache = TRUE)

tracts <- tracts(state = "CO", cb = TRUE, year = 2022) |>
  st_transform(4326)

m <- leaflet(tracts) |>
  addProviderTiles(providers$CartoDB.Positron) |>
  addPolygons(
    weight      = 0.5,
    color       = "#2166ac",
    fillColor   = "#d0e8f5",
    fillOpacity = 0.4,
    highlightOptions = highlightOptions(
      weight      = 1.5,
      color       = "#08519c",
      fillOpacity = 0.7,
      bringToFront = TRUE
    ),
    label = ~NAMELSAD
  )

saveWidget(m, "tracts_co.html", selfcontained = TRUE)
cat("Saved tracts_co.html —", nrow(tracts), "tracts\n")
