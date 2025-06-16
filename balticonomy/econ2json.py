import pandas as pd
import json
import numpy as np
import html_extractor

def parse_csv_to_json(df, splitNames = True):
    """
    Parse a CSV file with multiple tables and convert to JSON format.
    Handles comma-separated emails by creating duplicate records with corresponding names.
    
    Args:
        csv_file_path (str): Path to the input CSV file
    """
    
    all_records = []
    current_table_name = None
    
    # Iterate through each row
    for idx, row in df.iterrows():
        # Check if this row contains "Group Name" in column A (index 0)
        if row.iloc[0] == "Group Name" or row.iloc[0] == "Contact Name" :
            # Look back 2 rows to find the table name
            if idx >= 2:
                potential_table_name = df.iloc[idx - 2, 0]
                if potential_table_name and potential_table_name.strip():
                    current_table_name = potential_table_name.strip()
            
            # Get the header row (current row)
            headers = [col.strip() for col in row.values if col.strip()]
            
            # Process data rows following the header
            data_row_idx = idx + 1
            while data_row_idx < len(df):
                data_row = df.iloc[data_row_idx]
                
                # Check if we've hit another table (Group Name in column A)
                if data_row.iloc[0] == "Group Name" or data_row.iloc[0] == "Contact Name" or data_row.iloc[0] == "":
                    break
                
                # Check if the row has any non-empty content
                non_empty_cells = [cell.strip() for cell in data_row.values if cell.strip()]
                
                if non_empty_cells:  # If row has content
                    # Create base record
                    base_record = {"Occupation": current_table_name or "Unknown"}
                    
                    # Map non-empty cells to headers
                    for i, cell_value in enumerate(data_row.values):
                        if cell_value.strip() and i < len(headers):
                            base_record[headers[i]] = cell_value.strip()
                        elif cell_value.strip() and i >= len(headers):
                            # If there are more data columns than headers, use generic names
                            base_record[f"Column_{i+1}"] = cell_value.strip()
                    
                    # Handle contact name splitting
                    if splitNames:
                        processed_records = process_contact_name_splitting(base_record)
                        for record in processed_records:
                            if record.get("Email"):
                                del record["Email"]
                        all_records.extend(processed_records)
                    else:
                        all_records.append(base_record)


                
                data_row_idx += 1
    
    outrecords = []
    for record in all_records:
        if "Contact Name" in record:
            if record.get("Website"):
                WText = ""
                for url in record["Website"].split(','):
                    url = url.strip()
                    WText += html_extractor.url2text(url)[:2000] + "\n"
                record["Website Text"] = WText
            if record.get("Events Page"):
                EText = ""
                for url in record["Events Page"].split(','):
                    url = url.strip()
                    EText += html_extractor.url2text(url)[:2000] + "\n"
                record["Events Text"] = EText
            outrecords.append(record)
            print(record["Contact Name"])

    
    print(f"Parsed {len(outrecords)} records from CSV")
    
    return outrecords

def process_contact_name_splitting(record):
    """
    Process a record to handle comma-separated contact names.
    Creates one record for each contact name.
    
    Args:
        record (dict): The original record
        
    Returns:
        list: List of processed records (one for each contact name)
    """
    processed_records = []
    
    # Find contact name field
    contact_name_field = None
    contact_name_value = None
    for key, value in record.items():
        if 'contact name' in key.lower() or key.lower() == 'name':
            contact_name_field = key
            contact_name_value = value
            break
    
    # If no contact name field found, return original record
    if not contact_name_field or not contact_name_value:
        processed_records.append(record)
        return processed_records
    
    # Split contact names by comma
    contact_names = [name.strip() for name in contact_name_value.split(',') if name.strip()]
    
    # If only one name or no names, return original record
    if len(contact_names) <= 1:
        processed_records.append(record)
        return processed_records
    
    # Create a record for each contact name
    for contact_name in contact_names:
        new_record = record.copy()
        new_record[contact_name_field] = contact_name
        processed_records.append(new_record)
    
    return processed_records



def preview_results(records, num_records=5):
    """Preview the first few records"""
    print(f"\nPreview of first {min(num_records, len(records))} records:")
    print("-" * 50)
    for i, record in enumerate(records[:num_records]):
        print(f"Record {i+1}:")
        for key, value in record.items():
            print(f"  {key}: {value}")
        print()

# Main execution
if __name__ == "__main__":
    # File paths
    csv_file = "Baltimore Tech Economy - Tech Groups.csv"
    json_file = "baltimore_tech_groups.json"

    # Read the CSV file
    df = pd.read_csv(csv_file, header=None)
    
    # Convert all cells to strings and handle NaN values
    df = df.astype(str).replace('nan', '')
    
    # Parse the CSV and convert to JSON
    records = parse_csv_to_json(df)

    # Save to JSON file
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    print(f"JSON file saved to: {json_file}")

    # create a different JSON file organized by Org Type

    records = parse_csv_to_json(df, False)
    org_records = {}
    for record in records:
        record.pop("Email", None)
        record.pop("Website Text", None)
        record.pop("Events Text", None)
        record.pop("Contact Name", None)

        if record.get("Occupation") in org_records.keys():
            org_records[record.get("Occupation")] += [record]
        else:
            org_records[record.get("Occupation")] = [record]

    with open("orgs.json", 'w', encoding='utf-8') as f:
        json.dump(org_records, f, indent=2, ensure_ascii=False)
    print(f"JSON file saved to: orgs.json")