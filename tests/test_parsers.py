import csv
import textwrap
import yaml
from llm_evals.parsers import parse_prompts, parse_models, parse_cases
from llm_evals.models import Case, Check, Model, Prompt


class TestParsePrompts:
    def test_base(self):
        yaml_str = textwrap.dedent(
            """
            prompts: "Return just a single word in the specified language: Apple in Spanish"
        """
        )
        actual = parse_prompts(yaml.safe_load(yaml_str)["prompts"])

        assert len(actual) == 1
        assert len(actual[0]) == 1
        assert isinstance(actual[0][0], Prompt)
        assert actual[0][0].type == "user"

    def test_base_list(self):
        yaml_str = textwrap.dedent(
            """
            prompts:
              - "Return just a single word in the specified language: Apple in Spanish"
        """
        )
        actual = parse_prompts(yaml.safe_load(yaml_str)["prompts"])

        assert len(actual) == 1
        assert len(actual[0]) == 1
        assert isinstance(actual[0][0], Prompt)
        assert actual[0][0].type == "user"

    def test_base_list_multiple(self):
        yaml_str = textwrap.dedent(
            """
            prompts:
              - "Return just a single word in the specified language: Apple in Spanish"
              - "Translate: Apple in Spanish"
        """
        )
        actual = parse_prompts(yaml.safe_load(yaml_str)["prompts"])

        assert len(actual) == 2
        assert len(actual[0]) == 1
        assert isinstance(actual[0][0], Prompt)
        assert actual[0][0].type == "user"

    def test_system_simplified(self):
        """When prompts is an array of objects"""
        yaml_str = textwrap.dedent(
            """
            prompts:
              - type: system
                text: Return just a single word in the specified language
              - type: user
                text: Apple in Spanish
        """
        )
        actual = parse_prompts(yaml.safe_load(yaml_str)["prompts"])

        assert len(actual) == 1
        assert len(actual[0]) == 2
        assert isinstance(actual[0][0], Prompt)
        assert actual[0][0].type == "system"

    def test_system_prompt_verbose(self):
        """When prompts is an array of arrays of objects"""
        yaml_str = textwrap.dedent(
            """
            prompts:
              - - type: system
                  text: Return just a single word in the specified language
                - type: user
                  text: Apple in Spanish
        """
        )
        actual = parse_prompts(yaml.safe_load(yaml_str)["prompts"])

        assert len(actual) == 1
        assert len(actual[0]) == 2
        assert isinstance(actual[0][0], Prompt)
        assert actual[0][0].type == "system"

    def test_few_shot(self):
        yaml_str = textwrap.dedent(
            """
            prompts:
              - - type: system
                  text: Return just a single word in the specified language
                - type: user
                  text: Orange in Spanish
                - type: system
                  text: naranja
                - type: user
                  text: Apple in Spanish
        """
        )
        actual = parse_prompts(yaml.safe_load(yaml_str)["prompts"])

        assert len(actual) == 1
        assert len(actual[0]) == 4
        assert isinstance(actual[0][0], Prompt)
        assert actual[0][0].type == "system"

    def test_compare_basic_few_shot(self):
        """Multiple prompt versions"""
        yaml_str = textwrap.dedent(
            """
            prompts:
              - "Return just a single word in the specified language: Apple in Spanish"
              - - type: system
                  text: Return just a single word in the specified language
                - type: user
                  text: Orange in Spanish
                - type: system
                  text: naranja
                - type: user
                  text: Apple in Spanish
        """
        )
        actual = parse_prompts(yaml.safe_load(yaml_str)["prompts"])

        assert len(actual) == 2
        assert len(actual[0]) == 1
        assert len(actual[1]) == 4
        assert isinstance(actual[0][0], Prompt)
        assert isinstance(actual[1][0], Prompt)
        assert actual[0][0].type == "user"
        assert actual[1][0].type == "system"


