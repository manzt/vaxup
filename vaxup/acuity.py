import datetime
import json
import os
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any

import requests
from pydantic import BaseModel, validator
from pydantic.fields import Field
from pydantic.types import PositiveInt

ACUITY_URL = "https://acuityscheduling.com/api/v1"

FIELD_IDS = {
    # SCHEDULING FORM
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
    # VAX CONFIRMATION
    9715272: "vax_appointment_id",
    9730790: "vax_note",
}


class ErrorNote(Enum):
    SECOND_DOSE = "SECOND DOSE SCHEDULED"
    TIME_NOT_AVAILABLE = "TIME NOT AVAILABLE"
    ALREADY_SCHEDULED = "ALREADY SCHEDULED"
    NONE = ""


class Location(Enum):
    EAST_NY = "CHN Vaccination Site: Church of God (East NY)"
    HARLEM = "CHN Vaccination Site: Convent Baptist (Harlem)"
    WASHINGTON_HEIGHTS = "CHN Vaccination Site: Fort Washington (Washington Heights)"
    SOUTH_JAMAICA = "CHN Vaccination Site: New Jerusalem (South Jamaica)"


class AcuityAppointment(BaseModel):
    id: PositiveInt
    first_name: str = Field(alias="firstName")
    last_name: str = Field(alias="lastName")
    phone: str
    email: str
    datetime: datetime.datetime
    location: Location = Field(alias="calendar")
    canceled: bool
    # forms
    dob: str
    street_address: str
    city: str
    state: str
    apt: Optional[str]
    zip_code: str
    race: str
    ethnicity: str
    sex: str
    has_health_insurance: str
    # Custom form
    vax_appointment_id: Optional[str]
    vax_note: Optional[ErrorNote]

    @validator("datetime")
    def strip_tzinfo(cls, dt):
        return dt.replace(tzinfo=None)

    @validator("vax_appointment_id", "apt", "vax_note")
    def empty_as_none(cls, v):
        return None if v == "" else v

    @classmethod
    def from_api(cls, apt):
        apt |= {
            FIELD_IDS[v["fieldID"]]: v["value"]
            for form in apt["forms"]
            for v in form["values"]
            if v["fieldID"] in FIELD_IDS
        }
        return cls(**apt)


def get_auth() -> Tuple[str, str]:
    return os.environ["ACUITY_USER_ID"], os.environ["ACUITY_API_KEY"]


def get_appointments(
    date: datetime.date, canceled: bool = False, max_per_response: int = 5000
) -> List[AcuityAppointment]:
    res = requests.get(
        url=f"{ACUITY_URL}/appointments",
        auth=get_auth(),
        params={
            "max": max_per_response,
            "minDate": f"{date}T00:00",
            "maxDate": f"{date}T23:59",
            "canceled": "true" if canceled else "false",
        },
    )
    res.raise_for_status()
    return [AcuityAppointment.from_api(a) for a in res.json()]


def edit_appointment(
    acuity_id: int,
    fields: Optional[Dict[str, str]] = None,
    notes: Optional[str] = None,
) -> AcuityAppointment:
    data = {}
    if fields:
        id_map = {v: k for k, v in FIELD_IDS.items()}
        fields = [{"id": id_map[k], "value": v} for k, v in fields.items()]
        data |= {"fields": fields}
    if isinstance(notes, str):
        data |= {"notes": notes}
    res = requests.put(
        url=f"{ACUITY_URL}/appointments/{acuity_id}",
        auth=get_auth(),
        data=json.dumps(data),
        params={"admin": "true"},
    )

    res.raise_for_status()
    return AcuityAppointment.from_api(res.json())


def get_appointment(acuity_id: int, raw: bool = False) -> Dict[str, Any]:
    res = requests.get(url=f"{ACUITY_URL}/appointments/{acuity_id}", auth=get_auth())
    res.raise_for_status()
    return res.json()


def set_vax_appointment_id(
    acuity_id: int, vax_appointment_id: str
) -> AcuityAppointment:
    return edit_appointment(
        acuity_id=acuity_id, fields={"vax_appointment_id": vax_appointment_id}
    )


def delete_vax_appointment_id(acuity_id: int) -> AcuityAppointment:
    return set_vax_appointment_id(acuity_id=acuity_id, vax_appointment_id="")


def set_vax_note(acuity_id: int, note: ErrorNote) -> AcuityAppointment:
    return edit_appointment(acuity_id=acuity_id, fields={"vax_note": note.value})
