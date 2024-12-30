from flask import Flask, render_template, request
import mysql.connector
import pandas as pd
from collections import Counter
import requests
import os

# Your OpenAI API key
OPENAI_API_KEY = ''

# Database connection parameters
DB_CONFIG = {
    'user': 'root',  # Replace with your MySQL username
    'password': 'root',  # Replace with your MySQL password
    'host': 'localhost',
    'database': 'dgidb'
}


app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def default():
    drugs, genes, interactions, interaction_chart_data = [], [], [], []
    selected_drug = None
    selected_gene = None
    form_submitted = False
    openai_response = None

    # Fetch drugs and genes for dropdowns
    cursor.execute("""
        SELECT concept_id, drug_claim_name 
        FROM Drugs_Alias
        GROUP BY concept_id, drug_claim_name
        ORDER BY drug_claim_name
        LIMIT 25000
    """)
    drugs = cursor.fetchall()

    cursor.execute("""
        SELECT concept_id, gene_claim_name 
        FROM Genes_Alias
        GROUP BY concept_id, gene_claim_name
        ORDER BY gene_claim_name
        LIMIT 10000
    """)
    genes = cursor.fetchall()

    if request.method == "POST":
        form_submitted = True
        selected_drug = request.form.get("drug")
        selected_gene = request.form.get("gene")

        # Treat empty strings as None to represent NULL in SQL
        selected_drug = selected_drug if selected_drug else None
        selected_gene = selected_gene if selected_gene else None

        # Query logic to handle partial matches
        query = """
            SELECT 
                MIN(ga.gene_claim_name) AS gene_claim_name, 
                i.gene_concept_id, 
                MIN(da.drug_claim_name) AS drug_claim_name, 
                i.drug_concept_id, 
                i.interaction_type, 
                i.interaction_score, 
                i.interaction_source_db_name
            FROM Interactions i
            LEFT JOIN Genes_Alias ga ON i.gene_concept_id = ga.concept_id
            LEFT JOIN Drugs_Alias da ON i.drug_concept_id = da.concept_id
            WHERE 
                i.interaction_type IS NOT NULL 
                AND (%s IS NULL OR i.drug_concept_id = %s)
                AND (%s IS NULL OR i.gene_concept_id = %s)
            GROUP BY 
                i.gene_concept_id, 
                i.drug_concept_id, 
                i.interaction_type, 
                i.interaction_score, 
                i.interaction_source_db_name
        """
        cursor.execute(query, (selected_drug, selected_drug, selected_gene, selected_gene))
        interactions = cursor.fetchall()

        # If no interactions found, query OpenAI
        if not interactions:
            openai_response = get_openai_interactions(drug=selected_drug, gene=selected_gene)

        # Prepare data for pie chart
        interaction_types = [interaction[4] for interaction in interactions]
        interaction_counts = Counter(interaction_types)
        interaction_chart_data = [{"label": k, "value": v} for k, v in interaction_counts.items()]

    return render_template(
        "interactions.html", 
        drugs=drugs, 
        genes=genes, 
        interactions=interactions, 
        openai_response=openai_response,
        interaction_chart_data=interaction_chart_data,
        selected_drug=selected_drug, 
        selected_gene=selected_gene,
        form_submitted=form_submitted
    )

@app.route("/genes")
def genes():
    cursor.execute('''
    SELECT g.concept_id, ga.gene_claim_name, ga.source_db_name
    FROM Genes g
    INNER JOIN Genes_Alias ga ON g.concept_id = ga.concept_id
    ORDER BY g.concept_id, ga.gene_claim_name
    LIMIT 20000
    ''')
    
    rows = cursor.fetchall()

    return render_template('genes.html', genes=rows)

@app.route("/drugs")
def drugs():
    cursor.execute('''
    SELECT d.concept_id, da.drug_claim_name, da.source_db_name, d.approved, d.immunotherapy, d.anti_neoplastic
    FROM Drugs d
    INNER JOIN Drugs_Alias da ON d.concept_id = da.concept_id
    GROUP BY d.concept_id, da.drug_claim_name, da.source_db_name, d.approved, d.immunotherapy, d.anti_neoplastic
    ORDER BY d.concept_id, da.drug_claim_name
    LIMIT 50000
    ''')

    rows = cursor.fetchall()

    return render_template('drugs.html', drugs=rows)

