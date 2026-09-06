---
title: References
description: Publications this project sits on. Models and methods that run in the tool, plus related papers. APA and BibTeX.
permalink: /references/
date: 2026-09-06
type: article
---

# References

To cite **this** software or a laptop score, use [Cite]({{ '/cite/' | relative_url }}).
This page is the other direction: the publications the design and
the measurements sit on.

None of these papers is a hidden dependency. The helper is original
code. The models below are the weights the commands actually call.
The rest is related work: same problem, different ruler.

Collected 6 Sep 2026 from the papers, not from a second-hand summary.

<nav class="toc" aria-label="On this page">
<p>On this page</p>
<ol>
  <li><a href="#what-the-tool-runs">What the tool runs</a></li>
  <li><a href="#the-helper">The helper</a></li>
  <li><a href="#repair-and-oracles">Repair and oracles</a></li>
  <li><a href="#the-fields-ruler">The field’s ruler</a></li>
  <li><a href="#small-models">Small models</a></li>
  <li><a href="#bibtex">BibTeX</a></li>
</ol>
</nav>

## What the tool runs

Daily `ask` / `run` uses Ollama `llama3.1:8b`. The 0.5B style prior
and the exact-stdout eval use Qwen2.5-Coder. The adapter method is LoRA.

Grattafiori, A., et al. (2024). *The Llama 3 herd of models*.
<https://arxiv.org/abs/2407.21783>

Hui, B., Yang, J., Cui, Z., Yang, J., Liu, D., Zhang, L., Liu, T.,
Zhang, J., Yu, B., Dang, K., et al. (2024). *Qwen2.5-Coder technical
report*.
<https://arxiv.org/abs/2409.12186>

Hu, E. J., Shen, Y., Wallis, P., Allen-Zhu, Z., Li, Y., Wang, S.,
Wang, L., & Chen, W. (2022). LoRA: Low-rank adaptation of large
language models. *ICLR*.
<https://arxiv.org/abs/2106.09685>

The 0.5B files on the Hub are a style prior. They are not a daily
agent. Scores: [Which model]({{ '/investigations/which-model/' | relative_url }}) ·
[0.5B exact stdout]({{ '/investigations/held-out-exec-eval/' | relative_url }}).

## The helper

The loop is one `Action:` block, then tools. That is a tight
read-act loop, not a free shell.

Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., &
Cao, Y. (2023). ReAct: Synergizing reasoning and acting in language
models. *ICLR*.
<https://arxiv.org/abs/2210.03629>

Yang, J., Jimenez, C. E., Wettig, A., Lieret, K., Yao, S.,
Narasimhan, K., & Press, O. (2024). SWE-agent: Agent-computer
interfaces enable automated software engineering. *NeurIPS*.
<https://arxiv.org/abs/2405.15793>

Same model, better interface: about 3.8% (retrieval only) to 12.5%
resolved on SWE-bench. python-vibe’s first-run four jobs were **0 / 4**
then **4 / 4** after the helper. Same shape, smaller tree.
[First-run four]({{ '/investigations/first-run-four/' | relative_url }}).

Wang, X., Chen, Y., Yuan, L., Zhang, Y., Li, Y., Peng, H., & Ji, H.
(2024). Executable code actions elicit better LLM agents. *ICML*.
<https://arxiv.org/abs/2402.01030>

