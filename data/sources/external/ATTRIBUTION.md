# External Sources and Attribution

This directory collects candidate and record-holding coordinate sets contributed by researchers, imported from numerical search campaigns, or verified from the literature. Each configuration lives in its own directory and carries a `meta.json` recording its source, discovery credit, method, and date.

## Verification
Every submission is checked in exact rational arithmetic before it is merged: all triangle areas are enumerated from the decimal literals exactly, and the reported value is the true minimum for the chosen container.

## Credit Policy
Discovery credit belongs to whoever first reached the record value. When numerical optimization refines the coordinates of a configuration originally discovered or published by another researcher, the ledger keeps the credit with the original author rather than the optimizer. Corrections to credits are made in `data/curated/records.json`, not here.

## Superseded Entries
When a submission is overtaken by a better configuration for the same container and n, the earlier coordinates are moved to `tests/fixtures/golden/`, where they continue to serve as regression fixtures for the verifiers.
