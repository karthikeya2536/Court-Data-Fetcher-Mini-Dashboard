# Court-Data Fetcher & Mini-Dashboard

This project is a small web application designed to fetch case metadata and the latest orders/judgments from a specific Indian District Court portal.

## Court Targeted

**IMPORTANT:** The original target, Faridabad District Court, may sometimes be inaccessible. **You MUST verify that the court you choose is currently working for you.**

**Current Target Court Declaration:**
* Please replace this placeholder with the URL of the District Court eCourts portal that is currently working and you are targeting.
* **Example (replace with your choice):** `https://districts.ecourts.gov.in/lucknow` (Lucknow District Court, Uttar Pradesh)

## Technologies Used

* **Backend:** Python 3 (Flask)
* **Web Scraping:** Playwright (for headless browser automation)
* **Database:** SQLite (for logging queries and raw responses)
* **Frontend:** HTML, CSS, JavaScript (Vanilla)
* **Containerization (Optional):** Docker

## Functional Requirements Implemented

1.  **UI:** A simple HTML form with dropdowns for Case Type, Filing Year, and a text input for Case Number.
2.  **Backend:**
    * On form submission, it programmatically navigates the chosen eCourts portal using Playwright.
    * Extracts:
        * Parties' names (Petitioner, Respondent).
        * Filing Date.
        * Next Hearing Date.
        * Links to recent Order/Judgment PDFs (up to 3 most recent).
3.  **Storage:** Each query (including input parameters, status, error messages, parsed data, and the raw HTML response) is logged into an SQLite database (`court_queries.db`).
4.  **Display:** The parsed details are rendered nicely on the web page. PDF links are downloadable. A link to view recent query history is also provided (requires `history.html` template, not fully implemented in initial version but database supports it).
5.  **Error Handling:** User-friendly messages are displayed for:
    * Missing input fields.
    * "No case found" scenarios from the court website.
    * Errors during CAPTCHA solving.
    * Errors during HTML parsing (indicating potential site layout changes).
    * General network/internal errors (e.g., website unreachable).

## CAPTCHA Strategy

The `districts.ecourts.gov.in` portals typically use a simple **arithmetic CAPTCHA** (e.g., "3 + 5 = ?"). The approach implemented in `app.py` is as follows:

1.  Playwright locates the element containing the CAPTCHA question (assuming an ID like `#captcha`).
2.  The text content of this element is extracted.
3.  A Python regular expression is used to parse the two numbers and the operator (`+`, `-`, `*`, `/`).
4.  The arithmetic operation is performed programmatically.
5.  The calculated result is filled into the CAPTCHA input field (assuming an ID like `#captcha_code`).

**Robustness against changes:** This method is robust as long as the CAPTCHA format remains simple arithmetic and the HTML element IDs (for the question and input field) don't change. If the CAPTCHA becomes image-based or more complex, this strategy would require an update (e.g., integrating an OCR library like Tesseract, or a remote CAPTCHA solving service, which would be documented if needed).

## Setup and Running

### Prerequisites

* Python 3.8+
* `pip` (Python package installer)
* (Optional for Docker) Docker Desktop
* **Crucial:** Internet access to the chosen eCourts portal.

### 1. Local Setup (Recommended for Initial Development & Debugging)

This method allows for quicker iteration and visual debugging.

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd court_data_fetcher
    ```
2.  **Create a Python virtual environment (highly recommended):**
    ```bash
    python -m venv venv
    # On some systems, you might need 'python3 -m venv venv'
    ```
3.  **Activate the virtual environment:**
    * **On macOS/Linux:**
        ```bash
        source venv/bin/activate
        ```
    * **On Windows (PowerShell):**
        ```bash
        .\venv\Scripts\activate
        ```
    * **On Windows (Command Prompt):**
        ```bash
        venv\Scripts\activate.bat
        ```
4.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
5.  **Install Playwright browser drivers:**
    ```bash
    playwright install
    ```
6.  **Create a `.env` file:**
    Copy the `.env.sample` file to `.env` in the root directory.
    ```bash
    cp .env.sample .env # On macOS/Linux
    copy .env.sample .env # On Windows
    ```
    Edit `.env` and replace `FLASK_SECRET_KEY` with a strong, random string.
    ```
    FLASK_SECRET_KEY=your_very_secure_random_string_here_123abcDEF
    ```
7.  **Run the Flask application (with Headed Browser for Debugging):**
    * **Before running, open `app.py` and change `headless=True` to `headless=False` in the `p.chromium.launch()` line.** This will make Playwright open a visible browser window, allowing you to see its actions.
    * In your terminal (with venv active):
        ```bash
        export FLASK_APP=app.py # macOS/Linux
        export FLASK_DEBUG=1   # macOS/Linux
        # For Windows PowerShell:
        # $env:FLASK_APP="app.py"
        # $env:FLASK_DEBUG="1"
        flask run
        ```
8.  **Access the application:** Open your web browser and go to `http://127.0.0.1:5000`.

### 2. Docker Setup (For Production Deployment / Consistent Environment)

1.  **Ensure Docker Desktop is installed and running.**
2.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd court_data_fetcher
    ```
3.  **Create a `.env` file:** Same as Step 6 in Local Setup.
4.  **Build and run the Docker containers:**
    ```bash
    docker-compose up --build
    ```
5.  **Access the application:** Open your web browser and go to `http://localhost:5000`.

