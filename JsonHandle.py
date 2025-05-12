import json
import os.path

def new_json(file_path: str):
    """
    Creates a new JSON file with an empty dictionary.

    Args:
        file_path (str): The path to the new JSON file.
    """
    with open(file_path, 'w', encoding="utf-8") as file:
        json.dump({}, file, indent=2, ensure_ascii=False, sort_keys=True)

def read_json(file_path: str):
    """
    Opens a JSON file and returns its content as a dictionary.

    Args:
        file_path (str): The path to the JSON file.

    Returns:
        dict: The content of the JSON file as a dictionary.
    """
    if not os.path.exists(file_path):
        print(f"File {file_path} does not exist. Creating a new one.")
        new_json(file_path)
        return {}

    with open(file_path, 'r', encoding="utf-8") as file:
        # if not json format then return empty dict
        try:
            data = json.load(file)
        except json.JSONDecodeError:
            print(f"Error decoding JSON from {file_path}. Returning empty dictionary.")
            return {}
    return data


def write_json(file_path: str, data: dict):
    """
    Writes a dictionary to a JSON file.

    Args:
        file_path (str): The path to the JSON file.
        data (dict): The data to write to the JSON file.
    """
    with open(file_path, 'w', encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False, sort_keys=True)
