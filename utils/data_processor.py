import pandas as pd
from fuzzywuzzy import fuzz, process
import numpy as np

class DataProcessor:
    def __init__(self):
        self.expected_cols = [
            'GSTIN of supplier', 'Supplier', 'Invoice number', 
            'Invoice Date', 'Invoice Value', 'Rate', 'Taxable Value',
            'Integrated Tax', 'Central Tax', 'State/UT tax', 'Cess'
        ]
    
    def process_single_file_reconciliation(self, file_path):
        """Process a single Excel file with multiple sheets"""
        try:
            # Read Excel file to check available sheets
            excel_file = pd.ExcelFile(file_path)
            sheets = excel_file.sheet_names
            
            # Look for Tally and GSTR-2A sheets
            tally_sheet = None
            gstr_sheet = None
            
            for sheet in sheets:
                sheet_lower = sheet.lower()
                if 'tally' in sheet_lower:
                    tally_sheet = sheet
                elif 'gstr' in sheet_lower or '2a' in sheet_lower:
                    gstr_sheet = sheet
            
            if not tally_sheet or not gstr_sheet:
                raise Exception("Could not find both 'Tally' and 'GSTR-2A' sheets in the uploaded file. Please ensure your Excel file has sheets named 'Tally' and 'GSTR-2A'.")
            
            # Read the sheets
            df_tally = pd.read_excel(file_path, sheet_name=tally_sheet)
            df_gstr = pd.read_excel(file_path, sheet_name=gstr_sheet)
            
            # Fix column structure
            df_tally = self.fix_data_columns(df_tally, 'Tally')
            df_gstr = self.fix_data_columns(df_gstr, 'GSTR-2A')
            
            # Clean data
            df_tally = self.clean_data(df_tally)
            df_gstr = self.clean_data(df_gstr)
            
            # Perform reconciliation
            results = self.perform_reconciliation(df_tally, df_gstr)
            
            return results
            
        except Exception as e:
            raise Exception(f"Error processing reconciliation: {str(e)}")
    
    def fix_data_columns(self, df, sheet_type):
        """Fix column structure based on the provided data format"""
        # Skip the first row if it contains totals/summaries
        if len(df) > 1:
            # Check if first row contains non-header data (like totals)
            first_row = df.iloc[0]
            if any(pd.isna(first_row.iloc[:2])) and pd.notna(first_row.iloc[2]):
                df = df.iloc[1:].reset_index(drop=True)
        
        # Set proper column names
        if len(df.columns) >= len(self.expected_cols):
            df.columns = self.expected_cols + [f"Extra_Col_{i}" for i in range(len(self.expected_cols), len(df.columns))]
        
        return df
    
    def clean_data(self, df):
        """Clean and standardize data"""
        # Remove empty rows
        df = df.dropna(how='all')
        df = df.dropna(subset=['Supplier', 'Invoice number'])
        
        # Clean GSTIN column - handle missing GSTIN
        if 'GSTIN of supplier' in df.columns:
            df['GSTIN of supplier'] = df['GSTIN of supplier'].fillna('UNKNOWN').astype(str).str.strip()
        
        # Clean supplier names
        if 'Supplier' in df.columns:
            df['Supplier'] = df['Supplier'].astype(str).str.strip()
        
        # Clean invoice numbers
        if 'Invoice number' in df.columns:
            df['Invoice number'] = df['Invoice number'].astype(str).str.strip()
        
        # Ensure numeric columns are properly formatted
        numeric_columns = ['Invoice Value', 'Taxable Value', 'Integrated Tax', 'Central Tax', 'State/UT tax', 'Cess']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        return df
    
    def fuzzy_match_suppliers(self, tally_suppliers, gstr_suppliers, threshold=80):
        """Perform fuzzy matching on supplier names"""
        matches = {}
        for tally_supplier in tally_suppliers:
            match = process.extractOne(tally_supplier, gstr_suppliers, scorer=fuzz.ratio)
            if match and match[1] >= threshold:
                matches[tally_supplier] = match[0]
        return matches
    
    def perform_reconciliation(self, df_tally, df_gstr):
        """Main reconciliation logic"""
        results = {
            'matched_records': [],
            'unmatched_tally': [],
            'unmatched_gstr': [],
            'discrepancies': [],
            'summary': {}
        }
        
        # Create matching keys using invoice number primarily
        df_tally['match_key'] = df_tally['Invoice number'].astype(str)
        df_gstr['match_key'] = df_gstr['Invoice number'].astype(str)
        
        # Find exact matches by invoice number
        matched_keys = set(df_tally['match_key']).intersection(set(df_gstr['match_key']))
        
        for key in matched_keys:
            tally_records = df_tally[df_tally['match_key'] == key]
            gstr_records = df_gstr[df_gstr['match_key'] == key]
            
            # Handle multiple records with same invoice number
            for _, tally_record in tally_records.iterrows():
                for _, gstr_record in gstr_records.iterrows():
                    # Check for discrepancies
                    discrepancy = self.check_discrepancy(tally_record, gstr_record)
                    
                    match_record = {
                        'gstin': tally_record['GSTIN of supplier'],
                        'supplier_tally': tally_record['Supplier'],
                        'supplier_gstr': gstr_record['Supplier'],
                        'invoice_number': tally_record['Invoice number'],
                        'tally_value': tally_record['Invoice Value'],
                        'gstr_value': gstr_record['Invoice Value'],
                        'status': 'Discrepancy' if discrepancy else 'Matched',
                        'discrepancy_details': discrepancy
                    }
                    
                    if discrepancy:
                        results['discrepancies'].append(match_record)
                    else:
                        results['matched_records'].append(match_record)
        
        # Find unmatched records
        unmatched_tally_keys = set(df_tally['match_key']) - matched_keys
        unmatched_gstr_keys = set(df_gstr['match_key']) - matched_keys
        
        for key in unmatched_tally_keys:
            records = df_tally[df_tally['match_key'] == key]
            for _, record in records.iterrows():
                results['unmatched_tally'].append({
                    'gstin': record['GSTIN of supplier'],
                    'supplier': record['Supplier'],
                    'invoice_number': record['Invoice number'],
                    'invoice_value': record['Invoice Value']
                })
        
        for key in unmatched_gstr_keys:
            records = df_gstr[df_gstr['match_key'] == key]
            for _, record in records.iterrows():
                results['unmatched_gstr'].append({
                    'gstin': record['GSTIN of supplier'],
                    'supplier': record['Supplier'],
                    'invoice_number': record['Invoice number'],
                    'invoice_value': record['Invoice Value']
                })
        
        # Generate summary
        results['summary'] = {
            'total_tally_records': len(df_tally),
            'total_gstr_records': len(df_gstr),
            'matched_records': len(results['matched_records']),
            'discrepancies': len(results['discrepancies']),
            'unmatched_tally': len(results['unmatched_tally']),
            'unmatched_gstr': len(results['unmatched_gstr']),
            'match_percentage': round((len(results['matched_records']) / max(len(df_tally), 1)) * 100, 2)
        }
        
        return results
    
    def check_discrepancy(self, tally_record, gstr_record):
        """Check for discrepancies between matched records"""
        discrepancies = []
        tolerance = 0.01
        
        # Check invoice value
        if abs(float(tally_record['Invoice Value']) - float(gstr_record['Invoice Value'])) > tolerance:
            discrepancies.append(f"Invoice Value: Tally={tally_record['Invoice Value']}, GSTR={gstr_record['Invoice Value']}")
        
        # Check taxable value
        if abs(float(tally_record['Taxable Value']) - float(gstr_record['Taxable Value'])) > tolerance:
            discrepancies.append(f"Taxable Value: Tally={tally_record['Taxable Value']}, GSTR={gstr_record['Taxable Value']}")
        
        # Check tax amounts
        tax_fields = ['Integrated Tax', 'Central Tax', 'State/UT tax']
        for field in tax_fields:
            if abs(float(tally_record[field]) - float(gstr_record[field])) > tolerance:
                discrepancies.append(f"{field}: Tally={tally_record[field]}, GSTR={gstr_record[field]}")
        
        return discrepancies if discrepancies else None
