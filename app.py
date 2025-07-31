from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify, session
import pandas as pd
from fuzzywuzzy import fuzz, process
from openpyxl import load_workbook
from openpyxl.styles import Font
from openpyxl.utils.dataframe import dataframe_to_rows
import os
import io
import tempfile
from datetime import datetime
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Utility Functions from Streamlit app
def get_column(df, colname):
    """Handle integer column names properly"""
    for col in df.columns:
        col_str = str(col).strip().lower()
        colname_str = str(colname).strip().lower()
        if col_str == colname_str:
            return col
    raise KeyError(f"Column '{colname}' not found. Available columns: {df.columns.tolist()}")

def get_raw_unique_names(series):
    return pd.Series(series).dropna().drop_duplicates().tolist()

def fix_tally_columns(df_tally):
    """Fix Tally sheet column structure when headers are wrong"""
    expected_cols = [
        'GSTIN of supplier', 'Supplier', 'Invoice number', 'Invoice Date', 
        'Invoice Value', 'Rate', 'Taxable Value', 'Integrated Tax', 
        'Central Tax', 'State/UT tax', 'Cess'
    ]
    
    if (len(df_tally.columns) >= 2 and 
        str(df_tally.columns[0]).startswith('Unnamed') and 
        not any(col.lower().strip() == 'supplier' for col in df_tally.columns)):
        
        new_columns = []
        for i, col in enumerate(df_tally.columns):
            if i < len(expected_cols):
                new_columns.append(expected_cols[i])
            else:
                new_columns.append(f"Column_{i}")
        df_tally.columns = new_columns
    return df_tally

def process_single_file_reconciliation(file_path):
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
        tally_df = pd.read_excel(file_path, sheet_name=tally_sheet)
        gstr_df = pd.read_excel(file_path, sheet_name=gstr_sheet)
        
        # Fix columns
        tally_df = fix_tally_columns(tally_df)
        
        # Process reconciliation
        results = process_reconciliation(tally_df, gstr_df)
        
        return results
        
    except Exception as e:
        raise Exception(f"Error processing reconciliation: {str(e)}")

def create_default_format():
    """Create default Excel format with both sheets in one file"""
    # Sample data for Tally sheet
    tally_data = {
        'GSTIN of supplier': ['27AABCU9603R1ZX', '27AABCU9603R1ZY', ''],
        'Supplier': ['ABC Private Ltd', 'XYZ Industries', 'GHI Enterprises'],
        'Invoice number': ['INV-0001', 'INV-0002', 'INV-0003'],
        'Invoice Date': ['15-04-2024', '20-04-2024', '25-04-2024'],
        'Invoice Value': [118000, 177000, 112000],
        'Rate': [18, 18, 12],
        'Taxable Value': [100000, 150000, 100000],
        'Integrated Tax': [0, 27000, 0],
        'Central Tax': [9000, 0, 6000],
        'State/UT tax': [9000, 0, 6000],
        'Cess': [0, 0, 0]
    }
    
    # Sample data for GSTR-2A sheet
    gstr_data = {
        'GSTIN of supplier': ['27AABCU9603R1ZX', '27AABCU9603R1ZZ', ''],
        'Supplier': ['ABC Private Limited', 'DEF Corporation', 'GHI Enterprises'],
        'Invoice number': ['INV-0001', 'INV-0004', 'INV-0003'],
        'Invoice Date': ['15-04-2024', '25-04-2024', '25-04-2024'],
        'Invoice Value': [118000, 89600, 112000],
        'Rate': [18, 12, 12],
        'Taxable Value': [100000, 80000, 100000],
        'Integrated Tax': [0, 0, 0],
        'Central Tax': [9000, 4800, 6000],
        'State/UT tax': [9000, 4800, 6000],
        'Cess': [0, 0, 0]
    }
    
    df_tally = pd.DataFrame(tally_data)
    df_gstr = pd.DataFrame(gstr_data)
    
    # Create Excel in memory with both sheets
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Write Tally sheet
        df_tally.to_excel(writer, sheet_name='Tally', index=False)
        
        # Write GSTR-2A sheet
        df_gstr.to_excel(writer, sheet_name='GSTR-2A', index=False)
        
        # Add instructions sheet
        instructions = pd.DataFrame({
            'Instructions': [
                '1. This file contains sample data for GST Reconciliation',
                '2. Sheet "Tally" contains Tally export data',
                '3. Sheet "GSTR-2A" contains GSTR-2A portal data',
                '4. Replace sample data with your actual data',
                '5. Ensure column names match the sample format',
                '6. Upload this file to the reconciliation tool',
                '',
                'Required Sheets:',
                '- Tally (Your Tally data export)',
                '- GSTR-2A (Your GSTR-2A download)',
                '',
                'Important: Keep the sheet names as "Tally" and "GSTR-2A"'
            ]
        })
        instructions.to_excel(writer, sheet_name='Instructions', index=False)
    
    output.seek(0)
    return output.getvalue()

