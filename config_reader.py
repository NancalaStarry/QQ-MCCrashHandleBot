import yaml
import os

class Config:
    def __init__(self, config_file=os.path.join(os.path.dirname(os.path.realpath(__file__)),"config.yaml")):
        self.config_file = config_file
        if not os.path.exists(self.config_file):
            self.create_default_config()
        self.load_config()

    def create_default_config(self):
        default_config = """
# Configuration for the chatbot

# Cache file path
cache_file_path: "cache"

# Crash reason database file path
crash_reason_database_path: "crash_reasons.json"

# QQ number
QQ_number: 3630124032

# Websocket URL
ws_uri: "ws://127.0.0.1:3002"

# Group whitelist
group_whitelist:
    - 660119486
"""
        with open(self.config_file, 'w', encoding='utf-8') as file:
            file.write(default_config)

    def load_config(self):
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"Configuration file '{self.config_file}' not found.")

        with open(self.config_file, 'r', encoding='utf-8') as file:
            try:
                config = yaml.safe_load(file)
            except yaml.YAMLError as e:
                raise ValueError(f"Error parsing configuration file: {e}")

        self.QQ_number = config.get('QQ_number')
        self.cache_file_path = config.get('cache_file_path')
        self.ws_uri = config.get('ws_uri')
        self.crash_reason_database_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),config.get('crash_reason_database_path'))
        self.group_whitelist = config.get('group_whitelist')


# Example usage
if __name__ == "__main__":
    try:
        config = Config()
    except (FileNotFoundError, ValueError) as e:
        print(e)