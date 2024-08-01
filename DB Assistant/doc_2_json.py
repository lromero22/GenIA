import re
import json

def parse_txt_to_json(txt_file_path):
    tables = []
    current_table = None
    current_section = None
    current_relationships = []
    current_fields = []

    with open(txt_file_path, 'r', encoding='UTF-8') as file:
        lines = file.readlines()

        for line in lines:
            line = line.strip()

            if line.startswith('TABLA'):
                if current_table:
                    tables.append({
                        "name": current_table,
                        "relationships": current_relationships,
                        "fields": current_fields
                    })
                    current_relationships = []
                    current_fields = []

                _, table_name = line.split(': ')
                current_table = table_name

            elif line.startswith('RELACIONES'):
                current_section = 'relationships'

            elif line.startswith('CAMPOS'):
                current_section = 'fields'

            elif line.startswith('Se relaciona con la tabla:'):
                if current_section == 'relationships':
                    match = re.match(r'Se relaciona con la tabla: (\w+) por el (\w+)', line)
                    if match:
                        related_table = match.group(1)
                        related_field = match.group(2)
                        current_relationships.append({
                            "related_table": related_table,
                            "related_field": related_field
                        })

            elif line and current_section == 'fields':
                match = re.match(r'(\w+): (.*)', line)
                if match:
                    field_name = match.group(1)
                    field_description = match.group(2)
                    current_fields.append({
                        "name": field_name,
                        "description": field_description
                    })

        # Append the last table
        if current_table:
            tables.append({
                "name": current_table,
                "relationships": current_relationships,
                "fields": current_fields
            })

    # Create final JSON structure
    json_data = {
        "tables": tables
    }

    return json_data

def write_json_file(json_data, json_file_path):
    with open(json_file_path, 'w', encoding='utf-8') as json_file:
        json.dump(json_data, json_file, indent=2, ensure_ascii=False)

# Example usage:
txt_file_path = r'C:\Users\oscar\Documents\Coding\LikeU\GenIA\DB Assistant\description_db.txt'  # Replace with your file path
json_file_path = 'table_descriptions.json'  # Replace with desired output JSON file path

parsed_data = parse_txt_to_json(txt_file_path)
write_json_file(parsed_data, json_file_path)

print(f"Successfully parsed '{txt_file_path}' and saved as '{json_file_path}'.")
