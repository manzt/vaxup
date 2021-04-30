import re
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Literal, Optional, Tuple

from pydantic import ValidationError, validator
from pydantic.types import PositiveInt

from vaxup.acuity import Appointment

# Improve intellisense for VSCode
# https://github.com/microsoft/python-language-server/issues/1898
if TYPE_CHECKING:
    from dataclasses import dataclass
else:
    from pydantic.dataclasses import dataclass as dataclass


# Copied from VAX website <input name='email' pattern='....' />
VAX_EMAIL_REGEX = re.compile(
    r"^([a-zA-Z0-9_\-\.\+]+)@([a-zA-Z0-9_\-]+)((\.[a-zA-Z]{2,5})+)$"
)


class Location(Enum):
    EAST_NY = "CHN Vaccination Site: Church of God (East NY)"
    HARLEM = "CHN Vaccination Site: Convent Baptist (Harlem)"
    WASHINGTON_HEIGHTS = "CHN Vaccination Site: Fort Washington (Washington Heights)"
    SOUTH_JAMAICA = "CHN Vaccination Site: New Jerusalem (South Jamaica)"


class Race(Enum):
    ASIAN = "Asian (including South Asian)"
    BLACK = "Black including African American or Afro-Caribbean"
    NATIVE_AMERICAN = "Native American or Alaska Native"
    WHITE = "White"
    PACIFIC_ISLANDER = "Native Hawaiian or Pacific Islander"
    OTHER = "Other"
    PREFER_NOT_TO_ANSWER = "Prefer not to answer"


class Sex(Enum):
    MALE = "Male"
    FEMALE = "Female"
    NEITHER = "Neither"
    UNKNOWN = "Unknown"


class Ethnicity(Enum):
    LATINX = "Yes"
    NOT_LATINX = "No"
    PERFER_NOT_TO_ANSWER = "Prefer not to answer"


class Config:
    anystr_strip_whitespace = True


@dataclass(config=Config)
class VaxAppointment:
    id: PositiveInt
    datetime: datetime
    first_name: str
    last_name: str
    phone: Optional[PositiveInt]
    email: str
    location: Location
    dob: datetime
    street_address: str
    city: str
    state: Literal["NY", "NJ"]
    apt: Optional[str]
    zip_code: PositiveInt
    race: Race
    ethnicity: Ethnicity
    sex: Sex
    has_health_insurance: bool
    vax_appointment_id: Optional[str]
    canceled: Literal[False]

    @property
    def date_str(self):
        return self.datetime.strftime("%m/%d/%Y")

    @property
    def time_str(self):
        return self.datetime.strftime("%I:%M %p")

    @property
    def dob_str(self):
        return self.dob.strftime("%m/%d/%Y")

    @validator("datetime")
    def strip_tzinfo(cls, dt):
        return dt.replace(tzinfo=None)

    @validator("apt", "vax_appointment_id")
    def empty_as_none(cls, v):
        return None if v == "" else v

    @validator("state", pre=True)
    def cast_state(cls, v):
        # No validation for "state" in Acuity.
        # This function safely determines whether
        upper = str(v).strip().upper()
        if upper in {"NJ", "NY"}:
            return upper
        if "YORK" in upper:
            return "NY"
        if "JERSEY" in upper:
            return "NJ"
        return v

    @validator("email")
    def email_regex(cls, v):
        if VAX_EMAIL_REGEX.fullmatch(v) is None:
            raise ValueError("Email doesn't match regex on VAX.")
        return v

    @validator("phone", pre=True)
    def cast_phone(cls, v):
        if isinstance(v, int):
            if len(str(v)) != 10:
                raise ValueError("Phone number is longer than 10 digits")
            return v
        # Since it's not a required field, only provide number if its exactly 10 digits
        v = re.sub(r"[^0-9]+", "", str(v))[-10:]  # remove non-numeric characters
        v = v[-10:]  # and last 10 elements (or less)
        return v if len(v) == 10 else None

    @validator("dob", pre=True)
    def instance_dt(cls, v):
        if isinstance(v, datetime):
            return v
        return datetime.strptime(v.strip(), "%m/%d/%Y")

    @classmethod
    def from_acuity(cls, apt: Appointment):
        return cls(**apt.__vaxup__())


@dataclass
class VaxAppointmentError:
    id: PositiveInt
    location: Location
    datetime: datetime
    fields: List[Tuple[str, str]]
    vax_appointment_id = None

    @property
    def date(self):
        return self.datetime.strftime("%d/%m/%Y")

    @property
    def time(self):
        return self.datetime.strftime("%I:%M %p")

    @property
    def names(self):
        return [f[0] for f in self.fields]

    @property
    def values(self):
        return [f[1] for f in self.fields]

    @classmethod
    def from_err(cls, e: ValidationError, apt: Appointment):
        d = apt.__vaxup__()
        fields = []
        for err in e.errors():
            name = err["loc"][0]
            fields.append((name, d[name]))
        return cls(
            id=apt.id,
            location=d["location"],
            datetime=apt.datetime,
            fields=fields,
        )