import re
from datetime import datetime
from typing import TYPE_CHECKING, Literal, Optional

from pydantic import validator
from pydantic.types import PositiveInt

from .acuity import AcuityAppointment, Location, Race, Ethnicity, Sex

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

    @property
    def date_str(self):
        return self.datetime.strftime("%m/%d/%Y")

    @property
    def time_str(self):
        return self.datetime.strftime("%I:%M %p")

    @property
    def dob_str(self):
        return self.dob.strftime("%m/%d/%Y")

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
    def from_acuity(cls, apt: AcuityAppointment):
        return cls(**apt.dict())
