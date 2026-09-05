---
title: Cite
description: How to cite python-vibe and the laptop measurements. APA, BibTeX, and the CITATION.cff GitHub uses.
permalink: /cite/
date: 2026-09-05
type: article
---

# Cite

If you use the software or quote a measured score, cite **Yauhen Bichel**
and python-vibe. GitHub also offers **Cite this repository** from
[`CITATION.cff`](https://github.com/YauhenBichel/python-vibe/blob/HEAD/CITATION.cff).

Site: [yauhenbichel.github.io/python-vibe](https://yauhenbichel.github.io/python-vibe/).
Code: [github.com/YauhenBichel/python-vibe](https://github.com/YauhenBichel/python-vibe).

<nav class="toc" aria-label="On this page">
<p>On this page</p>
<ol>
  <li><a href="#software">Software</a></li>
  <li><a href="#this-measurement">This measurement</a></li>
  <li><a href="#sample-and-run">Sample-and-run</a></li>
  <li><a href="#bibtex">BibTeX</a></li>
</ol>
</nav>

## Software

Bichel, Y. (2026). *python-vibe* [Computer software].
<https://github.com/YauhenBichel/python-vibe>

## This measurement

Bichel, Y. (2026, September 5). 0.5B exact-stdout eval.
In *python-vibe* experiments.
<https://yauhenbichel.github.io/python-vibe/investigations/held-out-exec-eval/>

Eighteen held-out scripts, three repeats, Ollama `qwen2.5-coder:0.5b`:
**7 / 54** base, **12 / 54** after one traceback repair.

The full table of laptop runs:
[Experiments]({{ '/investigations/experiments/' | relative_url }}).

## Sample-and-run

Bichel, Y. (2026, September 5). 0.5B sample-and-run.
In *python-vibe* experiments.
<https://yauhenbichel.github.io/python-vibe/investigations/sample-and-run/>

Same 18 scripts on MLX Qwen2.5-Coder-0.5B-Instruct-4bit. Four drafts
at temperature 0.7: **6 / 18** base, **9 / 18** with one repair,
**2 / 18** LoRA, **6 / 18** LoRA with repair. Greedy (temperature 0,
three repeats): **2 / 18** unique tasks on base, **3 / 18** with
repair, **0 / 54** LoRA. Later the same day, four drafts plus
`datetime` prepend and an 8B hint: **12 / 18**. Zero of those
twelve were a hint-repair.

## BibTeX

```bibtex
@software{bichel_python_vibe_2026,
  author = {Bichel, Yauhen},
  title = {python-vibe},
  year = {2026},
  url = {https://github.com/YauhenBichel/python-vibe},
  license = {Apache-2.0}
}

@misc{bichel_05b_exec_eval_2026,
  author = {Bichel, Yauhen},
  title = {0.5{B} exact-stdout eval},
  howpublished = {python-vibe experiments},
  year = {2026},
  month = sep,
  day = {5},
  url = {https://yauhenbichel.github.io/python-vibe/investigations/held-out-exec-eval/}
}

@misc{bichel_05b_sample_and_run_2026,
  author = {Bichel, Yauhen},
  title = {0.5{B} sample-and-run},
  howpublished = {python-vibe experiments},
  year = {2026},
  month = sep,
  day = {5},
  url = {https://yauhenbichel.github.io/python-vibe/investigations/sample-and-run/}
}
```
