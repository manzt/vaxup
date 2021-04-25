import os
from dataclasses import asdict

import requests
from rich.console import Console
from rich.table import Table

from vaxup.cli import check
from vaxup.data import FormEntry


ACUITY_FORM_ID = 1717791  # "CHN Vaccine Scheduling Intake Form"

# Maps acuity intake form field 'id' -> 'name'
FIELD_IDS = {
    9519119: "dob",
    9519125: "street_address",
    9519126: "apt",
    9519128: "city",
    9519129: "state",
    9519130: "zip_code",
    9519140: "race",
    9519174: "ethnicity",
    9519161: "sex",
    9519166: "has_health_insurance",
    # Unused fields, we keep these for reference
    9517774: "_elgibility",
    9517872: "_certification",
    9517897: "_allergic_reaction",
    9519120: "_age",
    9605979: "_link",
    9605968: "_link",
}

# Ignore fields that are prefixed with "_"; we don't use them in vaxup
FIELD_MAP = {k: v for k, v in FIELD_IDS.items() if not v.startswith("_")}


def _assert_correct_form(form):
    assert form["id"] == ACUITY_FORM_ID, "Acuity form not found"


def _assert_has_all_fields(fields):
    for field in fields:
        msg = f"Field not found in mapping, {field['name']} {field['id']}"
        assert field["id"] in FIELD_IDS, msg


def check_acuity_mapping():
    form = get_forms()[0]
    _assert_correct_form(form)
    _assert_has_all_fields(form["fields"])


def transform_json(d):
    record = dict(
        id=d["id"],
        first_name=d["firstName"],
        last_name=d["lastName"],
        email=d["email"],
        phone=d["phone"],
        start_time=d["datetime"],
        location=d["calendar"],
    )

    # Grab first form and assert it is correct
    form = d["forms"][0]
    _assert_correct_form(form)

    return record | {
        FIELD_MAP[val["fieldID"]]: val["value"]
        for val in form["values"]
        if val["fieldID"] in FIELD_MAP
    }


def get_appointments(date: str = None, transform=True):
    response = requests.get(
        url="https://acuityscheduling.com/api/v1/appointments",
        auth=(os.environ["ACUITY_USER_ID"], os.environ["ACUITY_API_KEY"]),
        params={
            "minDate": f"{date}T00:00",
            "maxDate": f"{date}T23:59",
            "max": 2000,
        }
        if date
        else {"max": 2000},
    )
    data = response.json()
    return data if not transform else list(map(transform_json, data))


def get_forms():
    response = requests.get(
        url="https://acuityscheduling.com/api/v1/forms",
        auth=(os.environ["ACUITY_USER_ID"], os.environ["ACUITY_API_KEY"]),
    )
    return response.json()


def create_table(fields, list_all=False):
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("id", style="dim")
    table.add_column("field")
    table.add_column("text")
    table.add_column("type", justify="center")
    table.add_column("options")
    for f in fields:
        field = FIELD_IDS[f["id"]]
        row = map(str, (f["id"], field, f["name"], f["type"], f["options"]))
        if list_all:
            table.add_row(*row)
        elif not field.startswith("_"):
            table.add_row(*row)

    return table


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("date", default=None)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    console = Console()
    forms = get_forms()
    table = create_table(forms[0]["fields"])
    console.print(table)

    appts = list(get_appointments(args.date))
    if args.check:
        check(reader=appts, console=console, verbose=True)
    else:
        for a in appts:
            # console.print(a)
            # console.print(a)
            console.print(a)
            console.print(asdict(FormEntry(**a)))


if __name__ == "__main__":
    main()
