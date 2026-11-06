# Modeling

All notebooks read from PostgreSQL, so [`../db/`](../db/README.md) must be
running and the data must be loaded. Figures exported along the way are in
[`figures/`](figures/).

The work splits into two very different questions:

**A. Predicting the *aggregated* delay from weather and calendar**
(`aggregated_delay_regression.ipynb`, `aggregated_delay_classification.ipynb`) — one row per (day, hour) or per day,
features are the average weather and the type of day.

**B. Predicting the delay at the *next stops of a trip*** (`line_delay_analysis.ipynb`,
`prepare_trip_weather_features.ipynb`, `predict_remaining_stops.ipynb`, `predict_stops_ahead.ipynb`,
`chained_delay_prediction.ipynb`, `recurrent_delay_prediction.ipynb`) — one row per trip, features include the delay
already accumulated. This is where the project ended up.

---

## A. Aggregated delay

### `aggregated_delay_regression.ipynb`

Target: average `delay_departure`, aggregated **by hour of day** and, in a second
part, **by day**. Features come in three flavours: weather only, calendar only
(day of year encoded as `day_sin` / `day_cos`), and both.

Models: LinearRegression, Lasso, Ridge, SVR, DecisionTree, KNN, RandomForest,
GradientBoosting, AdaBoost, Bagging, ExtraTrees, a stacking ensemble, XGBoost,
and an MLP (scikit-learn and PyTorch), with `GridSearchCV` / `KFold` tuning.

The notebook then goes through four successive refinements — this is the
interesting part:

| Setup | Best model | R² |
| --- | --- | --- |
| Hourly aggregation, all features | Ridge / Linear | **0.014** |
| Daily aggregation, all features | RandomForest | **0.291** |
| Daily, **excluding the 5 % most delayed days** | RandomForest | **0.416** |
| same, XGBoost | XGBoost | **0.429** |
| same, PyTorch MLP (10 000 epochs) | MLP | **0.429** |
| XGBoost after `GridSearchCV` (10-fold) | XGBoost | 0.403 |
| **Temporal split**: train < 2020, test > 2022 | Lasso (best of 7) | **0.013** |
| Temporal split, also excluding extreme days | RandomForest | 0.072 |
| **10 folds over years** | RandomForest | **−0.37** (mean, MAE 39.7 s) |

Two things to read out of that table:

1. Dropping the 5 % most extreme days (strikes, storms, the incidents the EDA
   identified) roughly doubles R². Those days are real, but they are not
   explained by the weather.
2. Every gain disappears under a **temporal** split. Trained before 2020 and
   tested after 2022, the models sit at R² ≈ 0; averaged over 10 year-folds the
   R² is negative. Weather and calendar do not generalise across time — the
   random-split numbers are optimistic.

The tree models are consistently worse than the mean predictor on the hourly
data (RandomForest ≈ −0.15, DecisionTree ≈ −1.6).

### `aggregated_delay_classification.ipynb`

Same data, framed as classification. Several target definitions were tried:

| Target | Best accuracy | Note |
| --- | --- | --- |
| Above / below the **median** delay, weather only | 0.83 | GradientBoosting / ExtraTrees |
| Above / below the median, calendar only | 0.78 | |
| Above / below the median, all features | 0.86 | GradientBoosting |
| **10 classes** (deciles of the delay) | 0.35 | multi-class is hopeless |
| Late by SNCB's rule (**> 300 s**) | 0.92–0.94 | but the classes are very imbalanced |
| **> 300 s** after down-sampling the majority class | 0.84–0.87 | the honest number |

It also runs three families of feature selection — filter (`SelectKBest` with
`f_regression`), embedded, and wrapper (`RFE`) — which converge on roughly the
same 6–9 features and give a mean accuracy around **0.85**. A
hyperparameter-tuning section and an experiment injecting a synthetic `strike`
flag close the notebook.

A binary "worse than usual" call is doable; the fine-grained delay is not.

---

## B. Delay propagation along a line

