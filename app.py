
import requests
import pandas as pd
import streamlit as st
from datetime import date, timedelta
from urllib.parse import quote

API_URL = "https://api.fda.gov/device/event.json"

st.set_page_config(
    page_title="DeviceSignal",
    page_icon="📊",
    layout="wide",
)

st.title("📊 DeviceSignal")
st.caption("Medical Device Safety Intelligence | Portfolio Prototype v1.2")

st.warning(
    "Educational research prototype only. MAUDE reports are not verified "
    "proof of causation or device failure rates. Reporting counts cannot "
    "establish incidence, prevalence, or comparative risk. This application "
    "does not make clinical, reportability, or regulatory decisions."
)

st.markdown(
    "Search FDA device-event reports, review reporting patterns, "
    "inspect data quality, and export an evidence-linked review."
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
        "Maximum individual reports",
        [100, 500, 1000],
        index=1,
    )

    run_search = st.button(
        "Search FDA database",
        type="primary",
        use_container_width=True,
    )

st.markdown(
    "[openFDA device-event API](https://open.fda.gov/apis/device/event/)"
    " · "
    "[Searchable fields](https://open.fda.gov/apis/device/event/searchable-fields/)"
    " · "
    "[FDA MAUDE limitations](https://www.fda.gov/medical-devices/"
    "mandatory-reporting-requirements-manufacturers-importers-and-device-user-facilities/"
    "about-manufacturer-and-user-facility-device-experience-maude-database)"
)


def first_value(value):
    if isinstance(value, list):
        return "; ".join(str(x) for x in value if x)
    if value is None:
        return ""
    return str(value)


def extract_device(record):
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
        "manufacturer": first_value(first.get("manufacturer_d_name")),
        "product_code": first_value(
            first.get("device_report_product_code")
        ),
    }


def make_report_url(report_number):
    if not report_number:
        return ""

    query = quote(
        f'report_number:"{report_number}"',
        safe="",
    )
    return f"{API_URL}?search={query}&limit=1"


def build_search_query(term, start, end):
    term = term.replace('"', "").strip()

    if not term:
        raise ValueError("Enter a device generic name.")

    if start > end:
        raise ValueError(
            "The start date must be on or before the end date."
        )

    if not all(
        char.isalnum() or char.isspace() or char == "-"
        for char in term
    ):
        raise ValueError(
            "Use letters, numbers, spaces, or hyphens in the device name."
        )

    if " " in term:
        device_query = f'device.generic_name:"{term}"'
    else:
        device_query = f"device.generic_name:{term}"

    return (
        f"date_received:[{start:%Y%m%d} TO {end:%Y%m%d}]"
        f" AND {device_query}"
    )


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_reports(search, limit):
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
        return [], 0

    response.raise_for_status()
    payload = response.json()

    total = int(
        payload.get("meta", {})
        .get("results", {})
        .get("total", len(payload.get("results", [])))
    )

    return payload.get("results", []), total


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_monthly_counts(search):
    response = requests.get(
        API_URL,
        params={
            "search": search,
            "count": "date_received",
        },
        timeout=60,
    )

    if response.status_code == 404:
        return pd.Series(dtype="int64", name="FDA reports")

    response.raise_for_status()
    payload = response.json()

    rows = []

    for item in payload.get("results", []):
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
        return pd.Series(dtype="int64", name="FDA reports")

    daily = pd.DataFrame(rows)
    daily["month"] = daily["date_received"].dt.to_period("M")

    monthly = daily.groupby("month")["count"].sum()
    monthly.name = "FDA reports"

    return monthly.sort_index()


def clean_records(records):
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

    rows = []

    for record in records:
        device = extract_device(record)
        report_number = first_value(record.get("report_number"))

        rows.append({
            "date_received": first_value(record.get("date_received")),
            "date_of_event": first_value(record.get("date_of_event")),
            "report_number": report_number,
            "event_type": (
                first_value(record.get("event_type")) or "Not reported"
            ),
            "device_name": device["device_name"],
            "brand_name": device["brand_name"],
            "manufacturer": (
                device["manufacturer"]
                or first_value(record.get("manufacturer_name"))
            ),
            "product_code": device["product_code"],
            "product_problems": first_value(
                record.get("product_problems")
            ),
            "report_source": first_value(
                record.get("report_source_code")
            ),
            "source_types": first_value(record.get("source_type")),
            "adverse_event_flag": first_value(
                record.get("adverse_event_flag")
            ),
            "fda_record_url": make_report_url(report_number),
        })

    df = pd.DataFrame(rows, columns=columns)

    for column in ["date_received", "date_of_event"]:
        df[column] = pd.to_datetime(
            df[column],
            format="%Y%m%d",
            errors="coerce",
        )

    return df