That paper lets the model emit Python as the action. This project
does the opposite: named actions, a write limit, no general shell.
A 2026 ablation says the tool surface is load-bearing
(<https://arxiv.org/abs/2607.10569>).

Later benches treat the helper as a variable, not a footnote.

Yao, Y., Tan, X., Liu, C.-H., Li, Y., Wang, Z., Yu, W., Tan, Z.,
Tian, Y., Zhao, G., Sun, L., Zhang, X., & Yang, T. (2026).
Harness-Bench: Measuring harness effects across models in
realistic agent workflows.
<https://arxiv.org/abs/2605.27922>

Claw-SWE-Bench (2026). Same backbone: thin adapter 19.1% Pass@1,
full adapter 73.4%. Helper sweep 27.4 points, model sweep 29.4.
<https://arxiv.org/abs/2606.12344>

## Repair and oracles

`run` writes, then runs the tests, then may send **one** traceback
back. A green suite that never called the bug is not done.

Shinn, N., Cassano, F., Gopinath, A., Narasimhan, K., & Yao, S.
(2023). Reflexion: Language agents with verbal reinforcement
learning. *NeurIPS*.
<https://arxiv.org/abs/2303.11366>

Liu, J., Xia, C. S., Wang, Y., & Zhang, L. (2023). Is your code
generated really correct? Rigorous evaluation of neural code
generation. *NeurIPS* (EvalPlus / HumanEval+).
<https://arxiv.org/abs/2305.01210>

McAndrews, C. J. (2026). Feedback over form: Why execution
feedback matters more than pipeline topology in 1–3B code
generation. Laptop study: generate, run, refine. Fixes
`NameError` and `SyntaxError`. Rarely fixes logic errors.
<https://arxiv.org/abs/2604.21950>

Perry, N., Srivastava, M., Kumar, D., & Boneh, D. (2023). Do users
write more insecure code with AI assistants? *CCS*.
<https://arxiv.org/abs/2211.03622>

## The field’s ruler

Jimenez, C. E., Yang, J., Wettig, A., Yao, S., Pei, K., Press, O.,
& Narasimhan, K. (2024). SWE-bench: Can language models resolve
real-world GitHub issues? *ICLR* (oral).
<https://arxiv.org/abs/2310.06770>

This project does **not** report a SWE-bench score. The public
numbers are four jobs on `demo/orders` and a 4,580-file write rate
of **1 / 12**. SWE-bench is the field’s ruler. It is the wrong
ruler for a one-folder laptop helper.

Related later benches (not run here):

- SWE-Bench Pro — <https://arxiv.org/abs/2509.16941>
- SWE-PolyBench — <https://arxiv.org/abs/2504.08703>
  (Python-only benches overstate a multi-language agent; this
  tool is Python-only on purpose.)

## Small models

Belcak, P., Heinrich, G., Diao, S., Fu, Y., Dong, X.,
Muralidharan, S., Lin, Y. C., & Molchanov, P. (2025). Small
language models are the future of agentic AI.
<https://arxiv.org/abs/2506.02153>

Agrees at 7–8B. Does not claim a 0.5B style adapter is an agent.
Laptop split: 8B **9 / 9** daily; 0.5B vibe **0 / 4**; greedy LoRA
**0 / 54**.

SWE-Protégé (2026). A 7B coder plus SWE-agent plus rare expert
calls: 42.4% Pass@1 on SWE-bench Verified.
<https://arxiv.org/abs/2602.22124>

That is a different job: train a 7B to ask a larger model. Daily
python-vibe stays on one local 8B.

Lee, W., Cho, J., & Choi, J. (2026). MapCoder-Lite: Distilling
multi-agent coding into a single small LLM. *Findings of EACL*.
Agent-wise LoRA on a **7B**, not a 0.5B.
<https://aclanthology.org/2026.findings-eacl.346/>
<https://arxiv.org/abs/2509.17489>

Survey of small models in agent systems:
<https://arxiv.org/abs/2510.03847>.

## BibTeX

```bibtex
@article{grattafiori2024llama3,
  title = {The Llama 3 Herd of Models},
  author = {Grattafiori, Aaron and others},
  year = {2024},
  eprint = {2407.21783},
  archivePrefix = {arXiv}
}

@article{hui2024qwen25coder,
  title = {Qwen2.5-Coder Technical Report},
  author = {Hui, Binyuan and Yang, Jian and Cui, Zeyu and others},
  year = {2024},
  eprint = {2409.12186},
  archivePrefix = {arXiv}
}

@inproceedings{hu2022lora,
  title = {{LoRA}: Low-Rank Adaptation of Large Language Models},
  author = {Hu, Edward J. and Shen, Yelong and Wallis, Phillip and Allen-Zhu, Zeyuan and Li, Yuanzhi and Wang, Shean and Wang, Lu and Chen, Weizhu},
  booktitle = {ICLR},
  year = {2022},
  eprint = {2106.09685},
  archivePrefix = {arXiv}
}

@inproceedings{yao2023react,
  title = {{ReAct}: Synergizing Reasoning and Acting in Language Models},
  author = {Yao, Shunyu and Zhao, Jeffrey and Yu, Dian and Du, Nan and Shafran, Izhak and Narasimhan, Karthik and Cao, Yuan},
  booktitle = {ICLR},
  year = {2023},
  eprint = {2210.03629},
  archivePrefix = {arXiv}
}

@inproceedings{yang2024sweagent,
  title = {{SWE}-agent: Agent-Computer Interfaces Enable Automated Software Engineering},
  author = {Yang, John and Jimenez, Carlos E. and Wettig, Alexander and Lieret, Kilian and Yao, Shunyu and Narasimhan, Karthik and Press, Ofir},
  booktitle = {NeurIPS},
  year = {2024},
  eprint = {2405.15793},
  archivePrefix = {arXiv}
}

@inproceedings{jimenez2024swebench,
  title = {{SWE}-bench: Can Language Models Resolve Real-World GitHub Issues?},
  author = {Jimenez, Carlos E. and Yang, John and Wettig, Alexander and Yao, Shunyu and Pei, Kexin and Press, Ofir and Narasimhan, Karthik},
  booktitle = {ICLR},
  year = {2024},
  eprint = {2310.06770},
  archivePrefix = {arXiv}
}

@inproceedings{liu2023evalplus,
  title = {Is Your Code Generated Really Correct? Rigorous Evaluation of Neural Code Generation},
  author = {Liu, Jiawei and Xia, Chunqiu Steven and Wang, Yixuan and Zhang, Lingming},
  booktitle = {NeurIPS},
  year = {2023},
  eprint = {2305.01210},
  archivePrefix = {arXiv},
  note = {EvalPlus / HumanEval+}
}

@inproceedings{shinn2023reflexion,
  title = {Reflexion: Language Agents with Verbal Reinforcement Learning},
  author = {Shinn, Noah and Cassano, Federico and Gopinath, Ashwin and Narasimhan, Karthik and Yao, Shunyu},
  booktitle = {NeurIPS},
  year = {2023},
  eprint = {2303.11366},
  archivePrefix = {arXiv}
}

@inproceedings{perry2023insecure,
  title = {Do Users Write More Insecure Code with {AI} Assistants?},
  author = {Perry, Neil and Srivastava, Megha and Kumar, Deepak and Boneh, Dan},
  booktitle = {CCS},
  year = {2023},
  eprint = {2211.03622},
  archivePrefix = {arXiv}
}

@misc{belcak2025slm,
  title = {Small Language Models are the Future of Agentic {AI}},
  author = {Belcak, Peter and Heinrich, Greg and Diao, Shizhe and Fu, Yonggan and Dong, Xin and Muralidharan, Saurav and Lin, Yingyan Celine and Molchanov, Pavlo},
  year = {2025},
  eprint = {2506.02153},
  archivePrefix = {arXiv}
}

@inproceedings{wang2024codeact,
  title = {Executable Code Actions Elicit Better {LLM} Agents},
  author = {Wang, Xingyao and Chen, Yangyi and Yuan, Lifan and Zhang, Yizhe and Li, Yunzhu and Peng, Hao and Ji, Heng},
  booktitle = {ICML},
  year = {2024},
  eprint = {2402.01030},
  archivePrefix = {arXiv}
}

@article{mcandrews2026feedback,
  title = {Feedback Over Form: Why Execution Feedback Matters More Than Pipeline Topology in 1--3{B} Code Generation},
  author = {McAndrews, Charles Junichi},
  year = {2026},
  eprint = {2604.21950},
  archivePrefix = {arXiv}
}

@inproceedings{lee2026mapcoderlite,
  title = {{MapCoder}-Lite: Distilling Multi-Agent Coding into a Single Small {LLM}},
  author = {Lee, Woongkyu and Cho, Junhee and Choi, Jungwook},
  booktitle = {Findings of EACL},
  year = {2026},
  url = {https://aclanthology.org/2026.findings-eacl.346/},
  eprint = {2509.17489},
  archivePrefix = {arXiv}
}

@article{yao2026harnessbench,
  title = {Harness-Bench: Measuring Harness Effects across Models in Realistic Agent Workflows},
  author = {Yao, Yilun and Tan, Xinyu and Liu, Chao-Hsuan and others},
  year = {2026},
  eprint = {2605.27922},
  archivePrefix = {arXiv}
}
```

How to cite python-vibe itself: [Cite]({{ '/cite/' | relative_url }}).
The measured scores: [Results]({{ '/investigations/' | relative_url }}).
