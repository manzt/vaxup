import datetime
import json
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Union

import requests
from pydantic import BaseModel, validator
from pydantic.fields import Field
from pydantic.types import PositiveInt

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


def unnest_forms(forms: list[dict[str, Any]]):
    # unnest acuity forms into single key-value dict
    return {
        FIELD_IDS[v["fieldID"]]: v["value"]
        for form in forms
        for v in form["values"]
        if v["fieldID"] in FIELD_IDS
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
    phone: Optional[str]
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

    @validator("vax_appointment_id", "apt", "vax_note", "phone")
    def empty_as_none(cls, v):
        return None if v == "" else v

    def __rich_repr__(self):
        return self.dict().items()


@dataclass
class AcuityAPI:
    session: requests.Session = field(default_factory=requests.Session)
    base_url: str = "https://acuityscheduling.com/api/v1"

    def __post_init__(self):
        # If session is missing auth, inspect environment
        if self.session.auth is None:
            self.session.auth = (
                os.environ["ACUITY_USER_ID"],
                os.environ["ACUITY_API_KEY"],
            )
        # Raise an error for any bad response
        self.session.hooks |= {
            "response": lambda r, *args, **kwargs: r.raise_for_status()
        }

    def _unnest(self, apt: dict[str, Any]) -> AcuityAppointment:
        forms = unnest_forms(apt.pop("forms"))
        return AcuityAppointment(**(apt | forms))

    def url(self, path: str):
        base = self.base_url.rstrip("/")
        path = path.lstrip("/")
        return f"{base}/{path}"

    def get_appointment(self, id: int) -> AcuityAppointment:
        res = self.session.get(url=self.url(f"/appointments/{id}"))
        return self._unnest(res.json())

    def get_appointments(
        self, date: datetime.date, canceled: bool = False
    ) -> list[AcuityAppointment]:
        params = {
            "max": 10_000,  # well above daily amount
            "minDate": f"{date}T00:00",
            "maxDate": f"{date}T23:59",
            "canceled": "true" if canceled else "false",
        }
        res = self.session.get(url=self.url("/appointments"), params=params)
        return [self._unnest(d) for d in res.json()]

    def edit_appointment(self, id: int, fields: dict[str, str]) -> AcuityAppointment:
        assert len(fields) > 0, "Must provide dict with fields to update."

        data = {}
        fields = fields.copy()

        # Fields are not from intake froms
        for key in ("email", "phone", "notes"):
            if key in fields:
                data |= {key: fields.pop(key)}

        # Iterate through remaining form fields (if any)
        if len(fields) > 0:
            id_map = {v: k for k, v in FIELD_IDS.items()}
            fields = [{"id": id_map[k], "value": v} for k, v in fields.items()]
            data |= {"fields": fields}

        res = self.session.put(
            url=self.url(f"/appointments/{id}"),
            data=json.dumps(data),
            params={"admin": "true"},
        )

        return self._unnest(res.json())

    def set_vax_id(self, id: int, vax_id: Union[str, None]) -> AcuityAppointment:
        vax_id = "" if vax_id is None else vax_id
        return self.edit_appointment(id=id, fields={"vax_appointment_id": vax_id})

    def set_vax_note(self, id: int, note: ErrorNote) -> AcuityAppointment:
        return self.edit_appointment(id=id, fields={"vax_note": note.value})