## Debugging and Customizing for Your Chosen Court

This is the most critical part to get the scraper working correctly for your chosen District Court portal.

**Problem:** The selectors (like `#case_type`, `#case_no`, `table.orders-table`) in `app.py` are generic examples and **will almost certainly be different** on the actual eCourts website you choose. If Playwright can't find an element, it will time out.

**Solution: The Iterative Debugging Process**

1.  **Ensure Chosen Court is Accessible:**
    * Before anything else, manually open the URL of your chosen court (`https://districts.ecourts.gov.in/YOUR_COURT_SLUG`) in your regular web browser (e.g., Chrome, Firefox).
    * **Confirm it loads completely and you can manually perform a case search.** If the site itself is down or inaccessible, the scraper won't work. If it's down, you must pick another court.

2.  **Find a Valid Test Case (Manual Search):**
    * On your chosen live court portal, manually navigate to the "Case Status" or "Search" page.
    * **Perform a manual search with real data** (e.g., choose a Case Type, enter a Case Number, select a Filing Year, solve their CAPTCHA, and click search).
    * **Note down the exact Case Type, Case Number, and Filing Year** that successfully returns results. You will use these values in your Flask app for testing.

3.  **Run Your Flask App in Headed Mode (from "Local Setup" Step 7):**
    * Make sure `headless=False` in `app.py`.
    * Start your Flask app using `flask run`.

4.  **Interact with Your Flask App and Observe Playwright:**
    * Go to `http://127.0.0.1:5000`.
    * Enter the **known-good values** (Case Type, Number, Year) you found in step 2.
    * Click "Fetch Case Details."
    * **Carefully watch the Playwright browser window that pops up.**
        * Does it open the correct court URL?
        * Does it successfully select/fill the Case Type, Case Number, Filing Year?
        * Does it successfully parse and fill the CAPTCHA?
        * Does it click the search button?
        * Does it navigate to the results page?

5.  **Inspect and Adjust Selectors (The Core Loop):**
    * **When Playwright Fails:** If the Playwright window stops unexpectedly, or your Flask app's terminal shows a `TimeoutError` (e.g., `locator.fill: Timeout 30000ms exceeded`), this means a selector in `app.py` is incorrect. The error message will usually tell you *which* selector (e.g., `#case_no`) it couldn't find.
    * **Use Browser Developer Tools:**
        * Go back to the **live court website** in your *regular* browser (Chrome/Firefox/Edge).
        * **Right-click on the specific element** that Playwright failed to interact with (e.g., the Case Number input field, the CAPTCHA text element, a PDF link on the results page).
        * Select **"Inspect"** or **"Inspect Element"**.
        * In the Developer Tools panel (usually opens at the bottom or side), you'll see the HTML code for that element.
        * **Identify unique attributes:** Look for `id`, `name`, or `class` attributes. Sometimes you might need to use more complex CSS selectors (e.g., `input[type="text"][name="case_no_field"]`) or XPath.
        * **Update `app.py`:** Modify the corresponding `page.locator()`, `page.fill()`, `page.select_option()`, or `page.click()` calls in your `app.py` with the correct selectors you found.

    * **Example Adjustments (Illustrative - you need to verify!):**
        ```python
        # Original (Example):
        # page.select_option('#case_type', value=case_type)
        # page.fill('#case_no', case_number)
        # captcha_text = page.locator('#captcha').inner_text()
        # page.fill('#captcha_code', str(captcha_result))
        # petitioner = page.locator('//td[contains(text(), "Petitioner Name")]/following-sibling::td').inner_text()
        # order_rows = page.locator('table.orders-table tbody tr').all()

        # After inspection, you might change them to (for example):
        page.select_option('select[name="caseTypeDropdown"]', value=case_type) # Changed ID to name attribute
        page.fill('input#caseNumberInput', case_number) # Changed ID
        captcha_text = page.locator('.captcha-question-text').inner_text() # Changed ID to class
        page.fill('input[type="text"][placeholder="Enter CAPTCHA here"]', str(captcha_result)) # Using multiple attributes
        petitioner = page.locator('div#partiesDetails span.petitioner-value').inner_text() # More specific path
        order_rows = page.locator('div.order-list table tbody tr').all() # Different table structure
        ```

6.  **Repeat Step 3, 4, and 5:** Save `app.py`, restart your Flask app (Ctrl+C then `flask run`), and try fetching a case again. Continue this iterative process of inspecting, adjusting, and testing until Playwright successfully navigates, interacts with the form, solves the CAPTCHA, and extracts all the desired data from the results page.

## Final Steps (After Successful Scraping)

1.  **Revert to Headless Mode:** Once all selectors are working perfectly and the data is extracted reliably, you can change `headless=False` back to `headless=True` in `app.py` for faster execution and to run the browser silently in the background.
2.  **Thorough Testing:** Test with various valid and invalid case numbers, types, and years to ensure robustness.
3.  **Review `court_queries.db`:** Verify that all successful and failed attempts are being logged correctly in your SQLite database.

This detailed guide should help you systematically troubleshoot and adapt the scraper to your chosen live court portal. It's a hands-on process but very rewarding when it works!"# Court-Data-Fetcher-Mini-Dashboard" 
