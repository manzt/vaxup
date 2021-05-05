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

# Extends Enum with a `match` method that checks if the string
# value for the Enum is within another string
class FuzzyEnum(Enum):
    @classmethod
    def match(cls, v: str):
        for item in cls:
            if item.value in v:
                return item
        raise ValueError("No matches")


class Race(FuzzyEnum):
    ASIAN = "Asian (including South Asian)"
    BLACK = "Black including African American or Afro-Caribbean"
    NATIVE_AMERICAN = "Native American or Alaska Native"
    WHITE = "White"
    PACIFIC_ISLANDER = "Native Hawaiian or Pacific Islander"
    OTHER = "Other"
    PREFER_NOT_TO_ANSWER = "Prefer not to answer"


class Sex(FuzzyEnum):
    MALE = "Male"
    FEMALE = "Female"
    NEITHER = "Neither"
    UNKNOWN = "Unknown"


class Ethnicity(FuzzyEnum):
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
    def match_enum(cls, v, **kwargs):
        # Use the custom match method to account for bilingual options on Acuity.
        # Race.match("Other | Otro") == Race.match("Other") # True
        enum = {"race": Race, "sex": Sex, "ethnicity": Ethnicity}[kwargs["field"].name]
        return v if isinstance(v, enum) else enum.match(v)

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
    def from_acuity(cls, apt: AcuityAppointment):
        return cls(**apt.dict())
