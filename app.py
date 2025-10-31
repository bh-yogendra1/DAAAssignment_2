import streamlit as st
import pandas as pd
import io
import logging
from datetime import datetime

# -------------------------
# Logger setup
# -------------------------
logger = logging.getLogger("allocation_app")
logger.setLevel(logging.DEBUG)

# Add handlers only once (avoid duplicates when Streamlit re-runs)
if not logger.handlers:
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    fh = logging.FileHandler("allocation_app.log")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)

# -------------------------
# Helper functions
# -------------------------
def find_cgpa_col(cols):
    """Return index of first column containing 'cgpa' (case-insensitive), or None."""
    for i, c in enumerate(cols):
        if "cgpa" in str(c).lower():
            return i
    return None

def allocate_students(df):
    """
    df: input dataframe
    Returns: allocation_df, fac_count_df
    """
    try:
        cols = list(df.columns)
        cgpa_idx = find_cgpa_col(cols)
        if cgpa_idx is None:
            raise ValueError("No column with name containing 'cgpa' found. Please ensure your CSV has a CGPA column.")

        pref_cols = cols[cgpa_idx + 1 :]
        if len(pref_cols) == 0:
            raise ValueError("No preference columns found after the CGPA column. At least one preference column is required.")

        n = len(pref_cols)
        logger.info(f"Detected CGPA column at index {cgpa_idx} ('{cols[cgpa_idx]}'), preference columns: {pref_cols}, n={n}")

        # Ensure cgpa numeric
        cgpa_col = cols[cgpa_idx]
        df[cgpa_col] = pd.to_numeric(df[cgpa_col], errors="coerce")
        if df[cgpa_col].isna().any():
            logger.warning("Some CGPA values could not be converted to numeric (NaN). These rows will be sorted with NaN at the end.")

        # Sort descending CGPA (highest first), tie-breaker: keep original order
        df_sorted = df.sort_values(by=cgpa_col, ascending=False).reset_index(drop=True)

        assigned = []
        for idx, row in df_sorted.iterrows():
            pref_col = pref_cols[idx % n]   # pick preference column in round-robin
            assigned_fac = row[pref_col]
            assigned.append(assigned_fac)

        df_sorted["AssignedFaculty"] = assigned

        # Output file 1: allocation
        allocation_df = df_sorted.copy()

        # Output file 2: faculty preference counts
        fac_count = allocation_df["AssignedFaculty"].value_counts(dropna=False).reset_index()
        fac_count.columns = ["Faculty", "AllocatedCount"]

        return allocation_df, fac_count

    except Exception as e:
        logger.exception("Error during allocation")
        raise

# -------------------------
# Streamlit UI
# -------------------------
st.set_page_config(page_title="MTP Allocation", layout="wide")
st.title("MTP Allocation Tool")



uploaded_file = st.file_uploader("Upload input CSV", type=["csv"])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        st.write("Preview of uploaded data (first 10 rows):")
        st.dataframe(df.head(10))

        # Try to run allocation
        st.info("Running allocation...")
        allocation_df, fac_count_df = allocate_students(df)

        st.success("Allocation completed successfully.")

        st.subheader("Allocation Preview")
        st.dataframe(allocation_df.head(20))

        st.subheader("Faculty Allocation Counts")
        st.dataframe(fac_count_df)

        # Prepare CSVs for download
        allocation_csv = allocation_df.to_csv(index=False).encode("utf-8")
        fac_count_csv = fac_count_df.to_csv(index=False).encode("utf-8")

        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        allocation_filename = f"output_btp_mtp_allocation_{now}.csv"
        fac_count_filename = f"fac_preference_count_{now}.csv"

        st.download_button(
            label="Download allocation CSV",
            data=allocation_csv,
            file_name=allocation_filename,
            mime="text/csv",
        )
        st.download_button(
            label="Download faculty counts CSV",
            data=fac_count_csv,
            file_name=fac_count_filename,
            mime="text/csv",
        )

    except Exception as e:
        logger.exception("Processing error")
        st.error(f"Error: {e}. See logs for details (allocation_app.log).")
else:
    st.info("Please upload an input CSV to start allocation.")
