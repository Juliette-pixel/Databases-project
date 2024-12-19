import mysql.connector
import pandas as pd

# Database connection parameters
DB_CONFIG = {
    'user': 'root',  # Replace with your MySQL username
    'password': 'root',  # Replace with your MySQL password
    'host': 'localhost',
    'database': 'dgidb' # please create this empty schema yourself in mysql before running this script
}

# File paths
GENES_FILE = 'genes.tsv'
DRUGS_FILE = 'drugs.tsv'
INTERACTIONS_FILE = 'interactions.tsv'

CREATE_STATEMENTS = """
-- Table: Drugs
CREATE TABLE IF NOT EXISTS Drugs (
    concept_id VARCHAR(255) PRIMARY KEY,
    approved BOOLEAN,
    immunotherapy BOOLEAN,
    anti_neoplastic BOOLEAN
);

-- Table: Drugs_Alias
CREATE TABLE IF NOT EXISTS Drugs_Alias (
    concept_id VARCHAR(255),
    drug_claim_name VARCHAR(255),
    drug_name VARCHAR(255),
    source_db_name VARCHAR(255),
    source_db_version VARCHAR(255),
    FOREIGN KEY (concept_id) REFERENCES Drugs(concept_id)
);

-- Table: Genes
CREATE TABLE IF NOT EXISTS Genes (
    concept_id VARCHAR(255) PRIMARY KEY
);

-- Table: Genes_Alias
CREATE TABLE IF NOT EXISTS Genes_Alias (
    concept_id VARCHAR(255),
    gene_claim_name VARCHAR(255),
    gene_name VARCHAR(255),
    source_db_name VARCHAR(255),
    source_db_version VARCHAR(255),
    FOREIGN KEY (concept_id) REFERENCES Genes(concept_id)
);

-- Table: Interactions
CREATE TABLE IF NOT EXISTS Interactions (
    gene_concept_id VARCHAR(255),
    drug_concept_id VARCHAR(255),
    interaction_source_db_name VARCHAR(255),
    interaction_source_db_version VARCHAR(255),
    interaction_type VARCHAR(255),
    interaction_score FLOAT,
    FOREIGN KEY (gene_concept_id) REFERENCES Genes(concept_id),
    FOREIGN KEY (drug_concept_id) REFERENCES Drugs(concept_id)
);
"""

def connect_to_db():
    return mysql.connector.connect(
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        host=DB_CONFIG['host'],
        database=DB_CONFIG['database']
    )

def sanitize_row(row):
    """Converts NaN to None for MySQL compatibility."""
    return [None if pd.isna(value) else value for value in row]

def create_tables(cursor):
    for statement in CREATE_STATEMENTS.split(';'):
        if statement.strip():
            cursor.execute(statement)

def load_genes(cursor, file_path):
    df = pd.read_csv(file_path, sep='\t')
    for _, row in df.iterrows():
        sanitized_row = sanitize_row(row)
        concept_id = sanitized_row[2]  # Assuming concept_id is the 3rd column
        gene_claim_name = sanitized_row[0]  # Assuming gene_claim_name is the 1st column
        if concept_id and gene_claim_name:  # Exclude if gene_claim_name is empty
            # Check if concept_id already exists in Genes table
            cursor.execute("SELECT 1 FROM Genes WHERE concept_id = %s", (concept_id,))
            if not cursor.fetchone():
                # Insert into Genes table
                cursor.execute("INSERT INTO Genes (concept_id) VALUES (%s)", (concept_id,))
            
            # Check for duplicate gene_claim_name in a case-insensitive manner
            cursor.execute("""
                SELECT 1 FROM Genes_Alias WHERE LOWER(gene_claim_name) = LOWER(%s)
            """, (gene_claim_name,))
            if not cursor.fetchone():
                # Insert alias information
                cursor.execute("""
                    INSERT INTO Genes_Alias (concept_id, gene_claim_name, gene_name, source_db_name, source_db_version)
                    VALUES (%s, %s, %s, %s, %s)
                """, (concept_id, sanitized_row[0], sanitized_row[3], sanitized_row[4], sanitized_row[5]))

def load_drugs(cursor, file_path):
    df = pd.read_csv(file_path, sep='\t')
    for _, row in df.iterrows():
        sanitized_row = sanitize_row(row)
        concept_id = sanitized_row[2]  # Assuming concept_id is the 3rd column
        drug_claim_name = sanitized_row[0]  # Assuming drug_claim_name is the 1st column
        if concept_id and drug_claim_name:  # Exclude if drug_claim_name is empty
            # Check if concept_id already exists in Drugs table
            cursor.execute("SELECT 1 FROM Drugs WHERE concept_id = %s", (concept_id,))
            if not cursor.fetchone():
                # Insert into Drugs table with the first record's approved, immunotherapy, and anti_neoplastic values
                cursor.execute("""
                    INSERT INTO Drugs (concept_id, approved, immunotherapy, anti_neoplastic)
                    VALUES (%s, %s, %s, %s)
                """, (concept_id, sanitized_row[4], sanitized_row[5], sanitized_row[6]))
            
            # Check for duplicate drug_claim_name in a case-insensitive manner
            cursor.execute("""
                SELECT 1 FROM Drugs_Alias WHERE LOWER(drug_claim_name) = LOWER(%s)
            """, (drug_claim_name,))
            if not cursor.fetchone():
                # Insert alias information
                cursor.execute("""
                    INSERT INTO Drugs_Alias (concept_id, drug_claim_name, drug_name, source_db_name, source_db_version)
                    VALUES (%s, %s, %s, %s, %s)
                """, (concept_id, sanitized_row[0], sanitized_row[3], sanitized_row[7], sanitized_row[8]))

def load_interactions(cursor, file_path):
    df = pd.read_csv(file_path, sep='\t')
    for _, row in df.iterrows():
        sanitized_row = sanitize_row(row)
        interaction_type = sanitized_row[5]  # Assuming interaction_type is the 6th column
        if interaction_type:  # Exclude if interaction_type is NULL
            cursor.execute("""
                INSERT INTO Interactions (gene_concept_id, drug_concept_id, interaction_source_db_name, interaction_source_db_version, interaction_type, interaction_score)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (sanitized_row[1], sanitized_row[8], sanitized_row[3], sanitized_row[4], interaction_type, sanitized_row[6]))

def main():
    try:
        cnx = connect_to_db()
        cursor = cnx.cursor()

        # Create tables
        print("Creating tables...")
        create_tables(cursor)

        # Load data
        print("Loading genes...")
        load_genes(cursor, GENES_FILE)
        print("Loading drugs...")
        load_drugs(cursor, DRUGS_FILE)
        print("Loading interactions...")
        load_interactions(cursor, INTERACTIONS_FILE)

        # Commit changes
        cnx.commit()
        print("Data loaded successfully.")

    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'cnx' in locals():
            cnx.close()

if __name__ == "__main__":
    main()
