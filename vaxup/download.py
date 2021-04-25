import datetime
import os
from typing import cast

import requests
from rich.console import Console

from vaxup.data import COLUMNS, Location, Sex, Ethnicity, Race, cast_state
from vaxup.cli import check


def parse_forms(forms):
    values = forms[0]["values"]
    return {COLUMNS[d["name"]]: d["value"] for d in values if d["name"] in COLUMNS}


def parse_data(d):
    record = (
        dict(
            id=d["id"],
            first_name=d["firstName"],
            last_name=d["lastName"],
            email=d["email"],
            start_time=d["datetime"],
            location=d["calendar"],
        )
        | parse_forms(d["forms"])
    )
    try:
        dob = datetime.datetime.strptime(record["dob"].strip(), "%m/%d/%Y")
    except Exception:
        dob = record["dob"]
    return record | {
        "location": Location.from_str(record["location"]),
        "race": Race.from_str(record["race"]),
        "sex": Sex.from_str(record["sex"]),
        "ethnicity": Ethnicity.from_answer(record["ethnicity"]),
        "has_health_insurance": record.get("has_health_insurance", "no") == "yes",
        "is_allergic": record["is_allergic"] == "yes",
        "dob": dob,
        "state": cast_state(record["state"]),
    }


def main():
    console = Console()
    date = "2021-04-22"
    response = requests.get(
        url="https://acuityscheduling.com/api/v1/appointments",
        auth=(os.environ["ACUITY_USER_ID"], os.environ["ACUITY_API_KEY"]),
        params={
            "minDate": f"{date}T00:00:00",
            "maxDate": f"{date}T23:59:00",
        },
    )
    data = response.json()
    check(reader=map(parse_data, data), console=console, verbose=True)


if __name__ == "__main__":
    main()