class TestParseModels:
    def test_single_string(self):
        yaml_str = textwrap.dedent(
            """
            models: "gpt-4o-mini"
        """
        )
        actual = parse_models(yaml.safe_load(yaml_str)["models"])

        assert len(actual) == 1
        assert isinstance(actual[0], Model)
        assert actual[0].name == "gpt-4o-mini"
        assert actual[0].options == {}

    def test_array_of_strings(self):
        yaml_str = textwrap.dedent(
            """
            models:
              - "gpt-4o-mini"
              - "gpt-3.5-turbo"
              - "claude-3-sonnet"
        """
        )
        actual = parse_models(yaml.safe_load(yaml_str)["models"])

        assert len(actual) == 3
        assert isinstance(actual[0], Model)
        assert isinstance(actual[1], Model)
        assert isinstance(actual[2], Model)
        assert actual[0].name == "gpt-4o-mini"
        assert actual[1].name == "gpt-3.5-turbo"
        assert actual[2].name == "claude-3-sonnet"
        assert actual[0].options == {}
        assert actual[1].options == {}
        assert actual[2].options == {}

    def test_array_of_objects(self):
        yaml_str = textwrap.dedent(
            """
            models:
              - name: "gpt-4o-mini"
              - name: "gpt-3.5-turbo"
                options:
                  temperature: 0.7
              - name: "claude-3-sonnet"
                options:
                  temperature: 0.5
                  max_tokens: 1000
        """
        )
        actual = parse_models(yaml.safe_load(yaml_str)["models"])

        assert len(actual) == 3
        assert isinstance(actual[0], Model)
        assert isinstance(actual[1], Model)
        assert isinstance(actual[2], Model)
        assert actual[0].name == "gpt-4o-mini"
        assert actual[1].name == "gpt-3.5-turbo"
        assert actual[2].name == "claude-3-sonnet"
        assert actual[0].options == {}
        assert actual[1].options == {"temperature": 0.7}
        assert actual[2].options == {"temperature": 0.5, "max_tokens": 1000}

    def test_mixed_formats(self):
        yaml_str = textwrap.dedent(
            """
            models:
              - "gpt-4o-mini"
              - name: "gpt-3.5-turbo"
                options:
                  temperature: 0.7
        """
        )
        actual = parse_models(yaml.safe_load(yaml_str)["models"])

        assert len(actual) == 2
        assert isinstance(actual[0], Model)
        assert isinstance(actual[1], Model)
        assert actual[0].name == "gpt-4o-mini"
        assert actual[1].name == "gpt-3.5-turbo"
        assert actual[0].options == {}
        assert actual[1].options == {"temperature": 0.7}

    def test_string_with_options(self):
        yaml_str = textwrap.dedent(
            """
            models:
              - name: "gpt-4o-mini"
                options:
                  temperature: 0
                  top_p: 1
                  max_tokens: 4096
        """
        )
        actual = parse_models(yaml.safe_load(yaml_str)["models"])

        assert len(actual) == 1
        assert isinstance(actual[0], Model)
        assert actual[0].name == "gpt-4o-mini"
        assert actual[0].options == {"temperature": 0, "top_p": 1, "max_tokens": 4096}

    def test_empty_models(self):
        yaml_str = textwrap.dedent(
            """
            models: []
        """
        )
        actual = parse_models(yaml.safe_load(yaml_str)["models"])

        assert len(actual) == 0