def assess_data_quality(df, monthly, total, start, end):
    """Return transparent quality checks for the retrieved data."""
    checks = []

    received = df["date_received"]
    report_numbers = df["report_number"].fillna("").astype(str).str.strip()

    checks.append({
        "Check": "Individual reports retrieved",
        "Result": f"{len(df):,}",
        "Status": "INFO",
        "Meaning": "Number of individual reports in the downloaded sample.",
    })

    checks.append({
        "Check": "API-reported matching total",
        "Result": f"{total:,}",
        "Status": "INFO",
        "Meaning": "Total matches reported by the individual-report API query.",
    })

    missing_dates = int(received.isna().sum())

    checks.append({
        "Check": "Missing or invalid receipt dates",
        "Result": f"{missing_dates:,}",
        "Status": "PASS" if missing_dates == 0 else "REVIEW",
        "Meaning": "Receipt dates are required for date-based analysis.",
    })

    duplicate_mask = (
        report_numbers.ne("")
        & report_numbers.duplicated(keep=False)
    )
    duplicate_rows = int(duplicate_mask.sum())

    checks.append({
        "Check": "Rows with duplicated report numbers",
        "Result": f"{duplicate_rows:,}",
        "Status": "PASS" if duplicate_rows == 0 else "REVIEW",
        "Meaning": (
            "Repeated report numbers in the retrieved sample. "
            "Review before interpreting row counts."
        ),
    })

    missing_ids = int(report_numbers.eq("").sum())

    checks.append({
        "Check": "Missing report numbers",
        "Result": f"{missing_ids:,}",
        "Status": "PASS" if missing_ids == 0 else "REVIEW",
        "Meaning": "Rows without an identifier cannot be individually traced.",
    })

    if not received.dropna().empty:
        outside_range = int(
            (
                (received < pd.Timestamp(start))
                | (received > pd.Timestamp(end))
            ).sum()
        )
    else:
        outside_range = 0

    checks.append({
        "Check": "Receipt dates outside selected range",
        "Result": f"{outside_range:,}",
        "Status": "PASS" if outside_range == 0 else "REVIEW",
        "Meaning": "Checks date boundaries for the retrieved records.",
    })

    missing_manufacturer = int(
        df["manufacturer"].fillna("").astype(str).str.strip().eq("").sum()
    )

    checks.append({
        "Check": "Missing manufacturer values",
        "Result": f"{missing_manufacturer:,}",
        "Status": "INFO" if missing_manufacturer else "PASS",
        "Meaning": "Manufacturer information may not be provided in every report.",
    })

    if monthly.empty:
        checks.append({
            "Check": "Monthly aggregate counts",
            "Result": "Unavailable",
            "Status": "REVIEW",
            "Meaning": "Monthly aggregate data could not be validated.",
        })
    else:
        monthly_total = int(monthly.sum())
        matches = monthly_total == total

        checks.append({
            "Check": "Monthly sum vs API matching total",
            "Result": (
                f"{monthly_total:,} vs {total:,}"
            ),
            "Status": "PASS" if matches else "REVIEW",
            "Meaning": (
                "A comparison of the monthly aggregate sum with the "
                "individual query's reported total. A match is a "
                "consistency check, not proof of source-data completeness."
            ),
        })

    return pd.DataFrame(checks)


# ---------------------------------------------------------
# Search state
# ---------------------------------------------------------

if "searched" not in st.session_state:
    st.session_state.searched = False
    st.session_state.df = pd.DataFrame()
    st.session_state.total = 0
    st.session_state.query = ""
    st.session_state.error = ""
    st.session_state.monthly_error = ""
    st.session_state.monthly_counts = pd.Series(dtype="int64")
    st.session_state.searched_start = None
    st.session_state.searched_end = None

