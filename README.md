# llm-evals

[![PyPI](https://img.shields.io/pypi/v/llm-evals.svg)](https://pypi.org/project/llm-evals/)
[![Changelog](https://img.shields.io/github/v/release/simonw/llm-evals?include_prereleases&label=changelog)](https://github.com/simonw/llm-evals/releases)
[![Tests](https://github.com/simonw/llm-evals/actions/workflows/test.yml/badge.svg)](https://github.com/simonw/llm-evals/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/simonw/llm-evals/blob/main/LICENSE)

Run evals against prompts using LLM

**Very early alpha**: everything is likely to change.

## Installation

Install this plugin in the same environment as [LLM](https://llm.datasette.io/).
```bash
llm install llm-evals
```
## Usage

See [issue 1](https://github.com/simonw/llm-evals/issues/1).

## Development

To set up this plugin locally, first checkout the code. Then create a new virtual environment:
```bash
cd llm-evals
python3 -m venv venv
source venv/bin/activate
```
Now install the dependencies and test dependencies:
```bash
llm install -e '.[test]'
```
To run the tests:
```bash
pytest
```
