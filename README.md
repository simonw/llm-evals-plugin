# llm-evals-plugin

[![PyPI](https://img.shields.io/pypi/v/llm-evals-plugin.svg)](https://pypi.org/project/llm-evals-plugin/)
[![Changelog](https://img.shields.io/github/v/release/simonw/llm-evals-plugin?include_prereleases&label=changelog)](https://github.com/simonw/llm-evals-plugin/releases)
[![Tests](https://github.com/simonw/llm-evals-plugin/actions/workflows/test.yml/badge.svg)](https://github.com/simonw/llm-evals-plugin/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/simonw/llm-evals-plugin/blob/main/LICENSE)

Run evals against prompts using LLM

**Very early alpha**: everything is likely to change.

## Installation

Install this plugin in the same environment as [LLM](https://llm.datasette.io/).

```bash
llm install llm-evals-plugin
```

## Usage

This plugin adds the `llm evals` subcommand.

Evaluations are stored as yaml files. Here is a simple one:

```yaml
ev: 0.1
name: Basic languages

prompts:
  - |
    Return just a single word in the specified language: Apple in Spanish

models:
  - gpt-4o-mini
  - gpt-3.5-turbo

cases:
  - name: Apple in Spanish
    checks:
      - iexact: manzana
      - notcontains: apple
```

If you save that as `simple.yml` (and have an OpenAI key [properly set up](https://llm.datasette.io/en/stable/setup.html#api-key-management)), run it:

```bash
llm evals run simple.yml
```

`llm` will run each prompt-model-case combination and aggregate the results.

Running the same eval again will be much faster -- all responses are stored in the `llm` database so they can be reused. You can specify a different database:

```bash
llm evals run simple.yml -d simple.db
```

Each evaluation run will output two csv files for analysis:

- `aggregate.csv`: Topline accuracy for each prompt-model combination
- `results.csv`: One row per prompt-model-case-check combination for inspecting specific results

## Development

To set up this plugin locally, first checkout the code. Then create a new virtual environment:

```bash
cd llm-evals-plugin
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
