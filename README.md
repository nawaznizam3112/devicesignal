# devicesignal
A medical-device post-market safety intelligence portfolio prototype using public FDA adverse-event data.
# DeviceSignal

**Medical Device Safety Intelligence — Portfolio Prototype v1.0**

## Project objective

DeviceSignal is an educational regulatory affairs project that
retrieves publicly available FDA medical-device adverse-event
reports and performs descriptive post-market surveillance analysis.

It demonstrates data retrieval, data cleaning, visualisation,
transparent exploratory flagging, and evidence-linked regulatory
communication.

## Data source

- FDA openFDA Device Adverse Event API:
  https://open.fda.gov/apis/device/event/
- Searchable fields:
  https://open.fda.gov/apis/device/event/searchable-fields/

The data originates from MAUDE, the FDA Manufacturer and User
Facility Device Experience database.

## Features

- Search by device generic name and date range.
- Retrieve up to 1,000 matching records per search.
- Display reported event types and monthly report counts.
- Flag selected unusual reporting patterns for human review.
- Export retrieved records as CSV.
- Download an exploratory review summary.

## Methods

The application uses Python, pandas, requests and Streamlit.
It retrieves a bounded sample sorted by FDA receipt date.

The exploratory monthly flag compares the latest complete
month with the preceding three complete months. It requires
at least five reports and at least twice the baseline average.

This is a simple educational screening rule, not a validated
statistical signal-detection method.

## Important limitations

- Reports may be incomplete, inaccurate, biased or unverified.
- Reporting frequency is not device-use frequency.
- Duplicate or follow-up reports may affect counts.
- Changes in reporting practices can affect trends.
- A flag does not establish causation or a safety signal.
- A lack of a flag does not demonstrate product safety.
- The tool does not determine regulatory reportability.

## Intended use

Educational portfolio demonstration and preliminary research.
Not a validated production surveillance system or an official
FDA product. Human regulatory review remains necessary.

## Run locally

Install dependencies:

    pip install -r requirements.txt

Start the app:

    streamlit run app.py

## Author

Independent medical-device regulatory affairs portfolio project.

