from collections import namedtuple

COLUMN_MAPPING = {
    "Location": "location",
    "Start Time": "start_time",
    # 'Eligibility: Currently only the following groups are eligible to get vaccinated. Check all that apply to you. DO NOT SCHEDULE IF YOU ARE NOT CURRENTLY ELIGIBLE.',
    # '* I hereby certify under penalty of law that I live in New York City or, if I am claiming eligibility based on work or employment status, that I work in New York City. I agree that by selecting 'Yes', my response provided is true and correct.',
    # 'Have you ever had a serious or life-threatening allergic reaction, such as hives or difficulty breathing, to a previous dose of COVID-19 vaccine or any component of the vaccine? IF YES, DO NOT SCHEDULE given you are not eligible to receive the COVID-19.':
    "First Name": "first_name",
    "Last Name": "last_name",
    "Date of birth (M/DD/YYYY)": "dob",
    "Age": "age",
    "Email": "email",
    "Phone": "phone",
    "Street address (e.g., 60 Madison Ave.)": "street_adress",
    "City (e.g., Queens)": "city",
    "State (e.g., NY)": "state",
    "Zip code (e.g., 10010)": "zip_code",
    "Which race do you identify as?": "race",
    "Do you identify as Hispanic, Latino, or Latina?": "identify_as_hispanic_latino_latina",
    "What sex were you assigned at birth?": "sex",
    "Do you have health insurance?": "has_health_insurance",
    # 'Would you like to enter health insurance information now?': '',
    "Type of insurance": "insurance_type",
    "Insurance: Company name": "insurance_company",
    "Insurance: Member ID number": "insurance_number",
}


def ensure_mmddyyyy(date):
    m, d, y = date.split("/")
    return "/".join(
        [
            m if len(m) == 2 else "0" + m,
            d if len(d) == 2 else "0" + d,
            y if len(y) == 4 else "19" + y,
        ]
    )


@classmethod
def from_csv_dict(cls, entry):
    fields = {COLUMN_MAPPING[k]: entry[k] for k in entry if k in COLUMN_MAPPING}
    fields["dob"] = ensure_mmddyyyy(fields["dob"])
    return cls(**fields)


FormEntry = namedtuple("FormEntry", COLUMN_MAPPING.values())
setattr(FormEntry, "from_csv_dict", from_csv_dict)
