from dotenv import load_dotenv
import os
import fitz
import pandas as pd
import numpy as np
import requests
import json
from fuzzywuzzy import process
import re

load_dotenv()
poppler_bin = os.getenv('poppler_bin')

if poppler_bin is None:
    raise ValueError("Environment variable poppler_bin is not set!")

def extract_all_tables(pdf_path):
    tables = []
    doc = fitz.open(pdf_path)

    for page_number, page in enumerate(doc, 1):
        table_data = page.find_tables()
        if table_data.tables:
            for table in table_data.tables:
                raw_data = table.extract()
                if raw_data and len(raw_data):
                    df = pd.DataFrame(raw_data)
                    tables.append(df)
    
    if not tables:
        print("No tables found in the PDF.")
        return None
    
    result_df = pd.concat(tables, ignore_index=True)
    result_df = result_df.dropna(how='all')  # drop empty rows
    return result_df

def clean_balance(val):
    if pd.isna(val):
        return np.nan
    s = str(val).strip()
    # Remove newlines inside string
    s = s.replace('\n', '')
    # Remove commas
    s = s.replace(',', '')
    # Remove trailing Dr. or Cr. (case-insensitive), allowing spaces and dots before Dr/Cr
    s = re.sub(r'[\s\.]*(Dr\.?|Cr\.?)$', '', s, flags=re.IGNORECASE)
    s = s.strip()
    try:
        return float(s)
    except:
        return np.nan

def extract_transactions(df):
    header_row_idx = None
    for i, row in df.iterrows():
        if any("txn no." in str(cell).lower() for cell in row):
            header_row_idx = i
            break
    if header_row_idx is None:
        raise ValueError("Transaction header row not found.")

    new_header = df.iloc[header_row_idx]
    df_txn = df.iloc[header_row_idx+1:].copy()
    df_txn.columns = new_header
    df_txn = df_txn.reset_index(drop=True)
    return df_txn

def standardize(df):
    df = df.loc[:, ~df.columns.duplicated()]
    df.columns = df.columns.astype(str)
    df.columns = (df.columns
                  .str.strip()
                  .str.lower()
                  .str.replace(r'\s+', '_', regex=True)
                  .str.replace(r'\.', '', regex=True))
    standard_cols = ['date', 'description', 'dr amount', 'cr amount', 'balance']
    matched_cols = {}
    used_cols = set()
    for std_col in standard_cols:
        match, score = process.extractOne(std_col, df.columns)
        if score > 60 and match not in used_cols:
            matched_cols[std_col] = match
            used_cols.add(match)
        else:
            matched_cols[std_col] = None

    std_df = pd.DataFrame()
    for std_col in standard_cols:
        if matched_cols[std_col]:
            col_data = df[matched_cols[std_col]].astype(str).str.strip()
            std_df[std_col] = col_data
        else:
            std_df[std_col] = ""
    
    # print("Raw balance values before cleaning:")
    # print(std_df['balance'].head(10))

    # Now clean the balance column *after* assigning it as string
    std_df['balance'] = std_df['balance'].apply(clean_balance)

    return std_df

def clean_repeated_headers(df):
    mask = df.apply(lambda row: row.astype(str).str.lower().str.contains("txn date").any(), axis=1)
    df_clean = df[~mask].copy()
    df_clean = df_clean.dropna(how='all')
    df_clean = df_clean.reset_index(drop=True)
    return df_clean
def calculate_metrics(df):
    total_credit = 0
    total_debit = 0
    opening_bal = 0
    closing_bal = 0

    # Clean balance column using the helper
    df['balance'] = df['balance'].apply(clean_balance)

    if 'dr amount' in df.columns:
        debit_str = df['dr amount'].astype(str).fillna('')
        debit_str = debit_str.str.replace(',', '', regex=False).str.strip()
        debit_str = debit_str.replace('', '0')
        total_debit = pd.to_numeric(debit_str, errors='coerce').sum()

    if 'cr amount' in df.columns:
        credit_str = df['cr amount'].astype(str).fillna('')
        credit_str = credit_str.str.replace(',', '', regex=False).str.strip()
        credit_str = credit_str.replace('', '0')
        total_credit = pd.to_numeric(credit_str, errors='coerce').sum()

    balances = df['balance']
    if not balances.empty:
        opening_bal = balances.iloc[0]
        closing_bal = balances.iloc[-1]

    return total_debit, total_credit, opening_bal, closing_bal

# def clean_description(df):
#     if 'description' in df.columns:
#         df['description'] = df['description'].apply(clean_text)
#     else:
#         df['description'] = ""
#     return df 

def run(pdf_path, poppler_bin):
    raw_table = extract_all_tables(pdf_path)
    if raw_table is None:
        return None, (0,0,0,0)
    txn_df = extract_transactions(raw_table)
    txn_df = clean_repeated_headers(txn_df)
    std_df = standardize(txn_df)
    # print(std_df['balance'].head())
    total_debit, total_credit, opening_bal, closing_bal = calculate_metrics(std_df)
    return std_df, (total_credit, total_debit, opening_bal, closing_bal)