All the notebooks below study **one** relation: **Brussel-Zuid (station 159) →
Luxembourg (station 487)**, which has exactly **57 stops**. Trips are
reconstructed by walking `train_data` in `id` order and keeping only the
sequences that visit the 57 expected stops in the expected order.

### `prepare_trip_weather_features.ipynb` — build the modeling table

The shared data-preparation step: each stop of the line is matched to its
**nearest province** by haversine distance to the province centroids, then joined
with that province's hourly weather and with the `type_day` calendar. The other
notebooks in this section repeat this block at the top of their "Data Loading"
cell; this notebook is where it was worked out.

### `line_delay_analysis.ipynb` — EDA on that line

Missing values per column, distribution of arrival and departure delays
(filtered to ±500 s), and the ten stops with the highest median departure delay
among those seen more than 10 000 times. This justifies the choices made in the
others.

### `predict_remaining_stops.ipynb` — predict all remaining stops from the first one

One example per trip: features taken at **stop 1**, targets = the arrival delay
at **stops 2 → 55** at once (`MultiOutputRegressor`), plus 5-fold cross-validated
per-stop R² curves.

| Features | Model | Overall R² |
| --- | --- | --- |
| delay only (2 columns) | LinearRegression | 0.394 |
| delay only | RandomForest | 0.353 |
| delay only, tuned | RandomForest | 0.453 |
| full 21 columns (delay, planned times, coordinates, calendar, weather) | GradientBoosting | **0.51 – 0.55** |

"Static" because everything is known when the train leaves: the model never sees
what happens later in the trip.

### `predict_stops_ahead.ipynb` — predict *q* stops ahead

Given the delay observed at the current stop, how well can we predict the delay
**q** stops further? Each horizon is evaluated with 5-fold cross-validation and
plotted with a ±1 standard-deviation band, for q = 1, 5, 10 and 20.

- **q = 1**: R² above **0.9** for almost every stop (0.85 – 0.99).
- **q = 10**, **q = 20**: accuracy degrades steadily as the horizon grows.
- **Naive baseline** (carry the current delay forward unchanged): mean R² of
  **−5362** across the 56 targets, with a worst case near −295 000. It happens to
  be near-perfect on one stop (0.998) and catastrophic elsewhere — which is
  exactly why the learned models are worth having.

This is the clearest result of the project: a delay is very persistent in the
short term and washes out over distance.

### `chained_delay_prediction.ipynb` — chain the predictions

Instead of predicting each stop independently, feed each prediction into the next
(`RegressorChain`), so the model uses its own output as it moves along the line.
A PyTorch MLP (ReLU + dropout, MSE loss, 60 epochs with LR decay) is compared
against it.

| Model | Overall R² | RMSE (s) |
| --- | --- | --- |
| GradientBoosting chain, full features | **0.446** | 291.9 |
| PyTorch MLP | 0.415 | 308.2 |
| GradientBoosting chain, 2 features only | 0.411 | 303.5 |
| LinearRegression chain | 0.382 | 309.7 |

The per-stop breakdown shows the decay clearly: R² = 0.97 at stop 2, 0.68 at
stop 10, 0.51 at stop 20, 0.32 at stop 35, 0.22 at stop 55. Chaining does not
beat the static multi-output model — errors accumulate along the chain roughly as
fast as the extra information helps.

### `recurrent_delay_prediction.ipynb` — sequence model *(exploratory, not finished)*

Reshapes the data into `(trips, 57 stops, 23 features)` and trains a PyTorch
`RecurrentDelayModel` (2 layers, hidden size = 2 × features, L1 loss, Adam, 3 epochs) to
predict the delay at a target stop from the first `input_length` stops.

**The notebook has no saved outputs** — it was never run to completion, and no
result from it is used anywhere. Treat it as a starting point, not a result.

---

## Figures

`figures/` holds the plots exported from these notebooks: `correlation.png`,
`lasso.png`, `ridge.png`, `output.png` and the `sample*.png` prediction-vs-truth
scatter plots.
