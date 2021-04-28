import datetime
import json
import os
from typing import Any, Dict, List, Tuple

import requests
from pydantic import BaseModel, validator
from pydantic.fields import Field
from pydantic.types import PositiveInt

# Acuity API URL
ACUITY_URL = "https://acuityscheduling.com/api/v1"
# Acuity ID for intake form titled "CHN Vaccine Scheduling Intake Form"
ACUITY_FORM_ID = 1717791
# Acuity appointments/ endpoint is limited to 100 by default.
MAX_PER_RESPONSE = 5000
# Maps Acuity intake form field 'id' -> 'name'
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


class FormValue(BaseModel):
    id: PositiveInt
    fieldID: PositiveInt
    value: str
    name: str

    @validator("fieldID")
    def known_field(cls, v: int):
        assert v in FIELD_IDS, "Field not found in mapping"
        return v

    @property
    def field(self):
        return FIELD_IDS[self.fieldID]

    @property
    def keep(self):
        # Ignore fields that are prefixed with "_"; we don't use them in vaxup
        return not self.field.startswith("_")


class Form(BaseModel):
    id: PositiveInt
    name: str
    values: List[FormValue]

    @validator("id")
    def known_form(cls, v: int):
        assert v == ACUITY_FORM_ID, "Acuity form not found"
        return v


class Appointment(BaseModel):
    id: PositiveInt
    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")
    phone: str
    email: str
    datetime: str = Field(alias="datetime")
    location: str = Field(alias="calendar")
    forms: List[Form]


def get_auth() -> Tuple[str, str]:
    return os.environ["ACUITY_USER_ID"], os.environ["ACUITY_API_KEY"]


def get_appointments(date: datetime.date) -> List[Appointment]:
    res = requests.get(
        url=f"{ACUITY_URL}/appointments",
        auth=get_auth(),
        params={
            "max": MAX_PER_RESPONSE,
            "minDate": f"{date}T00:00",
            "maxDate": f"{date}T23:59",
        },
    )
    res.raise_for_status()
    return [Appointment(**d) for d in res.json()]


def get_appointment(appt_id: int) -> Appointment:
    res = requests.get(url=f"{ACUITY_URL}/appointments/{appt_id}", auth=get_auth())
    res.raise_for_status()
    return Appointment(**res.json())


def edit_appointment(appt_id: int, fields=List[Tuple[str, str]]) -> Appointment:
    id_map = {v: k for k, v in FIELD_IDS.items()}
    fields = [{"id": id_map[k], "value": v} for k, v in fields]
    res = requests.put(
        url=f"{ACUITY_URL}/appointments/{appt_id}",
        auth=get_auth(),
        data=json.dumps({"fields": fields}),
    )
    res.raise_for_status()
    return Appointment(**res.json())


if __name__ == "__main__":
    import sys

    from rich import print

    print(get_appointment(sys.argv[1]))
