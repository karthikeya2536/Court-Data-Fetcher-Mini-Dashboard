import os
import re
import sqlite3
from datetime import datetime

from flask import Flask, render_template, request, jsonify
from playwright.sync_api import sync_playwright

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'supersecretkey') # Replace with a strong key in production

DATABASE = 'court_queries.db'

def init_db():
    """Initializes the SQLite database."""
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                case_type TEXT,
                case_number TEXT,
                filing_year TEXT,
                status TEXT NOT NULL,
                error_message TEXT,
                parties_names TEXT,
                filing_date TEXT,
                next_hearing_date TEXT,
                pdf_links TEXT, -- Stored as JSON string
                raw_response_html TEXT
            )
        ''')
        conn.commit()

# Ensure DB is initialized on app startup
with app.app_context():
    init_db()

@app.route('/')
def index():
    """Renders the main dashboard page."""
    # Fetch some sample data or pre-populate dropdowns if needed
    case_types = [
        "CIVIL APPEAL", "CRIMINAL APPEAL", "CIVIL MISC. APPLICATION",
        "CRIMINAL MISC. APPLICATION", "SUIT", "EXECUTION PETITION"
    ]
    current_year = datetime.now().year
    filing_years = list(range(current_year, current_year - 20, -1)) # Last 20 years
    return render_template('index.html', case_types=case_types, filing_years=filing_years)

@app.route('/fetch_case', methods=['POST'])
def fetch_case():
    """Fetches case details from the eCourts portal and stores them."""
    case_type = request.form.get('caseType')
    case_number = request.form.get('caseNumber')
    filing_year = request.form.get('filingYear')

    if not all([case_type, case_number, filing_year]):
        return jsonify({'success': False, 'message': 'All fields are required.'})

    query_data = {
        'timestamp': datetime.now().isoformat(),
        'case_type': case_type,
        'case_number': case_number,
        'filing_year': filing_year,
        'status': 'FAILED',
        'error_message': None,
        'parties_names': None,
        'filing_date': None,
        'next_hearing_date': None,
        'pdf_links': None,
        'raw_response_html': None
    }

    try:
        with sync_playwright() as p:
            # Use Chromium browser
            browser = p.chromium.launch(headless=False) # Set headless=False for debugging UI
            page = browser.new_page()

            # Navigate to Faridabad District Court
            page.goto("https://districts.ecourts.gov.in/faridabad")
            page.wait_for_load_state('domcontentloaded')

            # Find and click the 'Case Status' link if needed
            # For Faridabad, the form is usually directly on the page or easily accessible.
            try:
                page.click('text="Case Status"') # Example, verify if this link exists/is needed
                page.wait_for_load_state('domcontentloaded')
            except Exception as e:
                print(f"Case Status link not found or clickable, assuming directly on page: {e}")

            # Select Case Type
            # Inspect the exact selector for the dropdown on districts.ecourts.gov.in
            # This is a common pattern for eCourts dropdowns
            try:
                page.select_option('#case_type', value=case_type) # Assuming ID is 'case_type'
            except Exception:
                # Fallback if ID is different or needs text
                page.select_option('select[name="case_type_select_name"]', label=case_type) # Example name attribute
                print(f"Could not find select option by value, trying by label for {case_type}")

            # Fill Case Number
            page.fill('#case_no', case_number) # Assuming ID is 'case_no'

            # Select Filing Year
            page.select_option('#year', value=filing_year) # Assuming ID is 'year'

            # --- CAPTCHA BYPASS ---
            # Most eCourts use simple arithmetic CAPTCHAs.
            captcha_text = page.locator('#captcha').inner_text() # Assuming CAPTCHA text is in an element with ID 'captcha'
            print(f"CAPTCHA text: {captcha_text}")
            try:
                # Basic parsing for "X + Y =" or "X - Y ="
                match = re.search(r'(\d+)\s*([+\-*/])\s*(\d+)', captcha_text)
                if match:
                    num1 = int(match.group(1))
                    operator = match.group(2)
                    num2 = int(match.group(3))
                    if operator == '+':
                        captcha_result = num1 + num2
                    elif operator == '-':
                        captcha_result = num1 - num2
                    elif operator == '*':
                        captcha_result = num1 * num2
                    elif operator == '/':
                        captcha_result = num1 // num2
                    else:
                        raise ValueError("Unsupported operator")
                    
                    page.fill('#captcha_code', str(captcha_result)) # Assuming CAPTCHA input field ID is 'captcha_code'
                else:
                    raise ValueError("Could not parse CAPTCHA text.")
            except Exception as e:
                query_data['error_message'] = f"CAPTCHA parsing failed: {e}. Please manually inspect the CAPTCHA."
                browser.close()
                print(query_data['error_message'])
                return jsonify({'success': False, 'message': query_data['error_message']})
            # --- END CAPTCHA BYPASS ---

            # Click Search Button
            page.click('input[type="submit"][value="Search"]') # Adjust selector as needed
            page.wait_for_load_state('networkidle') # Wait for network to be idle after submission

            # Get the raw HTML response for logging
            raw_html = page.content()
            query_data['raw_response_html'] = raw_html

            # --- PARSING RESULTS ---
            parsed_details = {}
            pdf_links = []

            # Check for "no case found" message
            if "No case found" in raw_html or "No record found" in raw_html: # Verify actual message
                query_data['error_message'] = "No case found for the given details."
                browser.close()
                return jsonify({'success': False, 'message': query_data['error_message']})

            # Example parsing (selectors are highly specific to the website's HTML)
            # You MUST inspect the HTML of Faridabad District Court's result page
            # These are illustrative examples and will need adjustment
            try:
                # Parties' Names
                # Look for tables or specific divs with party names
                petitioner = page.locator('//td[contains(text(), "Petitioner Name")]/following-sibling::td').inner_text()
                respondent = page.locator('//td[contains(text(), "Respondent Name")]/following-sibling::td').inner_text()
                parsed_details['parties_names'] = f"Petitioner: {petitioner}, Respondent: {respondent}"

                # Filing & Next Hearing Dates
                filing_date = page.locator('//td[contains(text(), "Filing Date")]/following-sibling::td').inner_text()
                next_hearing_date = page.locator('//td[contains(text(), "Next Hearing Date")]/following-sibling::td').inner_text()
                parsed_details['filing_date'] = filing_date
                parsed_details['next_hearing_date'] = next_hearing_date

                # Order/Judgment PDF Links
                # Look for a table or section containing orders/judgments
                # Example: finding all links within a table with class 'orders-table'
                order_rows = page.locator('table.orders-table tbody tr').all() # Adjust selector
                for row in order_rows:
                    pdf_link_element = row.locator('a[href$=".pdf"]').first # Find the first PDF link in the row
                    if pdf_link_element:
                        pdf_url = pdf_link_element.get_attribute('href')
                        order_date_element = row.locator('td.order-date').first # Example order date column
                        order_date = order_date_element.inner_text() if order_date_element else "Unknown Date"
                        # Ensure absolute URL
                        if pdf_url and not pdf_url.startswith('http'):
                            pdf_url = page.url.split('/services/')[0] + pdf_url # Adjust base URL logic
                        pdf_links.append({'date': order_date, 'url': pdf_url})
                
                # Sort by date if possible and take most recent, or just all for simplicity
                pdf_links.sort(key=lambda x: datetime.strptime(x['date'], '%d-%m-%Y') if re.match(r'\d{2}-\d{2}-\d{4}', x['date']) else datetime.min, reverse=True)
                
                parsed_details['pdf_links'] = json.dumps(pdf_links[:3]) # Store top 3 recent links as JSON string

                # Update query_data with parsed details
                query_data['parties_names'] = parsed_details['parties_names']
                query_data['filing_date'] = parsed_details['filing_date']
                query_data['next_hearing_date'] = parsed_details['next_hearing_date']
                query_data['pdf_links'] = parsed_details['pdf_links']
                query_data['status'] = 'SUCCESS'

            except Exception as e:
                query_data['error_message'] = f"Error parsing results: {e}. Site layout might have changed."
                print(query_data['error_message'])
                browser.close()
                return jsonify({'success': False, 'message': query_data['error_message']})
            finally:
                browser.close()

    except Exception as e:
        query_data['error_message'] = f"An unexpected error occurred: {e}. Could not reach court site or internal error."
        print(query_data['error_message'])

    finally:
        # Log query data to DB
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO queries (timestamp, case_type, case_number, filing_year, status, error_message, parties_names, filing_date, next_hearing_date, pdf_links, raw_response_html)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                query_data['timestamp'], query_data['case_type'], query_data['case_number'],
                query_data['filing_year'], query_data['status'], query_data['error_message'],
                query_data['parties_names'], query_data['filing_date'], query_data['next_hearing_date'],
                query_data['pdf_links'], query_data['raw_response_html']
            ))
            conn.commit()

        if query_data['status'] == 'SUCCESS':
            return jsonify({'success': True, 'data': parsed_details})
        else:
            return jsonify({'success': False, 'message': query_data['error_message']})


# API to retrieve past queries for a simple dashboard view (Optional)
@app.route('/history')
def history():
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row # Allows accessing columns by name
        cursor = conn.cursor()
        queries = cursor.execute('SELECT * FROM queries ORDER BY timestamp DESC LIMIT 10').fetchall() # Last 10 queries
        return render_template('history.html', queries=queries) # You'd need to create history.html template

if __name__ == '__main__':
    # Ensure Playwright drivers are installed when running locally
    # os.system("playwright install") # Uncomment if running locally without Docker
    app.run(debug=True, host='0.0.0.0', port=5000)