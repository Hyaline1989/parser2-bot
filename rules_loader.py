import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def load_rules():
    path = Path(__file__).with_name("rules.json")
    with path.open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def get_position_aliases():
    return load_rules().get("position_aliases", {})


def get_position_matches():
    return load_rules().get("position_matches", {})


def get_position_gender_defaults():
    return load_rules().get("position_gender_defaults", {})