if run_search:
    try:
        query = build_search_query(
            device_name,
            start_date,
            end_date,
        )

        with st.spinner(
            "Retrieving reports and validating monthly counts..."
        ):
            records, total = fetch_reports(query, record_limit)
            df = clean_records(records)

            st.session_state.df = df
            st.session_state.total = total
            st.session_state.query = query
            st.session_state.searched_start = start_date
            st.session_state.searched_end = end_date
            st.session_state.error = ""
            st.session_state.monthly_error = ""
            st.session_state.monthly_counts = pd.Series(
                dtype="int64",
                name="FDA reports",
            )
            st.session_state.searched = True

            try:
                st.session_state.monthly_counts = (
                    fetch_monthly_counts(query)
                )

                if (
                    total > 0
                    and st.session_state.monthly_counts.empty
                ):
                    st.session_state.monthly_error = (
                        "The API returned no usable monthly counts."
                    )

            except Exception as exc:
                st.session_state.monthly_error = (
                    f"{type(exc).__name__}: {exc}"
                )

    except Exception as exc:
        st.session_state.error = f"{type(exc).__name__}: {exc}"


if st.session_state.error:
    st.error(
        "Search failed. Check the device name, dates, internet connection, "
        "or FDA API availability."
    )
    with st.expander("Technical details"):
        st.code(st.session_state.error)


# ---------------------------------------------------------
# Dashboard
# ---------------------------------------------------------

df = st.session_state.df
monthly = st.session_state.monthly_counts
total = st.session_state.total

if not st.session_state.searched:
    st.info(
        "Choose a device and date range, then click Search FDA database."
    )

elif df.empty and total == 0:
    st.info("No matching reports were returned for this search.")

