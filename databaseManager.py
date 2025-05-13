import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from CrashDatabase import CrashReasonDatabase, CrashReason, DetectionRule, Person


class CrashDatabaseManager:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Crash Database Manager")
        self.root.geometry("900x600")

        # Initialize database with default file paths
        self.database = CrashReasonDatabase()

        # Set up the main UI
        self._setup_ui()

        # Load initial data
        self.refresh_crash_reasons()

    def _setup_ui(self):
        """Set up the main UI components"""
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Create crash reasons tab
        self.crash_reasons_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.crash_reasons_frame, text="Crash Reasons")
        self._setup_crash_reasons_tab()

        # Create detection rules tab
        self.detection_rules_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.detection_rules_frame, text="Detection Rules")
        self._setup_detection_rules_tab()

        # Status bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.grid(row=1, column=0, sticky="ew")
        self.status_var.set("Ready")

    def _setup_crash_reasons_tab(self):
        """Set up the crash reasons tab"""
        self.crash_reasons_frame.columnconfigure(0, weight=1)
        self.crash_reasons_frame.rowconfigure(0, weight=1)

        # Create treeview for crash reasons
        self.crash_reasons_tree = ttk.Treeview(self.crash_reasons_frame,
                                               columns=("ID", "Name", "Description", "Priority", "Promoter"))
        self.crash_reasons_tree.heading("#0", text="")
        self.crash_reasons_tree.column("#0", width=0, stretch=tk.NO)
        self.crash_reasons_tree.heading("ID", text="ID")
        self.crash_reasons_tree.column("ID", width=100)
        self.crash_reasons_tree.heading("Name", text="Name")
        self.crash_reasons_tree.column("Name", width=150)
        self.crash_reasons_tree.heading("Description", text="Description")
        self.crash_reasons_tree.column("Description", width=350)
        self.crash_reasons_tree.heading("Priority", text="Priority")
        self.crash_reasons_tree.column("Priority", width=10)
        self.crash_reasons_tree.heading("Promoter", text="Promoter")
        self.crash_reasons_tree.column("Promoter", width=70)
        self.crash_reasons_tree.grid(row=0, column=0, sticky="nsew")

        # double click to edit
        self.crash_reasons_tree.bind("<Double-1>", lambda e: self.edit_crash_reason())

        # Add scrollbar to treeview
        scrollbar = ttk.Scrollbar(self.crash_reasons_frame, orient=tk.VERTICAL, command=self.crash_reasons_tree.yview)
        self.crash_reasons_tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Button frame
        button_frame = ttk.Frame(self.crash_reasons_frame)
        button_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)

        # Buttons for managing crash reasons
        ttk.Button(button_frame, text="Add", command=self.add_crash_reason).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Edit", command=self.edit_crash_reason).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Delete", command=self.delete_crash_reason).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Refresh", command=self.refresh_crash_reasons).pack(side=tk.LEFT, padx=5)

    def _setup_detection_rules_tab(self):
        """Set up the detection rules tab"""
        self.detection_rules_frame.columnconfigure(0, weight=1)
        self.detection_rules_frame.rowconfigure(1, weight=1)

        # Crash reason selector
        selector_frame = ttk.Frame(self.detection_rules_frame)
        selector_frame.grid(row=0, column=0, sticky="ew", pady=5)

        ttk.Label(selector_frame, text="Select Crash Reason:").pack(side=tk.LEFT, padx=5)
        self.crash_reason_var = tk.StringVar()
        self.crash_reason_combo = ttk.Combobox(selector_frame, textvariable=self.crash_reason_var, state="readonly",
                                               width=40)
        self.crash_reason_combo.pack(side=tk.LEFT, padx=5)
        self.crash_reason_combo.bind("<<ComboboxSelected>>", lambda e: self.load_detection_rules())

        # Create treeview for detection rules
        self.rules_tree = ttk.Treeview(self.detection_rules_frame, columns=("Type", "Match", "Contributor"))
        self.rules_tree.heading("#0", text="")
        self.rules_tree.column("#0", width=0, stretch=tk.NO)
        self.rules_tree.heading("Type", text="Match Type")
        self.rules_tree.column("Type", width=100)
        self.rules_tree.heading("Match", text="Match")
        self.rules_tree.column("Match", width=500)
        self.rules_tree.heading("Contributor", text="Contributor")
        self.rules_tree.column("Contributor", width=100)
        self.rules_tree.grid(row=1, column=0, sticky="nsew")

        # double click to edit
        self.rules_tree.bind("<Double-1>", lambda e: self.edit_detection_rule())

        # Add scrollbar to treeview
        scrollbar = ttk.Scrollbar(self.detection_rules_frame, orient=tk.VERTICAL, command=self.rules_tree.yview)
        self.rules_tree.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=1, column=1, sticky="ns")

        # Button frame
        button_frame = ttk.Frame(self.detection_rules_frame)
        button_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)

        # Buttons for managing detection rules
        ttk.Button(button_frame, text="Add Rule", command=self.add_detection_rule).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Edit Rule", command=self.edit_detection_rule).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Delete Rule", command=self.delete_detection_rule).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Refresh", command=self.load_detection_rules).pack(side=tk.LEFT, padx=5)

    def refresh_crash_reasons(self):
        """Refresh the crash reasons list"""
        # Clear existing items
        for item in self.crash_reasons_tree.get_children():
            self.crash_reasons_tree.delete(item)

        # Get all crash reasons from the crash_reasons dictionary
        crash_reasons = []
        for reason_id, reason_data in self.database.crash_reasons.items():
            crash_reason = CrashReason(
                id=reason_data["id"],
                name=reason_data["name"],
                description=reason_data["description"],
                priority=reason_data["priority"]
            )
            crash_reasons.append(crash_reason)

        # Sort by priority
        crash_reasons.sort(key=lambda x: x.priority, reverse=True)

        # Add crash reasons to treeview
        for reason in crash_reasons:
            # Get promoter names
            promoters = self.database.get_promoters_for_crash(reason.id)
            promoter_names = ", ".join([p.name for p in promoters]) if promoters else "None"

            self.crash_reasons_tree.insert("", tk.END,
                                           values=(reason.id, reason.name, reason.description,
                                                   reason.priority, promoter_names))

        # Update the combobox in detection rules tab
        self.crash_reason_combo['values'] = list(self.database.crash_reasons.keys())
        self.status_var.set(f"Loaded {len(crash_reasons)} crash reasons")

    def add_crash_reason(self):
        """Add a new crash reason"""
        # Create a dialog for adding a new crash reason
        dialog = CrashReasonDialog(self.root,self.database, "Add Crash Reason")
        if dialog.result:
            id_val, name, description, priority, promoter_names = dialog.result

            # Create and add the crash reason
            crash_reason = CrashReason(
                id=id_val,
                name=name,
                description=description,
                priority=priority
            )
            if self.database.add_crash_reason(crash_reason):
                # Add promoters using their IDs directly from the selected persons
                for pid, _ in dialog.selected_promoters:
                    self.database.add_crash_promoter(id_val, pid)

                self.refresh_crash_reasons()
                self.status_var.set(f"Added crash reason: {id_val}")
            else:
                messagebox.showerror("Error", f"Failed to add crash reason with ID: {id_val}")

    def edit_crash_reason(self):
        selection = self.crash_reasons_tree.selection()
        if not selection:
            messagebox.showinfo("Information", "Please select a crash reason to edit")
            return

        item = self.crash_reasons_tree.item(selection[0])
        id_val, name, description, priority, promoters = item['values']

        dialog = CrashReasonDialog(self.root,self.database, "Edit Crash Reason",
                                   initial_values=(id_val, name, description, priority, promoters))

        if dialog.result:
            new_id, new_name, new_description, new_priority, new_promoter_names = dialog.result

            # If ID changed, delete old and create new
            if new_id != id_val:
                if id_val in self.database.crash_reasons:
                    del self.database.crash_reasons[id_val]
                    # Need to delete old promoter relationships
                    for key in list(self.database.crash_promoters.keys()):
                        if key.startswith(f"{id_val}_"):
                            del self.database.crash_promoters[key]

            # Create and add updated crash reason
            new_reason = CrashReason(id=new_id, name=new_name, description=new_description, priority=new_priority)
            self.database.update_crash_reason(new_reason)

            # Clear old promoters
            for key in list(self.database.crash_promoters.keys()):
                if key.startswith(f"{new_id}_"):
                    del self.database.crash_promoters[key]

            # Add new promoters
            for promoter_name in new_promoter_names.split(','):
                promoter_name = promoter_name.strip()
                if not promoter_name:
                    continue
                promoter_id = self._get_or_create_person(promoter_name)
                if promoter_id:
                    self.database.add_crash_promoter(new_id, promoter_id)

            self.database.save_crash_promoters()
            self.refresh_crash_reasons()
            self.status_var.set(f"Updated crash reason: {new_id}")

    def delete_crash_reason(self):
        selection = self.crash_reasons_tree.selection()
        if not selection:
            messagebox.showinfo("Information", "Please select a crash reason to delete")
            return

        item = self.crash_reasons_tree.item(selection[0])
        id_val = str(item['values'][0])

        if messagebox.askyesno("Confirm", f"Are you sure you want to delete crash reason '{id_val}'?"):
            if id_val in self.database.crash_reasons:
                del self.database.crash_reasons[id_val]
                self.database.save_crash_reasons()
                self.refresh_crash_reasons()
                self.status_var.set(f"Deleted crash reason: {id_val}")
            else:
                messagebox.showerror("Error", f"Failed to delete crash reason with ID: {id_val}")

    def load_detection_rules(self):
        """Load detection rules for the selected crash reason"""
        # Clear existing items
        for item in self.rules_tree.get_children():
            self.rules_tree.delete(item)

        selected_reason = self.crash_reason_var.get()
        if not selected_reason:
            return

        # Get detection rules for the selected crash reason
        detection_rules = self.database.get_detection_rules_for_crash(selected_reason)

        # Add detection rules to treeview
        for i, rule in enumerate(detection_rules):
            match_type = "Exact" if rule.match_type == 0 else "Regex"
            contributors = self.database.get_contributors_for_rule(rule.id)
            contributor_names = ", ".join([c.name for c in contributors]) if contributors else "None"

            self.rules_tree.insert("", tk.END, iid=str(i),
                                   values=(match_type, rule.match, contributor_names))

        self.status_var.set(f"Loaded {len(detection_rules)} detection rules for {selected_reason}")

    def add_detection_rule(self):
        """Add a new detection rule"""
        selected_reason = self.crash_reason_var.get()
        if not selected_reason:
            messagebox.showinfo("Information", "Please select a crash reason first")
            return

        # Create a dialog for adding a new detection rule
        dialog = DetectionRuleDialog(self.root,self.database, "Add Detection Rule")
        if dialog.result:
            match_type, match, contributor_names = dialog.result

            # Create a unique ID for the detection rule
            rule_id = f"rule_{selected_reason}_{len(self.database.detection_rules) + 1}"

            # Create and add the new rule
            rule = DetectionRule(
                id=rule_id,
                crash_reason_id=selected_reason,
                match_type=match_type,
                match=match
            )

            if self.database.add_detection_rule(rule):
                # Add contributors using their IDs directly from the selected persons
                for pid, _ in dialog.selected_contributors:
                    self.database.add_rule_contributor(rule_id, pid)

                self.load_detection_rules()
                self.status_var.set(f"Added detection rule to {selected_reason}")
            else:
                messagebox.showerror("Error", "Failed to add detection rule")

    def _get_or_create_person(self, name):
        """Find a person by name or create a new one if not found"""
        # Look for person with matching name
        for person_id, person_data in self.database.persons.items():
            if person_data["name"] == name:
                return person_data["id"]

        # If not found, ask to create new person
        if messagebox.askyesno("Person not found", f"Person '{name}' not found. Create new person?"):
            new_id = len(self.database.persons) + 1
            person = Person(id=new_id, name=name)
            if self.database.add_person(person):
                return new_id

        return None

    def edit_detection_rule(self):
        selected_reason = self.crash_reason_var.get()
        selection = self.rules_tree.selection()
        if not selected_reason or not selection:
            messagebox.showinfo("Information", "Please select a crash reason and a detection rule")
            return

        # Get the selected rule index
        rule_index = int(selection[0])

        # Get rules for this crash reason
        rules = self.database.get_detection_rules_for_crash(selected_reason)
        if rule_index >= len(rules):
            messagebox.showerror("Error", "Invalid rule selection")
            return

        # Get the actual rule object
        rule = rules[rule_index]

        # Get contributor names
        contributors = self.database.get_contributors_for_rule(rule.id)
        contributor_names = ", ".join([c.name for c in contributors]) if contributors else ""

        # Match type string
        match_type_str = "Exact" if rule.match_type == 0 else "Regex"

        # Display the edit dialog
        dialog = DetectionRuleDialog(self.root,self.database, "Edit Detection Rule",
                                     initial_values=(rule.match_type, rule.match, contributor_names))

        if dialog.result:
            new_match_type, new_match, new_contributor_names = dialog.result

            # Update rule in the database
            if rule.id in self.database.detection_rules:
                # Update the rule properties
                rule_data = self.database.detection_rules[rule.id]
                rule_data["match_type"] = new_match_type
                rule_data["match"] = new_match

                # Save changes
                self.database.save_detection_rules()

                # Clear old contributors
                for key in list(self.database.rule_contributors.keys()):
                    if key.startswith(f"{rule.id}_"):
                        del self.database.rule_contributors[key]

                # Add new contributors
                for contributor_name in new_contributor_names.split(','):
                    contributor_name = contributor_name.strip()
                    if not contributor_name:
                        continue
                    contributor_id = self._get_or_create_person(contributor_name)
                    if contributor_id:
                        self.database.add_rule_contributor(rule.id, contributor_id)

                self.database.save_rule_contributors()
                self.load_detection_rules()
                self.status_var.set(f"Updated detection rule for {selected_reason}")

    def delete_detection_rule(self):
        selected_reason = self.crash_reason_var.get()
        selection = self.rules_tree.selection()
        if not selected_reason or not selection:
            messagebox.showinfo("Information", "Please select a crash reason and a detection rule")
            return

        # Confirm deletion
        if messagebox.askyesno("Confirm", "Are you sure you want to delete this detection rule?"):
            # Get the selected rule index
            rule_index = int(selection[0])

            # Get rules for this crash reason
            rules = self.database.get_detection_rules_for_crash(selected_reason)
            if rule_index >= len(rules):
                messagebox.showerror("Error", "Invalid rule selection")
                return

            # Get the rule ID to delete
            rule_id = rules[rule_index].id

            # Delete the rule from the database
            if rule_id in self.database.detection_rules:
                del self.database.detection_rules[rule_id]
                self.database.save_detection_rules()
                self.load_detection_rules()
                self.status_var.set(f"Deleted detection rule from {selected_reason}")


