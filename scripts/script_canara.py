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

# def extract_info(df):
#     keywords = ['account holders name', 'account number', 'opening balance', 'closing balance']
#     acc_name, acc_no, opening_bal, closing_bal = None, None, 0, 0
    
#     for kw in keywords:
#         # Find rows where the first column contains the keyword (case-insensitive)
#         match = df.iloc[:, 0].str.lower().str.contains(kw, na=False)
        
#         if match.any():
#             matched_row = df[match].iloc[0]
#             value = matched_row.iloc[1]  # Get the adjacent cell in the second column
            
#             # Remove possible currency symbol and commas for balance
#             if kw in ['opening balance', 'closing balance']:
#                 # Clean and convert to numeric
#                 value = str(value).replace('Rs.', '').replace(',', '').strip()
#                 try:
#                     value = float(value)
#                 except:
#                     value = 0
            
#             if kw == 'account holders name':
#                 acc_name = value
#             elif kw == 'account number':
#                 acc_no = value
#             elif kw == 'opening balance':
#                 opening_bal = value
#             elif kw == 'closing balance':
#                 closing_bal = value
    
#     return acc_name, acc_no, opening_bal, closing_bal


def extract_transactions(df):
    header_row_idx = None
    for i, row in df.iterrows():
        if any("txn date" in str(cell).lower() for cell in row):
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
    standard_cols = ['date', 'description', 'debit', 'credit', 'balance']
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
            std_df[std_col] = df[matched_cols[std_col]]
        else:
            std_df[std_col] = ""
    return std_df

def clean_repeated_headers(df):
    mask = df.apply(lambda row: row.astype(str).str.lower().str.contains("txn date").any(), axis=1)
    df_clean = df[~mask].copy()
    df_clean = df_clean.dropna(how='all')
    df_clean = df_clean.reset_index(drop=True)
    return df_clean

def calculate_metrics(df):
    """Calculate total debit, credit, opening and closing balance"""
    total_credit = 0
    total_debit = 0
    opening_bal = 0
    closing_bal = 0

    if 'date' in df.columns and df['date'].notnull().any():
        if 'debit' in df.columns:
                debit_str = df['debit'].astype(str).replace('nan', '').str.replace(',', '', regex=False).str.strip()
                debit_str = debit_str.replace('', '0')
                total_debit = pd.to_numeric(debit_str, errors='coerce').sum()
        if 'credit' in df.columns:
                credit_str = df['credit'].astype(str).replace('nan', '').str.replace(',', '', regex=False).str.strip()
                credit_str = credit_str.replace('', '0')
                total_credit = pd.to_numeric(credit_str, errors='coerce').sum()
        if 'balance' in df.columns:
            balances = pd.to_numeric(df['balance'].replace('', '0').str.replace(',', '', regex=False), errors='coerce')
            opening_bal = balances.iloc[0] if not balances.empty else 0
            closing_bal = balances.iloc[-1] if not balances.empty else 0
    else:
        print("No debit/credit rows found")
        pass

    return total_credit, total_debit, opening_bal, closing_bal
    # print("Total credit :", total_credit)
    # print("Total debit :", total_debit)
    # print("Opening balance :", opening_bal)
    # print("Closing balance :", closing_bal)
    # print(total_credit - total_debit)
    # print(closing_bal - opening_bal)

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
    # acc_name, acc_no, opening_bal, closing_bal = extract_info(raw_table)
    txn_df = extract_transactions(raw_table)
    txn_df = clean_repeated_headers(txn_df)
    std_df = standardize(txn_df)
    total_credit, total_debit, opening_bal, closing_bal = calculate_metrics(std_df)
    return std_df, (total_credit, total_debit, opening_bal, closing_bal)