def process_reconciliation(tally_df, gstr_df):
    """Main reconciliation function from Streamlit app"""
    try:
        # Clean data
        tally_df = tally_df.dropna(how='all')
        gstr_df = gstr_df.dropna(how='all')
        
        # Create matching keys
        tally_df['match_key'] = (tally_df['GSTIN of supplier'].astype(str) + '_' + 
                                tally_df['Invoice number'].astype(str))
        gstr_df['match_key'] = (gstr_df['GSTIN of supplier'].astype(str) + '_' + 
                               gstr_df['Invoice number'].astype(str))
        
        # Initialize results
        results = {
            'matched_records': [],
            'unmatched_tally': [],
            'unmatched_gstr': [],
            'discrepancies': [],
            'summary': {}
        }
        
        # Find matches
        tally_keys = set(tally_df['match_key'])
        gstr_keys = set(gstr_df['match_key'])
        matched_keys = tally_keys.intersection(gstr_keys)
        
        # Process matches
        for key in matched_keys:
            tally_record = tally_df[tally_df['match_key'] == key].iloc[0]
            gstr_record = gstr_df[gstr_df['match_key'] == key].iloc[0]
            
            # Check for discrepancies
            discrepancy_details = []
            tolerance = 0.01
            
            if abs(float(tally_record['Invoice Value']) - float(gstr_record['Invoice Value'])) > tolerance:
                discrepancy_details.append(f"Invoice Value: Tally={tally_record['Invoice Value']}, GSTR={gstr_record['Invoice Value']}")
            
            if abs(float(tally_record['Taxable Value']) - float(gstr_record['Taxable Value'])) > tolerance:
                discrepancy_details.append(f"Taxable Value: Tally={tally_record['Taxable Value']}, GSTR={gstr_record['Taxable Value']}")
            
            match_record = {
                'gstin': tally_record['GSTIN of supplier'],
                'supplier_tally': tally_record['Supplier'],
                'supplier_gstr': gstr_record['Supplier'],
                'invoice_number': tally_record['Invoice number'],
                'tally_value': tally_record['Invoice Value'],
                'gstr_value': gstr_record['Invoice Value'],
                'status': 'Discrepancy' if discrepancy_details else 'Matched',
                'discrepancy_details': discrepancy_details
            }
            
            if discrepancy_details:
                results['discrepancies'].append(match_record)
            else:
                results['matched_records'].append(match_record)
        
        # Unmatched records
        unmatched_tally_keys = tally_keys - matched_keys
        unmatched_gstr_keys = gstr_keys - matched_keys
        
        for key in unmatched_tally_keys:
            record = tally_df[tally_df['match_key'] == key].iloc[0]
            results['unmatched_tally'].append({
                'gstin': record['GSTIN of supplier'],
                'supplier': record['Supplier'],
                'invoice_number': record['Invoice number'],
                'invoice_value': record['Invoice Value']
            })
        
        for key in unmatched_gstr_keys:
            record = gstr_df[gstr_df['match_key'] == key].iloc[0]
            results['unmatched_gstr'].append({
                'gstin': record['GSTIN of supplier'],
                'supplier': record['Supplier'],
                'invoice_number': record['Invoice number'],
                'invoice_value': record['Invoice Value']
            })
        
        # Summary
        results['summary'] = {
            'total_tally_records': len(tally_df),
            'total_gstr_records': len(gstr_df),
            'matched_records': len(results['matched_records']),
            'discrepancies': len(results['discrepancies']),
            'unmatched_tally': len(results['unmatched_tally']),
            'unmatched_gstr': len(results['unmatched_gstr']),
            'match_percentage': round((len(results['matched_records']) / max(len(tally_df), 1)) * 100, 2)
        }
        
        return results
        
    except Exception as e:
        raise Exception(f"Error processing reconciliation: {str(e)}")

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'gst_file' not in request.files:
        flash('Please select a GST reconciliation file', 'error')
        return redirect(url_for('index'))
    
    gst_file = request.files['gst_file']
    
    if gst_file.filename == '':
        flash('Please select a file', 'error')
        return redirect(url_for('index'))
    
    if not allowed_file(gst_file.filename):
        flash('Only Excel files (.xlsx, .xls) are allowed', 'error')
        return redirect(url_for('index'))
    
    try:
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
        
        # Save uploaded file
        gst_filename = secure_filename(f"{session_id}_gst_data.xlsx")
        gst_path = os.path.join(app.config['UPLOAD_FOLDER'], gst_filename)
        
        gst_file.save(gst_path)
        
        # Process the single file with multiple sheets
        results = process_single_file_reconciliation(gst_path)
        
        # Store results in session
        session['results'] = results
        
        flash('File processed successfully!', 'success')
        return redirect(url_for('results'))
        
    except Exception as e:
        flash(f'Error processing file: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/results')
