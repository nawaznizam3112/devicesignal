
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
    layout="wide",
)

st.title("📊 DeviceSignal")
st.caption("Medical Device Safety Intelligence | Portfolio Prototype v1.1")

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
        value="infusion pump",
    ).strip()

    end_date = st.date_input(
        "Received by FDA up to",
        value=date.today(),
    )

    start_date = st.date_input(
        "Received by FDA from",
        value=date.today() - timedelta(days=365),
    )

    record_limit = st.selectbox(
        "Maximum individual reports to retrieve",
        [100, 500, 1000],
        index=1,
    )

    run_search = st.button(
        "Search FDA database",
        type="primary",
        use_container_width=True,
    )

st.markdown(
    "[Official FDA data and limitations]"
    "(https://open.fda.gov/apis/device/event/)"
    " · "
    "[Searchable fields]"
    "(https://open.fda.gov/apis/device/event/searchable-fields/)"
    " · "
    "[FDA API time-series documentation]"
    "(https://open.fda.gov/apis/timeseries/)"
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

    first = (
        devices[0]
        if devices and isinstance(devices[0], dict)
        else {}
    )

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
    """Create an FDA API lookup link for a report number."""
    if not report_number:
        return ""

    query = quote(
        f'report_number:"{report_number}"',
        safe="",
    )

    return f"{API_URL}?search={query}&limit=1"


def build_search_query(term, start, end):
    """Build and validate the FDA API search query."""
    clean_term = term.replace('"', "").strip()

    if not clean_term:
        raise ValueError("Enter a device name.")

    if start > end:
        raise ValueError(
            "The start date must be on or before the end date."
        )

    if not all(
        c.isalnum() or c.isspace() or c == "-"
        for c in clean_term
    ):
        raise ValueError(
            "Use letters, numbers, spaces or hyphens "
            "in the device name."
        )

    if " " in clean_term:
        search_term = f'device.generic_name:"{clean_term}"'
    else:
        search_term = f"device.generic_name:{clean_term}"

    return (
        f"date_received:[{start:%Y%m%d} TO {end:%Y%m%d}]"
        f" AND {search_term}"
    )


def fetch_reports(term, start, end, limit):
    """Retrieve a bounded sample of individual FDA reports."""
    search = build_search_query(term, start, end)

    response = requests.get(
        API_URL,
        params={
            "search": search,
            "limit": limit,
            "sort": "date_received:desc",
        },
        timeout=45,
    )

    if response.status_code == 404:
        return [], 0, search

    response.raise_for_status()
    payload = response.json()

    meta = payload.get("meta", {}).get("results", {})
    total = int(
        meta.get(
            "total",
            len(payload.get("results", [])),
        )
    )

    return payload.get("results", []), total, search


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_monthly_counts(search):
    """
    Fetch FDA date_received time-series counts independently
    of the capped individual report sample.

    openFDA returns date counts in a time-series format.
    Aggregate those daily counts into calendar months.
    """
    response = requests.get(
        API_URL,
        params={
            "search": search,
            "count": "date_received",
        },
        timeout=60,
    )

    if response.status_code == 404:
        return pd.Series(
            dtype="int64",
            name="FDA reports",
        )

    response.raise_for_status()
    payload = response.json()

    results = payload.get("results", [])
    rows = []

    for item in results:
        # Time-series responses commonly use "time".
        # "term" is accepted as a fallback.
        raw_date = item.get("time", item.get("term"))
        raw_count = item.get("count")

        if raw_date is None or raw_count is None:
            continue

        parsed_date = pd.to_datetime(
            str(raw_date),
            format="%Y%m%d",
            errors="coerce",
        )

        if pd.isna(parsed_date):
            parsed_date = pd.to_datetime(
                str(raw_date),
                errors="coerce",
            )

        if pd.isna(parsed_date):
            continue

        rows.append({
            "date_received": parsed_date,
            "count": int(raw_count),
        })

    if not rows:
        return pd.Series(
            dtype="int64",
            name="FDA reports",
        )

    daily = pd.DataFrame(rows)

    daily["month"] = (
        daily["date_received"].dt.to_period("M")
    )

    monthly = daily.groupby("month")["count"].sum()
    monthly.name = "FDA reports"

    return monthly.sort_index()


def clean_records(records):
    """Convert FDA JSON reports into a tabular DataFrame."""
    rows = []

    for record in records:
        device = extract_device(record)
        report_number = first_value(
            record.get("report_number")
        )

        rows.append({
            "date_received": first_value(
                record.get("date_received")
            ),
            "date_of_event": first_value(
                record.get("date_of_event")
            ),
            "report_number": report_number,
            "event_type": (
                first_value(record.get("event_type"))
                or "Not reported"
            ),
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
            "report_source": first_value(
                record.get("report_source_code")
            ),
            "source_types": first_value(
                record.get("source_type")
            ),
            "adverse_event_flag": first_value(
                record.get("adverse_event_flag")
            ),
            "fda_record_url": make_report_url(report_number),
        })

    columns = [
        "date_received",
        "date_of_event",
        "report_number",
        "event_type",
        "device_name",
        "brand_name",
        "manufacturer",
        "product_code",
        "product_problems",
        "report_source",
        "source_types",
        "adverse_event_flag",
        "fda_record_url",
    ]

    df = pd.DataFrame(rows, columns=columns)

    for column in ["date_received", "date_of_event"]:
        df[column] = pd.to_datetime(
            df[column],
            format="%Y%m%d",
            errors="coerce",
        )

    return df


@st.cache_data(ttl=3600, show_spinner=False)
def cached_fetch(term, start, end, limit):
    return fetch_reports(term, start, end, limit)


# ---------------------------------------------------------
# Session state
# ---------------------------------------------------------

if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame()
    st.session_state.total = 0
    st.session_state.query = ""
    st.session_state.error = ""
    st.session_state.monthly_counts = pd.Series(
        dtype="int64",
        name="FDA reports",
    )
    st.session_state.monthly_error = ""
    st.session_state.searched_start = None
    st.session_state.searched_end = None
    st.session_state.searched_device = ""


# ---------------------------------------------------------
# Search and retrieve both datasets
# ---------------------------------------------------------

if run_search:
    try:
        search_query = build_search_query(
            device_name,
            start_date,
            end_date,
        )

        with st.spinner(
            "Retrieving individual reports and monthly FDA counts..."
        ):
            records, total, query = cached_fetch(
                device_name,
                start_date,
                end_date,
                record_limit,
            )

            st.session_state.df = clean_records(records)
            st.session_state.total = total
            st.session_state.query = query
            st.session_state.searched_start = start_date
            st.session_state.searched_end = end_date
            st.session_state.searched_device = device_name
            st.session_state.error = ""
            st.session_state.monthly_error = ""
            st.session_state.monthly_counts = pd.Series(
                dtype="int64",
                name="FDA reports",
            )

            try:
                st.session_state.monthly_counts = (
                    fetch_monthly_counts(search_query)
                )

                if st.session_state.monthly_counts.empty and total > 0:
                    st.session_state.monthly_error = (
                        "The FDA search returned individual reports, "
                        "but no usable monthly aggregate counts."
                    )

            except Exception as exc:
                st.session_state.monthly_error = (
                    f"{type(exc).__name__}: {exc}"
                )

    except Exception as exc:
        st.session_state.error = (
            f"{type(exc).__name__}: {exc}"
        )


# ---------------------------------------------------------
# Display errors
# ---------------------------------------------------------

if st.session_state.error:
    st.error(
        "The search could not be completed. Check the device name, "
        "date range, internet connection, or FDA API availability."
    )

    with st.expander("Technical details"):
        st.code(st.session_state.error)


# ---------------------------------------------------------
# Dashboard
# ---------------------------------------------------------

df = st.session_state.df
total = st.session_state.total
monthly_counts = st.session_state.monthly_counts

if df.empty:
    st.info(
        "Choose a device and date range in the sidebar, then click "
        "'Search FDA database'. Start with 'infusion pump' to test "
        "the app."
    )

else:
    returned = len(df)
    truncated = total > returned

    searched_start = st.session_state.searched_start
    searched_end = st.session_state.searched_end

    st.caption(
        f"FDA matches reported by API: {total:,} | "
        f"Individual reports retrieved: {returned:,} | "
        f"Search period: {searched_start} to {searched_end}"
    )

    if truncated:
        st.warning(
            "The individual report table contains a limited sample "
            "of a larger result set. The monthly chart uses a separate "
            "FDA aggregate-count request, not just the retrieved "
            "individual reports."
        )

    # -----------------------------------------------------
    # Key metrics
    # -----------------------------------------------------

    event_counts = df["event_type"].value_counts()

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Individual reports retrieved",
        f"{returned:,}",
    )

    c2.metric(
        "Reported event types",
        f"{df['event_type'].nunique():,}",
    )

    c3.metric(
        "Reports with a problem description",
        f"{(df['product_problems'].str.len() > 0).sum():,}",
    )

    # -----------------------------------------------------
    # Event types
    # -----------------------------------------------------

    st.subheader("Reported event types")
    st.bar_chart(event_counts)

    # -----------------------------------------------------
    # Monthly chart using independent aggregate counts
    # -----------------------------------------------------

    st.subheader("Reports received by FDA over time")

    if not monthly_counts.empty:
        chart_start = pd.Period(
            searched_start,
            freq="M",
        )

        chart_end = pd.Period(
            searched_end,
            freq="M",
        )

        complete_range = pd.period_range(
            start=chart_start,
            end=chart_end,
            freq="M",
        )

        chart_data = monthly_counts.reindex(
            complete_range,
            fill_value=0,
        )

        chart_data.index = chart_data.index.astype(str)
        chart_data.name = "FDA reports"

        st.line_chart(chart_data)

        st.caption(
            "Monthly totals are based on FDA date_received aggregate "
            "counts, independently of the capped individual-report "
            "table. Receipt date is not necessarily the date the "
            "event occurred."
        )

        with st.expander("View monthly aggregate counts"):
            monthly_table = chart_data.rename_axis(
                "Month"
            ).reset_index()

            st.dataframe(
                monthly_table,
                use_container_width=True,
                hide_index=True,
            )

            st.download_button(
                "Download monthly counts (CSV)",
                data=monthly_table.to_csv(
                    index=False
                ).encode("utf-8"),
                file_name="devicesignal_monthly_counts.csv",
                mime="text/csv",
            )

    elif st.session_state.monthly_error:
        st.warning(
            "Monthly aggregate counts could not be retrieved. "
            "The monthly trend and exploratory flag are unavailable."
        )

        with st.expander("Monthly-count technical details"):
            st.code(st.session_state.monthly_error)

    else:
        st.info(
            "No monthly aggregate counts are available for this search."
        )

    # -----------------------------------------------------
    # Exploratory reporting-pattern flag
    # -----------------------------------------------------

    st.subheader("Exploratory reporting-pattern flag")

    if st.session_state.monthly_error:
        st.info(
            "Not calculated because the monthly aggregate counts "
            "could not be retrieved."
        )

    elif monthly_counts.empty:
        st.info(
            "Not calculated because there are no usable monthly "
            "aggregate counts."
        )

    else:
        # Exclude the current month because it is incomplete.
        current_month = pd.Period(
            date.today(),
            freq="M",
        )

        latest_allowed_month = min(
            pd.Period(searched_end, freq="M"),
            current_month - 1,
        )

        first_month = pd.Period(
            searched_start,
            freq="M",
        )

        if latest_allowed_month < first_month:
            st.info(
                "The selected search period contains no complete "
                "month available for assessment."
            )

        else:
            complete_months = pd.period_range(
                start=first_month,
                end=latest_allowed_month,
                freq="M",
            )

            counts = monthly_counts.reindex(
                complete_months,
                fill_value=0,
            )

            if len(counts) < 4:
                st.info(
                    "Select a date range covering at least four "
                    "calendar months to assess the latest complete "
                    "month against the preceding three months."
                )

            else:
                latest_month = counts.index[-1]
                latest_count = int(counts.iloc[-1])

                previous_three = counts.iloc[-4:-1]
                baseline = float(previous_three.mean())

                st.write(
                    f"Latest complete month: **{latest_month}**"
                )

                st.write(
                    f"Reports in that month: **{latest_count:,}**"
                )

                st.write(
                    "Average across the preceding three complete "
                    f"months: **{baseline:.1f}**"
                )

                st.caption(
                    "Exploratory rule: at least five reports in the "
                    "latest complete month and a count at least twice "
                    "the preceding three-month average."
                )

                if (
                    latest_count >= 5
                    and latest_count >= 2 * baseline
                ):
                    st.warning(
                        "Exploratory reporting-pattern flag triggered. "
                        "Review the individual reports, possible "
                        "duplicates or follow-ups, device context, "
                        "reporting changes, and other safety evidence. "
                        "This is not a confirmed safety signal."
                    )

                else:
                    st.info(
                        "The simple exploratory criteria were not met. "
                        "This does not establish the absence of a "
                        "safety signal."
                    )

    # -----------------------------------------------------
    # Individual report table
    # -----------------------------------------------------

    st.subheader("Individual report records")

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
            "date_received": st.column_config.DateColumn(
                "Date received"
            ),
            "date_of_event": st.column_config.DateColumn(
                "Date of event"
            ),
        },
    )

    # -----------------------------------------------------
    # Download individual reports
    # -----------------------------------------------------

    csv_data = df.to_csv(
        index=False,
    ).encode("utf-8")

    st.download_button(
        "Download individual reports (CSV)",
        data=csv_data,
        file_name="devicesignal_fda_reports.csv",
        mime="text/csv",
    )

    # -----------------------------------------------------
    # Download review summary
    # -----------------------------------------------------

    if not monthly_counts.empty:
        summary_monthly = monthly_counts.copy()
        summary_monthly.index = (
            summary_monthly.index.astype(str)
        )
        monthly_text = summary_monthly.to_string()
    else:
        monthly_text = (
            "Unavailable: monthly aggregate counts were not retrieved."
        )

    summary = f"""# DeviceSignal - Exploratory Review

## Search details
- Data source: FDA openFDA Device Adverse Event API (MAUDE data)
- Search: {st.session_state.query}
- Search period: {searched_start} to {searched_end}
- Total matches reported by API: {total}
- Individual reports retrieved: {returned}
- Individual report sample truncated: {"Yes" if truncated else "No"}

## Reported event types in the retrieved individual reports
{event_counts.to_string()}

## Monthly aggregate counts
These counts were requested separately from the individual report sample.

{monthly_text}

## Interpretation and limitations
This is a descriptive review of adverse-event reports, not a determination
of causation, incidence, prevalence, device failure rate, or reportability.

Reports may be affected by under-reporting, duplicate or follow-up reports,
changes in reporting practices, device usage, missing information, and
other biases. A change in reporting volume does not by itself establish
a new or confirmed safety signal.

Any unusual reporting pattern requires review of individual records,
device context, applicable reporting requirements, other safety sources,
and qualified human assessment.

## Official references
- https://open.fda.gov/apis/device/event/
- https://open.fda.gov/apis/device/event/searchable-fields/
- https://open.fda.gov/apis/timeseries/
- https://www.fda.gov/medical-devices/postmarket-requirements-devices
"""

    st.download_button(
        "Download review summary (Markdown)",
        data=summary,
        file_name="devicesignal_review_summary.md",
        mime="text/markdown",
    )


# ---------------------------------------------------------
# Footer
# ---------------------------------------------------------

st.divider()

st.caption(
    "DeviceSignal is an independent educational prototype, not an FDA "
    "product or official FDA system. It does not determine reportability "
    "or replace validated post-market surveillance processes."
)