class TestParseCases:
    def test_single_case(self):
        yaml_str = textwrap.dedent(
            """
            cases:
              - name: Apple in Spanish
                checks:
                  - iexact: manzana
                  - notcontains: apple
        """
        )
        actual = parse_cases(yaml.safe_load(yaml_str)["cases"])

        assert len(actual) == 1
        assert isinstance(actual[0], Case)
        assert actual[0].name == "Apple in Spanish"
        assert len(actual[0].checks) == 2
        assert isinstance(actual[0].checks[0], Check)
        assert actual[0].checks[0].name == "iexact"
        assert actual[0].checks[0].value == "manzana"
        assert isinstance(actual[0].checks[1], Check)
        assert actual[0].checks[1].name == "notcontains"
        assert actual[0].checks[1].value == "apple"

    def test_multiple_cases(self):
        yaml_str = textwrap.dedent(
            """
            cases:
              - name: Apple in Spanish
                checks:
                  - iexact: manzana
                  - notcontains: apple
              - name: Orange in French
                checks:
                  - iexact: orange
                  - notcontains: naranja
        """
        )
        actual = parse_cases(yaml.safe_load(yaml_str)["cases"])

        assert len(actual) == 2
        assert isinstance(actual[0], Case)
        assert isinstance(actual[1], Case)
        assert actual[0].name == "Apple in Spanish"
        assert actual[1].name == "Orange in French"
        assert len(actual[0].checks) == 2
        assert len(actual[1].checks) == 2
        assert actual[1].checks[0].name == "iexact"
        assert actual[1].checks[0].value == "orange"

    def test_case_with_multiple_checks(self):
        yaml_str = textwrap.dedent(
            """
            cases:
              - name: Complex translation
                checks:
                  - iexact: manzana
                  - notcontains: apple
                  - contains: fruit
                  - regex: m[a-z]+a
                  - icontains: MAN
        """
        )
        actual = parse_cases(yaml.safe_load(yaml_str)["cases"])

        assert len(actual) == 1
        assert isinstance(actual[0], Case)
        assert actual[0].name == "Complex translation"
        assert len(actual[0].checks) == 5
        assert actual[0].checks[0].name == "iexact"
        assert actual[0].checks[0].value == "manzana"
        assert actual[0].checks[1].name == "notcontains"
        assert actual[0].checks[1].value == "apple"
        assert actual[0].checks[2].name == "contains"
        assert actual[0].checks[2].value == "fruit"
        assert actual[0].checks[3].name == "regex"
        assert actual[0].checks[3].value == "m[a-z]+a"
        assert actual[0].checks[4].name == "icontains"
        assert actual[0].checks[4].value == "MAN"

    def test_case_without_name(self):
        yaml_str = textwrap.dedent(
            """
            cases:
              - checks:
                  - iexact: manzana
                  - notcontains: apple
        """
        )
        actual = parse_cases(yaml.safe_load(yaml_str)["cases"])

        assert len(actual) == 1
        assert isinstance(actual[0], Case)
        assert actual[0].name is None
        assert len(actual[0].checks) == 2

    def test_case_with_inputs(self):
        yaml_str = textwrap.dedent(
            """
            cases:
              - name: Translation with inputs
                inputs:
                  language: "Spanish"
                  word: "Apple"
                checks:
                  - iexact: manzana
        """
        )
        actual = parse_cases(yaml.safe_load(yaml_str)["cases"])

        assert len(actual) == 1
        assert isinstance(actual[0], Case)
        assert actual[0].name == "Translation with inputs"
        assert len(actual[0].checks) == 1
        assert actual[0].inputs == {"language": "Spanish", "word": "Apple"}

    def test_multiple_cases_with_inputs(self):
        yaml_str = textwrap.dedent(
            """
            cases:
              - name: Apple in Spanish
                inputs:
                  language: "Spanish"
                  word: "Apple"
                checks:
                  - iexact: manzana
              - name: Orange in French
                inputs:
                  language: "French"
                  word: "Orange"
                checks:
                  - iexact: orange
        """
        )
        actual = parse_cases(yaml.safe_load(yaml_str)["cases"])

        assert len(actual) == 2
        assert actual[0].inputs == {"language": "Spanish", "word": "Apple"}
        assert actual[1].inputs == {"language": "French", "word": "Orange"}

    def test_csv(self, tmpdir):
        with open(tmpdir / "cases.csv", "w") as f:
            writer = csv.writer(f)
            writer.writerow(["name", "inputs", "checks"])
            writer.writerow(
                [
                    "Apple in Spanish",
                    "",
                    '[{"iexact": "manzana"}, {"notcontains": "apple"}]',
                ]
            )
        yaml_str = textwrap.dedent(
            """
            cases: cases.csv
        """
        )
        actual = parse_cases(yaml.safe_load(yaml_str)["cases"], tmpdir)

        assert len(actual) == 1
        assert isinstance(actual[0], Case)
        assert actual[0].name == "Apple in Spanish"
        assert len(actual[0].checks) == 2
        assert isinstance(actual[0].checks[0], Check)
        assert actual[0].checks[0].name == "iexact"
        assert actual[0].checks[0].value == "manzana"
        assert isinstance(actual[0].checks[1], Check)
        assert actual[0].checks[1].name == "notcontains"
        assert actual[0].checks[1].value == "apple"
