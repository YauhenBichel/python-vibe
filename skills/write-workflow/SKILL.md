---
name: write-workflow
description: Adds one workflow YAML that runs the unit test suite. Use when the task is CI, pipeline, or workflow. Do not use for questions or one Python function.
---

One YAML file. Run `python -m unittest discover -s tests -q`. No curl. No 0.0.0.0. No secrets.

Action: edit
Path: .github/workflows/tests.yml
name: tests
on:
  pull_request:
  push:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: python -m unittest discover -s tests -q
