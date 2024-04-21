class Contains:
    name = "contains"

    def __init__(self, text):
        if not isinstance(text, str):
            raise ValueError("text must be a string")
        self.text = text

    def __call__(self, response):
        return self.text in response.text()


class NotContains:
    name = "notcontains"

    def __init__(self, text):
        if not isinstance(text, str):
            raise ValueError("text must be a string")
        self.text = text

    def __call__(self, response):
        return self.text not in response.text()


class Exact:
    name = "exact"

    def __init__(self, text):
        if not isinstance(text, str):
            raise ValueError("text must be a string")
        self.text = text

    def __call__(self, response):
        return self.text == response.text()


class Iexact:
    name = "iexact"

    def __init__(self, text):
        if not isinstance(text, str):
            raise ValueError("text must be a string")
        self.text = text

    def __call__(self, response):
        return self.text.lower() == response.text().lower()


classes = [Contains, NotContains, Exact, Iexact]
