import re
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Literal, Optional

from pydantic import validator
from pydantic.types import PositiveInt

from .acuity import AcuityAppointment, ErrorNote, Location

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
    canceled: bool
    location: Location

    # Form validation
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
    vax_note: Optional[ErrorNote]

    @property
    def date_str(self):
        return self.datetime.strftime("%m/%d/%Y")

    @property
    def time_str(self):
        return self.datetime.strftime("%I:%M %p")

    @property
    def dob_str(self):
        return self.dob.strftime("%m/%d/%Y")

    @validator("race", "sex", "ethnicity", pre=True)
    def strip_translation(cls, v):
        # The dropdown options on Acuity were changed
        #
        # from "<OPTION>"
        # to   "<OPTION> | <OPTION_TRANSLATION>"
        #
        # In order to be both backward and forward compatible,
        # we strip the translation (if present) and use the
        # exisiting pydantic validation.
        if isinstance(v, str) and "|" in v:
            # "Other | Otro" -> "Other"
            return v.split("|")[0].strip()
        return v

    @validator("state", pre=True)
    def coerce_state(cls, v):
        # No validation for "state" in Acuity.
        # This greedly coerces a string into "NJ" or "NY"
        # based on some simple heuristics.
        if isinstance(v, str):
            upper = v.strip().upper()
            if upper in {"NJ", "NY"}:
                return upper
            if "YORK" in upper:
                return "NY"
            if "JERSEY" in upper:
                return "NJ"
        return v

    @validator("dob", pre=True)
    def instance_dt(cls, v):
        if isinstance(v, str):
            return datetime.strptime(v.strip(), "%m/%d/%Y")
        return v

    @validator("email")
    def email_regex(cls, v):
        if VAX_EMAIL_REGEX.fullmatch(v) is None:
            raise ValueError("Email doesn't match regex on VAX.")
        return v

    @validator("phone")
    def check_length(cls, v):
        length = len(str(v))
        if length > 10:
            # Might be able to fix, raise as an error
            raise ValueError("Phone number is longer than 10 digits")
        if length < 10:
            # Not clear how to fix, default to `None` since
            # it's an optional field on VAX.
            return None
        return v

    @classmethod
    def from_acuity(cls, apt: AcuityAppointment):
        return cls(**apt.dict())
