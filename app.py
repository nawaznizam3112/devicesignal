
import requests
import pandas as pd
import streamlit as st
from datetime import date, timedelta
from urllib.parse import quote

API_URL = "https://api.fda.gov/device/event.json"
MAX_RECORDS = 1000

st.set_page_config(
    page_title="DeviceSignal",
    page_icon="📊",
    layout="wide"
)

st.title("📊 DeviceSignal")
st.caption("Medical Device Safety Intelligence | Portfolio Prototype v1.0")

st.warning(
    "Research and educational use only. FDA adverse-event reports are "
    "not verified proof of causation or device failure rates. "
    "This tool does not make clinical, reportability, or regulatory "
    "compliance decisions."
)

st.markdown(
    "Explore publicly available FDA device-event reports, inspect "
    "reporting patterns, and prepare an evidence-linked review."
)

with st.sidebar:
    st.header("Search settings")
    device_name = st.text_input(
        "Device generic name",
        value="infusion pump"
    ).strip()

    end_date = st.date_input("Received by FDA up to", value=date.today())
    start_date = st.date_input(
        "Received by FDA from",
        value=date.today() - timedelta(days=365)
    )

    record_limit = st.selectbox(
        "Maximum records to retrieve",
        [100, 500, 1000],
        index=1
    )

    run_search = st.button(
        "Search FDA database",
        type="primary",
        use_container_width=True
    )

st.markdown(
    "[Official FDA data and limitations]"
    "(https://open.fda.gov/apis/device/event/)"
    " · "
    "[Searchable fields]"
    "(https://open.fda.gov/apis/device/event/searchable-fields/)"
)


def first_value(value):
    """Convert a field that may be a list into readable text."""
    if isinstance(value, list):
        return "; ".join(str(x) for x in value if x)
    if value is None:
        return ""
    return str(value)


def extract_device(record):
    """Safely extract fields from the device array."""
    devices = record.get("device", [])
    if isinstance(devices, dict):
        devices = [devices]
    if not isinstance(devices, list):
        devices = []

    first = devices[0] if devices and isinstance(devices[0], dict) else {}

    return {
        "device_name": first_value(first.get("generic_name")),
        "brand_name": first_value(first.get("brand_name")),
        "device_manufacturer": first_value(
            first.get("manufacturer_d_name")
        ),
        "product_code": first_value(
            first.get("device_report_product_code")
        ),
    }


def make_report_url(report_number):
    if not report_number:
        return ""
    query = quote(f'report_number:"{report_number}"', safe="")
    return f"{API_URL}?search={query}&limit=1"


def fetch_reports(term, start, end, limit):
    """Retrieve a bounded sample of matching FDA reports."""
    clean_term = term.replace('"', "").strip()

    if not clean_term:
        raise ValueError("Enter a device name.")
    if start > end:
        raise ValueError("The start date must be on or before the end date.")

    if not all(c.isalnum() or c.isspace() or c == "-" for c in clean_term):
        raise ValueError(
            "Use letters, numbers, spaces or hyphens in the device name."
        )

    search_term = (
        f'device.generic_name:"{clean_term}"'
        if " " in clean_term
        else f"device.generic_name:{clean_term}"
    )

    search = (
        f"date_received:[{start:%Y%m%d} TO {end:%Y%m%d}]"
        f" AND {search_term}"
    )

    response = requests.get(
        API_URL,
        params={
            "search": search,
            "limit": limit,
            "sort": "date_received:desc",
        },
        timeout=30,
    )

    if response.status_code == 404:
        return [], 0, search

    response.raise_for_status()
    payload = response.json()

    meta = payload.get("meta", {}).get("results", {})
    total = int(meta.get("total", len(payload.get("results", []))))

    return payload.get("results", []), total, search


