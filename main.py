import logging
import os
import re
from datetime import datetime as dt
from enum import Enum
from typing import List, Optional, Union, Dict
from flashtext import KeywordProcessor

import crash_database_old

import config_reader
cf = config_reader.Config()

class Special_CrashReason(Enum):
    # Mod issues
    JAVA_TOO_HIGH = ("Java版本过高","PCL Loader")
    JAVA_VERSION_ERROR = ("Java版本错误","PCL Loader")
    MOD_MISSING = ("缺少依赖Mod","PCL Loader")
    MOD_DUPLICATE = ("Mod重复安装","PCL Loader")
    MOD_INCOMPATIBLE = ("Mod互不兼容","PCL Loader")
    MOD_SUSPECTED = ("怀疑Mod导致游戏崩溃","PCL Loader")
    MOD_CONFIRMED = ("确定Mod导致游戏崩溃","PCL Loader")
    MOD_INIT_FAILED = ("Mod初始化失败","PCL Loader")
    MOD_MIXIN_FAILED = ("Mod注入(Mixin)失败","PCL Loader")
    MOD_CONFIG_ERROR = ("Mod配置文件错误","PCL Loader")
    MOD_SPECIAL_CHARS = ("Mod名称包含特殊字符","PCL Loader")
    MOD_REQUIRES_JAVA11 = ("Mod需要Java11或更高版本","PCL Loader")
    MOD_TOO_MANY = ("Mod过多导致超出ID限制","PCL Loader")

    # Loader issues
    FABRIC_ERROR = ("Fabric报错","PCL Loader")
    FABRIC_SOLUTION = ("Fabric报错并给出解决方案","PCL Loader")
    FORGE_ERROR = ("Forge报错","PCL Loader")
    FORGE_INCOMPLETE = ("Forge安装不完整","PCL Loader")
    FORGE_JAVA_INCOMPATIBLE = ("低版本Forge与高版本Java不兼容","PCL Loader")
    MULTIPLE_FORGE = ("版本Json中存在多个Forge","PCL Loader")
    MIXIN_BOOTSTRAP_MISSING = ("MixinBootstrap缺失","PCL Loader")

    # Game errors
    BLOCK_ERROR = ("特定方块导致崩溃","PCL Loader")
    ENTITY_ERROR = ("特定实体导致崩溃","PCL Loader")
    OPTIFINE_FORGE_INCOMPATIBLE = ("OptiFine与Forge不兼容","PCL Loader")
    OPTIFINE_WORLD_LOAD_ERROR = ("OptiFine导致无法加载世界","PCL Loader")
    SHADERSMOD_OPTIFINE_CONFLICT = ("ShadersMod与OptiFine同时安装","PCL Loader")
    FILE_VALIDATION_ERROR = ("文件或内容校验失败","PCL Loader")
    MANUAL_DEBUG_CRASH = ("玩家手动触发调试崩溃","PCL Loader")

    # Other
    STACK_KEYWORD_FOUND = ("堆栈分析发现关键字","PCL Loader")
    NO_ANALYSIS_FILES = ("没有可用的分析文件","NONE")
    UNKNOWN = ("未知原因，请查看完整日志", "NONE")


def class_java_mapping(class_version: int) -> int:
    return class_version - 44


class FileType:
    HS_ERR = "HsErr"
    MINECRAFT_LOG = "MinecraftLog"
    DEBUG_LOG = "DebugLog"
    EXTRA_LOG = "ExtraLog"
    CRASH_REPORT = "CrashReport"


