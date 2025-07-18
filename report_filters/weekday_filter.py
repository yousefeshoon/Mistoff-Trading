# report_filters/weekday_filter.py

import customtkinter as ctk
import db_manager
import tkinter as tk
from persian_chart_utils import process_persian_text_for_matplotlib

class WeekdayFilterFrame(ctk.CTkFrame):
    def __init__(self, master, on_change_callback=None, fg_color="transparent", **kwargs):
        super().__init__(master, fg_color=fg_color, **kwargs)
        self.on_change_callback = on_change_callback
        self.weekday_names_persian_map = {
            0: "دوشنبه",
            1: "سه‌شنبه",
            2: "چهارشنبه",
            3: "پنج‌شنبه",
            4: "جمعه",
            5: "شنبه",
            6: "یکشنبه"
        }
        self.weekday_vars = {}
        self.all_weekdays_var = ctk.BooleanVar(value=True)

        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, text=process_persian_text_for_matplotlib("روزهای هفته:"), font=("Vazirmatn", 12))
        self.label.grid(row=0, column=0, padx=5, pady=5, sticky="e")

        self.checkbox_container_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.checkbox_container_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.checkbox_container_frame.grid_columnconfigure(0, weight=1)

        self.all_checkbox = ctk.CTkCheckBox(self.checkbox_container_frame,
                                            text=process_persian_text_for_matplotlib("همه روزها"),
                                            variable=self.all_weekdays_var,
                                            command=self._toggle_all_weekdays,
                                            font=("Vazirmatn", 11, "bold"),
                                            fg_color=("blue", "blue"),
                                            checkbox_width=18, checkbox_height=18,
                                            border_color=("gray60", "gray40"),
                                            checkmark_color="white")
        self.all_checkbox.grid(row=0, column=0, sticky="e", padx=10, pady=5)

        self._load_weekdays() # Initial loading. **No on_change_callback here anymore.**

        self.settings_hint_label = ctk.CTkLabel(self, text=process_persian_text_for_matplotlib("روزهای کاری را از بخش تنظیمات برنامه تغییر دهید."),
                                                font=("Vazirmatn", 9, "italic"), text_color="gray50", anchor="e", wraplength=250)
        self.settings_hint_label.grid(row=2, column=0, padx=5, pady=(0,5), sticky="ew")


    def _load_weekdays(self):
        for widget in self.checkbox_container_frame.winfo_children():
            if widget != self.all_checkbox:
                widget.destroy()

        db_working_days = db_manager.get_working_days()
        
        for i in range(7):
            day_name = self.weekday_names_persian_map.get(i, f"روز نامشخص {i}")
            var = ctk.BooleanVar()
            var.set(self.all_weekdays_var.get() or i in db_working_days)
            self.weekday_vars[i] = var

            checkbox = ctk.CTkCheckBox(self.checkbox_container_frame,
                                       text=process_persian_text_for_matplotlib(day_name),
                                       variable=var,
                                       command=lambda d=i: self._on_weekday_checkbox_change(d),
                                       font=("Vazirmatn", 11),
                                       checkbox_width=18, checkbox_height=18,
                                       border_color=("gray60", "gray40"),
                                       checkmark_color="white")
            checkbox.grid(row=i + 1, column=0, sticky="e", padx=10, pady=2)

        if db_working_days and len(db_working_days) < 7:
             self.all_weekdays_var.set(False)
             for i in range(7):
                 if i not in db_working_days:
                     self.weekday_vars[i].set(False)
                 else:
                     self.weekday_vars[i].set(True)
        else:
             self.all_weekdays_var.set(True)
             for i in range(7):
                 self.weekday_vars[i].set(True)

        # Removed the call to self.on_change_callback() from here.
        # It will be called externally by ReportSelectionWindow after all filters are initialized.


    def _toggle_all_weekdays(self):
        is_all_selected = self.all_weekdays_var.get()
        for day_index, var in self.weekday_vars.items():
            var.set(is_all_selected)
        if self.on_change_callback:
            self.on_change_callback()

    def _on_weekday_checkbox_change(self, day_index):
        if not self.weekday_vars[day_index].get():
            self.all_weekdays_var.set(False)
        elif all(var.get() for var in self.weekday_vars.values()):
            self.all_weekdays_var.set(True)
        
        if self.on_change_callback:
            self.on_change_callback()

    def get_selection(self):
        if self.all_weekdays_var.get():
            return "همه"
        else:
            return [d for d, var in self.weekday_vars.items() if var.get()]

    def set_selection(self, selected_list):
        if selected_list == "همه":
            self.all_weekdays_var.set(True)
            for var in self.weekday_vars.values():
                var.set(True)
        else:
            self.all_weekdays_var.set(False)
            for day_index, var in self.weekday_vars.items():
                var.set(day_index in selected_list)
        if self.on_change_callback:
            self.on_change_callback()