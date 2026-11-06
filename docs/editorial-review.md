# Documentation editorial review

This report accompanies the prose edits on `docs/prose-clarity`, based on the
local `dev` checkout. It records suggestions for a later content review, not a
literature audit. Numerical results and publication claims have not been
independently revalidated. The HRD analysis tutorials, API docstrings, and
historical changelog were outside the prose-editing scope.

The existing reading order is useful: installation, recording devices, session
setup, task comparison, theory, task procedure, and analysis tutorials. The edits
retain that order and the existing heading anchors. They introduce concepts
before implementation details, split paragraphs with several purposes, and
replace compressed or colloquial explanations with direct prose.

## HSD restructuring completed after review

The approved structural edit divides the former HSD design and validation page
into [method and rationale](source/tasks/hsd/design.md) and
[validation and technical details](source/tasks/hsd/validation.md). This implements
the HSD restructuring suggestion below. The methods page follows the measurement
logic; the validation page organizes the results around accuracy, difficult
response patterns, timing variability, detection evidence, and session length.

Both figures remain visible in the main narrative. All original table rows,
figure captions, citation keys, and reproduction commands are retained across
the two pages. Detailed numerical comparisons, implementation history, and
outstanding literature checks are available in expandable sections. The main
reading paths contain approximately 1,640 and 1,790 words, respectively,
excluding those sections.

The distinction between historical marginal estimates and the current
conditional stopping rule is now explicit before the simulation results and
again beside the session-length analysis. The code confirms that the current
simulation records conditional estimates by default. Reproducing the historical
tables requires identifying the original source revision. The meaning of the
small demonstration's interval ranges still needs confirmation.

One further check is needed: the historical simulation description gives upper
delay bounds of 570 to 784 ms for periods of 0.8 to 1.1 s. The current
`TaskConfig.bounds` uses 0.675 of the period, which gives 540 to 742.5 ms.
The original simulation settings and output should be checked before changing
the historical numbers; they have been retained in the technical details.

The rebuilt documentation passed with warnings treated as errors. An additional
check confirmed preservation of the tables, figures, citations, and commands,
and verified local links and anchors on all three HSD pages. Both figures are
outside the collapsed sections.

## Content questions to resolve