class MinecraftCrashAnalyzer:
    def __init__(self, folder_path: str = None):
        self.analyzed_files = []
        self.log_mc = None
        self.log_mc_debug = None
        self.log_hs = None
        self.log_crash = None
        self.log_all = None
        self.crash_reasons = {}
        self.crashdb = crash_database.CrashReasonDatabase(folder_path)
        self.keyword_processor = KeywordProcessor()

    def collect_logs(self, folder_path: str) -> bool:
        """
        Collect available log files from specified folder

        Args:
            folder_path: Path to folder containing crash logs

        Returns:
            True if any files were found, False otherwise
        """
        print(f"Collecting logs from: {folder_path}")
        self.analyzed_files = []

        # Check if folder exists
        if not os.path.exists(folder_path):
            print(f"Folder {folder_path} does not exist")
            return False

        # Find all potential log files
        recent_files = []
        for file in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file)
            if not os.path.isfile(file_path):
                continue

            # Check file extension and content
            name_lower = file.lower()
            if (name_lower.endswith('.log') or name_lower.endswith('.txt')) and os.path.getsize(file_path) > 0:
                # Check if file was modified recently (within last 30 minutes)
                mod_time = os.path.getmtime(file_path)
                recent_files.append(file_path)
                print(f"Found recent log file: {file}")

        # Read files content
        for file_path in recent_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if content:
                        self.analyzed_files.append((file_path, content.splitlines()))
                        print(f"Added {file_path} for analysis")
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")

        return len(self.analyzed_files) > 0

    def prepare_logs(self) -> int:
        """
        Process collected log files and categorize them

        Returns:
            Number of useful log files found
        """
        print("Preparing logs for analysis")
        # Reset log variables
        self.log_mc = None
        self.log_mc_debug = None
        self.log_hs = None
        self.log_crash = None

        # Categorize files
        categorized_files = {}

        for file_path, content in self.analyzed_files:
            file_name = os.path.basename(file_path).lower()

            # Categorize file by name
            file_type = None
            if file_name.startswith("hs_err"):
                file_type = FileType.HS_ERR
            elif file_name.startswith("crash-"):
                file_type = FileType.CRASH_REPORT
            elif file_name.startswith("latest") or file_name.startswith("游戏崩溃前的输出") or file_name.startswith("rawoutput"):
                file_type = FileType.MINECRAFT_LOG
            elif file_name == "debug.log" or file_name == "debug log.txt":
                file_type = FileType.DEBUG_LOG
            elif file_name == "pcl 启动器日志.txt" or file_name == "hmcl.log":
                continue
            elif file_name.endswith(".log") or file_name.endswith(".txt"):
                # Check if this is launcher log with game output
                if any("以下为游戏输出的最后一段内容" in line for line in content):
                    file_type = FileType.MINECRAFT_LOG
                else:
                    file_type = FileType.EXTRA_LOG

            if file_type and len(content) > 0:
                if file_type not in categorized_files:
                    categorized_files[file_type] = []
                categorized_files[file_type].append((file_path, content))
                print(f"Categorized {file_path} as {file_type}")

        # Process each file type
        file_count = 0

        # Process crash reports
        if FileType.CRASH_REPORT in categorized_files:
            # Use the newest crash report
            file_path, content = categorized_files[FileType.CRASH_REPORT][0]
            self.log_crash = "\n".join(content)
            file_count += 1
            print(f"Using crash report: {file_path}")

        # Process Minecraft logs
        if FileType.MINECRAFT_LOG in categorized_files:
            # Use the newest Minecraft log
            file_path, content = categorized_files[FileType.MINECRAFT_LOG][0]
            self.log_mc = "\n".join(content)
            file_count += 1
            print(f"Using Minecraft log: {file_path}")

        # Process debug logs
        if FileType.DEBUG_LOG in categorized_files:
            # Use the newest debug log
            file_path, content = categorized_files[FileType.DEBUG_LOG][0]
            self.log_mc_debug = "\n".join(content)
            file_count += 1
            print(f"Using debug log: {file_path}")

        # Process JVM error logs
        if FileType.HS_ERR in categorized_files:
            # Use the newest hs_err log
            file_path, content = categorized_files[FileType.HS_ERR][0]
            self.log_hs = "\n".join(content)
            file_count += 1
            print(f"Using JVM error log: {file_path}")

        # Combine all logs for full-text search
        all_logs = []
        if self.log_crash:
            all_logs.append(self.log_crash)
        if self.log_mc:
            all_logs.append(self.log_mc)
        if self.log_mc_debug:
            all_logs.append(self.log_mc_debug)
        if self.log_hs:
            all_logs.append(self.log_hs)

        self.log_all = "\n".join(all_logs)

        print(f"Log preparation complete. Found {file_count} useful files for analysis.")
        return file_count

    def append_keyword_reason(self, reason: str, details: Union[str, List[str]] = None) -> None:
        """Add a keyword reason with optional details"""
        if isinstance(details, str) and details:
            details = [details]

        if reason in self.crash_reasons:
            if details:
                self.crash_reasons[reason].extend(details)
        else:
            self.crash_reasons[reason] = details if details else []

    def append_regex_reason(self, reason: str, details: Union[str, List[str]] = None) -> None:
        """Add a regex reason with optional details"""
        if isinstance(details, str) and details:
            details = [details]

        if reason in self.crash_reasons:
            if details:
                self.crash_reasons[reason].extend(details)
        else:
            self.crash_reasons[reason] = details if details else []

    def append_special_reason(self, reason: Special_CrashReason, details: Union[str, List[str]] = None) -> None:
        """Add a crash reason with optional details"""
        if isinstance(details, str) and details:
            details = [details]

        if reason in self.crash_reasons:
            if details:
                self.crash_reasons[reason].extend(details)
        else:
            self.crash_reasons[reason] = details if details else []

        print(f"Found crash reason: {reason.value} {details if details else ''}")

    def analyze(self) -> str:
        """
        Analyze logs to determine crash reasons

        Returns:
            Analysis result as a user-friendly string
        """
        print("Starting crash analysis")
        self.crash_reasons = {}

        # Check if we have any files to analyze
        if not self.log_all:
            self.append_special_reason(Special_CrashReason.NO_ANALYSIS_FILES)
            return self.get_analysis_result()

        # Step 1: High priority log matching
        self.analyze_crit1()
        if self.crash_reasons:
            return self.get_analysis_result()

        # Step 2: Keyword matching
        self.analyze_with_keyword()
        if self.crash_reasons:
            return self.get_analysis_result()

        # Step 3: Regex matching
        self.analyze_with_all_regex()
        if self.crash_reasons:
            return self.get_analysis_result()

        # Step 4: Stack trace analysis
        if any(loader in self.log_all.lower() for loader in ["forge", "fabric", "quilt", "liteloader"]):
            stack_trace = self.extract_stack_trace()
            if stack_trace:
                keywords = self.analyze_stack_keyword(stack_trace)
                if keywords:
                    mod_names = self.analyze_mod_name(keywords)
                    if mod_names:
                        self.append_special_reason(Special_CrashReason.MOD_SUSPECTED, mod_names)
                        return self.get_analysis_result()
                    else:
                        self.append_special_reason(Special_CrashReason.STACK_KEYWORD_FOUND, keywords)
                        return self.get_analysis_result()

        # Step 4: Low priority log matching
        self.analyze_crit3()

        # If no reasons found, return unknown
        if not self.crash_reasons:
            self.append_special_reason(Special_CrashReason.UNKNOWN)

        return self.get_analysis_result()

    def extract_stack_trace(self) -> Optional[str]:
        """Extract stack trace from crash log"""
        if not self.log_crash:
            return None

        # Look for stack trace patterns
        stack_matches = re.search(r"-- Stack Trace --\s*\n((?:.*\n)*?)(?:\n--|\Z)", self.log_crash)
        if stack_matches:
            return stack_matches.group(1)

        # Alternative pattern for some crash reports
        alt_matches = re.search(r"java\.lang\.[A-Za-z]+Exception.*\n((?:\s+at .*\n)*)", self.log_crash)
        if alt_matches:
            return alt_matches.group(0) + alt_matches.group(1)

        return None

    def build_keyword_dictionary(self):
        """
        Build a dictionary of keywords from crash database for keyword matching.
        Sets up the keyword processor with these keywords.

        Returns:
            bool: True if keywords were successfully added to the processor
        """
        try:
            # Clear existing processor keywords
            self.keyword_processor.remove_keywords_from_list(list(self.keyword_processor.get_all_keywords()))

            # Build keyword dictionary
            self.keywords_dict = {}
            crash_items = self.crashdb.get_all_crash_reasons()

            for crash_item in crash_items:
                detection_rules = self.crashdb.get_detection_rule(crash_item.id)

                if not detection_rules:
                    continue

                # Filter rules that use keyword matching (match_type == 0)
                keyword_match = [rule.match for rule in detection_rules.detectionRule
                                   if rule.match_type == 0 and rule.match]

                if keyword_match:
                    self.keywords_dict[crash_item.id] = keyword_match

            # Add keywords to processor if dictionary isn't empty
            if self.keywords_dict:
                self.keyword_processor.add_keywords_from_dict(self.keywords_dict)
                return True

            return False

        except Exception as e:
            self.log(f"[ERROR] Building keyword dictionary failed: {str(e)}")
            return False

    def analyze_with_keyword(self):
        """
        Analyze logs for keywords defined in the crash database and identify matching crash reasons.
        Uses flashtext's KeywordProcessor for efficient multi-keyword matching.
        """
        try:
            # First build the keyword dictionary
            if not self.build_keyword_dictionary():
                return

            # Now perform the analysis if we have logs to analyze
            if self.log_all:
                keywords_found = set(self.keyword_processor.extract_keywords(self.log_all))

                # Record found crash reasons
                for keyword in keywords_found:
                    crash_item = self.crashdb.get_crash_reason(keyword)
                    if crash_item:
                        self.append_keyword_reason(crash_item.id, self.crashdb.get_crash_reason(crash_item.id).description)
                        self.log(f"[Keyword] Found matching crash reason: {crash_item.id} - {crash_item.name}")

        except Exception as e:
            self.log(f"[ERROR] Keyword analysis failed: {str(e)}")

    def analyze_with_all_regex(self):
        """
        Analyze text using regex patterns and template to generate formatted results.
        """
        crash_items = self.crashdb.get_all_crash_reasons()

        for crash_item in crash_items:
            detection_rules = self.crashdb.get_detection_rule(crash_item.id)

            if not detection_rules:
                continue

            # Filter rules that use keyword matching (match_type == 1)
            regex_patterns = [(crash_item.id, rule.match) for rule in detection_rules.detectionRule
                               if rule.match_type == 1 and rule.match]

            # analyze each regex pattern
            for id, pattern in regex_patterns:
                results = self.analyze_with_regex(pattern, crash_item.description)
                if results:
                    self.append_regex_reason(id, results)
                    self.log(f"[Regex] Found matching crash reason: {id} - {crash_item.name}")


    def analyze_with_regex(self, pattern: str, template: str) -> List[str]:
        """
        Analyze text using regex patterns and template to generate formatted results.

        Args:
            pattern: regex pattern to extract values
            template: Template string with placeholders like [[1]], [[2]]

        Returns:
            List of formatted strings where placeholders are replaced with extracted values
        """
        results = []
        print(pattern)
        for match in re.finditer(pattern, self.log_all, re.DOTALL):
            all_matched = True
            values = []
            for i in range(1, len(match.groups()) + 1):
                print(f"Group {i}: {match.group(i)}")
                value = match.group(i)
                if value is None:
                    all_matched = False
                    break
                values.append(value)

            # Check if all groups matched and the number of values matches the number of placeholders
            if all_matched and len(values) == template.count("[["):

                result = template
                for i, value in enumerate(values):
                    result = result.replace(f"[[{i + 1}]]", value)
                results.append(result)

        return results

    def analyze_crit1(self):
        """High priority log matching for critical issues"""
        # Check Forge Suggestion
        # 寻找所有的“Suspected Mod: ”，获取这一行的下一行的一整行，如有重复则剔除
        if "Suspected Mod: " in self.log_all:
            suspected_mods = []
            raw_suspected_mods: List[str] = re.findall(r"Suspected Mod: \s*(.*?)\n", self.log_all, re.DOTALL)
            # 汉化
            for i, text in enumerate(raw_suspected_mods):
                text = "第" + str(i + 1) + "个: " + text
                text = text.replace(", Version: ", "模组，其在游戏中的版本号为: ")
                suspected_mods.append(text)
            if suspected_mods:
                self.append_special_reason(Special_CrashReason.MOD_SUSPECTED, list(set(suspected_mods)))
                return

        # Java版本错误：
        if "Class file major version" in self.log_all:
            major_version = re.search(r"Class file major version (\d+)", self.log_all)
            if major_version:
                mapped_major_version = class_java_mapping(int(major_version.group(1)))
                now_version = re.search(r"supports class version (\d+)", self.log_all)
                mapped_now_version = class_java_mapping(int(now_version.group(1)))
                if mapped_major_version > mapped_now_version:
                    self.append_special_reason(Special_CrashReason.JAVA_TOO_HIGH,
                                       "需要的Java版本: " + str(mapped_major_version) + "，当前Java版本: " + str(
                                           mapped_now_version))
                    return
                else:
                    self.append_special_reason(Special_CrashReason.JAVA_VERSION_ERROR,
                                       "需要的Java版本: " + str(mapped_major_version) + "，当前Java版本: " + str(
                                           mapped_now_version))
                    return



        # Check for incompatible mods
        # TODO

        # Check for specific mod causing crashes


        # Check for block/entity errors
        # if self.log_crash:
        #     if "\tBlock location: World: " in self.log_crash:
        #         block_type = re.search(r"(?<=\tBlock: Block\{)[^\}]+", self.log_crash)
        #         block_location = re.search(r"(?<=\tBlock location: World: )\([^\)]+\)", self.log_crash)
        #         block_info = []
        #         if block_type:
        #             block_info.append(block_type.group())
        #         if block_location:
        #             block_info.append(block_location.group())
        #         self.append_special_reason(Special_CrashReason.BLOCK_ERROR, " ".join(block_info) if block_info else None)
        #         return
        #
        #     if "\tEntity's Exact location: " in self.log_crash:
        #         entity_type = re.search(r"(?<=\tEntity Type: )[^\n]+(?= \()", self.log_crash)
        #         entity_location = re.search(r"(?<=\tEntity's Exact location: )[^\n]+", self.log_crash)
        #         entity_info = []
        #         if entity_type:
        #             entity_info.append(entity_type.group())
        #         if entity_location:
        #             entity_info.append("(" + entity_location.group().strip() + ")")
        #         self.append_special_reason(Special_CrashReason.ENTITY_ERROR, " ".join(entity_info) if entity_info else None)
        #         return

        # Check for mod requirements missing

        if "Missing or unsupported mandatory dependencies:" in self.log_all:
            missing_mods_notice = re.findall(r"Missing or unsupported mandatory dependencies:\n((?:\tMod ID:.*\n?)+)",
                                             self.log_all)
            if missing_mods_notice:
                mod_entries = re.findall(
                    r"\tMod ID: '(.+?)', Requested by: '(.+?)', Expected range: '(.+?)', Actual version: '(.+?)'",
                    missing_mods_notice[0])
                last_mod_id = None
                merged_mods = []
                for mod_id, requested_by, expected_range, actual_version in mod_entries:
                    if actual_version == '[MISSING]':
                        self.append_special_reason(Special_CrashReason.MOD_MISSING,
                                           f"需要安装'{mod_id}'前置模组（请求自: '{requested_by}'）")
                    else:
                        self.append_special_reason(Special_CrashReason.MOD_MISSING,
                                           f"需要更换 '{mod_id}'前置模组版本（请求自: '{requested_by}'），需要的版本：'{expected_range}'，当前版本: '{actual_version}'")
            else:
                print("未找到任何缺失的模组依赖信息。")

    def analyze_crit3(self):
        """Low priority log matching"""
        # Check for Mixin errors

        if "Mixin prepare failed " in self.log_all or \
                "Mixin apply failed " in self.log_all or \
                "MixinApplyError" in self.log_all or \
                "MixinTransformerError" in self.log_all or \
                "mixin.injection.throwables." in self.log_all or \
                ".json] FAILED during " in self.log_all:
            # Mod name matching
            mod_name = re.search(r"(?<=from mod )[^.\/ ]+(?=\] from)", self.log_all)
            if not mod_name:
                mod_name = re.search(r"(?<=for mod )[^.\/ ]+(?= failed)", self.log_all)
            if mod_name:
                self.append_special_reason(Special_CrashReason.MOD_MIXIN_FAILED,
                                           self.try_analyze_mod_name(mod_name.group().strip()))
                return
            # JSON name matching
            json_names = re.findall(r"(?<=^[^\t]+[ \[{(]{1})[^ \[{(]+\.[^ ]+(?=\.json)", self.log_all,
                                      re.MULTILINE)
            for json_name in json_names:
                self.append_special_reason(Special_CrashReason.MOD_MIXIN_FAILED,
                                           self.try_analyze_mod_name(json_name.replace("mixins", "mixin").replace(".mixin", "")
                                                             .replace("mixin.", "")))
                return
            # No explicit match
            self.append_special_reason(Special_CrashReason.MOD_MIXIN_FAILED)
            return



        # Specific pattern matching for various issues
        patterns = [
            (Special_CrashReason.FABRIC_ERROR, ["Fabric has crashed!", "Fabric has detected a mod loading error"]),
            (Special_CrashReason.FORGE_ERROR, ["Forge mod loading errors have been detected"]),
            (Special_CrashReason.MOD_INIT_FAILED, ["Failed to initialize mod", "Failed to create mod instance"])
        ]

        for reason, search_patterns in patterns:
            for pattern in search_patterns:
                if self.log_all and pattern in self.log_all:
                    self.append_special_reason(reason)
                    pattern = r"Failed to create mod instance\..*?\njava\.lang\.NoClassDefFoundError: ([^/]+/[^/]+/[^/]+)"
                    match = re.search(pattern, self.log_all)
                    if match:
                        missing_mod = match.group(1)
                        self.append_special_reason(Special_CrashReason.FORGE_ERROR,
                            f"检测到文件 '{missing_mod}'不存在，这可能是一个模组，请检查是否已安装该前置模组，或双方模组版本是否最新")


                    break

        # Look for Fabric solution
        fabric_solution_patterns = [
            r"(?<=A potential solution has been determined:\n)((\t)+ - [^\n]+\n)+",
            r"(?<=A potential solution has been determined, this may resolve your problem:\n)((\t)+ - [^\n]+\n)+"
        ]

        for pattern in fabric_solution_patterns:
            solution_match = re.search(pattern, self.log_all)
            if solution_match:
                solution_lines = re.findall(r"(?<=\t+)[^\n]+", solution_match.group())
                if solution_lines:
                    self.append_special_reason(Special_CrashReason.FABRIC_SOLUTION, solution_lines)
                    return

        # If very short output with no useful information
        if not (self.log_crash or "at net." in self.log_mc or "INFO]" in self.log_mc) and self.log_mc and len(
                self.log_mc) < 100:
            self.append_special_reason(Special_CrashReason.UNKNOWN)
            return

    def analyze_stack_keyword(self, stack_text):
        """Extract meaningful keywords from stack traces"""
        if not stack_text:
            return []

        keywords = []

        # Known keywords to ignore
        ignore_keywords = ["java", "sun", "javax", "lwjgl", "paulscode", "glcontext",
                           "native", "netty", "guava", "gson", "apache", "logging",
                           "minecraftforge", "fml", "minecraft"]

        # Extract package and class names from stack trace
        stack_lines = re.findall(r"\s+at\s+([^\(]+)", stack_text)
        for line in stack_lines:
            parts = line.strip().split(".")
            if len(parts) < 2:
                continue

            pkg_name = parts[0].lower()
            if any(keyword in pkg_name for keyword in ignore_keywords):
                continue

            keywords.append(pkg_name)

        # Extract exception class names
        exceptions = re.findall(r"([a-zA-Z0-9_$.]+\.[a-zA-Z0-9_$.]+Exception)", stack_text)
        for exception in exceptions:
            parts = exception.split(".")
            if len(parts) >= 2 and parts[0].lower() not in ignore_keywords:
                keywords.append(parts[0].lower())

        return list(set(keywords))

    def analyze_mod_name(self, keywords):
        """
        Try to get actual mod names from keywords.
        Returns a list of mod names if found, None if not.
        """
        mod_file_names = []

        # Preprocess keywords (split parentheses)
        real_keywords = []
        for keyword in keywords:
            if keyword:  # Check if keyword is not None or empty
                for sub_keyword in keyword.split("("):
                    real_keywords.append(sub_keyword.strip(" )"))
        keywords = real_keywords

        # Get mod information from crash report
        if self.log_crash and "A detailed walkthrough of the error" in self.log_crash:
            details = self.log_crash.split("A detailed walkthrough of the error", 1)[1]
            is_fabric_detail = "Fabric Mods" in details

            if is_fabric_detail:
                details = details.split("Fabric Mods", 1)[1]
                self.log("[Crash] Detected Fabric Mod information format in crash report")

            # Get lines containing .jar or mod information
            mod_name_lines = []
            for line in details.split("\n"):
                if ((".jar" in line.lower() and line.lower().count(".jar") == 1) or
                        (is_fabric_detail and line.startswith("\t\t") and not re.search(r"\t\tfabric[\w-]*: Fabric",
                                                                                        line))):
                    mod_name_lines.append(line)

            self.log(f"[Crash] Found {len(mod_name_lines)} possible mod item lines in crash report")

            # Find lines matching keywords
            hint_lines = []
            for keyword in keywords:
                for mod_string in mod_name_lines:
                    real_mod_string = mod_string.lower().replace("_", "")
                    if keyword.lower().replace("_", "") not in real_mod_string:
                        continue
                    if "minecraft.jar" in real_mod_string or " forge-" in real_mod_string or " mixin-" in real_mod_string:
                        continue
                    hint_lines.append(mod_string.strip("\r\n "))
                    break

            hint_lines = list(dict.fromkeys(hint_lines))  # Remove duplicates while preserving order
            self.log(f"[Crash] Found {len(hint_lines)} possible crash mod matching lines in crash report")
            for mod_line in hint_lines:
                self.log(f"[Crash]  - {mod_line}")

            # Extract .jar filenames
            for line in hint_lines:
                name = None
                if is_fabric_detail:
                    match = re.search(r": ([^\n]+) [^\n]+", line)
                    if match:
                        name = match.group(1)
                else:
                    match = re.search(r"\(([^\t]+\.jar)\)|(\t\t|^| \| )([^\t \|]+\.jar)", line, re.IGNORECASE)
                    if match:
                        groups = match.groups()
                        name = next((g for g in groups if g and g.strip() and '.jar' in g), None)

                if name and '.jar' in name:
                    mod_file_names.append(name)

        # Check debug log for mod information
        if self.log_mc_debug:
            # Forge format: Found valid mod file ModName-1.20.jar with {modid} mods
            mod_name_lines = re.findall(r"valid mod file .*", self.log_mc_debug, re.MULTILINE)
            self.log(f"[Crash] Found {len(mod_name_lines)} possible mod item lines in debug info")

            # Find match with keywords
            hint_lines = []
            for keyword in keywords:
                for mod_string in mod_name_lines:
                    if f"{{{keyword}}}" in mod_string:
                        hint_lines.append(mod_string)

            hint_lines = list(dict.fromkeys(hint_lines))
            self.log(f"[Crash] Found {len(hint_lines)} possible crash mod matching lines in debug info")
            for mod_line in hint_lines:
                self.log(f"[Crash]  - {mod_line}")

            # Extract mod filenames
            for line in hint_lines:
                match = re.search(r"(.*) with", line)
                if match:
                    name = match.group(1)
                    if name:
                        mod_file_names.append(name)

        # Final output
        mod_file_names = list(dict.fromkeys(mod_file_names))
        if not mod_file_names:
            return None
        else:
            self.log(f"[Crash] Found {len(mod_file_names)} possible crash mod filenames")
            for mod_filename in mod_file_names:
                self.log(f"[Crash]  - {mod_filename}")
            return mod_file_names

    def get_analysis_result(self) -> str:
        """
        Generate a user-friendly result message based on the detected crash reasons.

        Returns:
            A formatted string explaining the crash reasons
        """
        if not self.crash_reasons:
            return "无法确定崩溃原因，请检查完整日志获取更多信息。"

        results = []

        for reason, details in self.crash_reasons.items():
            if reason in (self.crashdb.data.keys()):
                if isinstance(details, list):
                    details = list(set(details))
                    details_str = "\n".join(details)
                if details_str:
                    desr = details_str.replace("\\n", "\n")
                    results.append(desr+"\n")

            if reason == Special_CrashReason.MOD_MISSING:
                if details:
                    DETAIL = '\n'.join(details)
                    results.append(f"缺少以下依赖Mod:\n{DETAIL}\n\n请安装以上缺失的Mod。")
                else:
                    results.append("缺少某些依赖Mod，导致游戏崩溃。\n\n请确保安装了所有必需的Mod。")

            elif reason == Special_CrashReason.MOD_DUPLICATE:
                if details:
                    results.append(
                        f"以下Mod被重复安装:\n{', '.join(details)}\n\n请删除重复的Mod文件，每个Mod只保留一个版本。")
                else:
                    results.append("某些Mod被重复安装，导致游戏崩溃。\n\n请检查mods文件夹，确保每个Mod只有一个版本。")

            elif reason == Special_CrashReason.MOD_SUSPECTED:
                if details:
                    results.append(
                        f"以下Mod可能导致了游戏崩溃:\n{', '.join(details)}\n\n尝试暂时移除以上的{len(details)}个Mod，看看是否可以解决问题。")
                else:
                    results.append(
                        "某些Mod可能导致了游戏崩溃，但无法确定具体是哪个Mod。\n\n尝试暂时移除部分Mod，看看是否可以解决问题。")

            elif reason == Special_CrashReason.MOD_CONFIRMED:
                if details:
                    results.append(f"以下Mod导致了游戏崩溃:\n{', '.join(details)}\n\n请更新或移除这些Mod。")
                else:
                    results.append("某个Mod导致了游戏崩溃。\n\n请检查并更新你的Mod。")

            elif reason == Special_CrashReason.MOD_INIT_FAILED:
                if details:
                    results.append(f"以下Mod初始化失败:\n{', '.join(details)}\n\n请尝试更新或重新安装这些Mod。")
                else:
                    results.append("某些Mod初始化失败，导致游戏崩溃。\n\n请检查并更新你的Mod。")

            elif reason == Special_CrashReason.MOD_MIXIN_FAILED:
                results.append(
                    "Mod的Mixin注入失败，导致游戏崩溃。\n\n这通常是由于Mod间的冲突导致的，请尝试更新或移除最近安装的Mod。")

            elif reason == Special_CrashReason.FABRIC_ERROR:
                if details and len(details) == 1:
                    results.append(
                        f"Fabric提供了以下错误信息:\n{details[0]}\n\n请根据上述信息进行对应处理，如果看不懂英文可以使用翻译软件。")
                else:
                    results.append(
                        "Fabric可能已经提供了错误信息，请根据错误报告中的日志信息进行对应处理，如果看不懂英文可以使用翻译软件。")

            elif reason == Special_CrashReason.FABRIC_SOLUTION:
                if details and len(details) == 1:
                    results.append(
                        f"Fabric提供了以下解决方案:\n{details[0]}\n\n请根据上述信息进行对应处理，如果看不懂英文可以使用翻译软件。")
                else:
                    results.append(
                        "Fabric可能已经提供了解决方案，请根据错误报告中的日志信息进行对应处理，如果看不懂英文可以使用翻译软件。")

            elif reason == Special_CrashReason.FORGE_ERROR:
                if details and len(details) == 1:
                    results.append(
                        f"Forge提供了以下错误信息:\n{details[0]}\n\n请根据上述信息进行对应处理，如果看不懂英文可以使用翻译软件。")
                else:
                    results.append(
                        "Forge可能已经提供了错误信息，请根据错误报告中的日志信息进行对应处理，如果看不懂英文可以使用翻译软件。")

            elif reason == Special_CrashReason.MIXIN_BOOTSTRAP_MISSING:
                results.append(
                    "MixinBootstrap缺失，导致游戏崩溃。\n\n这通常是由于Mod配置错误导致的，请重新安装Forge或Fabric。")

            elif reason == Special_CrashReason.BLOCK_ERROR:
                if details:
                    results.append(
                        f"特定方块导致崩溃:\n{details}\n\n请尝试进入游戏世界的其他区域，或者使用MCEdit等工具删除这个位置的方块。\n更多请查阅https://www.bilibili.com/opus/807799450495877206")
                else:
                    results.append(
                        "特定方块导致游戏崩溃。\n\n请尝试进入游戏世界的其他区域，或者使用MCEdit等工具编辑存档。")

            elif reason == Special_CrashReason.ENTITY_ERROR:
                if details:
                    results.append(
                        f"特定实体导致崩溃:\n{details}\n\n请尝试进入游戏世界的其他区域，或者使用MCEdit等工具删除这个实体。")
                else:
                    results.append(
                        "特定实体导致游戏崩溃。\n\n请尝试进入游戏世界的其他区域，或者使用MCEdit等工具编辑存档。")

            elif reason == Special_CrashReason.FILE_VALIDATION_ERROR:
                results.append(
                    "部分文件或内容校验失败，导致游戏出现了问题。\n\n请尝试删除游戏（包括Mod）并重新下载，或尝试在重新下载时使用VPN。")

            elif reason == Special_CrashReason.MANUAL_DEBUG_CRASH:
                results.append("这是一个手动触发的调试崩溃，不是真正的游戏错误。")

            elif reason == Special_CrashReason.STACK_KEYWORD_FOUND:
                if details:
                    results.append(
                        f"堆栈分析发现潜在问题关键字:\n{', '.join(details)}\n\n这些关键字可能表示相关的Mod或组件出现了问题。")
                else:
                    results.append("堆栈分析发现了一些潜在的问题，但无法确定具体原因。")

            elif reason == Special_CrashReason.NO_ANALYSIS_FILES:
                results.append("你的游戏出现了一些问题，但未能找到相关记录文件，因此无法进行分析。")

            elif reason == Special_CrashReason.UNKNOWN:
                results.append("未能确定崩溃的具体原因，请查看完整的崩溃日志了解更多信息。")

        # Join all results with newlines between them
        final_result = "\n\n此外，".join(results)

        # Add help message for seeking assistance
        if any(reason in [Special_CrashReason.FORGE_INCOMPLETE, Special_CrashReason.FABRIC_ERROR, Special_CrashReason.MOD_MISSING,
                          Special_CrashReason.NO_ANALYSIS_FILES] for reason in self.crash_reasons):
            final_result += "\n\n如果要寻求帮助，请把错误报告文件发给对方，而不是发送这个窗口的照片或者截图。"

        return final_result

    def try_analyze_mod_name(self, text: str) -> List[str]:
        """
        Extract mod name from text

        Args:
            text: Text containing mod information

        Returns:
            List of extracted mod names
        """
        if not text:
            return []

        # Remove common prefixes/suffixes
        text = re.sub(r'(mods\.|com\.|org\.|net\.|io\.)', '', text)

        # Extract the most likely mod name part
        parts = text.split('.')
        if len(parts) > 1:
            # Try to get the most meaningful part
            candidates = [p for p in parts if len(p) > 2 and not p.isdigit()]
            if candidates:
                return [candidates[0]]

        return [text]

    def log(self, param):
        print(param)


