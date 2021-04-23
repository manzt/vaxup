import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional, Tuple, Iterable
from itertools import groupby

from openpyxl import load_workbook
from pydantic import BaseModel, validator

COLUMNS = {
    "Start Time": "start_time",
    "First Name": "first_name",
    "Last Name": "last_name",
    "Phone": "phone",
    "Email": "email",
    "Calendar": "location",
    "Date of birth (M/DD/YYYY)": "dob",
    "Street address (e.g., 60 Madison Ave.)": "street_address",
    "Apt / suite number": "apt",
    "City (e.g., Queens)": "city",
    "State (e.g., NY)": "state",
    "Zip code (e.g., 10010)": "zip_code",
    "Which race do you identify as?": "race",
    "Do you identify as Hispanic, Latino, or Latina?": "ethnicity",
    "What sex were you assigned at birth?": "sex",
    "COVID-19 vaccines are free for you and we will not be billing your insurance. For informational purposes, do you have health insurance?": "has_health_insurance",
    "Have you ever had a serious or life-threatening allergic reaction, such as hives or difficulty breathing, to a previous dose of COVID-19 vaccine or any component of the vaccine?  IF YES, DO NOT SCHEDULE given you are not eligible to receive the vaccine.": "is_allergic",
}


class Location(Enum):
    # Values are the "data-id" attribute for the "Select" buttons after login on website.
    # e.g. <lightning-button data-id='0013d000002jkZPAAY'>
    EAST_NY = "0013d000002jkZPAAY"
    HARLEM = "0013d000002jkZ0AAI"
    WASHINGTON_HEIGHTS = "0013d000002vZH6AAM"
    SOUTH_JAMAICA = "0013d000002jkSKAAY"

    @classmethod
    def from_str(cls, v: str):
        v = v.lower()
        if "east ny" in v:
            return cls.EAST_NY
        if "harlem" in v:
            return cls.HARLEM
        if "washington heights" in v:
            return cls.WASHINGTON_HEIGHTS
        if "south jamaica":
            return cls.SOUTH_JAMAICA
        raise ValueError(f"Location not identified, got {v}")


class Race(Enum):
    # Values are the "data-label" attribute for the clickable span on website.
    # e.g. <span data-label='Other'...>
    BLACK = "Black, including African American or Afro-Caribbean"
    ASIAN = "Asian, including South Asian"
    NATIVE_AMERICAN = "Native American or Alaska Native"
    PACIFIC_ISLANDER = "Native Hawaiian or Pacific Islander"
    WHITE = "White"
    PREFER_NOT_TO_ANSWER = "Prefer not to answer"
    OTHER = "Other"

    @classmethod
    def from_str(cls, v: str):
        v = v.lower()
        if "asian" in v:
            return cls.ASIAN
        elif "black" in v:
            return cls.BLACK
        elif "alaska" in v:
            return cls.NATIVE_AMERICAN
        elif "pacific" in v:
            return cls.PACIFIC_ISLANDER
        elif "white" in v:
            return cls.WHITE
        elif "prefer" in v:
            return cls.PREFER_NOT_TO_ANSWER
        else:
            return cls.OTHER


class Sex(Enum):
    # Values are the "data-value" attribute for the dropdown on website.
    # e.g. <lightning-base-combobox-item data-value='Unknown' ...>
    MALE = "Male"
    FEMALE = "Female"
    NEITHER = "Neither male or female"
    UNKNOWN = "Unknown"

    @classmethod
    def from_str(cls, v: str):
        v = v.lower()
        if "male" == v:
            return cls.MALE
        if "female" == v:
            return cls.FEMALE
        if "neither" in v:
            return cls.NEITHER
        return cls.UNKNOWN


class Ethnicity(Enum):
    # Values are the "data-value" attribute for the dropdown on website.
    # e.g. <lightning-base-combobox-item data-value='Prefer not to answer' ... >
    LATINX = "Yes, Hispanic, Latino, or Latina"
    NOT_LATINX = "No, not Hispanic, Latino, or Latina"
    PERFER_NOT_TO_ANSWER = "Prefer not to answer"

    @classmethod
    def from_answer(cls, v: str):
        # Answer to question: 'Do you identify as Hispanic, Latino, or Latina?'
        v = v.lower()
        if "yes" == v:
            return cls.LATINX
        if "no" == v:
            return cls.NOT_LATINX
        return cls.PERFER_NOT_TO_ANSWER


class FormEntry(BaseModel):
    start_time: datetime
    first_name: str
    last_name: str
    phone: Optional[str]
    email: str
    location: Location
    dob: datetime
    street_address: str
    city: str
    state: Literal["NY", "NJ"]
    apt: Optional[str]
    zip_code: int
    race: Race
    ethnicity: Ethnicity
    sex: Sex
    has_health_insurance: bool
    is_allergic: Literal[False]

    @property
    def date_str(self):
        return self.start_time.strftime("%m/%d/%Y")

    @property
    def time_str(self):
        return self.start_time.strftime("%I:%M %p")

    @property
    def dob_str(self):
        return self.dob.strftime("%m/%d/%Y")

    @validator("phone")
    def cast_phone(cls, v):
        # Since it's not a required field, only provide number if its exactly 10 digits
        v = re.sub(r"[^0-9]+", "", str(v))[-10:]  # remove non-numeric characters
        v = v[-10:]  # and last 10 elements (or less)
        return v if len(v) == 10 else None


def cast_state(v: str):
    # No validation for "state" in Acuity.
    # This function safely determines whether
    upper = str(v).strip().upper()
    if upper in {"NJ", "NY"}:
        return upper
    return v


@dataclass
class FormError:
    date: datetime
    errors: List[Tuple[str, str]]

    @classmethod
    def from_err(cls, e, record):
        errors = []
        for err in e.errors():
            field = err["loc"][0]
            errors.append({field: record[field]})
        date = str(record["start_time"])
        return cls(date=date, errors=errors)


class AcuityExportReader:
    def __init__(self, path: str):
        wb = load_workbook(path)
        self.name = wb.sheetnames[0]
        self._ws = wb[self.name]

    def __iter__(self):
        data = self._ws.values
        headers = next(data)
        for row in data:
            # Rename and pick fields
            record = {COLUMNS[k]: v for k, v in zip(headers, row) if k in COLUMNS}
            # Cast string / answer fields to corresponding Enum or bool
            yield record | {
                "location": Location.from_str(record["location"]),
                "race": Race.from_str(record["race"]),
                "sex": Sex.from_str(record["sex"]),
                "ethnicity": Ethnicity.from_answer(record["ethnicity"]),
                "has_health_insurance": record["has_health_insurance"] == "yes",
                "state": cast_state(record["state"]),
                "is_allergic": record["is_allergic"] == "yes",
            }

    def __len__(self):
        data = self._ws.values
        next(data)
        return sum(1 for _ in data)


def group_entries(entries: Iterable[FormEntry]):
    sorted_entries = sorted(entries, key=lambda e: e.location.value)
    return groupby(sorted_entries, key=lambda e: e.location)
