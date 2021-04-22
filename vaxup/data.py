from enum import Enum
from typing import Optional

import pandas as pd
from pydantic import BaseModel

COLUMNS = {
    "Start Time": "start_time",
    "First Name": "first_name",
    "Last Name": "last_name",
    "Phone": "phone",
    "Email": "email",
    "Calendar": "location",
    "Date of birth (M/DD/YYYY)": "dob",
    "Street address (e.g., 60 Madison Ave.)": "street",
    "Apt / suite number": "apt",
    "City (e.g., Queens)": "city",
    "State (e.g., NY)": "state",
    "Zip code (e.g., 10010)": "zip_code",
    "Which race do you identify as?": "race",
    "Do you identify as Hispanic, Latino, or Latina?": "identify_as_hispanic",
    "What sex were you assigned at birth?": "sex",
    "COVID-19 vaccines are free for you and we will not be billing your insurance. For informational purposes, do you have health insurance?": "has_health_insurance",
}

STATES = {
    "AL",
    "AK",
    "AS",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DE",
    "DC",
    "FL",
    "GA",
    "HI",
    "ID",
    "IL",
    "IN",
    "IA",
    "KS",
    "KY",
    "LA",
    "ME",
    "MH",
    "MD",
    "MA",
    "MI",
    "MN",
    "MS",
    "MO",
    "MT",
    "NE",
    "NV",
    "NH",
    "NJ",
    "NM",
    "NY",
    "NC",
    "ND",
    "MP",
    "OH",
    "OK",
    "OR",
    "PA",
    "PR",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VT",
    "VA",
    "WA",
    "WV",
    "WI",
    "WY",
}


class Location(Enum):
    EAST_NY = 0
    HARLEM = 1
    WASHINGTON_HEIGHTS = 2
    SOUTH_JAMAICA = 3

    @classmethod
    def from_str(cls, v: str):
        if v == "CHN Vaccination Site: Church of God (East NY)":
            return cls.EAST_NY
        if v == "CHN Vaccination Site: Convent Baptist (Harlem)":
            return cls.HARLEM
        if v == "CHN Vaccination Site: Fort Washington (Washington Heights)":
            return cls.WASHINGTON_HEIGHTS
        if v == "CHN Vaccination Site: New Jerusalem (South Jamaica)":
            return cls.SOUTH_JAMAICA
        raise ValueError(f"Location not identified, got {v}")


class Race(Enum):
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
    date: str
    time: str
    first_name: str
    last_name: str
    phone: Optional[str]
    email: str
    location: Location
    dob: str
    street: str
    city: str
    state: str
    apt: Optional[str]
    zip_code: int
    race: Race
    ethnicity: Ethnicity
    sex: Sex
    has_health_insurance: bool

    @classmethod
    def from_df_record(cls, r) -> "FormEntry":
        r = r.copy()
        answer = r.pop("identify_as_hispanic")
        update = dict(
            location=Location.from_str(r["location"]),
            ethnicity=Ethnicity.from_answer(answer),
            sex=Sex.from_str(r["sex"]),
            race=Race.from_str(r["race"]),
        )
        return cls(**{**r, **update})


def clean_phone_numbers(phone: pd.Series) -> pd.Series:
    # cast to string
    phone = phone.astype("string")
    # remove non numeric characters
    phone = phone.str.replace(r"[^0-9]+", "", regex=True)
    # get last 10 digits (or less)
    phone = phone.str[-10:]
    return phone


def read_excel(path: str) -> pd.DataFrame:
    # Read XLS & rename columns
    df = pd.read_excel(path).rename(columns=COLUMNS)[COLUMNS.values()]

    # Split datetime into date & time strings that correspond to inputs
    df["date"] = df.start_time.dt.strftime("%m/%d/%Y")
    df["time"] = df.start_time.dt.strftime("%I:%M %p")
    df.drop(columns="start_time", inplace=True)

    # Phones are string of length 10 or less
    df.phone = clean_phone_numbers(df.phone)

    # Unrecognized dates coerced to null
    df.dob = pd.to_datetime(df.dob, errors="coerce").dt.strftime("%m/%d/%Y")

    # Cast to bool
    df.has_health_insurance = df.has_health_insurance.str.lower() == "yes"

    return df.where(pd.notnull(df), None)


class FormReader:
    def __init__(self, path: str):
        self._df = read_excel(path)

    def __iter__(self):
        for record in self._df.to_dict(orient="records"):
            yield FormEntry.from_df_record(record)

    def __len__(self):
        return len(self._df)