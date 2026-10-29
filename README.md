# Mini AI Business Intelligence Assistant

An AI-powered business intelligence application that allows users to analyze sales data through natural-language questions. The application uses Google Gemini for question classification and predefined SQL queries to retrieve reliable results from a SQLite database.

## 1. Features

- **Natural-Language Analytics:** Ask questions about sales performance without writing SQL.
- **Revenue Analysis:** Calculate total revenue and identify the highest-revenue product.
- **Regional Analysis:** Identify the region with the highest revenue.
- **Monthly Trends:** View monthly revenue and compare revenue between two months.
- **Data Cleaning:** Handle duplicate transactions, missing values, invalid dates, and excluded transactions.
- **AI-Based Classification:** Use the Google Gemini API to identify the intent of a business question.
- **Keyword Fallback:** Use a keyword-based classifier when Gemini classification fails.
- **Deterministic Results:** Perform business calculations using predefined SQL queries rather than AI-generated numerical answers.
- **Interactive Dashboard:** Display key performance indicators and answers through a React frontend.

## 2. Supported Questions

The application supports five analytical intents and one unsupported intent category.

| Intent | Description | Example |
|---|---|---|
| `total_revenue` | Calculate total revenue and count included transactions | What is our total revenue? |
| `top_product` | Identify the product with the highest revenue | Which product generated the highest revenue? |
| `monthly_trend` | Show revenue across months | Show me the monthly revenue trend |
| `top_region` | Identify the region with the highest revenue | Which region had the highest sales? |
| `month_comparison` | Compare revenue between two months | Compare April and May 2026 |
| `unsupported` | Handle questions outside the supported analytical scope | What is the weather? |

## 3. Technology Stack

| Component | Technology |
|---|---|
| Frontend | React, TypeScript, Vite |
| Backend | Python, FastAPI |
| Data Processing | pandas |
| Database | SQLite |
| AI Integration | Google Gemini API, Google GenAI SDK |
| Automated Testing | pytest |

## 4. System Architecture

The application follows a layered architecture:

1. **Frontend:** React and Vite provide the dashboard and question input interface.
2. **Backend API:** FastAPI validates requests and coordinates classification and query execution.
3. **Intent Classification:** Gemini identifies the type of business question. A keyword-based fallback is available if classification fails.
4. **Query Layer:** Python maps supported intents to predefined, parameterized SQL queries.
5. **Database:** SQLite stores the processed sales transactions and supplies data for analytical calculations.
6. **Data Processing:** pandas cleans the sales CSV before it is loaded into the database.

### Request Flow

The user submits a question through the dashboard. FastAPI receives it and obtains an analytical intent from the classifier. The backend maps the intent to a predefined SQL query, retrieves the relevant data from SQLite, and returns the calculated answer and supporting information to the frontend.

**Key design principle:** AI interprets the question; predefined SQL queries and the database perform the business calculations. User input is not executed as SQL.

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the architecture diagram and additional details.

## 5. Revenue Calculation and Data Validation

Revenue is calculated using the following formula:

`Revenue = Quantity × Unit Price − Discount Amount`

The data-loading pipeline processes the CSV before storing the records in SQLite.

The cleaning process includes:

- Validating required columns.
- Removing duplicate transaction IDs deterministically.
- Normalizing dates into a consistent format.
- Identifying missing or invalid numeric values.
- Excluding invalid transactions and transactions whose status is not completed.
- Recording exclusion reasons for auditing.

Missing discounts, invalid discounts, and other data-quality cases are handled according to the rules implemented in the data loader. Only transactions marked as included contribute to analytical results.

## 6. Setup and Installation

### Prerequisites

- Python 3.12 or a compatible version supported by the dependencies.
- Node.js and npm.
- A Google Gemini API key for AI-based classification.

### Step 1: Clone the Repository

```bash
git clone <your-github-repository-url>
cd MiniAIBusinessIntelligenceAssistant
```

Replace the placeholder URL with your actual repository URL.

### Step 2: Set Up the Python Environment

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Step 3: Configure Environment Variables

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=your_configured_gemini_model
```

Use the model name or model list supported by your application's configuration. Never commit your real API key to GitHub.

If the application supports keyword fallback without an API key, supported questions may still be handled by that fallback.

### Step 4: Load the Sales Dataset

Place the sales CSV file in the location expected by the data loader, then run:

```bash
python -m app.data_loader
```

The loader should report the number of rows processed, duplicates removed, included transactions, and excluded transactions.

### Step 5: Start the Backend

From the project root, with the virtual environment activated:

```bash
python -m uvicorn app.main:app --reload --port 8000
```

The backend should be available at:

- API: `http://127.0.0.1:8000`
- Interactive API documentation: `http://127.0.0.1:8000/docs`

### Step 6: Start the Frontend

Open another terminal and navigate to the frontend directory:

```bash
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite in your terminal.

## 7. API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Check application liveness |
| `GET` | `/kpis` | Retrieve dashboard metrics |
| `POST` | `/ask` | Submit a natural-language analytics question |

Example request to `/ask`:

```json
{
  "question": "Which product generated the highest revenue?"
}
```

The response includes the answer and, according to the implemented API contract, fields such as the identified intent, SQL information, parameters, supporting data, and classification source.

## 8. Automated Testing

Automated tests are maintained in the `tests/` directory. The test suite uses temporary data and databases to verify application behavior without depending on the production dataset.

Run the tests from the project root:

```bash
python -m pytest -v
```

Test coverage includes business calculations, data validation, excluded transactions, invalid requests, API behavior, and classification fallback.

Use the actual test output as the final record of the number of passing and failing tests.

## 9. Security and Reliability

- Analytical SQL queries are predefined and parameterized.
- User questions are classified rather than executed as SQL.
- Read-only SQLite connections are used for analytical query operations.
- Invalid inputs and unsupported questions are handled through API validation and error responses.
- API credentials should be stored in environment variables and excluded from version control.
- The keyword fallback can help maintain supported functionality when Gemini classification is unavailable.

Read-only database access is one layer of protection; parameterized queries and strict control over executable SQL are also important for security.

## 10. Limitations and Future Improvements

- Improve classification of ambiguous natural-language questions.
- Expand automated tests for date comparisons and unusual data-quality cases.
- Add visualizations for monthly and regional sales performance where supported by real backend data.
- Improve dependency health checks and error reporting.
- Test the setup instructions in a clean environment and document any remaining limitations.

## 11. AI Usage

AI tools assisted with development guidance, code review, debugging, and documentation. Google Gemini is integrated into the application to classify business questions. The analytical calculations are performed using predefined SQL queries and the stored sales data.

See [`AI_Usage.md`](AI_Usage.md) for the AI usage reflection.
