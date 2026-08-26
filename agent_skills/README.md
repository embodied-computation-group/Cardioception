# Agent skills

Skills for AI coding agents (Claude Code and compatible tools) working with Heart Rate
Discrimination Task data.

> **Use with extreme caution.**
>
> These are convenience utilities, provided with no guarantee of any kind. They encode
> how we currently analyse HRD data; they are not validated software, they are not a
> substitute for understanding the models, and they can be wrong or go out of date.
>
> Use them with extreme caution. An agent following one of these skills will produce
> model code and numbers that look authoritative. **You remain responsible for every
> analysis decision and every result you report.** Read the model specification, check
> the priors against your design, inspect the diagnostics yourself, and never publish a
> fit you have not personally verified.

## What is here

| Skill | Use it for |
|---|---|
| `hrd-psychophysics/` | Fitting the psychometric function: threshold, slope and lapse rate, and testing effects on them |
| `hrd-metacognition/` | Modelling confidence ratings, and the relationship between confidence and accuracy |

They are deliberately separate. Perception and metacognition answer different questions,
take different models and different data preparation, and an effect can appear in one
with the other unchanged. Keeping them apart makes it harder to conflate the two.

## Installing

Copy a skill directory into your agent's skills location. For Claude Code:

```bash
cp -r agent_skills/hrd-psychophysics ~/.claude/skills/
cp -r agent_skills/hrd-metacognition ~/.claude/skills/
```

The agent picks them up from the `description` field in each `SKILL.md` frontmatter,
so no further configuration is needed.

## What they assume

Both assume R with brms and a working Stan backend, and data from the Heart Rate
Discrimination task in Cardioception, or in the same shape. The models themselves come
from the [Hierarchical Interoception toolbox](https://github.com/embodied-computation-group/Hierarchical-Interoception),
described in [Courtin et al. (2026)](https://doi.org/10.3758/s13428-026-03137-3). Cite
that paper for the models, and Cardioception for the data collection.

Fitting these models takes hours, not minutes. Neither skill can make that faster.
