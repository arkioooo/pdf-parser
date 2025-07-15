from dotenv import load_dotenv
import os
import fitz
import pandas as pd
import numpy as np
import requests
import json
from fuzzywuzzy import process
from pdf2image import convert_from_path
import pytesseract
import re
import pandas as pd

load_dotenv()
poppler_bin = os.getenv('poppler_bin')

if poppler_bin is None:
    raise ValueError("Environment variable poppler_bin is not set!")
print("Poppler path being used:", poppler_bin)

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

def ocr_extract_account_info(pdf_path, poppler_bin):
    # Convert first page (or all) to image(s)
    images = convert_from_path(pdf_path, dpi=300, poppler_path=poppler_bin)
    first_page_text = pytesseract.image_to_string(images[0])  # OCR first page only

    # Use regex or manual string search for account number and name
    # Customize these regex patterns to your PDF text layout
    acc_no_match = re.search(r'Account Number[:\s]*([\d]+)', first_page_text, re.IGNORECASE)
    acc_name_match = re.search(r'Account Holders? Name[:\s]*([A-Z\s]+)', first_page_text, re.IGNORECASE)

    acc_no = acc_no_match.group(1).strip() if acc_no_match else None
    acc_name = acc_name_match.group(1).strip() if acc_name_match else None

    return acc_name, acc_no

def calculate_metrics(df):
    total_credit = 0
    total_debit = 0
    opening_bal = 0
    b1 = 0
    closing_bal = 0
    d1 = 0
    c1 = 0

    if 'date' in df.columns and df['date'].notnull().any():
        if 'debit' in df.columns:
            debit_str = df['debit'].astype(str).fillna('')  # Fill NaNs with empty string
            debit_str = debit_str.str.replace(',', '', regex=False).str.strip()
            debit_str = debit_str.replace('', '0')  # Replace empty strings with '0'
            total_debit = pd.to_numeric(debit_str, errors='coerce').sum()
            d1_str = debit_str.iloc[0]  # first row as string (still string here)
            d1 = pd.to_numeric(d1_str, errors='coerce')

        if 'credit' in df.columns:
            credit_str = df['credit'].astype(str).fillna('')  # Fill NaNs with empty string
            credit_str = credit_str.str.replace(',', '', regex=False).str.strip()
            credit_str = credit_str.replace('', '0')  # Replace empty strings with '0'
            total_credit = pd.to_numeric(credit_str, errors='coerce').sum()
            c1_str = credit_str.iloc[0]  # first row as string
            c1 = pd.to_numeric(c1_str, errors='coerce')

        if 'balance' in df.columns:
            balances = pd.to_numeric(df['balance'].replace('', '0').str.replace(',', '', regex=False), errors='coerce')
            b1 = balances.iloc[0] if not balances.empty else 0
            closing_bal = balances.iloc[-1] if not balances.empty else 0
    else:
        print("No debit/credit rows found")
        pass
    
    opening_bal = b1 - c1 + d1
    return total_debit,total_credit,opening_bal,closing_bal

def extract_transactions(df):
    header_row_idx = None
    for i, row in df.iterrows():
        if any("tran date" in str(cell).lower() for cell in row):
            header_row_idx = i
            break
    if header_row_idx is None:
        raise ValueError("Transaction header row not found.")

    new_header = df.iloc[header_row_idx]
    df_txn = df.iloc[header_row_idx+1:].copy()
    df_txn.columns = new_header
    df_txn = df_txn.reset_index(drop=True)

    # Remove the row that contains "opening balance" in any cell (case-insensitive)
    mask_opening = df_txn.apply(lambda row: row.astype(str).str.lower().str.contains("opening balance").any(), axis=1)
    df_txn = df_txn.loc[~mask_opening].reset_index(drop=True)

    # If you want to apply end_key logic (e.g., remove everything after a row containing "Transaction")
    end_key = "transaction"
    mask_end = df_txn.apply(lambda row: row.astype(str).str.lower().str.contains(end_key).any(), axis=1)
    if mask_end.any():
        first_idx = mask_end.idxmax()
        df_txn = df_txn.loc[:first_idx-1].copy() if first_idx > 0 else pd.DataFrame(columns=df_txn.columns)

    return df_txn

