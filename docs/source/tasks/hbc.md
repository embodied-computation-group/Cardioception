---
myst:
  html_meta:
    description: "The Heartbeat Counting task in Cardioception: procedure, the Hart et al. accuracy score, default schedule and versions."
    keywords: "heartbeat counting task, heartbeat tracking, Schandry, interoceptive accuracy, cardioception"
---

# Heartbeat Counting task

**The Heartbeat Counting task** {cite:p}`1981:schandry,1978:dale` asks participants to attend to their heartbeats over intervals of various lengths and count the beats they feel. An accuracy score compares the reported number with the true number, following Hart et al. {cite:p}`2013:hart`:

```{math}
   Accuracy = 1-\frac{\left | N_{real} - N_{reported} \right |}{\frac{N_{real} + N_{reported}}{2}}
```

By default the task runs 6 counting trials (25, 30, 35, 40, 45 and 50 s) in randomised order; the `'Training'` condition exists in the parameters but is not scheduled by default. Trial length, condition (`'Rest'`, `'Count'`, `'Training'`) and randomisation are set in the parameters dictionary; the version is selected with `"taskVersion"`. With the default settings the task takes about 4 minutes. We keep this task because much of the literature rests on it. [Theory](index.md#what-heartbeat-counting-can-establish) explains what a counting score can and cannot establish.
