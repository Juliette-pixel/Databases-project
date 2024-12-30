# Interaction Explorer Application

This application is a web-based platform for exploring drug-gene interactions. Users can search for known interactions stored in a local MySQL database or fetch potential interaction information via OpenAI's API if no local data is available.

## Features

- **Drug and Gene Search:** Search for interactions between selected drugs and genes using data from a MySQL database.
- **Google Charts Integration:** Visualize interaction types in a pie chart for better insights.
- **OpenAI Integration:** Fetch potential interactions when none are found in the local database.
- **REST API Endpoints:** Retrieve drugs, genes, and interactions programmatically using the provided API.
- **Pagination and Filtering:** Easily browse large datasets using filters and limits.

## Requirements

- Python 3.10+
- Flask 2.0+, pandas, mysql, requests
- MySQL Database
- OpenAI API Key (optional)

## Installation

### Step 1: Set Up the MySQL Database

1. Create a MySQL database named `dgidb`.
2. Either import the database using the dump saved /database/dump_Juliette.sql or import it yourself using the script /database/import.py
3. Update the `DB_CONFIG` dictionary in the `app.py` file with your MySQL credentials.

```python
DB_CONFIG = {
    'user': 'root',  # Replace with your MySQL username
    'password': 'root',  # Replace with your MySQL password
    'host': 'localhost',
    'database': 'dgidb'
}
```

### Step 2: Set Your OpenAI API Key (optional)

This requires you to have a balance above 0$. A request usually costs about 1 cent.

1. Sign up for OpenAI API access at [OpenAI's website](https://openai.com/api/).
2. Obtain your API key.
3. Replace the `OPENAI_API_KEY` placeholder in `app.py` with your actual API key.

```python
OPENAI_API_KEY = 'your_openai_api_key_here'
```

### Step 3: Run the Application

1. Start the MySQL server.
2. Launch the Flask application:

```bash
flask --app app run
```

3. Open your web browser and go to `http://127.0.0.1:5000`.

## API EndpointsS

### 1. Get Drugs

- **URL:** `/api/drugs`
- **Method:** `GET`
- **Parameters:**
  - `id` (optional): Filter by drug concept ID.
  - `limit` (default: 50): Number of records to return.
  - `offset` (default: 0): Number of records to skip.
- **Response:** JSON object with drug data.

### 2. Get Genes

- **URL:** `/api/genes`
- **Method:** `GET`
- **Parameters:**
  - `id` (optional): Filter by gene concept ID.
  - `limit` (default: 50): Number of records to return.
  - `offset` (default: 0): Number of records to skip.
- **Response:** JSON object with gene data.

### 3. Get Interactions

- **URL:** `/api/interactions`
- **Method:** `GET`
- **Parameters:**
  - `drug_id` (optional): Filter by drug concept ID.
  - `gene_id` (optional): Filter by gene concept ID.
- **Response:** JSON object with interaction data.

## License

This project is licensed under the MIT License. See `LICENSE` for more details.

---
