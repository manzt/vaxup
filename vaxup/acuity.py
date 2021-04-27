import json
import os
from typing import List, Tuple
from vaxup.data import FormError

import requests
from rich.table import Table
from rich import box

ACUITY_URL = "https://acuityscheduling.com/api/v1"

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
        msg = f"Field not found in mapping, {field['name']=} {field['id']=}"
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
    params = {"max": 2000}
    if date:
        params |= {"minDate": f"{date}T00:00", "maxDate": f"{date}T23:59"}
    response = requests.get(
        url=f"{ACUITY_URL}/appointments",
        auth=(os.environ["ACUITY_USER_ID"], os.environ["ACUITY_API_KEY"]),
        params=params,
    )
    data = response.json()
    return data if not transform else list(map(transform_json, data))


def edit_appointment(appt_id: int, fields=List[Tuple[str, str]]):
    id_map = {v: k for k, v in FIELD_IDS.items()}
    fields = [{"id": id_map[k], "value": v} for k, v in fields]
    res = requests.put(
        url=f"{ACUITY_URL}/appointments/{appt_id}",
        auth=(os.environ["ACUITY_USER_ID"], os.environ["ACUITY_API_KEY"]),
        data=json.dumps({"fields": fields}),
    )
    return res, fields


def get_forms():
    response = requests.get(
        url=f"{ACUITY_URL}/forms",
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


def create_error_table(errs: List[FormError]):
    row_styles = ["none", "dim"] if len(errs) > 2 else None
    table = Table(show_header=True, row_styles=row_styles, box=box.SIMPLE_HEAD)
    table.add_column("appt. id", style="magenta")
    table.add_column("date", justify="center")

    table.add_column("time", justify="center")

    table.add_column("field", justify="right", style="yellow")
    table.add_column("value", style="bold yellow")

    for err in errs:
        table.add_row(
            str(err.id),
            err.date,
            err.time,
            "\n".join(err.names),
            "\n".join(err.values),
        )

    return table