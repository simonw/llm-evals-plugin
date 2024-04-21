from pluggy import HookspecMarker

hookspec = HookspecMarker("llm")


@hookspec
def register_eval_checks():
    "Register additional eval check functions"
