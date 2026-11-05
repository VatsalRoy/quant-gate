"""Templated tool-call and strict-JSON test cases. Fixed seed -> same cases every time."""
import itertools
import random


def _tool(name, desc, props, required):
    return {"type": "function", "function": {
        "name": name, "description": desc,
        "parameters": {"type": "object", "properties": props, "required": required}}}


ALL_TOOLS = [
    _tool("get_weather", "Get the current weather for a city.",
          {"city": {"type": "string", "description": "City name"},
           "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}},
          ["city", "unit"]),
    _tool("convert_currency", "Convert an amount of money between currencies.",
          {"amount": {"type": "number"},
           "from_currency": {"type": "string", "description": "3-letter ISO code, e.g. USD"},
           "to_currency": {"type": "string", "description": "3-letter ISO code, e.g. EUR"}},
          ["amount", "from_currency", "to_currency"]),
    _tool("set_timer", "Start a countdown timer.",
          {"minutes": {"type": "integer"}, "label": {"type": "string"}},
          ["minutes", "label"]),
    _tool("book_table", "Reserve a table at a restaurant.",
          {"restaurant": {"type": "string"},
           "people": {"type": "integer"},
           "time": {"type": "string", "description": "24-hour time, HH:MM"}},
          ["restaurant", "people", "time"]),
    _tool("get_stock_price", "Get the latest price for a stock ticker.",
          {"ticker": {"type": "string", "description": "Uppercase ticker symbol"}},
          ["ticker"]),
]

SYSTEM_TOOL = "You are a helpful assistant. Use a tool when one fits the request."
SYSTEM_JSON = "You are a precise data-extraction assistant."


# ---- tool-call templates: yield (prompt, function_name, expected_arguments) ----
def _weather():
    for city, unit in itertools.product(
            ["Paris", "Tokyo", "Nairobi", "Lima", "Oslo", "Toronto", "Mumbai", "Sydney"],
            ["celsius", "fahrenheit"]):
        yield (f"What's the weather in {city} right now? Give it to me in {unit}.",
               "get_weather", {"city": city, "unit": unit})


def _currency():
    for amt, (a, b) in itertools.product(
            [25.0, 120.0, 99.5, 1000.0, 42.0],
            [("USD", "EUR"), ("GBP", "JPY"), ("INR", "USD"), ("CAD", "MXN")]):
        yield (f"How much is {amt:g} {a} in {b}?",
               "convert_currency", {"amount": amt, "from_currency": a, "to_currency": b})


def _timer():
    for m, label in itertools.product([5, 12, 25, 45, 90],
                                      ["pasta", "laundry", "study break", "tea", "oven"]):
        yield (f"Set a {m}-minute timer called '{label}'.",
               "set_timer", {"minutes": m, "label": label})


def _booking():
    for r, n, (t_text, t) in itertools.product(
            ["Luigi's", "Blue Lotus", "The Grill House", "Sakura"], [2, 4, 6],
            [("7pm", "19:00"), ("8:30pm", "20:30"), ("noon", "12:00")]):
        yield (f"Book a table for {n} at {r} at {t_text}.",
               "book_table", {"restaurant": r, "people": n, "time": t})


def _stock():
    for tk, phr in itertools.product(
            ["NVDA", "AAPL", "MSFT", "TSLA", "AMZN", "GOOGL", "META"],
            ["Get me the latest price for {t}.", "What is {t} trading at right now?"]):
        yield (phr.format(t=tk), "get_stock_price", {"ticker": tk})


# ---- strict-JSON templates: yield (prompt, expected_object) ----
def _person():
    for name, age, city in itertools.product(
            ["Maria Lopez", "Kenji Sato", "Amara Okafor", "Liam Walsh", "Priya Nair", "Omar Haddad"],
            [23, 37, 51, 68], ["Berlin", "Chicago", "Cape Town", "Seoul"]):
        yield (f'Extract the person\'s details from this sentence: "{name} is {age} years old '
               f'and lives in {city}."\nReturn ONLY a JSON object with keys "name" (string), '
               f'"age" (integer) and "city" (string). No other text.',
               {"name": name, "age": age, "city": city})


def _order():
    for prod, qty, express in itertools.product(
            ["wireless mouse", "desk lamp", "water bottle", "notebook"], [1, 3, 12], [True, False]):
        ship = "express shipping please" if express else "standard shipping is fine"
        yield (f'Extract the order from this message: "I need {qty} x {prod}, {ship}."\n'
               f'Return ONLY a JSON object with keys "product" (string), "quantity" (integer) '
               f'and "express" (boolean). No other text.',
               {"product": prod, "quantity": qty, "express": express})


def _event():
    for ev, (d_text, d) in itertools.product(
            ["product launch", "team offsite", "board meeting", "hackathon"],
            [("March 14, 2026", "2026-03-14"), ("the 3rd of July 2026", "2026-07-03"),
             ("December 1, 2026", "2026-12-01"), ("January 22, 2027", "2027-01-22")]):
        yield (f'Extract the event from this sentence: "Heads up: the {ev} is scheduled for '
               f'{d_text}."\nReturn ONLY a JSON object with keys "event" (string) and "date" '
               f'(string, YYYY-MM-DD). No other text.',
               {"event": ev, "date": d})


TOOL_TEMPLATES = [("weather", _weather), ("currency", _currency), ("timer", _timer),
                  ("booking", _booking), ("stock", _stock)]
JSON_TEMPLATES = [("person", _person, 4), ("order", _order, 3), ("event", _event, 3)]


def build_cases(seed: int = 1234) -> list[dict]:
    """60 cases: 6 per tool template, 10 per JSON template. 20 are marked screen=True."""
    rng = random.Random(seed)
    cases = []
    for name, gen in TOOL_TEMPLATES:
        pool = list(gen())
        rng.shuffle(pool)
        for i, (prompt, fn, args) in enumerate(pool[:6]):
            cases.append({
                "id": f"tool-{name}-{i}", "kind": "tool", "screen": i < 2,
                "messages": [{"role": "system", "content": SYSTEM_TOOL},
                             {"role": "user", "content": prompt}],
                "tools": ALL_TOOLS,
                "expected": {"name": fn, "arguments": args}})
    for name, gen, n_screen in JSON_TEMPLATES:
        pool = list(gen())
        rng.shuffle(pool)
        for i, (prompt, obj) in enumerate(pool[:10]):
            cases.append({
                "id": f"json-{name}-{i}", "kind": "json", "screen": i < n_screen,
                "messages": [{"role": "system", "content": SYSTEM_JSON},
                             {"role": "user", "content": prompt}],
                "expected": obj})
    return cases