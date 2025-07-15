# PDF Bank Statement Parser

A **Streamlit web application** that extracts transaction data and calculates key financial metrics from bank statement PDFs. The application supports multiple banks and provides an intuitive interface for uploading and processing bank statements.

## Features

- **Multi-bank support**: Supports 10 major banks including SBI, ICICI, HDFC, Axis Bank, and more
- **Automated data extraction**: Extracts transaction details, amounts, dates, and descriptions
- **Financial metrics calculation**: Computes total credits, debits, opening balance, and closing balance
- **Clean data presentation**: Displays extracted data in an organized tabular format
- **Error handling**: Robust error handling for various PDF formats and edge cases

## Supported Banks

- Canara Bank
- Axis Bank
- State Bank of India (SBI)
- Yes Bank (MSME)
- ICICI Bank
- Punjab National Bank (PNB)
- City Union Bank
- IDBI Bank
- Federal Bank
- Indian Bank

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Setup

1. **Clone the repository**:
```bash
git clone https://github.com/yourusername/pdf-bank-statement-parser.git
cd pdf-bank-statement-parser
```

2. **Create a virtual environment**:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**:
Create a `.env` file in the root directory:
```
poppler_bin=path/to/poppler/bin
```

## Usage

### Running the Application

1. **Start the Streamlit app**:
```bash
streamlit run app.py
```

2. **Open your browser** and navigate to `http://localhost:8501`

3. **Upload a bank statement PDF**:
   - Select your bank from the dropdown
   - Upload your PDF file using the file uploader
   - Wait for processing to complete

4. **View results**:
   - Review extracted transactions in the data table
   - Check financial summary metrics
   - Export data if needed

### Example Output

The application provides:
- **Transaction Table**: Date, Description, Debit, Credit, Balance
- **Financial Summary**:
  - Total Credits: ₹50,000
  - Total Debits: ₹25,000
  - Opening Balance: ₹10,000
  - Closing Balance: ₹35,000

## Project Structure

```
pdf-parser/
├── app.py                 # Main Streamlit application
├── scripts/              # Bank-specific parsing scripts
│   ├── script_sbi.py
│   ├── script_icici.py
│   ├── script_axis.py
│   └── ...
├── .env                  # Environment variables
├── requirements.txt      # Python dependencies
├── .gitignore           # Git ignore file
└── README.md            # This file
```

## Technical Details

### Dependencies

- **Streamlit**: Web application framework
- **PyMuPDF (fitz)**: PDF text extraction
- **pandas**: Data manipulation and analysis
- **numpy**: Numerical computations
- **python-dotenv**: Environment variable management
- **fuzzywuzzy**: Fuzzy string matching for column detection

### Key Components

1. **PDF Processing**: Uses PyMuPDF for reliable text extraction from bank statement PDFs
2. **Data Standardization**: Normalizes column names and data formats across different banks
3. **Transaction Parsing**: Extracts transaction details using regex patterns and fuzzy matching
4. **Metric Calculation**: Computes financial summaries with validation checks

## Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature-name`
3. **Make your changes** and test thoroughly
4. **Submit a pull request** with a clear description

### Adding New Banks

To add support for a new bank:

1. Create a new script file in `/scripts/` (e.g., `script_newbank.py`)
2. Implement the required functions following the existing pattern
3. Add the bank to the `banks` list and `bank_scripts` dictionary in `app.py`
4. Test with sample statements from the new bank

## Known Limitations

- PDF quality affects extraction accuracy
- Complex table layouts may require manual adjustments
- Some bank-specific formatting nuances may need fine-tuning
- Large PDF files may take longer to process

## Troubleshooting

### Common Issues

1. **"Transaction header row not found"**: 
   - Ensure PDF contains recognizable transaction headers
   - Check if bank script supports your specific statement format

2. **"No tables found in PDF"**:
   - Verify PDF contains actual tables (not just images)
   - Try with a different PDF or contact support

3. **Environment variable errors**:
   - Ensure `.env` file is properly configured
   - Check poppler installation path    

## Support

For issues and questions:
- Open an issue on GitHub
- Check existing documentation
- Contact the development team

**Note**: This tool is designed for personal finance management and should not be used for commercial purposes without proper testing and validation.