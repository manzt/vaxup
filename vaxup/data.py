import datetime
import re
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, validator
from pydantic.types import PositiveInt

from .acuity import AcuityAppointment, ErrorNote, Location

# Copied from VAX website <input name='email' pattern='....' />
VAX_EMAIL_REGEX = re.compile(
    r"^([a-zA-Z0-9_\-\.\+]+)@([a-zA-Z0-9_\-]+)((\.[a-zA-Z]{2,5})+)$"
)
DATE_FORMAT = "%m/%d/%Y"
TIME_FORMAT = "%I:%M %p"


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


class VaxAppointment(BaseModel):
    id: PositiveInt
    first_name: str
    last_name: str
    phone: Optional[PositiveInt]
    email: str
    datetime: datetime.datetime
    location: Location
    canceled: bool

    # Form validation
    dob: datetime.date
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

    class Config:
        anystr_strip_whitespace = True

    @property
    def date_str(self):
        return self.datetime.strftime(DATE_FORMAT)

    @property
    def time_str(self):
        return self.datetime.strftime(TIME_FORMAT)

    @property
    def dob_str(self):
        return self.dob.strftime(DATE_FORMAT)

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
    def date_from_acuity_str(cls, v):
        if isinstance(v, str):
            return datetime.datetime.strptime(v.strip(), DATE_FORMAT).date()
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

    def __rich_repr__(self):
        return self.dict().items()