class LogLevel(Enum):
    INFO = 0
    WARNING = 1
    ERROR = 2
    DEBUG = 3
    FEEDBACK = 4

def start_analyzer(logs_folder):
    """
    Start the crash analyzer and return an instance.
    """
    result = "No analysis performed."
    # Initialize the crash analyzer
    analyzer = MinecraftCrashAnalyzer(cf.crash_reason_database_path)
    if analyzer.collect_logs(logs_folder):
        # Prepare logs for analysis
        analyzer.prepare_logs()
        # Perform crash analysis
        result = analyzer.analyze()

    if not result or not analyzer.crash_reasons:
        return "NULL"
    if Special_CrashReason.UNKNOWN in analyzer.crash_reasons.keys() or Special_CrashReason.NO_ANALYSIS_FILES in analyzer.crash_reasons.keys():
        return "NULL"

    contributors = []
    for reason, details in analyzer.crash_reasons.items():
        if type(reason) is str:
            contributors.append(analyzer.crashdb.get_crash_reason(reason).promoter)
        else:
            contributors.append(reason.value[1])
    contributors_str = list(set(contributors))

    analyzer_result_message = "--- Analysis Result ---" + "\n" + result + "\n" + "--- Detected Crash Reasons ---" + "\n" + \
        "\n".join([f"- {reason}: {details if details else 'No additional details'}" for reason, details in analyzer.crash_reasons.items()]) + \
        "\n\n" + "--- Analysis Contributor ---" + "\n" + \
        f"This analysis item(s) was contributed by: {contributors_str}"



    return analyzer_result_message

