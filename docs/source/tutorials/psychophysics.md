# The psychophysical model

What the Heart Rate Discrimination task measures, and how to get it out of the data
for a single participant.

Start with [inspecting and plotting data](inspecting-data.md) if you have not
already: this page assumes the aggregated data frame prepared there.

## What the task produces

On each trial the participant hears tones played at their own heart rate plus or
minus some offset, and judges whether the tones were faster or slower than their
heart. The offset is the stimulus intensity, in ΔBPM, and the staircase moves it
around from trial to trial.

Plotting the proportion of "faster" responses against that intensity gives the
shape the model has to describe:

![Responses against stimulus intensity for one participant](../images/psychometric_example.png)

## Three parameters

The curve is a cumulative normal with a lapse rate:

$$
P(\text{faster}) = \frac{\lambda}{2} + (1-\lambda)\,\Phi\!\left(e^{\beta}(x - \alpha)\right)
$$

where $\lambda$ is on a logit scale in the model. Each parameter answers a
different question, and the reason the HRD exists is that it separates them.

| Parameter | Scale | Question it answers |
|---|---|---|
| `alpha` | ΔBPM | **Where is the curve?** The bias in what the participant believes their heart rate to be. Negative means they judge their heart as slower than it is. |
| `beta` | log | **How steep is it?** `exp(beta)` is the inverse of the psychometric sigma, so **larger `beta` means finer discrimination**. |
| `lambda` | logit | **How much of the data is noise?** `inv_logit(lambda)` is the proportion of trials answered without regard to the stimulus. |

The distinction between `alpha` and `beta` is the whole point. A participant can
be badly wrong about their heart rate while discriminating changes in it very
precisely, and someone else can be unbiased but unable to tell 60 from 75 BPM.
Heartbeat counting scores confound the two; this separates them.

Watch the sign on `beta`. It is a log *slope*, so bigger is better, and it is easy
to describe an improvement backwards.

## The data the model wants

Aggregated binomial: `y` successes out of `n` trials at intensity `x`, per
participant and condition.

```r
model_df <- raw |>
  filter(Decision %in% c("More", "Less")) |>
  mutate(resp = as.integer(Decision == "More")) |>
  group_by(subj = Subject, condition = Modality, x = Alpha) |>
  summarise(y = sum(resp), n = dplyr::n(), .groups = "drop")
```

With a Psi staircase almost every intensity is visited once, so `n` is usually 1.
That is expected. Do not bin `x` to make `n` larger: the staircase spent the whole
session choosing those intensities, and binning throws that away.

Check the direction of the coding before fitting. `y` must count responses in the
direction that increases with `x`; if the fitted curve comes out running downhill,
this is why.

## One participant

```r
library(brms)
inv_logit <- function(x) 1 / (1 + exp(-x))

bff <- bf(
  y | trials(n) ~ inv_logit(lambda) / 2 +
    (1 - inv_logit(lambda)) * (0.5 + 0.5 * erf(exp(beta) * (x - alpha) / sqrt(2))),
  alpha ~ 1, beta ~ 1, lambda ~ 1,
  nl = TRUE,
  family = binomial(link = "identity")
)

fit_one <- brm(
  bff,
  data = filter(model_df, subj == "sub-0019", condition == "Intero"),
  prior = c(
    set_prior("normal(-8.67, 11.23)", class = "b", nlpar = "alpha", coef = "Intercept"),
    set_prior("normal(-2.3, 0.34)",   class = "b", nlpar = "beta",  coef = "Intercept"),
    set_prior("normal(-4.32, 1.96)",  class = "b", nlpar = "lambda")
  ),
  chains = 4, cores = 4, backend = "cmdstanr"
)
```

Those priors are not arbitrary. They come from a population refit reported in
[Courtin et al. (2026)](https://doi.org/10.3758/s13428-026-03137-3): a mean
threshold near -8.7 ΔBPM with a between-subject SD of 11.23, and a lapse rate
around 1.3%. They carry real information, which matters most for the slope, since
the staircase leaves few trials in the tails to constrain it.

## Why you should not stop here

Fitting participants one at a time is the obvious thing to do and it is not what we
recommend. Two reasons.

The staircase concentrates trials near each person's threshold, so there is little
data far from it and the slope is poorly determined. Individual slope estimates are
noisy, sometimes wildly so.

Worse, taking those point estimates into a second-stage t-test or regression
throws away how uncertain each one was. A participant whose slope is barely
identified counts exactly as much as one with a clean fit.

Fitting everyone in one model solves both, and that is the
[next tutorial](hierarchical.md).

## Do not analyse the online estimates

The task writes `EstimatedThreshold` and `EstimatedSlope` on every row. These are
the Psi algorithm's running estimates, used to decide what to present next. They
are useful for checking that a session behaved, and they are not an analysis.
Using them as a dependent variable discards the trial-level data and its
uncertainty in one step.