class CrashReasonDialog:
    """Dialog for adding/editing crash reasons"""

    def __init__(self, parent, database:CrashReasonDatabase, title, initial_values=None):
        self.result = None
        self.parent = parent
        self.selected_promoters = []
        self.database = database

        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x280")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Initialize fields
        ttk.Label(self.dialog, text="ID:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.id_entry = ttk.Entry(self.dialog, width=40)
        self.id_entry.grid(row=0, column=1, padx=10, pady=5)

        ttk.Label(self.dialog, text="Name:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        self.name_entry = ttk.Entry(self.dialog, width=40)
        self.name_entry.grid(row=1, column=1, padx=10, pady=5)

        ttk.Label(self.dialog, text="Description:").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        self.description_text = tk.Text(self.dialog, width=30, height=5)
        self.description_text.grid(row=2, column=1, padx=10, pady=5)

        ttk.Label(self.dialog, text="Priority:").grid(row=3, column=0, sticky="w", padx=10, pady=5)
        self.priority_var = tk.IntVar(value=0)
        self.priority_spin = ttk.Spinbox(self.dialog, from_=0, to=100, width=5, textvariable=self.priority_var)
        self.priority_spin.grid(row=3, column=1, sticky="w", padx=10, pady=5)

        # Promoters section
        ttk.Label(self.dialog, text="Promoters:").grid(row=4, column=0, sticky="w", padx=10, pady=5)
        self.promoters_frame = ttk.Frame(self.dialog)
        self.promoters_frame.grid(row=4, column=1, sticky="w", padx=10, pady=5)

        self.promoters_var = tk.StringVar()
        self.promoters_label = ttk.Label(self.promoters_frame, textvariable=self.promoters_var, width=30)
        self.promoters_label.pack(side=tk.LEFT)

        ttk.Button(self.promoters_frame, text="Select", command=self.select_promoters).pack(side=tk.LEFT, padx=5)

        # Set initial values if provided
        if initial_values:
            id_val, name, description, priority, promoters = initial_values
            self.id_entry.insert(0, id_val)
            self.name_entry.insert(0, name)
            self.description_text.insert("1.0", description)
            self.priority_var.set(priority)
            self.promoters_var.set(promoters)

            # Extract promoter names
            if promoters and promoters != "None":
                promoter_names = [p.strip() for p in promoters.split(",")]
                # Find promoter IDs if they exist
                for name in promoter_names:
                    for pid, person in database.persons.items():
                        if person["name"] == name:
                            self.selected_promoters.append((int(pid), name))
                            break

        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10)

        ttk.Button(button_frame, text="OK", command=self.ok).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.LEFT, padx=10)

        # Wait for the dialog to be closed
        self.dialog.wait_window()

    def select_promoters(self):
        """Open dialog to select promoters"""
        selector = PersonSelectorDialog(self.parent,self.database, "Select Promoters", multi_select=True)
        if selector.result:
            self.selected_promoters = selector.result
            promoter_names = [name for _, name in self.selected_promoters]
            self.promoters_var.set(", ".join(promoter_names))

    def ok(self):
        """Handle OK button"""
        id_val = self.id_entry.get().strip()
        name = self.name_entry.get().strip()
        description = self.description_text.get("1.0", "end-1c").strip()
        priority = self.priority_var.get()

        # Get promoter names as comma-separated string
        promoter_names = ", ".join([name for _, name in self.selected_promoters]) if self.selected_promoters else ""

        # Validate inputs
        if not id_val or not name or not description:
            messagebox.showwarning("Warning", "Please fill in all required fields")
            return

        self.result = (id_val, name, description, priority, promoter_names)
        self.dialog.destroy()

    def cancel(self):
        """Handle Cancel button"""
        self.dialog.destroy()


