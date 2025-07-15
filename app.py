import streamlit as st
import time
import os
import tempfile
import pandas as pd
from dotenv import load_dotenv

st.set_page_config(page_title="PDF Bank Statement Parser", layout="wide")
st.title("PDF Bank Statement Parser")

load_dotenv()
poppler_bin = os.getenv('poppler_bin')

banks = [
    'Canara Bank', 'Axis Bank', 'SBI', 'Yes Bank (MSME)', 'ICICI Bank', 'PNB',
    'City Union Bank', 'IDBI', 'Federal Bank', 'Indian Bank'
]
selected_bank = st.selectbox("Select a bank", banks)

bank_scripts = {
    'Canara Bank': 'scripts.script_canara',
    'Axis Bank': 'scripts.script_axis',
    'SBI': 'scripts.script_sbi',
    'Yes Bank (MSME)': 'scripts.script_yesmsme',
    'ICICI Bank': 'scripts.script_icici',
    'PNB': 'scripts.script_pnb',
    'City Union Bank': 'scripts.script_cityunion',
    'IDBI': 'scripts.script_idbi',
    'Federal Bank': 'scripts.script_federal',
    'Indian Bank': 'scripts.script_indianbank',
}

def save_uploaded_file(uploadedfile, save_dir):
    file_path = os.path.join(save_dir, uploadedfile.name)
    with open(file_path, "wb") as f:
        f.write(uploadedfile.getbuffer())
    return file_path

uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])

if uploaded_file:
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = save_uploaded_file(uploaded_file, tmpdir)

        if not os.path.exists(pdf_path):
            st.error(f"PDF file not found at {pdf_path}")
        elif not os.path.isfile(pdf_path):
            st.error(f"Expected a file but got a directory at {pdf_path}")
        else:
            st.markdown(f"**Uploaded File:** `{uploaded_file.name}`")
            with st.spinner("Processing the file..."):
                try:
                    if selected_bank:
                        module_name = bank_scripts.get(selected_bank)
                        if module_name:
                            # Dynamically import the required script
                            module = __import__(module_name, fromlist=[''])
                            result = module.run(pdf_path, poppler_bin)
                            if result is not None:
                                df, metrics = result
                                total_debit, total_credit, opening_bal, closing_bal = metrics

                                st.subheader("Extracted Transactions")
                                if df is not None and not df.empty:
                                    st.dataframe(df)
                                else:
                                    st.info("No transactions extracted from the PDF.")

                                st.subheader("Summary")
                                metric_data = {
                                    "Total Credit": total_credit,
                                    "Total Debit": total_debit,
                                    "Opening Balance": opening_bal,
                                    "Closing Balance": closing_bal,
                                }
                                st.table(pd.DataFrame(list(metric_data.items()), columns=["Metric", "Value"]))
                            else:
                                st.warning("No data returned from processing script.")
                        else:
                            st.warning(f"No script found for {selected_bank}")
                except Exception as e:
                    st.error(f"An error occurred while processing: {e}")