| Location | Observation | Suggested follow-up |
|---|---|---|
| [PAT: trial description](source/tasks/pat.md#what-a-trial-looks-like) | The opening explanation says a guessing participant should score near 0.33 at 28 trials. The scoring section and `cardioception/PAT/scoring.py` identify approximately 0.33 as a 95th-percentile threshold. A threshold for rejecting chance is different from the typical score under chance. | Distinguish the expected MRL under random responding from its upper-tail threshold. Verify the numerical description against the scoring simulation before changing it. |
| [PAT: timing](source/tasks/pat.md#timing-and-latency), [HSD: hardware dry run](source/tasks/hsd/design.md#hardware-dry-run), and their output tables | The pages alternate among scheduled time, driver-reported onset, and the physical arrival of sound. Phrases such as “true onset” and “true R-to-tone interval” imply more direct measurement than some later caveats support. | Define the timing quantities once and state which measurements require audio loopback or other calibration. Review the claims against the tone player and bench recordings. |
| [HSD: model](source/tasks/hsd/design.md#the-model) | The current stopping rule uses conditional intervals, but the simulation tables report marginal estimates. The stated 70 to 170 ms and 160 to 420 ms intervals also need an explicit definition: ranges of widths across seeds or interval endpoints. | Confirm the meaning against the saved simulation output and prominently distinguish validation of the current rule from earlier results. |
| [PAT and HSD comparison](source/tasks/index.md#the-pat-and-the-hsd) | The statement that PAT cannot separate location from precision is broad. The task records chosen delays, while the stated limitation concerns what can be inferred from consistency and search behaviour. | Clarify which quantities can be calculated and which perceptual claims those quantities support. Keep the comparison neutral between tasks. |
| [Running a session: random seed](source/getting-started/running-a-session.md#where-the-data-goes) | “Draws the same session again” can be read as a guarantee of full reproducibility despite live physiology, participant responses, and adaptive stimulus selection. | Specify which random choices a seed reproduces, and under what other fixed inputs. |
| [Confidence scales](source/getting-started/running-a-session.md#confidence-scales) and the PAT output table | Rescaling ratings to 0 to 1 provides common numeric bounds but does not establish equivalence between discrete, continuous, and signed scales. The PAT table still suggests that rescaling alone permits pooling. | Add an analysis note explaining scale compatibility and model assumptions. The shared session page now describes the saved information without promising statistical comparability. |
| [HBC: trial description](source/tasks/hbc.md#what-a-trial-looks-like) | The Schandry version has a minute of rest, while the next paragraph describes a 30 s recording before the first window in every version. It is unclear whether these are additional or overlapping periods. | Check the runner and show the complete schedule for each version. |
| [HRD: Psi presets](source/tasks/hrd/index.md#the-main-settings) and output interpretation | The legacy preset is described as directly comparable with published data, but a later paragraph notes a changed heart-rate calculation in version 1.0. | Limit the comparability statement to staircase settings and cross-reference the change in `listenBPM`. |
| [Task overview](source/tasks/index.md) and [HSD procedure](source/tasks/hsd/index.md#what-a-trial-looks-like) | The overview's “60 took 7 minutes” comes from one hardware dry run. Its proximity to other session-duration estimates can make it appear representative. | Label it consistently as a single dry-run observation; revise expected duration once pilot data are available. |
| [Installation](source/getting-started/installation.md) | Release-specific instructions, example installation output, and Python installer recommendations will age independently of prose quality. | Verify them at release time. Keep this separate from the present copy edit. |

## Structure and unnecessary detail

- The HSD design page combines the current model, design history, superseded
  grids, simulation results, hardware measurements, and an implementation roadmap.
  Consider a shorter methods page linked to a separate validation record. Retain
  the historical results there, with a configuration identifier for each run.
- The task overview has a wide comparison table with six task columns, including
  two unimplemented tasks. Consider a compact comparison of the four available
  tasks and a short paragraph linking to planned implementations.
- The PAT page combines participant instructions, a long simulated-participant
  code example, scoring, and detailed latency accounting. The simulation example
  could move to developer documentation, with a link from the task page.
- Several task pages repeat output directory and recording-device explanations
  already covered under Getting started. Short cross-references could reduce
  repetition while preserving task-specific exceptions.
- The HSD warning listing two unverified literature claims interrupts the methods
  narrative. Consider moving it to a research note until the original papers
  have been checked.

## Figures and examples worth adding

- A timing diagram for PAT and HSD could show the R-wave, sample timestamp,
  detector availability, scheduling lead, reported onset, and physical sound
  onset. This would explain the delay floor and latency correction more clearly
  than another paragraph of arithmetic.
- A small HSD model figure could label `mu`, `sigma`, `floor`, and `peak`, with a
  flat response pattern alongside it. A second panel could distinguish the
  marginal and conditional location intervals.
- A minimal HBC scoring example could connect an output pulse file to beat
  detection, the recorded count, and the existing accuracy formula. It should
  make the unit of scoring explicit without implying that a counting score
  isolates heartbeat perception.
- A small manifest and trial-row excerpt on the session page could help readers
  recognize their output files. Use synthetic values and label them as such.

## Validation

The local HTML preview was built from `docs/source` into `docs/build/html`, using
the development channel so the installation instructions match the source
branch. The final build passed with Python 3.10, Sphinx 5.3.0, and warnings
treated as errors:

```powershell
$env:DOCS_CHANNEL = 'dev'
& '.\.venv-docs\Scripts\python.exe' -m sphinx -E -W --keep-going -b html docs/source docs/build/html
```

The first build encountered blocked external inventory downloads and obsolete
generated API pages from a previous local build. The old generated source files
were preserved under `docs/build/generated-before-copyedit`, and Sphinx
regenerated the API pages. The final build had network access for inventories.
No documentation configuration changes were needed.

`git diff --check` passed. A comparison against the branch's starting revision
confirmed that all 13 edited pages preserve their headings, citation markers,
and executable code examples. The analysis tutorials remain unchanged.
