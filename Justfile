# Run tests and linters
@default: test lint

# Run pytest with supplied options
@test *options:
  uv run pytest {{options}}

# Run linters
@lint:
  uvx black . --check
  uvx ruff check

# Apply Black
@black:
  uvx black .

# Apply ruff
@ruff:
  uvx ruff check --fix

# Auto-format and fix things
@fix: black ruff
