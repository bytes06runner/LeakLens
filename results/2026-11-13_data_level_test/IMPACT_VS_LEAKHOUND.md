# Impact estimates vs true inflation, injected TEST, single-leak files, seed 0

Rows: 29 located single-leak findings with a LeakLens impact record (any status). Comparable = the pipeline reports AUC or R2 (LeakHound's own metrics).

| type | findings | comparable | LeakLens: estimates / MAE | LeakHound (no column named): estimates / MAE | LeakHound (true column named): estimates / MAE |
|---|---|---|---|---|---|
| group | 6 | 6 | 6 / 0.158 | 0 / n/a | 0 / n/a |
| overlap | 6 | 6 | 6 / 0.000 | 0 / n/a | 0 / n/a |
| preprocessing | 8 | 8 | 8 / 0.000 | 8 / 0.299 | 3 / 0.444 |
| target_derived | 3 | 3 | 3 / 0.000 | 1 / 0.022 | 0 / n/a |
| temporal | 6 | 3 | 3 / 0.000 | 0 / n/a | 0 / n/a |

On the 3 findings where both tools give an estimate (LeakHound with the true column named): LeakLens MAE 0.001, LeakHound MAE 0.444; sign agreement with the truth: LeakLens 2/3, LeakHound 0/3.

| item | type | metric | true | LeakLens | LeakHound (none) | LeakHound (true column) |
|---|---|---|---|---|---|---|
| grp_eeg__grp_cv__kfold | group | cv_auc | +0.191 | +0.264 | - | - |
| grp_eeg__grp_cv__stratified | group | cv_auc | +0.196 | +0.269 | - | - |
| grp_eeg__grp_cv__default_cv | group | cv_auc | +0.022 | +0.095 | - | - |
| grp_eeg__tgt_proxy__proxy | target_derived | cv_auc | +0.439 | +0.439 | - | - |
| grp_patients__pre_scaler__standard | preprocessing | test_auc | -0.000 | +0.002 | +0.443 | +0.443 |
| grp_patients__pre_scaler__minmax | preprocessing | test_auc | -0.001 | +0.000 | +0.443 | +0.443 |
| grp_patients__pre_scaler__robust | preprocessing | test_auc | -0.001 | +0.000 | +0.443 | +0.443 |
| grp_patients__ovl_test_in_fit__concat | overlap | test_auc | +0.427 | +0.427 | - | - |
| grp_patients__ovl_test_in_fit__refit_all | overlap | test_auc | +0.427 | +0.427 | - | - |
| grp_patients__grp_holdout__tts | group | test_auc | +0.201 | -0.043 | - | - |
| grp_patients__grp_holdout__tts_stratified | group | test_auc | +0.235 | -0.009 | - | - |
| grp_patients__grp_holdout__shufflesplit | group | test_auc | +0.201 | -0.043 | - | - |
| grp_patients__tgt_proxy__proxy | target_derived | test_auc | +0.427 | +0.427 | - | - |
| tab_credit__pre_scaler__standard | preprocessing | test_auc | +0.000 | +0.000 | +0.217 | - |
| tab_credit__pre_scaler__minmax | preprocessing | test_auc | +0.000 | +0.000 | +0.217 | - |
| tab_credit__pre_scaler__robust | preprocessing | test_auc | +0.000 | +0.000 | +0.217 | - |
| tab_credit__pre_imputer__mean | preprocessing | test_auc | +0.000 | +0.000 | +0.215 | - |
| tab_credit__pre_imputer__median | preprocessing | test_auc | +0.000 | +0.000 | +0.199 | - |
| tab_credit__ovl_test_in_fit__concat | overlap | test_auc | +0.049 | +0.049 | - | - |
| tab_credit__ovl_test_in_fit__refit_all | overlap | test_auc | +0.049 | +0.049 | - | - |
| tab_credit__ovl_raw_duplicates__frac30 | overlap | test_auc | +0.043 | +0.043 | - | - |
| tab_housing__ovl_raw_duplicates__frac30 | overlap | cv_r2 | +0.030 | +0.030 | - | - |
| tab_housing__tgt_proxy__proxy | target_derived | cv_r2 | +0.052 | +0.052 | +0.030 | - |
| ts_air__tmp_cv__kfold_shuffle | temporal | cv_auc | +0.007 | +0.007 | - | - |
| ts_air__tmp_cv__kfold_plain | temporal | cv_auc | -0.009 | -0.009 | - | - |
| ts_air__tmp_cv__default_cv | temporal | cv_auc | +0.005 | +0.005 | - | - |
| ts_sales__tmp_holdout__tts_default | temporal | test_mae | +0.448 | +0.448 | - | - |
| ts_sales__tmp_holdout__tts_shuffle_true | temporal | test_mae | +0.448 | +0.448 | - | - |
| ts_sales__tmp_hidden_time__renamed_time_col | temporal | test_mae | +0.448 | +0.448 | - | - |