class DetectionRuleDialog:
    """Dialog for adding/editing detection rules"""

    def __init__(self, parent, database: CrashReasonDatabase, title, initial_values=None):
        self.result = None
        self.parent = parent
        self.selected_contributors = []
        self.database = database

        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x280")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Initialize fields
        ttk.Label(self.dialog, text="Match Type:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        self.match_type_var = tk.IntVar(value=0)
        self.match_type_frame = ttk.Frame(self.dialog)
        self.match_type_frame.grid(row=0, column=1, sticky="w", padx=10, pady=5)
        ttk.Radiobutton(self.match_type_frame, text="Exact", variable=self.match_type_var, value=0).pack(side=tk.LEFT)
        ttk.Radiobutton(self.match_type_frame, text="Regex", variable=self.match_type_var, value=1).pack(side=tk.LEFT)

        ttk.Label(self.dialog, text="Match:").grid(row=1, column=0, sticky="nw", padx=10, pady=5)
        self.match_text = tk.Text(self.dialog, width=30, height=8)
        self.match_text.grid(row=1, column=1, padx=10, pady=5)

        # Contributors section
        ttk.Label(self.dialog, text="Contributors:").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        self.contributors_frame = ttk.Frame(self.dialog)
        self.contributors_frame.grid(row=2, column=1, sticky="w", padx=10, pady=5)

        self.contributors_var = tk.StringVar()
        self.contributors_label = ttk.Label(self.contributors_frame, textvariable=self.contributors_var, width=30)
        self.contributors_label.pack(side=tk.LEFT)

        ttk.Button(self.contributors_frame, text="Select", command=self.select_contributors).pack(side=tk.LEFT, padx=5)

        # Set initial values if provided
        if initial_values:
            match_type, match, contributors = initial_values
            self.match_type_var.set(match_type)
            self.match_text.insert("1.0", match)
            self.contributors_var.set(contributors)

            # Extract contributor names
            if contributors and contributors != "None":
                contributor_names = [c.strip() for c in contributors.split(",")]
                # Find contributor IDs if they exist
                for name in contributor_names:
                    for pid, person in database.persons.items():
                        if person["name"] == name:
                            self.selected_contributors.append((int(pid), name))
                            break

        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)

        ttk.Button(button_frame, text="OK", command=self.ok).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.LEFT, padx=10)

        # Wait for the dialog to be closed
        self.dialog.wait_window()

    def select_contributors(self):
        """Open dialog to select contributors"""
        selector = PersonSelectorDialog(self.parent,self.database, "Select Contributors", multi_select=True)
        if selector.result:
            self.selected_contributors = selector.result
            contributor_names = [name for _, name in self.selected_contributors]
            self.contributors_var.set(", ".join(contributor_names))

    def ok(self):
        """Handle OK button"""
        match_type = self.match_type_var.get()
        match = self.match_text.get("1.0", "end-1c").strip()

        # Get contributor names as comma-separated string
        contributor_names = ", ".join(
            [name for _, name in self.selected_contributors]) if self.selected_contributors else ""

        # Validate inputs
        if not match:
            messagebox.showwarning("Warning", "Please add a match pattern")
            return

        self.result = (match_type, match, contributor_names)
        self.dialog.destroy()

    def cancel(self):
        """Handle Cancel button"""
        self.dialog.destroy()


