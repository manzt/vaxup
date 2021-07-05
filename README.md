# vaxup

A bot to batch fill vaccine registration forms for authorized enrollers in NYC.

> _**Update 2021-07-01**: This project is no longer maintained. The City of New York has discontinued VAX, and this bot has served its purpose._ 


### Requirements

- Python 3.9
- [ChromeDriver](https://www.kenst.com/2015/03/installing-chromedriver-on-mac-osx/) (Optional, required for running the 🤖)

### Installation

Clone this repository,

```bash
$ cd vaxup && pip install .
```

### Usage

The CLI requires `ACUITY_API_KEY` and `ACUITY_USER_ID` environment 
variables for interacting with the Acuity API.

```bash
$ source .env # load environment variables
```

#### `check`

Print a table of appointments from Acuity in the console. Validates 
whether the information from Acuity for an appointment is compatible 
with VAX website. Can fix errors interactively with the `--fix` flag.

```bash
$ vaxup check 2021-05-04 # [--fix]
```

#### `check-id`

Find an appointment from Acuity by `acuity_id` and print information
in the console. Use `--add-note` to tag an appointment as 
`"SECOND DOSE SCHEDULED"`, `"TIME NOT AVAILABLE"`, or `"ALREADY SCHEDULED"`.

```bash
$ vaxup check-id 10000030 # [--add-note]
```


#### `enroll` (the 🤖, requires `ChromeDriver`)

Register all remaining appointments on a date from Acuity on VAX webiste. 
Skips Acuity appointments that already have a VAX appointment number or 
have been tagged with one of the notes above. Using the `--dry-run` flag 
prevents the bot from submitting each forms (useful for debugging).

```bash
$ vaxup enroll 2021-05-04 # [--dry-run]
```

#### `unenroll` (another 🤖, requires `ChromeDriver`)

Cancels an Acuity appointment that has already been registered on VAX website.
This should be used sparingly, and typically in the case where an Acuity 
appointment is canceled. Will try to cancel the corresponding VAX appointment,
and remove the VAX ID from Acuity if successful.

```bash
$ vaxup unenroll 10000030
```
