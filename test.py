import json

# Load the original data
with open('crash_reasons.json', 'r', encoding='utf-8') as f:
    original_data = json.load(f)

# Initialize the new data structures
persons = {}
crash_reasons = {}
detection_rules = {}

# Extract unique person names and assign IDs
unique_persons = set()
for crash_id, crash_data in original_data.items():
    if "promoter" in crash_data:
        unique_persons.add(crash_data["promoter"])

    # Extract contributors from detection rules
    if "detectionRule" in crash_data:
        for rule in crash_data["detectionRule"]:
            if "contributor" in rule:
                unique_persons.add(rule["contributor"])

# Create person entries
for i, name in enumerate(sorted(unique_persons), 1):
    persons[str(i)] = {
        "id": i,
        "name": name
    }

# Create a mapping of names to IDs
name_to_id = {person_data["name"]: person_data["id"] for person_id, person_data in persons.items()}

# Process crash reasons and detection rules
rule_counter = 1
for crash_id, crash_data in original_data.items():
    # Create crash reason entry
    promoter_id = name_to_id.get(crash_data.get("promoter", "Unknown"), 1)  # Default to ID 1 if not found

    crash_reasons[crash_id] = {
        "id": crash_id,
        "name": crash_data.get("name", ""),
        "description": crash_data.get("description", ""),
        "priority": crash_data.get("priority", 0),
        "promoter_id": promoter_id
    }

    # Process detection rules
    if "detectionRule" in crash_data:
        for rule in crash_data["detectionRule"]:
            contributor_id = name_to_id.get(rule.get("contributor", "Unknown"), 1)  # Default to ID 1 if not found
            rule_id = f"rule_{crash_id}_{rule_counter}"
            rule_counter += 1

            detection_rules[rule_id] = {
                "id": rule_id,
                "crash_reason_id": crash_id,
                "match_type": rule.get("match_type", 0),
                "match": rule.get("match", ""),
                "contributor_id": contributor_id
            }

# Write the new data to separate files
with open('persons.json', 'w', encoding='utf-8') as f:
    json.dump(persons, f, ensure_ascii=False, indent=4)

with open('crash_reasons.json', 'w', encoding='utf-8') as f:
    json.dump(crash_reasons, f, ensure_ascii=False, indent=4)

with open('detection_rules.json', 'w', encoding='utf-8') as f:
    json.dump(detection_rules, f, ensure_ascii=False, indent=4)

print(
    f"Migration complete. Created {len(persons)} persons, {len(crash_reasons)} crash reasons, and {len(detection_rules)} detection rules.")