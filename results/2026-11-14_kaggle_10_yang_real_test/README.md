# Kaggle job 10: Yang et al. analyser on the 79 real TEST notebooks

Run 2026-11-14 13:21-14:27 UTC on Kaggle CPU. Analyser commit `a7d038bf`, default command, Souffle 2.4.1 built from
source (the apt package has an unmet dependency on this image). Notebooks given as the plain scripts LeakLens's
loader writes (cell order), as the analyser's README requires. Internet was on for the build only; the analyser
reads code and executes nothing from the notebooks. Per-file timeout 300 s.

- Report produced: 69 of 79. Timed out (300 s): R017, R041, R044, R073, R089, R111, R121. Finished with no
  report: R136, R139, R143. These count as "no finding" in scoring (CLAUDE.md Rule 5).
- Median time per analysed notebook: 10.2 s (LeakLens static: 7 ms on the laptop).
- Scored per notebook and type against the frozen AI-drafted labels (`benchmark/real/labels_TEST.csv`, commit
  f8e901e): `../2026-11-14_real_test_static/FILELEVEL.md`. Paired comparison: `paired_vs_leaklens.json`
  (`benchmark/real/paired_real.py`): of 237 decisions, LeakLens right on 206, Yang on 162; 53 vs 9 discordant;
  exact McNemar p = 1.1e-8.