#API
@app.route("/api/drugs", methods=["GET"])
def api_get_drugs():
    """
    REST API endpoint to fetch drug data.
    Query parameters:
        - id: Optional. Filter by specific drug concept ID.
        - limit: Number of records to return (default: 50).
        - offset: Number of records to skip (default: 0).
    Returns:
        JSON response with drug data.
    """
    drug_id = request.args.get("id", default=None, type=str)
    limit = request.args.get("limit", default=50, type=int)
    offset = request.args.get("offset", default=0, type=int)

    query = '''
        SELECT d.concept_id, da.drug_claim_name, da.source_db_name, d.approved, d.immunotherapy, d.anti_neoplastic
        FROM Drugs d
        INNER JOIN Drugs_Alias da ON d.concept_id = da.concept_id
        {filter_clause}
        GROUP BY d.concept_id, da.drug_claim_name, da.source_db_name, d.approved, d.immunotherapy, d.anti_neoplastic
        ORDER BY d.concept_id, da.drug_claim_name
        LIMIT %s OFFSET %s
    '''

    filter_clause = ""
    params = []

    if drug_id:
        filter_clause = "WHERE d.concept_id = %s"
        params.append(drug_id)

    params.extend([limit, offset])

    cursor.execute(query.format(filter_clause=filter_clause), params)

    rows = cursor.fetchall()
    drugs = [
        {
            "concept_id": row[0],
            "drug_claim_name": row[1],
            "source_db_name": row[2],
            "approved": row[3],
            "immunotherapy": row[4],
            "anti_neoplastic": row[5]
        }
        for row in rows
    ]

    return {
        "status": "success",
        "data": drugs,
        "limit": limit,
        "offset": offset
    }, 200

@app.route("/api/genes", methods=["GET"])
def api_get_genes():
    """
    REST API endpoint to fetch gene data.
    Query parameters:
        - id: Optional. Filter by specific gene concept ID.
        - limit: Number of records to return (default: 50).
        - offset: Number of records to skip (default: 0).
    Returns:
        JSON response with gene data.
    """
    gene_id = request.args.get("id", default=None, type=str)
    limit = request.args.get("limit", default=50, type=int)
    offset = request.args.get("offset", default=0, type=int)

    query = '''
        SELECT g.concept_id, ga.gene_claim_name, ga.source_db_name
        FROM Genes g
        INNER JOIN Genes_Alias ga ON g.concept_id = ga.concept_id
        {filter_clause}
        GROUP BY g.concept_id, ga.gene_claim_name, ga.source_db_name
        ORDER BY g.concept_id, ga.gene_claim_name
        LIMIT %s OFFSET %s
    '''

    filter_clause = ""
    params = []

    if gene_id:
        filter_clause = "WHERE g.concept_id = %s"
        params.append(gene_id)

    params.extend([limit, offset])

    cursor.execute(query.format(filter_clause=filter_clause), params)

    rows = cursor.fetchall()
    genes = [
        {
            "concept_id": row[0],
            "gene_claim_name": row[1],
            "source_db_name": row[2]
        }
        for row in rows
    ]

    return {
        "status": "success",
        "data": genes,
        "limit": limit,
        "offset": offset
    }, 200

@app.route("/api/interactions", methods=["GET"])
def api_get_interactions():
    """
    REST API endpoint to fetch interaction data.
    Query parameters:
        - drug_id: Optional. Filter by specific drug concept ID.
        - gene_id: Optional. Filter by specific gene concept ID.
    Returns:
        JSON response with interaction data.
    """
    drug_id = request.args.get("drug_id", default=None, type=str)
    gene_id = request.args.get("gene_id", default=None, type=str)

    query = '''
        SELECT 
            MIN(ga.gene_claim_name) AS gene_claim_name, 
            i.gene_concept_id, 
            MIN(da.drug_claim_name) AS drug_claim_name, 
            i.drug_concept_id, 
            i.interaction_type, 
            i.interaction_score, 
            i.interaction_source_db_name
        FROM Interactions i
        LEFT JOIN Genes_Alias ga ON i.gene_concept_id = ga.concept_id
        LEFT JOIN Drugs_Alias da ON i.drug_concept_id = da.concept_id
        WHERE 
            i.interaction_type IS NOT NULL 
            AND (%s IS NULL OR i.drug_concept_id = %s)
            AND (%s IS NULL OR i.gene_concept_id = %s)
        GROUP BY 
            i.gene_concept_id, 
            i.drug_concept_id, 
            i.interaction_type, 
            i.interaction_score, 
            i.interaction_source_db_name
    '''

    params = [drug_id, drug_id, gene_id, gene_id]

    cursor.execute(query, params)

    rows = cursor.fetchall()
    interactions = [
        {
            "gene_claim_name": row[0],
            "gene_concept_id": row[1],
            "drug_claim_name": row[2],
            "drug_concept_id": row[3],
            "interaction_type": row[4],
            "interaction_score": row[5],
            "interaction_source_db_name": row[6]
        }
        for row in rows
    ]

    return {
        "status": "success",
        "data": interactions
    }, 200


def connect_to_db():
    return mysql.connector.connect(
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        host=DB_CONFIG['host'],
        database=DB_CONFIG['database']
    )

def get_openai_interactions(drug=None, gene=None):
    """
    Fetch potential interactions from OpenAI if none are found in the database.
    """
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    
    if drug and gene:
        user_message = f"Can you find me possible interactions between {drug} and {gene}. Don't tell me to look it up myself and try to always give an answer. Please also provide sources."
    elif drug:
        user_message = f"Can you find me possible interactions for the drug {drug}. Don't tell me to look it up myself and try to always give an answer. Please also provide sources."
    elif gene:
        user_message = f"Can you find me possible interactions for the gene {gene}. Don't tell me to look it up myself and try to always give an answer. Please also provide sources."
    else:
        return "No drug or gene provided."

    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_message}
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        return f"Error querying OpenAI: {e}"

cnx = connect_to_db()
cursor = cnx.cursor()

