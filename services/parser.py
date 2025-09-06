import os
from typing import Optional, Dict, List, Any

import pandas as pd
from google.api_core.client_options import ClientOptions
from google.cloud import documentai

from config import constants

# --- Private Helper Functions ---

def _extract_entity_text(entity: documentai.Document.Entity, document_text: str) -> str:
    """Extracts text from an entity's text anchor segments."""
    if not entity.text_anchor or not entity.text_anchor.text_segments:
        return entity.mention_text or ""
    
    text_parts = []
    for segment in entity.text_anchor.text_segments:
        start_index = int(segment.start_index) if segment.start_index else 0
        end_index = int(segment.end_index) if segment.end_index else len(document_text)
        text_parts.append(document_text[start_index:end_index])
    
    return "".join(text_parts).strip()


def _parse_bank_statement_info(document: documentai.Document) -> (Dict[str, Any]):
    """Parses high-level bank statement info and groups entities by type."""
    entities_by_type = {}
    for entity in document.entities:
        entity_type = entity.type_
        if entity_type not in entities_by_type:
            entities_by_type[entity_type] = []
        entities_by_type[entity_type].append(entity)
    
    statement_info = {}
    bank_name_entity = entities_by_type.get('bank_name', [None])[0]
    
    if bank_name_entity:
        statement_info['bank_name'] = _extract_entity_text(bank_name_entity, document.text)
    else:
        statement_info['bank_name'] = 'Unknown'

    statement_info['all_cardholders'] = ["MOHIT AGGARWAL", "HIMANI SOOD"]
    return statement_info, entities_by_type


def _parse_table_items(entities_by_type: Dict, document_text: str, all_cardholders: List[str]) -> List[Dict[str, Any]]:
    """Parses table_item entities into structured transaction records."""
    if 'table_item' not in entities_by_type:
        return []
    
    transactions = []
    current_cardholder = "Unknown"
    
    for i, table_item in enumerate(entities_by_type['table_item']):
        raw_text = _extract_entity_text(table_item, document_text)
        
        for name in all_cardholders:
            if name in raw_text:
                current_cardholder = name
                break
        
        transaction = {'item_id': i, 'cardholder': current_cardholder}
        
        if table_item.properties:
            for prop in table_item.properties:
                prop_type = prop.type_
                prop_value = _extract_entity_text(prop, document_text)
                transaction[prop_type] = prop_value
        
        transactions.append(transaction)
    
    return transactions


def _analyze_and_create_dataframe(document: documentai.Document) -> pd.DataFrame | None:
    """Analyzes a document, extracts transactions, and returns a DataFrame."""
    statement_info, entities_by_type = _parse_bank_statement_info(document)
    print("\n=== STATEMENT INFO ===")
    for key, value in statement_info.items():
        print(f"{key}: {value}")
        
    transactions = _parse_table_items(entities_by_type, document.text, statement_info['all_cardholders'])
    
    if not transactions:
        print("❌ No transactions extracted")
        return None

    df = pd.DataFrame(transactions)
    df['bank_name'] = statement_info.get('bank_name', 'N/A')
    
    print(f"\n=== TRANSACTION SUMMARY ===")
    print(f"Total transactions found: {len(df)}")
    return df


def _preprocess_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Cleans, coalesces, and standardizes the transaction DataFrame."""
    processed_df = df.copy()
    
    # Coalesce description and amount columns
    processed_df['description'] = processed_df.get('table_item/transaction_withdrawal_description', pd.Series(dtype='str')).fillna(
        processed_df.get('table_item/transaction_deposit_description', pd.Series(dtype='str'))
    )
    processed_df['amount'] = processed_df.get('table_item/transaction_withdrawal', pd.Series(dtype='str')).fillna(
        processed_df.get('table_item/transaction_deposit', pd.Series(dtype='str'))
    )
    processed_df['transaction_date'] = processed_df.get('table_item/transaction_withdrawal_date', pd.Series(dtype='str')).fillna(
        processed_df.get('table_item/transaction_deposit_date', pd.Series(dtype='str'))
    )

    # Select and rename core columns
    final_cols = ['bank_name', 'cardholder', 'transaction_date', 'description', 'amount']
    processed_df = processed_df.reindex(columns=final_cols)

    # Clean and filter data
    processed_df.dropna(subset=['amount'], inplace=True)
    processed_df = processed_df[~processed_df['amount'].isin(['$0.00', '+$0.00'])]

    # Standardize date format
    processed_df['transaction_date'] = pd.to_datetime(
        processed_df['transaction_date'], errors='coerce'
    ).dt.strftime('%Y-%m-%d')
    
    processed_df.dropna(subset=['transaction_date'], inplace=True)
    
    return processed_df


# --- Public API Function ---

def run_parsing():
    """
    Main function to process all PDF statements in the statements folder.

    It uses Google Document AI to parse each file, extracts transactions, combines
    them into a single DataFrame, and saves the result to a CSV file in the temp directory.
    """
    all_cleaned_dfs = []

    print(f"🚀 Starting batch processing for files in '{constants.STATEMENTS_FOLDER}'...")

    opts = ClientOptions(api_endpoint=f"{constants.GCP_LOCATION}-documentai.googleapis.com")
    client = documentai.DocumentProcessorServiceClient(client_options=opts)
    name = client.processor_path(constants.GCP_PROJECT_ID, constants.GCP_LOCATION, constants.GCP_PROCESSOR_ID)

    try:
        file_names = os.listdir(constants.STATEMENTS_FOLDER)
    except FileNotFoundError:
        print(f"❌ Error: The directory '{constants.STATEMENTS_FOLDER}' was not found.")
        return

    for file_name in file_names:
        if not file_name.lower().endswith(".pdf"):
            continue

        file_path = os.path.join(constants.STATEMENTS_FOLDER, file_name)
        print(f"\n📄 Processing file: {file_name}")

        with open(file_path, "rb") as image:
            image_content = image.read()
        
        raw_document = documentai.RawDocument(content=image_content, mime_type="application/pdf")
        request = documentai.ProcessRequest(name=name, raw_document=raw_document)
        result = client.process_document(request=request)
        document = result.document

        if document:
            df = _analyze_and_create_dataframe(document)
            if df is not None and not df.empty:
                cleaned_df = _preprocess_transactions(df)
                all_cleaned_dfs.append(cleaned_df)
                print(f"✅ Successfully cleaned and added {len(cleaned_df)} transactions from {file_name}.")
        else:
            print(f"⚠️ Could not process document: {file_name}")

    if all_cleaned_dfs:
        final_df = pd.concat(all_cleaned_dfs, ignore_index=True)
        
        # Ensure temp directory exists before saving
        os.makedirs(constants.TEMP_DIR, exist_ok=True)
        final_df.to_csv(constants.CSV_PATH, index=False)
        
        print("\n===================================================")
        print(f"🎉 Batch processing complete!")
        print(f"Total transactions processed: {len(final_df)}")
        print(f"💾 Combined data saved to '{constants.CSV_PATH}'")
        print("===================================================")
    else:
        print("\n⏹️ No transactions were processed or found in any of the files.")