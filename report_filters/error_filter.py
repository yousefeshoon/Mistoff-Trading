# report_filters/error_filter.py

import customtkinter as ctk
import db_manager
import tkinter as tk
from persian_chart_utils import process_persian_text_for_matplotlib

class ErrorFilterFrame(ctk.CTkFrame):
    def __init__(self, master, on_change_callback=None, fg_color="transparent", **kwargs):
        super().__init__(master, fg_color=fg_color, **kwargs)
        self.on_change_callback = on_change_callback
        self.errors = [] # List of unique errors from DB based on filters
        self.selected_errors_vars = {} # Dictionary to hold BooleanVars for each error
        self.all_errors_var = ctk.BooleanVar(value=True) # "همه" initially selected

        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, text=process_persian_text_for_matplotlib("اشتباهات:"), font=("Vazirmatn", 12))
        self.label.grid(row=0, column=0, padx=5, pady=5, sticky="e") # Right-aligned

        self.checkbox_container_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.checkbox_container_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.checkbox_container_frame.grid_columnconfigure(0, weight=1)

        # Checkbox "همه خطاها"
        self.all_checkbox = ctk.CTkCheckBox(self.checkbox_container_frame,
                                            text=process_persian_text_for_matplotlib("همه خطاها"),
                                            variable=self.all_errors_var,
                                            command=self._toggle_all_errors,
                                            font=("Vazirmatn", 11, "bold"),
                                            fg_color=("blue", "blue"),
                                            checkbox_width=18, checkbox_height=18,
                                            border_color=("gray60", "gray40"),
                                            checkmark_color="white")
        self.all_checkbox.grid(row=0, column=0, sticky="e", padx=10, pady=5) # Right-aligned

        # Hint label for date range
        self.date_range_hint_label = ctk.CTkLabel(self, text=process_persian_text_for_matplotlib("نمایش اشتباهات مرتبط با بازه تاریخی و نوع ترید انتخابی."),
                                                  font=("Vazirmatn", 9, "italic"), text_color="gray50", anchor="e", wraplength=250)
        self.date_range_hint_label.grid(row=2, column=0, padx=5, pady=(0,5), sticky="ew")

        # Initial load (this will be called by ReportSelectionWindow's _on_filter_changed)
        # We explicitly pass True for initial_load to prevent on_change_callback from firing
        # during the filter's own __init__ phase.
        self.reload_errors(initial_load=True)


    def reload_errors(self, date_range_selection=None, trade_type_filter=None, initial_load=False): # Add initial_load parameter
        """
        Reloads error options based on the provided date range and trade type.
        This function is called by the main report window when date/trade_type filters change.
        """
        # Clear previous checkboxes, keeping "همه"
        for widget in self.checkbox_container_frame.winfo_children():
            if widget != self.all_checkbox:
                widget.destroy()

        start_date = date_range_selection.get("start_date") if date_range_selection else None
        end_date = date_range_selection.get("end_date") if date_range_selection else None

        self.errors = db_manager.get_unique_errors_by_filters(start_date, end_date, trade_type_filter) #
        
        # Reset selected errors. We will re-check based on previous selection or default to all.
        previously_selected = self.get_selection() # Get current selection before clearing checkboxes

        self.selected_errors_vars = {}
        # self.all_errors_var.set(True) # Assume "همه" is checked initially for reload - this will be set based on individual checks

        if not self.errors:
            no_errors_label = ctk.CTkLabel(self.checkbox_container_frame, text=process_persian_text_for_matplotlib("هیچ خطایی در بازه انتخابی یافت نشد."), font=("Vazirmatn", 10), text_color="gray50")
            no_errors_label.grid(row=1, column=0, sticky="e", padx=10, pady=5) # جهت به E تغییر یافته
            self.all_checkbox.configure(state="disabled")
            self.all_errors_var.set(False)
            # Removed self.on_change_callback() here to prevent recursion during initial setup.
            return

        self.all_checkbox.configure(state="normal")

        # Create checkboxes for each error
        all_selected_after_reload = True # Flag to check if all are selected
        for i, error_text in enumerate(sorted(self.errors)):
            # Check if this error was previously selected, otherwise default to all if "همه" was active
            # During initial load, default to all being selected (value=True in CTkBooleanVar).
            if initial_load:
                is_checked = True
            else:
                is_checked = (previously_selected == "همه خطاها" or (isinstance(previously_selected, list) and error_text in previously_selected))
            
            var = ctk.BooleanVar(value=is_checked)
            self.selected_errors_vars[error_text] = var

            checkbox = ctk.CTkCheckBox(self.checkbox_container_frame,
                                       text=process_persian_text_for_matplotlib(error_text),
                                       variable=var,
                                       command=lambda err=error_text: self._on_error_checkbox_change(err),
                                       font=("Vazirmatn", 11),
                                       checkbox_width=18, checkbox_height=18,
                                       border_color=("gray60", "gray40"),
                                       checkmark_color="white")
            checkbox.grid(row=i + 1, column=0, sticky="e", padx=10, pady=2) # Right-aligned

            if not is_checked:
                all_selected_after_reload = False
        
        # Set "همه" checkbox based on the state of individual checkboxes
        self.all_errors_var.set(all_selected_after_reload)

        # Removed self.on_change_callback() here to prevent recursion during initial setup.


    def _toggle_all_errors(self):
        is_all_selected = self.all_errors_var.get()
        for error_text, var in self.selected_errors_vars.items():
            var.set(is_all_selected)
        if self.on_change_callback:
            self.on_change_callback()

    def _on_error_checkbox_change(self, error_text):
        if not self.selected_errors_vars[error_text].get():
            self.all_errors_var.set(False)
        elif all(var.get() for var in self.selected_errors_vars.values()):
            self.all_errors_var.set(True)
        
        if self.on_change_callback:
            self.on_change_callback()

    def get_selection(self):
        if self.all_errors_var.get():
            return "همه خطاها"
        else:
            return [e for e, var in self.selected_errors_vars.items() if var.get()]

    def set_selection(self, selected_list):
        if selected_list == "همه خطاها":
            self.all_errors_var.set(True)
            for var in self.selected_errors_vars.values():
                var.set(True)
        else:
            self.all_errors_var.set(False)
            for error_text, var in self.selected_errors_vars.items():
                var.set(error_text in selected_list)
        # No need to call on_change_callback here directly.