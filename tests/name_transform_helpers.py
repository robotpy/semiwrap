CALLS = 0


def reset():
    global CALLS
    CALLS = 0


def custom_transform(name, kind):
    global CALLS
    CALLS += 1
    return f"{kind}_{name}"


def returns_non_string(name, kind):
    return 123


not_callable = 5