def clean_records(records):
    rows = []

    for record in records:
        device = extract_device(record)
        report_number = first_value(record.get("report_number"))

        rows.append({
            "date_received": first_value(record.get("date_received")),
            "date_of_event": first_value(record.get("date_of_event")),
            "report_number": report_number,
            "event_type": first_value(record.get("event_type"))
                or "Not reported",
            "device_name": device["device_name"],
            "brand_name": device["brand_name"],
            "manufacturer": (
                device["device_manufacturer"]
                or first_value(record.get("manufacturer_name"))
            ),
            "product_code": device["product_code"],
            "product_problems": first_value(
                record.get("product_problems")
            ),
            "report_source": first_value(record.get("report_source_code")),
            "source_types": first_value(record.get("source_type")),
            "adverse_event_flag": first_value(
                record.get("adverse_event_flag")
            ),
            "fda_record_url": make_report_url(report_number),
        })

    df = pd.DataFrame(rows)

    if not df.empty:
        df["date_received"] = pd.to_datetime(
            df["date_received"], format="%Y%m%d", errors="coerce"
        )
        df["date_of_event"] = pd.to_datetime(
            df["date_of_event"], format="%Y%m%d", errors="coerce"
        )

    return df


@st.cache_data(ttl=3600, show_spinner=False)
def cached_fetch(term, start, end, limit):
    return fetch_reports(term, start, end, limit)


if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame()
    st.session_state.total = 0
    st.session_state.query = ""
    st.session_state.error = ""

if run_search:
    try:
        with st.spinner("Retrieving reports from the FDA API..."):
            records, total, query = cached_fetch(
                device_name,
                start_date,
                end_date,
                record_limit,
            )
            st.session_state.df = clean_records(records)
            st.session_state.total = total
            st.session_state.query = query
            st.session_state.error = ""
    except Exception as exc:
        st.session_state.error = (
            f"{type(exc).__name__}: {exc}"
        )

if st.session_state.error:
    st.error(
        "The search could not be completed. Check the device name, "
        "date range, internet connection, or FDA API availability."
    )
    with st.expander("Technical details"):
        st.code(st.session_state.error)

df = st.session_state.df
total = st.session_state.total

if df.empty:
    st.info(
        "Choose a device and date range in the sidebar, then click "
        "'Search FDA database'. Start with 'infusion pump' if you "
        "want to test the app."
    )