def results():
    if 'results' not in session:
        flash('No results found. Please upload files first.', 'error')
        return redirect(url_for('index'))
    
    return render_template('results.html', results=session['results'])

@app.route('/download_report')
def download_report():
    if 'results' not in session or 'session_id' not in session:
        flash('No results found. Please upload files first.', 'error')
        return redirect(url_for('index'))
    
    try:
        results = session['results']
        session_id = session['session_id']
        
        # Create Excel report
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Summary sheet
            summary_data = {
                'Metric': ['Total Tally Records', 'Total GSTR Records', 'Matched Records', 
                          'Discrepancies', 'Unmatched Tally', 'Unmatched GSTR', 'Match Percentage'],
                'Value': [
                    results['summary']['total_tally_records'],
                    results['summary']['total_gstr_records'],
                    results['summary']['matched_records'],
                    results['summary']['discrepancies'],
                    results['summary']['unmatched_tally'],
                    results['summary']['unmatched_gstr'],
                    f"{results['summary']['match_percentage']}%"
                ]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
            
            # Matched records
            if results['matched_records']:
                pd.DataFrame(results['matched_records']).to_excel(writer, sheet_name='Matched Records', index=False)
            
            # Discrepancies
            if results['discrepancies']:
                pd.DataFrame(results['discrepancies']).to_excel(writer, sheet_name='Discrepancies', index=False)
            
            # Unmatched Tally
            if results['unmatched_tally']:
                pd.DataFrame(results['unmatched_tally']).to_excel(writer, sheet_name='Unmatched Tally', index=False)
            
            # Unmatched GSTR
            if results['unmatched_gstr']:
                pd.DataFrame(results['unmatched_gstr']).to_excel(writer, sheet_name='Unmatched GSTR', index=False)
        
        output.seek(0)
        
        return send_file(
            io.BytesIO(output.read()),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'GST_Reconciliation_Report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
    except Exception as e:
        flash(f'Error generating report: {str(e)}', 'error')
        return redirect(url_for('results'))

@app.route('/download_sample')
def download_sample():
    try:
        sample_data = create_default_format()
        
        return send_file(
            io.BytesIO(sample_data),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='GST_Reconciliation_Sample_Format.xlsx'
        )
    except Exception as e:
        flash(f'Error generating sample: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/contact', methods=['POST'])
def contact_submit():
    name = request.form.get('name')
    email = request.form.get('email')
    message = request.form.get('message')
    
    flash('Thank you for your message! We will get back to you soon.', 'success')
    return redirect(url_for('contact'))

@app.route('/analytics')
def analytics():
    return render_template('analytics.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
