# report_filters/session_filter.py

import customtkinter as ctk
import db_manager # برای دسترسی به تنظیمات سشن‌ها و تابع جدید
from persian_chart_utils import process_persian_text_for_matplotlib
import tkinter as tk # برای messagebox

class SessionFilterFrame(ctk.CTkFrame):
    def __init__(self, master, on_change_callback=None, fg_color="transparent", **kwargs):
        super().__init__(master, fg_color=fg_color, **kwargs)
        self.on_change_callback = on_change_callback
        self.session_names_map = { # Display names for sessions
            'ny': 'Newyork',
            'sydney': 'Sydney',
            'tokyo': 'Tokyo',
            'london': 'London'
        }
        self.session_vars = {} # To hold BooleanVar for each session
        # Initial value for all_sessions_var should be False by default.
        # It will be set correctly by _load_weekdays based on the actual selection.
        self.all_sessions_var = ctk.BooleanVar(value=False) 

        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, text=process_persian_text_for_matplotlib("سشن‌های معاملاتی:"), font=("Vazirmatn", 12))
        self.label.grid(row=0, column=0, padx=5, pady=5, sticky="e") # Placed to the right

        self.checkbox_container_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.checkbox_container_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.checkbox_container_frame.grid_columnconfigure(0, weight=1)

        # Checkbox "همه سشن‌ها"
        self.all_checkbox = ctk.CTkCheckBox(self.checkbox_container_frame,
                                            text=process_persian_text_for_matplotlib("همه سشن‌ها"),
                                            variable=self.all_sessions_var,
                                            command=self._toggle_all_sessions,
                                            font=("Vazirmatn", 11, "bold"),
                                            fg_color=("blue", "blue"),
                                            checkbox_width=18, checkbox_height=18,
                                            border_color=("gray60", "gray40"),
                                            checkmark_color="white")
        self.all_checkbox.grid(row=0, column=0, sticky="e", padx=10, pady=5) # Right-aligned

        self.current_user_timezone_label = ctk.CTkLabel(self, text="",
                                                        font=("Vazirmatn", 9, "italic"), text_color="gray50", anchor="e", wraplength=250)
        self.current_user_timezone_label.grid(row=2, column=0, padx=5, pady=(0,5), sticky="ew") # اضافه شده

        self.settings_hint_label = ctk.CTkLabel(self, text=process_persian_text_for_matplotlib("ساعت‌های سشن‌ها را از بخش تنظیمات برنامه تغییر دهید."),
                                                font=("Vazirmatn", 9, "italic"), text_color="gray50", anchor="e", wraplength=250)
        self.settings_hint_label.grid(row=3, column=0, padx=5, pady=(0,5), sticky="ew") # ردیف تغییر کرده

        self.reload_sessions(initial_load=True) # Initial loading of sessions. Pass a flag to indicate initial load.

    def reload_sessions(self, initial_load=False): # Add initial_load parameter
        """
        Reloads session options based on current settings.
        This function is called by the main report window when filter dependencies change.
        """
        # Update user timezone hint
        user_tz_name = db_manager.get_default_timezone()
        self.current_user_timezone_label.configure(text=process_persian_text_for_matplotlib(f"ساعت‌ها بر اساس منطقه زمانی: {user_tz_name}"))

        # Clear previous checkboxes, keeping "همه"
        for widget in self.checkbox_container_frame.winfo_children():
            if widget != self.all_checkbox:
                widget.destroy()

        # Get current selection before clearing checkboxes
        # This is important for non-initial loads to preserve user's choice
        previously_selected = self.get_selection() 
        
        self.session_vars = {}

        current_session_times = db_manager.get_session_times_with_display_utc(user_tz_name)

        if not current_session_times:
            no_sessions_label = ctk.CTkLabel(self.checkbox_container_frame, text=process_persian_text_for_matplotlib("سشنی در تنظیمات یافت نشد."), font=("Vazirmatn", 10), text_color="gray50")
            no_sessions_label.grid(row=1, column=0, sticky="e", padx=10, pady=5)
            self.all_checkbox.configure(state="disabled")
            self.all_sessions_var.set(False)
            return

        self.all_checkbox.configure(state="normal")

        # Create checkboxes for each session
        row_idx = 1
        all_selected_after_reload = True # Flag to check if all are selected
        for key, times in current_session_times.items():
            session_display_name = self.session_names_map.get(key, key.capitalize())
            display_text = f"{session_display_name} ({times['start_display']} - {times['end_display']} به وقت محلی)"
            
            # Logic for initial selection (Newyork by default)
            if initial_load:
                is_checked = (key == 'ny') # Default: only New York is selected on initial load
            else:
                # If not initial load, try to restore previous selection
                is_checked = (previously_selected == "همه") or (isinstance(previously_selected, list) and key in previously_selected)
            
            var = ctk.BooleanVar(value=is_checked)
            self.session_vars[key] = var

            checkbox = ctk.CTkCheckBox(self.checkbox_container_frame,
                                       text=process_persian_text_for_matplotlib(display_text),
                                       variable=var,
                                       command=lambda s_key=key: self._on_session_checkbox_change(s_key),
                                       font=("Vazirmatn", 11),
                                       checkbox_width=18, checkbox_height=18,
                                       border_color=("gray60", "gray40"),
                                       checkmark_color="white")
            checkbox.grid(row=row_idx, column=0, sticky="e", padx=10, pady=2)
            row_idx += 1

            if not is_checked:
                all_selected_after_reload = False
        
        # Set "همه" checkbox based on the state of individual checkboxes and initial_load logic
        if current_session_times and all(var.get() for var in self.session_vars.values()):
            self.all_sessions_var.set(True)
        else:
            self.all_sessions_var.set(False)


    def _toggle_all_sessions(self):
        is_all_selected = self.all_sessions_var.get()
        for session_key, var in self.session_vars.items():
            var.set(is_all_selected)
        if self.on_change_callback:
            self.on_change_callback()

    def _on_session_checkbox_change(self, session_key):
        if not self.session_vars[session_key].get():
            self.all_sessions_var.set(False)
        elif all(var.get() for var in self.session_vars.values()):
            self.all_sessions_var.set(True)
        
        if self.on_change_callback:
            self.on_change_callback()

    def get_selection(self):
        if self.all_sessions_var.get():
            return "همه"
        else:
            # فقط کلیدهای سشن انتخاب شده را برمی‌گرداند (مثل 'ny', 'london')
            selected = [s for s, var in self.session_vars.items() if var.get()]
            return selected if selected else [] # اگر هیچکدام انتخاب نشده، لیست خالی برگردون

    def set_selection(self, selected_list):
        # This function is called when loading a template or resetting.
        # It sets the checkboxes according to selected_list.
        
        # If selected_list is empty (e.g., from a reset command), default to 'ny'
        if not selected_list:
            selected_list = ['ny']
            
        if selected_list == "همه":
            self.all_sessions_var.set(True)
            for var in self.session_vars.values():
                var.set(True)
        else:
            self.all_sessions_var.set(False) # Default to false for specific list
            for session_key, var in self.session_vars.items():
                var.set(session_key in selected_list)
            
            # If all individual sessions are checked after setting, and the list is not empty,
            # then 'All' should be True.
            current_session_times = db_manager.get_session_times_with_display_utc(db_manager.get_default_timezone()) # Re-fetch for accurate count
            if selected_list and current_session_times and all(var.get() for var in self.session_vars.values()):
                 self.all_sessions_var.set(True)
        # No need to call on_change_callback here directly.