else:
    returned = len(df)
    truncated = total > returned

    st.caption(
        f"FDA matches reported by API: {total:,} | "
        f"Records retrieved: {returned:,} | "
        f"Search period: {start_date} to {end_date}"
    )

    if truncated:
        st.warning(
            "This is a limited sample of a larger result set. "
            "The API returned fewer records than the total match count. "
            "Charts and counts below describe only the retrieved sample, "
            "not all matching FDA reports."
        )

    valid_dates = df["date_received"].dropna()
    if not valid_dates.empty:
        df = df.copy()
        df["month"] = df["date_received"].dt.to_period("M").astype(str)

    event_counts = df["event_type"].value_counts()

    c1, c2, c3 = st.columns(3)
    c1.metric("Records retrieved", f"{returned:,}")
    c2.metric("Reported event types", f"{df['event_type'].nunique():,}")
    c3.metric(
        "Records with a problem description",
        f"{(df['product_problems'].str.len() > 0).sum():,}",
    )

    st.subheader("Reported event types")
    st.bar_chart(event_counts)

    st.subheader("Reports received by FDA over time")
    if not valid_dates.empty:
        monthly = (
            df.dropna(subset=["date_received"])
            .assign(month=lambda x: x["date_received"].dt.to_period("M").astype(str))
            .groupby("month")
            .size()
            .rename("reports_in_retrieved_sample")
        )
        st.line_chart(monthly)
        st.caption(
            "Monthly distribution within the retrieved records. "
            "Reporting dates are not necessarily event occurrence dates."
        )
    else:
        st.info("No usable FDA receipt dates were returned.")

    st.subheader("Exploratory reporting-pattern flag")

    # Only assess this simple flag if the retrieved sample covers
    # all matches for the selected search.
    if truncated:
        st.info(
            "Not calculated because the search result was truncated. "
            "A capped, date-sorted sample can distort monthly trends."
        )
    elif not valid_dates.empty:
        current_month = pd.Period(date.today(), freq="M")
        end_period = pd.Period(end_date, freq="M")

        complete_end = min(
            end_period,
            current_month - 1
        )

        monthly_full = (
            df.dropna(subset=["date_received"])
            .assign(
                month_period=lambda x: x["date_received"].dt.to_period("M")
            )
            .groupby("month_period")
            .size()
        )

        available_months = pd.period_range(
            start=pd.Period(start_date, freq="M"),
            end=complete_end,
            freq="M",
        )

        if len(available_months) >= 4:
            counts = monthly_full.reindex(
                available_months, fill_value=0
            )
            latest_count = int(counts.iloc[-1])
            baseline = float(counts.iloc[-4:-1].mean())

            st.write(
                f"Latest complete month: **{available_months[-1]}**"
            )
            st.write(f"Reports in that month: **{latest_count}**")
            st.write(
                "Average across the preceding three complete months: "
                f"**{baseline:.1f}**"
            )

            if latest_count >= 5 and latest_count >= 2 * baseline:
                st.warning(
                    "Exploratory flag: the latest month's report count "
                    "is at least five and at least twice the preceding "
                    "three-month average. This warrants contextual review, "
                    "not a conclusion that a safety signal exists."
                )
            else:
                st.info(
                    "The simple flag criteria were not met. "
                    "This does not establish the absence of a safety signal."
                )
        else:
            st.info(
                "Select a longer date range to assess the latest "
                "complete month against three preceding months."
            )

    st.subheader("Report records")
    display_columns = [
        "date_received",
        "date_of_event",
        "report_number",
        "event_type",
        "device_name",
        "brand_name",
        "manufacturer",
        "product_code",
        "product_problems",
        "fda_record_url",
    ]

    st.dataframe(
        df[display_columns],
        use_container_width=True,
        hide_index=True,
        column_config={
            "fda_record_url": st.column_config.LinkColumn(
                "FDA record lookup"
            ),
            "date_received": st.column_config.DateColumn("Date received"),
            "date_of_event": st.column_config.DateColumn("Date of event"),
        },
    )

    csv_data = df.drop(columns=["month"], errors="ignore").to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        "Download retrieved records (CSV)",
        data=csv_data,
        file_name="devicesignal_fda_reports.csv",
        mime="text/csv",
    )

    summary = f"""# DeviceSignal - Exploratory Review

## Search details
- Data source: FDA openFDA Device Adverse Event API (MAUDE data)
- Search: {st.session_state.query}
- Search period: {start_date} to {end_date}
- Total matches reported by API: {total}
- Records retrieved: {returned}
- Sample truncated: {"Yes" if truncated else "No"}

## Descriptive findings
- Most frequently reported event types:
{event_counts.to_string()}

## Interpretation and limitations
This is a descriptive review of reports, not a determination of causation,
incidence, prevalence, or device failure rate. Report counts may be affected
by under-reporting, duplicate or follow-up reports, reporting changes,
device usage, missing data, and other biases.

Any unusual reporting pattern requires review of individual records,
device context, applicable reporting requirements, other safety sources,
and qualified human assessment. A flag is not a regulatory conclusion.

## Official references
- https://open.fda.gov/apis/device/event/
- https://open.fda.gov/apis/device/event/searchable-fields/
- https://www.fda.gov/medical-devices/postmarket-requirements-devices
"""
    st.download_button(
        "Download review summary (Markdown)",
        data=summary,
        file_name="devicesignal_review_summary.md",
        mime="text/markdown",
    )

st.divider()
st.caption(
    "DeviceSignal is an independent educational prototype, not an FDA "
    "product or an official FDA system. It does not determine "
    "reportability or replace validated post-market surveillance processes."
)
