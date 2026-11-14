# Do impact estimates compare the same evaluation rows?

34 findings with a measured impact (seed 0). Identical: same row positions of the same rows, or the same multiset of row fingerprints, in every recorded fold of every split call. Jaccard: overlap of the evaluated rows' fingerprints, averaged over folds (1 when identical).

| canonical fix | findings | identical eval rows | mean Jaccard | eval rows (leaky -> fixed, total) | estimate > 0 |
|---|---|---|---|---|---|
| chronological split | 7 | 0 | 0.202 | 5231 -> 4502 | 6 |
| duplicates removed before split | 2 | 0 | 0.285 | 1333 -> 1025 | 2 |
| evaluation rows removed from fit | 5 | 5 | 1.000 | 1019 -> 1019 | 5 |
| feature removed | 3 | 3 | 1.000 | 1932 -> 1932 | 3 |
| group-aware split | 7 | 0 | 0.133 | 3608 -> 3568 | 7 |
| transformer refitted on training rows | 10 | 10 | 1.000 | 2048 -> 2048 | 4 |

Sign convention: 4 estimates use a lower-is-better metric (['test_mae']); their delta is negated, so for every row a positive estimate means the leaky pipeline reported a better score than the fixed one.
