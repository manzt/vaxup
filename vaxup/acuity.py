import os
from dataclasses import asdict

import requests
from rich.console import Console

from vaxup.cli import check
from vaxup.data import COLUMNS, FormEntry


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
    form_values = d["forms"][0]["values"]
    return record | {
        COLUMNS[d["name"]]: d["value"] for d in form_values if d["name"] in COLUMNS
    }


def get_appointments(date: str = None, transform=False):
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
    return data if not transform else list(map(transform, data))


def get_forms():
    response = requests.get(
        url="https://acuityscheduling.com/api/v1/forms",
        auth=(os.environ["ACUITY_USER_ID"], os.environ["ACUITY_API_KEY"]),
    )
    return response.json()


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("date", default=None)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    console = Console()
    forms = get_forms()
    console.print(forms)
    return
    appts = list(get_appointments(args.date))
    if args.check:
        check(reader=appts, console=console, verbose=True)
    else:
        for a in appts:
            # console.print(a)
            # console.print(a)
            console.print(asdict(FormEntry(**a)))


if __name__ == "__main__":
    main()