def standardize(df):
    df = df.loc[:, ~df.columns.duplicated()]
    df.columns = df.columns.astype(str)
    df.columns = (df.columns
                  .str.strip()
                  .str.lower()
                  .str.replace(r'\s+', '_', regex=True)
                  .str.replace(r'\.', '', regex=True))
    
    # Detect if 'dr/cr' and 'amount' columns are present (some variants allowed)
    drcr_col = None
    amount_col = None
    for col in df.columns:
        if col in ['dr/cr', 'dr_cr', 'drcr']:
            drcr_col = col
        if col in ['amount(inr)', 'amount', 'amt']:
            amount_col = col

    standard_cols = ['date', 'particulars', 'debit', 'credit', 'balance']
    matched_cols = {}
    used_cols = set()

    # If we have dr/cr and amount columns, we'll handle debit and credit separately later
    skip_cols = set()
    if drcr_col and amount_col:
        skip_cols.add('debit')
        skip_cols.add('credit')

    # Fuzzy match columns except debit and credit if dr/cr & amount are detected
    for std_col in standard_cols:
        if std_col in skip_cols:
            matched_cols[std_col] = None
            continue
        
        match, score = process.extractOne(std_col, df.columns)
        if score > 60 and match not in used_cols:
            matched_cols[std_col] = match
            used_cols.add(match)
        else:
            matched_cols[std_col] = None
    
    std_df = pd.DataFrame()
    for std_col in standard_cols:
        if std_col in ['debit', 'credit'] and drcr_col and amount_col:
            # populate debit and credit based on dr/cr and amount columns
            std_df['debit'] = ""
            std_df['credit'] = ""
            drcr_vals = df[drcr_col].str.lower().str.strip()
            amounts = df[amount_col]
            std_df.loc[drcr_vals == 'dr', 'debit'] = amounts[drcr_vals == 'dr']
            std_df.loc[drcr_vals == 'cr', 'credit'] = amounts[drcr_vals == 'cr']
        else:
            if matched_cols[std_col]:
                # For balance, clean data a bit to avoid NaNs downstream
                if std_col == 'balance':
                    bal_col = df[matched_cols[std_col]].astype(str).str.replace(',', '', regex=False).str.strip()
                    bal_col = bal_col.replace('', '0')  # Replace empty string with '0'
                    std_df[std_col] = bal_col
                else:
                    std_df[std_col] = df[matched_cols[std_col]]
            else:
                if std_col == 'balance':
                    std_df[std_col] = '0'
                else:
                    std_df[std_col] = ""
    return std_df

def clean_repeated_headers(df):
    mask = df.apply(lambda row: row.astype(str).str.lower().str.contains("txn date").any(), axis=1)
    df_clean = df[~mask].copy()
    df_clean = df_clean.dropna(how='all')
    df_clean = df_clean.reset_index(drop=True)
    return df_clean

# def clean_description(df):
#     if 'description' in df.columns:
#         df['description'] = df['description'].apply(clean_text)
#     else:
#         df['description'] = ""
#     return df 

def run(pdf_path, poppler_bin):
    # acc_name, acc_no = ocr_extract_account_info(pdf_path, poppler_bin)
    raw_table = extract_all_tables(pdf_path)
    if raw_table is None:
        return None, (0,0,0,0)
    txn_df = extract_transactions(raw_table)
    txn_df = clean_repeated_headers(txn_df)
    std_df = standardize(txn_df)
    total_debit, total_credit, opening_bal, closing_bal = calculate_metrics(std_df)
    return std_df, (total_debit, total_credit, opening_bal, closing_bal)
