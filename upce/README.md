# Underlying PCE Data
---

The detailed underlying PCE data is not available prior to 2002 through the BEA API for some reason. To be clear, this is not a restriction imposed by the `beapy` package -- editing a proper API url in the browser by changing the `year` parameter from 2002 to 2001 throws an error. I'm not sure why this is, but regardless I thought I'd throw the data & metadata into a repo.

### Naming Scheme

Each column label is formatted as `{dataset}!{table}!{series}`. 