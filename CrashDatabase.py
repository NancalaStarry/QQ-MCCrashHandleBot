from dataclasses import dataclass
from typing import List, Dict, Optional
import JsonHandle

@dataclass
class Person:
    id: int
    name: str

    # 将对象转换为字典格式
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

    # 将对象转换为字典格式
    def dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "priority": self.priority
        }

@dataclass
class CrashReasonPromoter:
    crash_reason_id: str  # 崩溃原因的ID
    person_id: int        # 关联的人员ID

@dataclass
class RuleContributor:
    rule_id: str          # 规则的ID
    person_id: int        # 关联的人员ID

@dataclass
class DetectionRule:
    id: str
    crash_reason_id: str
    match_type: int       # 匹配类型（0：精确匹配，1：正则匹配）
    match: str            # 匹配内容

    # 将对象转换为字典格式
    def dict(self):
        return {
            "id": self.id,
            "crash_reason_id": self.crash_reason_id,
            "match_type": self.match_type,
            "match": self.match
        }

class CrashReasonDatabase:
    def __init__(self,
                 persons_file_path: str = "persons.json",
                 crash_reasons_file_path: str = "crash_reasons.json",
                 detection_rules_file_path: str = "detection_rules.json",
                 crash_promoters_file_path: str = "crash_promoters.json",
                 rule_contributors_file_path: str = "rule_contributors.json"):
        # 初始化文件路径
        self.persons_file_path = persons_file_path
        self.crash_reasons_file_path = crash_reasons_file_path
        self.detection_rules_file_path = detection_rules_file_path
        self.crash_promoters_file_path = crash_promoters_file_path
        self.rule_contributors_file_path = rule_contributors_file_path

        # 初始化数据容器
        self.crash_promoters = {}  # 存储崩溃原因与人员的关联
        self.rule_contributors = {}  # 存储规则与人员的关联
        self.persons = {}  # 存储人员信息
        self.crash_reasons = {}  # 存储崩溃原因信息
        self.detection_rules = {}  # 存储检测规则信息

        # 从文件加载数据
        self.load_all()

    # 加载所有数据
    def load_all(self):
        self.load_persons()
        self.load_crash_reasons()
        self.load_detection_rules()
        self.load_crash_promoters()
        self.load_rule_contributors()

    # 加载崩溃原因与人员的关联数据
    def load_crash_promoters(self) -> bool:
        try:
            self.crash_promoters = JsonHandle.read_json(self.crash_promoters_file_path)
            return True
        except Exception as e:
            print(f"加载崩溃原因发现者数据时出错: {e}")
            self.crash_promoters = {}
            return False

    # 加载规则与人员的关联数据
    def load_rule_contributors(self) -> bool:
        try:
            self.rule_contributors = JsonHandle.read_json(self.rule_contributors_file_path)
            return True
        except Exception as e:
            print(f"加载规则贡献者数据时出错: {e}")
            self.rule_contributors = {}
            return False

    # 保存崩溃原因与人员的关联数据
    def save_crash_promoters(self) -> bool:
        try:
            JsonHandle.write_json(self.crash_promoters_file_path, self.crash_promoters)
            return True
        except Exception as e:
            print(f"保存崩溃原因发现者数据时出错: {e}")
            return False

    # 保存规则与人员的关联数据
    def save_rule_contributors(self) -> bool:
        try:
            JsonHandle.write_json(self.rule_contributors_file_path, self.rule_contributors)
            return True
        except Exception as e:
            print(f"保存规则贡献者数据时出错: {e}")
            return False

    # 添加崩溃原因与发现者的关联
    def add_crash_promoter(self, crash_id: str, person_id: int) -> bool:
        key = f"{crash_id}_{person_id}"
        if key in self.crash_promoters:
            return True  # 如果已存在，直接返回
        self.crash_promoters[key] = {
            "crash_reason_id": crash_id,
            "person_id": person_id
        }
        return self.save_crash_promoters()

    # 获取某个崩溃原因的所有发现者
    def get_promoters_for_crash(self, crash_id: str) -> List[Person]:
        promoters = []
        for key, relation in self.crash_promoters.items():
            if relation["crash_reason_id"] == crash_id:
                person = self.get_person(relation["person_id"])
                if person:
                    promoters.append(person)
        return promoters

    # 添加规则与贡献者的关联
    def add_rule_contributor(self, rule_id: str, person_id: int) -> bool:
        key = f"{rule_id}_{person_id}"
        if key in self.rule_contributors:
            return True  # 如果已存在，直接返回
        self.rule_contributors[key] = {
            "rule_id": rule_id,
            "person_id": person_id
        }
        return self.save_rule_contributors()

    # 获取某个规则的所有贡献者
    def get_contributors_for_rule(self, rule_id: str) -> List[Person]:
        contributors = []
        for key, relation in self.rule_contributors.items():
            if relation["rule_id"] == rule_id:
                person = self.get_person(relation["person_id"])
                if person:
                    contributors.append(person)
        return contributors

    # 加载人员数据
    def load_persons(self) -> bool:
        try:
            self.persons = JsonHandle.read_json(self.persons_file_path)
            return True
        except Exception as e:
            print(f"加载人员数据时出错: {e}")
            self.persons = {}
            return False

    # 加载崩溃原因数据
    def load_crash_reasons(self) -> bool:
        try:
            self.crash_reasons = JsonHandle.read_json(self.crash_reasons_file_path)
            return True
        except Exception as e:
            print(f"加载崩溃原因数据时出错: {e}")
            self.crash_reasons = {}
            return False

    # 加载检测规则数据
    def load_detection_rules(self) -> bool:
        try:
            self.detection_rules = JsonHandle.read_json(self.detection_rules_file_path)
            return True
        except Exception as e:
            print(f"加载检测规则数据时出错: {e}")
            self.detection_rules = {}
            return False

    # 保存人员数据
    def save_persons(self) -> bool:
        try:
            JsonHandle.write_json(self.persons_file_path, self.persons)
            return True
        except Exception as e:
            print(f"保存人员数据时出错: {e}")
            return False

    # 保存崩溃原因数据
    def save_crash_reasons(self) -> bool:
        try:
            JsonHandle.write_json(self.crash_reasons_file_path, self.crash_reasons)
            return True
        except Exception as e:
            print(f"保存崩溃原因数据时出错: {e}")
            return False

    # 保存检测规则数据
    def save_detection_rules(self) -> bool:
        try:
            JsonHandle.write_json(self.detection_rules_file_path, self.detection_rules)
            return True
        except Exception as e:
            print(f"保存检测规则数据时出错: {e}")
            return False

    # 添加人员
    def add_person(self, person: Person) -> bool:
        if str(person.id) in self.persons:
            print(f"ID为{person.id}的人员已存在。")
            return False
        self.persons[str(person.id)] = person.dict()
        return self.save_persons()

    # 根据ID获取人员信息
    def get_person(self, person_id: int) -> Optional[Person]:
        str_id = str(person_id)
        if str_id not in self.persons:
            print(f"未找到ID为{person_id}的人员。")
            return None
        person_data = self.persons[str_id]
        return Person(
            id=person_data["id"],
            name=person_data["name"]
        )

    # 添加崩溃原因
    def add_crash_reason(self, crash_reason: CrashReason) -> bool:
        if crash_reason.id in self.crash_reasons:
            print(f"ID为{crash_reason.id}的崩溃原因已存在。")
            return False
        self.crash_reasons[crash_reason.id] = crash_reason.dict()
        return self.save_crash_reasons()

    # 更新崩溃原因
    def update_crash_reason(self, crash_reason: CrashReason) -> bool:
        if crash_reason.id not in self.crash_reasons:
            print(f"ID为{crash_reason.id}的崩溃原因不存在。")
            return False
        self.crash_reasons[crash_reason.id] = crash_reason.dict()
        return self.save_crash_reasons()

    # 根据ID获取崩溃原因
    def get_crash_reason(self, crash_reason_id: str) -> Optional[CrashReason]:
        if crash_reason_id not in self.crash_reasons:
            print(f"未找到ID为{crash_reason_id}的崩溃原因。")
            return None
        data = self.crash_reasons[crash_reason_id]
        return CrashReason(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            priority=data["priority"]
        )

    # 添加检测规则
    def add_detection_rule(self, rule: DetectionRule) -> bool:
        # 确保崩溃原因存在
        if not self.get_crash_reason(rule.crash_reason_id):
            print(f"ID为{rule.crash_reason_id}的崩溃原因不存在。")
            return False

        if rule.id in self.detection_rules:
            print(f"ID为{rule.id}的检测规则已存在。")
            return False
        self.detection_rules[rule.id] = rule.dict()
        return self.save_detection_rules()

    # 获取某个崩溃原因的所有检测规则
    def get_detection_rules_for_crash(self, crash_reason_id: str) -> List[DetectionRule]:
        rules = []
        for rule_id, rule_data in self.detection_rules.items():
            if rule_data["crash_reason_id"] == crash_reason_id:
                rules.append(DetectionRule(
                    id=rule_id,
                    crash_reason_id=rule_data["crash_reason_id"],
                    match_type=rule_data["match_type"],
                    match=rule_data["match"]
                ))
        return rules

    # 获取崩溃原因及其相关规则和发现者
    def get_crash_with_rules(self, crash_reason_id: str) -> Optional[Dict]:
        crash_reason = self.get_crash_reason(crash_reason_id)
        if not crash_reason:
            return None

        rules = self.get_detection_rules_for_crash(crash_reason_id)
        promoters = self.get_promoters_for_crash(crash_reason_id)

        return {
            "crash_reason": crash_reason,
            "detection_rules": rules,
            "promoters": promoters
        }