if __name__ == "__main__":
    # Example usage of MinecraftCrashAnalyzer
    import sys

    # Check if a folder path is provided as a command-line argument
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_logs_folder>")
        sys.exit(1)

    logs_folder = sys.argv[1]

    # Initialize the crash analyzer
    analyzer = MinecraftCrashAnalyzer(cf.crash_reason_database_path)

    # Collect logs from the specified folder
    if analyzer.collect_logs(logs_folder):
        # Prepare logs for analysis
        analyzer.prepare_logs()

        # Perform crash analysis
        result = analyzer.analyze()

        # Print the analysis result
        print("\n--- Analysis Result ---")
        print(result)

        # Print detected crash reasons
        print("\n--- Detected Crash Reasons ---")
        for reason, details in analyzer.crash_reasons.items():
            if type(reason) is str:
                print(f"- {reason}: {details if details else 'No additional details'}")
            else:
                print(f"- {reason.value[0]}: {details if details else 'No additional details'}")

        print("\n--- Analysis Contributor ---")
        contributors = []
        for reason, details in analyzer.crash_reasons.items():
            if type(reason) is str:
                contributors.append(analyzer.crashdb.get_crash_reason(reason).promoter)
            else:
                contributors.append(reason.value[1])
        contributors = list(set(contributors))
        print(f"This analysis item(s) was contributed by: {', '.join(contributors)}")
    else:
        print("No valid logs found in the specified folder.")