else:
    start = st.session_state.searched_start
    end = st.session_state.searched_end
    returned = len(df)
    truncated = total > returned

    st.caption(
        f"API-reported matches: {total:,} | "
        f"Individual reports retrieved: {returned:,} | "
        f"Period: {start} to {end}"
    )

    if truncated:
        st.warning(
            "The individual report table is a capped sample. "
            "The monthly chart uses a separate aggregate-count request."
        )

    # -----------------------------------------------------
    # Key metrics
    # -----------------------------------------------------

    c1, c2, c3 = st.columns(3)

    c1.metric("Reports retrieved", f"{returned:,}")
    c2.metric(
        "Event types represented",
        f"{df['event_type'].nunique():,}" if not df.empty else "0",
    )
    c3.metric(
        "Reports with problem descriptions",
        f"{df['product_problems'].fillna('').str.len().gt(0).sum():,}",
    )

    # -----------------------------------------------------
    # Data quality and validation
    # -----------------------------------------------------

    st.subheader("Data Quality & Validation")

    if not df.empty:
        quality = assess_data_quality(
            df,
            monthly,
            total,
            start,
            end,
        )

        st.dataframe(
            quality,
            use_container_width=True,
            hide_index=True,
        )

        review_count = int(
            quality["Status"].eq("REVIEW").sum()
        )

        if review_count:
            st.warning(
                f"{review_count} validation check(s) need review. "
                "Read the table before interpreting the analysis."
            )
        else:
            st.success(
                "No issues were detected by the checks displayed. "
                "These checks do not prove that the underlying FDA data "
                "are complete or clinically valid."
            )

    if st.session_state.monthly_error:
        st.warning(
            "Monthly aggregate validation is unavailable."
        )
        with st.expander("Monthly API technical details"):
            st.code(st.session_state.monthly_error)

    # -----------------------------------------------------
    # Event-type distribution
    # -----------------------------------------------------

    if not df.empty:
        st.subheader("Reported event types")
        st.bar_chart(df["event_type"].value_counts())

    # -----------------------------------------------------
    # Monthly trend
    # -----------------------------------------------------

    st.subheader("Monthly reports received by FDA")

    if not monthly.empty:
        months = pd.period_range(
            start=pd.Period(start, freq="M"),
            end=pd.Period(end, freq="M"),
            freq="M",
        )

        chart = monthly.reindex(months, fill_value=0)
        chart.index = chart.index.astype(str)
        chart.name = "FDA reports"

        st.line_chart(chart)

        monthly_table = chart.rename_axis("Month").reset_index()

        with st.expander("View monthly aggregate data"):
            st.dataframe(
                monthly_table,
                use_container_width=True,
                hide_index=True,
            )

            st.download_button(
                "Download monthly counts CSV",
                data=monthly_table.to_csv(index=False).encode("utf-8"),
                file_name="devicesignal_monthly_counts.csv",
                mime="text/csv",
            )

        st.caption(
            "These are counts of reports received, not event incidence "
            "or device failure rates. An apparent change can reflect "
            "reporting practices, data updates, or other factors."
        )

    else:
        st.info("Monthly aggregate counts are unavailable.")

    # -----------------------------------------------------
    # Exploratory reporting-volume review
    # -----------------------------------------------------

    st.subheader("Exploratory reporting-volume review")

    st.caption(
        "Educational screening rule only — not a validated safety-signal "
        "detection method. FDA cautions against using MAUDE data alone "
        "to evaluate changes in adverse-event rates over time."
    )

    monthly_sum_matches = (
        not monthly.empty and int(monthly.sum()) == total
    )

    if monthly.empty:
        st.info(
            "Review not calculated because monthly counts are unavailable."
        )

    elif not monthly_sum_matches:
        st.warning(
            "Review not calculated because the monthly aggregate sum "
            "does not match the API-reported total. Investigate the "
            "count discrepancy first."
        )

    else:
        latest_complete = min(
            pd.Period(end, freq="M"),
            pd.Period(date.today(), freq="M") - 1,
        )

        first_month = pd.Period(start, freq="M")

        if latest_complete < first_month:
            st.info("No complete month is available in this date range.")

        else:
            periods = pd.period_range(
                start=first_month,
                end=latest_complete,
                freq="M",
            )

            counts = monthly.reindex(periods, fill_value=0)

            if len(counts) < 4:
                st.info(
                    "Select at least four calendar months to calculate "
                    "the exploratory comparison."
                )

            else:
                latest_month = counts.index[-1]
                latest_count = int(counts.iloc[-1])
                baseline = float(counts.iloc[-4:-1].mean())

                st.write(f"Latest complete month: **{latest_month}**")
                st.write(f"Reports in that month: **{latest_count:,}**")
                st.write(
                    "Average across the preceding three months: "
                    f"**{baseline:.1f}**"
                )

                if (
                    latest_count >= 5
                    and latest_count >= 2 * baseline
                ):
                    st.warning(
                        "Reporting-volume review flag triggered. "
                        "Review individual reports and other evidence. "
                        "This is not a confirmed safety signal."
                    )
                else:
                    st.info(
                        "The simple review threshold was not triggered. "
                        "This does not establish the absence of a safety issue."
                    )

    # -----------------------------------------------------
    # Individual report table
    # -----------------------------------------------------

    st.subheader("Individual report records")

    if not df.empty:
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

        st.download_button(
            "Download individual reports CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="devicesignal_fda_reports.csv",
            mime="text/csv",
        )

    # -----------------------------------------------------
    # Review summary export
    # -----------------------------------------------------

    event_summary = (
        df["event_type"].value_counts().to_string()
        if not df.empty
        else "No individual reports returned."
    )

    monthly_summary = (
        monthly.to_string()
        if not monthly.empty
        else "Monthly aggregate data unavailable."
    )

    quality_summary = (
        quality.to_string(index=False)
        if not df.empty
        else "No individual records available for quality checks."
    )

    summary = f"""# DeviceSignal Exploratory Review

## Search details
- Source: FDA openFDA Device Event API / MAUDE
- Query: {st.session_state.query}
- Period: {start} to {end}
- API-reported matching total: {total}
- Individual reports retrieved: {returned}
- Individual sample truncated: {"Yes" if truncated else "No"}

## Reported event types in retrieved sample
{event_summary}

## Monthly aggregate counts
{monthly_summary}

## Data quality checks
{quality_summary}

## Interpretation and limitations
This is an exploratory review of medical-device reports, not a determination
of causation, incidence, prevalence, device failure rates, or reportability.

MAUDE reports may be incomplete, inaccurate, duplicated, unverified, delayed,
or affected by reporting bias. Report volume cannot be interpreted in
isolation as evidence of device risk. The monthly aggregate consistency
check is a technical cross-check, not proof of data completeness.

Any unusual pattern requires qualified human review and assessment of
individual reports, device context, other safety sources, and applicable
regulatory requirements.

## Official references
- https://open.fda.gov/apis/device/event/
- https://open.fda.gov/apis/timeseries/
- https://www.fda.gov/medical-devices/mandatory-reporting-requirements-manufacturers-importers-and-device-user-facilities/about-manufacturer-and-user-facility-device-experience-maude-database
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
    "product or official FDA system. It does not replace validated "
    "post-market surveillance or regulatory decision-making."
)

