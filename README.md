# Home Internet Fault Diagnosis

##**If you want to see a COMMIT history view the other Github link.**

This is my full COM6008 Coursework 1 project repository. It is a Python command-line expert system that guides a householder through basic broadband checks and helps narrow down possible fault areas. It asks about the type of connection, which devices are affected, Ethernet and Wi-Fi results, equipment indicators and provider status. It then uses frames and IF-THEN rules to suggest possible explanations and next steps. The results are guidance based on the answers, not confirmed engineering diagnoses.

## How it works

The questions are asked in a fixed order, with checks skipped when they do not apply. The answers are stored in five frames covering the router, fibre box, separate modem, user device and household connection.

The rule base contains 23 rules. Four derive intermediate facts and 19 suggest possible diagnoses. The system keeps unknown answers separate from negative answers, so an unanswered or uncertain observation is not treated as evidence that something is working or faulty. It reports every diagnosis supported by the answers rather than ranking the results or assigning confidence scores.

## Project folders

- `src/` contains the expert-system code, including the questions, frames, rules, inference engine, explanations and command-line interface.
- `tests/` contains the automated tests and regression tests.
- `scripts/` contains the source traceability audit, forum-case evaluation and eight-puzzle search experiment.
- `cases/` contains the forum cases and worked scenarios used by the project.
- `knowledge/` contains the extracted evidence and source register.
- `history/` contains the earlier R06 rule definitions used by a regression test.
- `results/` contains the saved forum-evaluation and search-experiment results. The forum evaluation and search experiment scripts generate these files.

## Running the project

```bash
python3 -m src.cli
```

```bash
python3 -m unittest discover -s tests -v
```

## Evaluation notes

The forum evaluation uses 20 public broadband and networking forum threads. The posts describe users' symptoms and their own understanding of the problem. They do not provide independently confirmed engineering diagnoses. The cases were mapped by one reviewer, and only a subset of the diagnostic rules was exercised. The results therefore show agreement with the expected labels used in this project, not the system's real-world diagnostic accuracy. The evaluation also reports a sensitivity result with the inferred answer for case F15 left unknown.

The eight-puzzle experiment is separate from the broadband expert system. It compares breadth-first, uniform-cost, depth-first, A* and greedy search using 50 solvable states. Its results apply to that selected sample and should not be treated as a general ranking of search algorithms.
