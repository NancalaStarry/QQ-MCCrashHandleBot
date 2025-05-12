from dataclasses import dataclass
from typing import List, Dict, Optional
import JsonHandle


@dataclass
class Person:
    id: int
    name: str

    def dict(self):
        return {
            "id": self.id,
            "name": self.name
        }


@dataclass
class CrashReason:
    id: str
    name: str
    description: str
    priority: int
    promoter_id: int  # Foreign key to Person

    def dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "priority": self.priority,
            "promoter_id": self.promoter_id
        }


@dataclass
class DetectionRule:
    id: str  # Primary key
    crash_reason_id: str  # Foreign key to CrashReason
    match_type: int
    match: str
    contributor_id: int  # Foreign key to Person

    def dict(self):
        return {
            "id": self.id,
            "crash_reason_id": self.crash_reason_id,
            "match_type": self.match_type,
            "match": self.match,
            "contributor_id": self.contributor_id
        }


class CrashReasonDatabase:
    def __init__(self,
                 persons_file_path: str = "persons.json",
                 crash_reasons_file_path: str = "crash_reasons.json",
                 detection_rules_file_path: str = "detection_rules.json"):
        self.persons_file_path = persons_file_path
        self.crash_reasons_file_path = crash_reasons_file_path
        self.detection_rules_file_path = detection_rules_file_path

        # Initialize data containers
        self.persons = {}
        self.crash_reasons = {}
        self.detection_rules = {}

        # Load data from files
        self.load_all()

    def load_all(self):
        self.load_persons()
        self.load_crash_reasons()
        self.load_detection_rules()

    def load_persons(self) -> bool:
        try:
            self.persons = JsonHandle.read_json(self.persons_file_path)
            return True
        except Exception as e:
            print(f"Error loading persons from {self.persons_file_path}: {e}")
            self.persons = {}
            return False

    def load_crash_reasons(self) -> bool:
        try:
            self.crash_reasons = JsonHandle.read_json(self.crash_reasons_file_path)
            return True
        except Exception as e:
            print(f"Error loading crash reasons from {self.crash_reasons_file_path}: {e}")
            self.crash_reasons = {}
            return False

    def load_detection_rules(self) -> bool:
        try:
            self.detection_rules = JsonHandle.read_json(self.detection_rules_file_path)
            return True
        except Exception as e:
            print(f"Error loading detection rules from {self.detection_rules_file_path}: {e}")
            self.detection_rules = {}
            return False

    def save_persons(self) -> bool:
        try:
            JsonHandle.write_json(self.persons_file_path, self.persons)
            return True
        except Exception as e:
            print(f"Error saving persons to {self.persons_file_path}: {e}")
            return False

    def save_crash_reasons(self) -> bool:
        try:
            JsonHandle.write_json(self.crash_reasons_file_path, self.crash_reasons)
            return True
        except Exception as e:
            print(f"Error saving crash reasons to {self.crash_reasons_file_path}: {e}")
            return False

    def save_detection_rules(self) -> bool:
        try:
            JsonHandle.write_json(self.detection_rules_file_path, self.detection_rules)
            return True
        except Exception as e:
            print(f"Error saving detection rules to {self.detection_rules_file_path}: {e}")
            return False

    # Person methods
    def add_person(self, person: Person) -> bool:
        if str(person.id) in self.persons:
            print(f"Person with ID {person.id} already exists.")
            return False
        self.persons[str(person.id)] = person.dict()
        return self.save_persons()

    def get_person(self, person_id: int) -> Optional[Person]:
        str_id = str(person_id)
        if str_id not in self.persons:
            print(f"Person with ID {person_id} not found.")
            return None
        person_data = self.persons[str_id]
        return Person(
            id=person_data["id"],
            name=person_data["name"]
        )

    # CrashReason methods
    def add_crash_reason(self, crash_reason: CrashReason) -> bool:
        # Verify promoter exists
        if not self.get_person(crash_reason.promoter_id):
            print(f"Promoter with ID {crash_reason.promoter_id} does not exist.")
            return False

        if crash_reason.id in self.crash_reasons:
            print(f"Crash reason with ID {crash_reason.id} already exists.")
            return False
        self.crash_reasons[crash_reason.id] = crash_reason.dict()
        return self.save_crash_reasons()

    def get_crash_reason(self, crash_reason_id: str) -> Optional[CrashReason]:
        if crash_reason_id not in self.crash_reasons:
            print(f"Crash reason with ID {crash_reason_id} not found.")
            return None
        data = self.crash_reasons[crash_reason_id]
        return CrashReason(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            priority=data["priority"],
            promoter_id=data["promoter_id"]
        )

    # DetectionRule methods
    def add_detection_rule(self, rule: DetectionRule) -> bool:
        # Verify crash_reason exists
        if not self.get_crash_reason(rule.crash_reason_id):
            print(f"Crash reason with ID {rule.crash_reason_id} does not exist.")
            return False

        # Verify contributor exists
        if not self.get_person(rule.contributor_id):
            print(f"Contributor with ID {rule.contributor_id} does not exist.")
            return False

        if rule.id in self.detection_rules:
            print(f"Detection rule with ID {rule.id} already exists.")
            return False
        self.detection_rules[rule.id] = rule.dict()
        return self.save_detection_rules()

    def get_detection_rules_for_crash(self, crash_reason_id: str) -> List[DetectionRule]:
        rules = []
        for rule_id, rule_data in self.detection_rules.items():
            if rule_data["crash_reason_id"] == crash_reason_id:
                rules.append(DetectionRule(
                    id=rule_id,
                    crash_reason_id=rule_data["crash_reason_id"],
                    match_type=rule_data["match_type"],
                    match=rule_data["match"],
                    contributor_id=rule_data["contributor_id"]
                ))
        return rules

    # Helper methods to maintain compatibility with original code
    def get_crash_with_rules(self, crash_reason_id: str) -> Dict:
        crash_reason = self.get_crash_reason(crash_reason_id)
        if not crash_reason:
            return None

        rules = self.get_detection_rules_for_crash(crash_reason_id)
        promoter = self.get_person(crash_reason.promoter_id)

        return {
            "crash_reason": crash_reason,
            "detection_rules": rules,
            "promoter": promoter
        }