class PersonSelectorDialog:
    """Dialog for selecting or creating persons"""

    def __init__(self, parent, database:CrashReasonDatabase=None, title="Select Person", multi_select=False):
        self.result = None
        self.parent = parent
        self.multi_select = multi_select
        self.selected_persons = []
        self.database = database

        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Search frame
        search_frame = ttk.Frame(self.dialog)
        search_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(search_frame, text="Search", command=self.search).pack(side=tk.LEFT)

        # Persons listbox with scrollbar
        self.listbox_frame = ttk.Frame(self.dialog)
        self.listbox_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.persons_listbox = tk.Listbox(self.listbox_frame, selectmode=tk.MULTIPLE if multi_select else tk.SINGLE)
        self.persons_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(self.listbox_frame, orient=tk.VERTICAL, command=self.persons_listbox.yview)
        self.persons_listbox.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Populate the listbox
        self.load_persons()

        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(button_frame, text="Select", command=self.select).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="Create New", command=self.create_new).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.RIGHT)

        # Wait for the dialog to be closed
        self.dialog.wait_window()

    def load_persons(self):
        """Load all persons into the listbox"""
        self.persons_listbox.delete(0, tk.END)
        self.persons_data = []

        if not self.database:
            return

        for person_id, person_data in self.database.persons.items():
            person_str = f"{person_data['id']}: {person_data['name']}"
            self.persons_listbox.insert(tk.END, person_str)
            self.persons_data.append(person_data)

    def search(self):
        """Search for persons based on the search term"""
        search_term = self.search_var.get().strip().lower()
        self.persons_listbox.delete(0, tk.END)
        self.persons_data = []

        if not self.database:
            return

        for person_id, person_data in self.database.persons.items():
            if (search_term in str(person_data['id']).lower() or
                    search_term in person_data['name'].lower()):
                person_str = f"{person_data['id']}: {person_data['name']}"
                self.persons_listbox.insert(tk.END, person_str)
                self.persons_data.append(person_data)

    def select(self):
        """Handle the selection of persons"""
        selection = self.persons_listbox.curselection()
        if not selection:
            messagebox.showinfo("Information", "Please select at least one person")
            return

        if self.multi_select:
            self.selected_persons = [self.persons_data[i] for i in selection]
            self.result = [(person['id'], person['name']) for person in self.selected_persons]
        else:
            selected_index = selection[0]
            selected_person = self.persons_data[selected_index]
            self.result = (selected_person['id'], selected_person['name'])

        self.dialog.destroy()

    def create_new(self):
        """Create a new person"""
        name = simpledialog.askstring("Create New Person", "Enter name for new person:")
        if name and name.strip():
            if not self.database:
                messagebox.showerror("Error", "Database not available")
                return

            # Create a new ID
            new_id = max([int(pid) for pid in self.database.persons.keys()], default=0) + 1
            new_person = Person(id=new_id, name=name.strip())

            if self.database.add_person(new_person):
                if self.multi_select:
                    self.result = [(new_id, name.strip())]
                else:
                    self.result = (new_id, name.strip())
                self.dialog.destroy()
            else:
                messagebox.showerror("Error", "Failed to create new person")

    def cancel(self):
        """Handle Cancel button"""
        self.dialog.destroy()


def main():
    root = tk.Tk()
    app = CrashDatabaseManager(root)
    root.mainloop()


if __name__ == "__main__":
    main()