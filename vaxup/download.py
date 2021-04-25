import os

import requests
from rich.console import Console

from vaxup.cli import check
from vaxup.data import COLUMNS, Ethnicity, Location, Race, Sex, cast_state, FormEntry


def parse_data(d):
    record = dict(
        id=d["id"],
        first_name=d["firstName"],
        last_name=d["lastName"],
        email=d["email"],
        start_time=d["datetime"],
        location=d["calendar"],
    )
    record |= {
        COLUMNS[d["name"]]: d["value"]
        for d in d["forms"][0]["values"]
        if d["name"] in COLUMNS
    }
    return record | {
        "location": Location.from_str(record["location"]),
        "race": Race.from_str(record["race"]),
        "sex": Sex.from_str(record["sex"]),
        "ethnicity": Ethnicity.from_answer(record["ethnicity"]),
        "has_health_insurance": record.get("has_health_insurance", "no") == "yes",
        "state": cast_state(record["state"]),
    }


def get_appointments(date: str = None):
    response = requests.get(
        url="https://acuityscheduling.com/api/v1/appointments",
        auth=(os.environ["ACUITY_USER_ID"], os.environ["ACUITY_API_KEY"]),
        params={
            "minDate": f"{date}T00:00:00",
            "maxDate": f"{date}T23:59:00",
            "max": 2000,
        }
        if date
        else {"max": 2000},
    )
    return map(parse_data, response.json())


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("date", default=None)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    console = Console()
    appts = list(get_appointments(args.date))
    if args.check:
        check(reader=appts, console=console, verbose=True)
    else:
        for a in appts:
            console.print(FormEntry(**a))


if __name__ == "__main__":
    main()