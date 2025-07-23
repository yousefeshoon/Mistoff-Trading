# report_files/report_filter_summary_frame.py

import customtkinter as ctk
import tkinter as tk
from persian_chart_utils import process_persian_text_for_matplotlib
import db_manager
from datetime import datetime, timedelta

class ReportFilterSummaryFrame(ctk.CTkFrame):
    def __init__(self, master, on_change_date_range_callback=None, on_change_template_callback=None, **kwargs):
        super().__init__(master, **kwargs)
        self.on_change_date_range_callback = on_change_date_range_callback
        self.on_change_template_callback = on_change_template_callback
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0) # For header (fixed height or content based)
        self.grid_rowconfigure(1, weight=1) # For scrollable content (takes remaining space)

        self.current_template_name = ""
        self.current_filters_data = {}

        # Header for filter name and change template button
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        # تغییر: استفاده از grid به جای pack
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5) 
        self.header_frame.grid_columnconfigure(0, weight=1)
        self.header_frame.grid_columnconfigure(1, weight=0) # For button

        self.template_info_label = ctk.CTkLabel(self.header_frame, 
                                                text=process_persian_text_for_matplotlib("در حال مشاهده گزارشات با فیلتر:"),
                                                font=("Vazirmatn", 12, "bold"), text_color="#202124", anchor="e")
        self.template_info_label.grid(row=0, column=0, sticky="ew", padx=(0,5))

        self.template_name_button = ctk.CTkButton(self.header_frame,
                                                    text=process_persian_text_for_matplotlib("فیلتری انتخاب نشده"),
                                                    command=self._on_change_template_button_click,
                                                    font=("Vazirmatn", 11),
                                                    fg_color="#007BFF",
                                                    hover_color="#0056B3",
                                                    corner_radius=8,
                                                    height=30)
        self.template_name_button.grid(row=0, column=1, sticky="e")

        # Main scrollable frame for filter details (contains all filter sections)
        self.main_scrollable_filter_details_frame = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=8)
        # تغییر: استفاده از grid به جای pack
        self.main_scrollable_filter_details_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0,5)) 
        self.main_scrollable_filter_details_frame.grid_columnconfigure(0, weight=1) # Single column for sections

        self.filter_elements = {} # To hold references to labels/buttons for easy update

        # Initialize UI elements (will be updated by update_summary)
        self._create_initial_filter_elements()
        
    def _on_change_template_button_click(self):
        if self.on_change_template_callback:
            self.on_change_template_callback()

    def _create_initial_filter_elements(self):
        # Date Range
        self._add_filter_section("date_range", "بازه تاریخی:", True, command=self._on_change_date_range_button_click) # Always shows fields

        # Weekdays
        self._add_filter_section("weekday", "روزهای هفته:", all_text="همه")
        
        # Sessions
        self._add_filter_section("sessions", "سشن‌های معاملاتی:", all_text="همه")

        # Instruments
        self._add_filter_section("instruments", "نمادها:", all_text="همه")

        # Hourly
        self._add_filter_section("hourly", "ساعات ترید:")

        # Trade Type
        self._add_filter_section("trade_type", "نوع ترید:", all_text="همه انواع")

        # Errors
        self._add_filter_section("errors", "اشتباهات:", all_text="همه خطاها")

    def _add_filter_section(self, key, label_text, is_date_range=False, command=None, all_text=None):
        section_frame = ctk.CTkFrame(self.main_scrollable_filter_details_frame, fg_color="white", corner_radius=8)
        # تغییر: استفاده از pack به جای grid برای فریم‌های بخش‌های فیلتر
        # اینها داخل ScrollableFrame هستند و باید با pack چیده شوند.
        # اما height=40 برای value_scrollable_frame باید کنترل شود.
        section_frame.pack(fill="x", padx=5, pady=5, ipadx=5, ipady=5) 
        section_frame.grid_columnconfigure(0, weight=1) # Value side
        section_frame.grid_columnconfigure(1, weight=0) # Label side

        label = ctk.CTkLabel(section_frame, text=process_persian_text_for_matplotlib(label_text),
                             font=("Vazirmatn", 12, "bold"), text_color="#202124", anchor="e")
        label.grid(row=0, column=1, sticky="e", padx=(0,5), pady=5)
        
        # Inner frame to hold buttons, with horizontal scroll
        # Using a fixed height for consistency if content overflows
        value_scrollable_frame = ctk.CTkScrollableFrame(section_frame, fg_color="transparent", orientation="horizontal", height=40)
        value_scrollable_frame.grid(row=0, column=0, sticky="ew", padx=(5,0), pady=5)
        value_scrollable_frame.grid_columnconfigure(0, weight=0) # Will pack buttons, so weight 0

        self.filter_elements[key] = {
            "section_frame": section_frame,
            "label": label,
            "value_scrollable_frame": value_scrollable_frame,
            "is_date_range": is_date_range,
            "command": command,
            "all_text": all_text # Store all_text for consistency
        }

    def _clear_value_frame(self, key):
        for widget in self.filter_elements[key]["value_scrollable_frame"].winfo_children():
            widget.destroy()

    def _on_change_date_range_button_click(self):
        if self.on_change_date_range_callback:
            self.on_change_date_range_callback(self.current_filters_data.get("date_range", {}))

    def update_summary(self, template_name, filters_data):
        self.current_template_name = template_name
        self.current_filters_data = filters_data

        display_name = process_persian_text_for_matplotlib(template_name) if template_name else process_persian_text_for_matplotlib("فیلتری انتخاب نشده")
        self.template_name_button.configure(text=display_name)
        
        summary_display_limit = 3 # Max items to show before "and X more"

        button_category_colors = {
            "date_range": "#4CAF50", # Green
            "weekday": "#FFC107",   # Amber
            "sessions": "#6F42C1",  # Purple
            "instruments": "#20C997", # Teal
            "hourly": "#DC3545",    # Red
            "trade_type": "#17A2B8",  # Info Blue
            "errors": "#6C757D"     # Gray
        }
        button_text_color = "#212121" # Dark gray for contrast on light buttons

        # Date Range - Always show start/end and change button
        self._clear_value_frame("date_range")
        date_range_data = filters_data.get("date_range", {})
        start_date = date_range_data.get("start_date")
        end_date = date_range_data.get("end_date")

        date_value_frame = self.filter_elements["date_range"]["value_scrollable_frame"]
        
        if start_date and end_date:
            ctk.CTkButton(date_value_frame,
                            text=process_persian_text_for_matplotlib(f"از: {start_date}"),
                            font=("Vazirmatn", 11, "bold"),
                            fg_color=self._lighten_color(button_category_colors["date_range"], 85),
                            text_color=button_text_color,
                            hover_color=self._lighten_color(button_category_colors["date_range"], 85),
                            corner_radius=15, width=120, height=25).pack(side="right", padx=2)
            ctk.CTkButton(date_value_frame,
                            text=process_persian_text_for_matplotlib(f"تا: {end_date}"),
                            font=("Vazirmatn", 11, "bold"),
                            fg_color=self._lighten_color(button_category_colors["date_range"], 85),
                            text_color=button_text_color,
                            hover_color=self._lighten_color(button_category_colors["date_range"], 85),
                            corner_radius=15, width=120, height=25).pack(side="right", padx=2)
        else:
            ctk.CTkButton(date_value_frame,
                            text=process_persian_text_for_matplotlib("بازه نامشخص"),
                            font=("Vazirmatn", 11, "bold"),
                            fg_color=self._lighten_color(button_category_colors["date_range"], 85),
                            text_color=button_text_color,
                            hover_color=self._lighten_color(button_category_colors["date_range"], 85),
                            corner_radius=15, width=100, height=25).pack(side="right", padx=2)

        # "تغییر بازه تاریخی" button - Always present
        change_date_button = ctk.CTkButton(date_value_frame,
                                            text=process_persian_text_for_matplotlib("تغییر بازه تاریخی"),
                                            command=self._on_change_date_range_button_click,
                                            font=("Vazirmatn", 11),
                                            fg_color=button_category_colors["date_range"],
                                            hover_color=self._darken_color(button_category_colors["date_range"], 20),
                                            corner_radius=8, height=25, width=140)
        change_date_button.pack(side="right", padx=2)
        
        # Weekdays
        self._display_list_filter_summary(
            "weekday", 
            filters_data.get("weekday", []), 
            button_category_colors["weekday"], 
            button_text_color,
            item_map={
                0: "دوشنبه", 1: "سه‌شنبه", 2: "چهارشنبه", 3: "پنج‌شنبه", 4: "جمعه", 5: "شنبه", 6: "یکشنبه"
            },
            all_text="همه"
        )

        # Sessions
        all_session_details = db_manager.get_session_times_with_display_utc(db_manager.get_default_timezone())
        session_names_map = { 
            'ny': 'Newyork', 'sydney': 'Sydney', 'tokyo': 'Tokyo', 'london': 'London'
        }
        
        selected_sessions = filters_data.get('sessions', [])
        display_sessions_texts = []
        if selected_sessions == "همه":
            pass # Handled by _display_list_filter_summary directly
        elif isinstance(selected_sessions, list) and selected_sessions:
            for key in selected_sessions:
                details = all_session_details.get(key)
                if details:
                    session_display_name = session_names_map.get(key, key.capitalize())
                    display_sessions_texts.append(f"{session_display_name} ({details['start_display']} - {details['end_display']})")
        
        self._display_list_filter_summary(
            "sessions",
            selected_sessions, # Pass original selection for 'all' check
            button_category_colors["sessions"],
            button_text_color,
            item_map=session_names_map, # This map is used for simple names, not full display
            all_text="همه",
            custom_display_list=display_sessions_texts # Use pre-formatted list for individual items
        )

        # Instruments
        self._display_list_filter_summary(
            "instruments",
            filters_data.get("instruments", []),
            button_category_colors["instruments"],
            button_text_color,
            all_text="همه"
        )

        # Hourly
        self._clear_value_frame("hourly")
        hourly_value_frame = self.filter_elements["hourly"]["value_scrollable_frame"]
        hourly_selection = filters_data.get("hourly", {})
        hourly_summary_elements = [] # For the main button text

        current_mode = hourly_selection.get("mode")

        if current_mode == "full_session":
            text = process_persian_text_for_matplotlib("سشن کامل")
            # For detail, check if actual sessions are selected
            selected_sessions_for_hourly_display = filters_data.get('sessions', [])
            if selected_sessions_for_hourly_display == "همه":
                text += process_persian_text_for_matplotlib(" (همه سشن‌ها)")
            elif isinstance(selected_sessions_for_hourly_display, list) and selected_sessions_for_hourly_display:
                # Get display names of selected sessions for a compact view
                session_display_names_compact = [
                    session_names_map.get(key, key.capitalize()) 
                    for key in selected_sessions_for_hourly_display if key in session_names_map
                ]
                if session_display_names_compact:
                    text += process_persian_text_for_matplotlib(f" ({', '.join(session_display_names_compact)})")
            
            ctk.CTkButton(hourly_value_frame,
                            text=text,
                            font=("Vazirmatn", 11, "bold"),
                            fg_color=self._lighten_color(button_category_colors["hourly"], 85),
                            text_color=button_text_color,
                            hover_color=self._lighten_color(button_category_colors["hourly"], 85),
                            corner_radius=15, height=25).pack(side="right", padx=2)

        elif current_mode == "session_segmentation":
            segment_count = hourly_selection.get("segment_count")
            text = process_persian_text_for_matplotlib("تفکیک سشن")
            if segment_count:
                text += process_persian_text_for_matplotlib(f" ({segment_count} قسمت)")
            
            # Show actual segments if available and not too many
            segments_data = hourly_selection.get("segments", [])
            if segments_data:
                # Display individual session segments
                displayed_segments = []
                for seg_idx, seg in enumerate(segments_data):
                    session_key = seg.get("session_key", "")
                    session_name = session_names_map.get(session_key, session_key.capitalize() if session_key else "")
                    displayed_segments.append(f"{session_name}: {seg['start']}-{seg['end']}")
                
                if len(displayed_segments) > summary_display_limit:
                    text_for_button_segments = process_persian_text_for_matplotlib(f"{displayed_segments[0]} ... و {len(displayed_segments) - 1} مورد دیگر")
                else:
                    text_for_button_segments = process_persian_text_for_matplotlib(", ".join(displayed_segments))

                ctk.CTkButton(hourly_value_frame,
                                text=text,
                                font=("Vazirmatn", 11, "bold"),
                                fg_color=self._lighten_color(button_category_colors["hourly"], 85),
                                text_color=button_text_color,
                                hover_color=self._lighten_color(button_category_colors["hourly"], 85),
                                corner_radius=15, height=25).pack(side="right", padx=2)
                
                # Add a separate button for the segments if they are many, or include in main button
                ctk.CTkButton(hourly_value_frame,
                                text=text_for_button_segments,
                                font=("Vazirmatn", 11, "bold"),
                                fg_color=self._lighten_color(button_category_colors["hourly"], 85),
                                text_color=button_text_color,
                                hover_color=self._lighten_color(button_category_colors["hourly"], 85),
                                corner_radius=15, height=25).pack(side="right", padx=2)

            else:
                ctk.CTkButton(hourly_value_frame,
                                text=text + process_persian_text_for_matplotlib(" (بازه‌ای انتخاب نشده)"),
                                font=("Vazirmatn", 11, "bold"),
                                fg_color=self._lighten_color(button_category_colors["hourly"], 85),
                                text_color=button_text_color,
                                hover_color=self._lighten_color(button_category_colors["hourly"], 85),
                                corner_radius=15, height=25).pack(side="right", padx=2)


        elif current_mode in ["hourly_segmentation", "half_hourly_segmentation", "quarter_hourly_segmentation"]:
            intervals = hourly_selection.get("intervals", [])
            granularity_value = hourly_selection.get("granularity")
            granularity_display_name_map = {
                60: process_persian_text_for_matplotlib("تفکیک ساعتی (60min)"),
                30: process_persian_text_for_matplotlib("تفکیک نیم‌ساعتی (30min)"),
                15: process_persian_text_for_matplotlib("تفکیک یک‌ربعی (15min)")
            }
            granularity_text = granularity_display_name_map.get(granularity_value, process_persian_text_for_matplotlib("ناشناس"))
            
            ctk.CTkButton(hourly_value_frame,
                            text=granularity_text,
                            font=("Vazirmatn", 11, "bold"),
                            fg_color=self._lighten_color(button_category_colors["hourly"], 85),
                            text_color=button_text_color,
                            hover_color=self._lighten_color(button_category_colors["hourly"], 85),
                            corner_radius=15, height=25).pack(side="right", padx=2)

            if intervals:
                interval_texts = [f"{i['start']}-{i['end']}" for i in intervals]
                if len(interval_texts) > summary_display_limit:
                    text_for_intervals = process_persian_text_for_matplotlib(f"{interval_texts[0]} ... و {len(interval_texts) - 1} مورد دیگر")
                else:
                    text_for_intervals = process_persian_text_for_matplotlib(", ".join(interval_texts))
                
                ctk.CTkButton(hourly_value_frame,
                                text=text_for_intervals,
                                font=("Vazirmatn", 11, "bold"),
                                fg_color=self._lighten_color(button_category_colors["hourly"], 85),
                                text_color=button_text_color,
                                hover_color=self._lighten_color(button_category_colors["hourly"], 85),
                                corner_radius=15, height=25).pack(side="right", padx=2)
            else:
                ctk.CTkButton(hourly_value_frame,
                                text=process_persian_text_for_matplotlib("هیچ بازه‌ای انتخاب نشده است."),
                                font=("Vazirmatn", 11, "bold"),
                                fg_color=self._lighten_color(button_category_colors["hourly"], 85),
                                text_color=button_text_color,
                                hover_color=self._lighten_color(button_category_colors["hourly"], 85),
                                corner_radius=15, height=25).pack(side="right", padx=2)
        else:
             ctk.CTkButton(hourly_value_frame,
                            text=process_persian_text_for_matplotlib("نامشخص"),
                            font=("Vazirmatn", 11, "bold"),
                            fg_color=self._lighten_color(button_category_colors["hourly"], 85),
                            text_color=button_text_color,
                            hover_color=self._lighten_color(button_category_colors["hourly"], 85),
                            corner_radius=15, height=25).pack(side="right", padx=2)


        # Trade Type
        self._clear_value_frame("trade_type")
        trade_type_value_frame = self.filter_elements["trade_type"]["value_scrollable_frame"]
        selected_trade_type = filters_data.get('trade_type', 'همه')
        display_trade_type_text = ""
        if selected_trade_type == "همه": display_trade_type_text = process_persian_text_for_matplotlib("همه انواع")
        elif selected_trade_type == "Profit": display_trade_type_text = process_persian_text_for_matplotlib("سودده")
        elif selected_trade_type == "Loss": display_trade_type_text = process_persian_text_for_matplotlib("زیان‌ده")
        elif selected_trade_type == "RF": display_trade_type_text = process_persian_text_for_matplotlib("ریسک فری")

        ctk.CTkButton(trade_type_value_frame,
                        text=display_trade_type_text,
                        font=("Vazirmatn", 11, "bold"),
                        fg_color=self._lighten_color(button_category_colors["trade_type"], 85),
                        text_color=button_text_color,
                        hover_color=self._lighten_color(button_category_colors["trade_type"], 85),
                        corner_radius=15, width=80, height=25).pack(side="right", padx=2)
        
        # Errors
        self._display_list_filter_summary(
            "errors",
            filters_data.get("errors", []),
            button_category_colors["errors"],
            button_text_color,
            all_text="همه خطاها"
        )


        self.main_scrollable_filter_details_frame.update_idletasks()
        self.main_scrollable_filter_details_frame._parent_canvas.yview_moveto(0) # Scroll to top

    def _display_list_filter_summary(self, key, selected_items, color, text_color, item_map=None, all_text=None, custom_display_list=None):
        self._clear_value_frame(key)
        value_frame = self.filter_elements[key]["value_scrollable_frame"]
        summary_display_limit = 3 # This limit is for the "and X more" text, buttons will still flow

        display_list = []
        is_all_selected_explicitly = False

        if selected_items == all_text:
            is_all_selected_explicitly = True
        elif custom_display_list is not None:
            display_list = custom_display_list
        elif isinstance(selected_items, list):
            if item_map:
                display_list = [item_map.get(item, str(item)) for item in selected_items]
            else:
                display_list = selected_items
        
        if is_all_selected_explicitly and all_text:
            ctk.CTkButton(value_frame,
                          text=process_persian_text_for_matplotlib(all_text),
                          font=("Vazirmatn", 11, "bold"),
                          fg_color=self._lighten_color(color, 85),
                          text_color=text_color,
                          hover_color=self._lighten_color(color, 85),
                          corner_radius=15, width=60, height=25).pack(side="right", padx=2)
        elif display_list:
            # We don't use summary_display_limit for packing, all items will be packed
            # The scrollable frame will handle overflow.
            # But we can add "and X more" if it's packed horizontally for clarity.
            items_to_display_on_buttons = display_list
            # if len(display_list) > summary_display_limit:
            #     items_to_display_on_buttons = display_list[:summary_display_limit]
            #     remaining_count = len(display_list) - summary_display_limit
            #     # Add a button for "and X more" if it's not the 'all' option
            #     ctk.CTkButton(value_frame,
            #                   text=process_persian_text_for_matplotlib(f"و {remaining_count} مورد دیگر"),
            #                   font=("Vazirmatn", 11), text_color=text_color,
            #                   fg_color=self._lighten_color(color, 85), hover_color=self._lighten_color(color, 85),
            #                   corner_radius=15, height=25, width=100).pack(side="right", padx=2)

            for item in items_to_display_on_buttons:
                ctk.CTkButton(value_frame,
                              text=process_persian_text_for_matplotlib(item),
                              font=("Vazirmatn", 11, "bold"),
                              fg_color=self._lighten_color(color, 85),
                              text_color=text_color,
                              hover_color=self._lighten_color(color, 85),
                              corner_radius=15, width=80, height=25).pack(side="right", padx=2)
        else: # No items selected
            ctk.CTkButton(value_frame,
                          text=process_persian_text_for_matplotlib('هیچکدام'),
                          font=("Vazirmatn", 11, "bold"),
                          fg_color=self._lighten_color(color, 85),
                          text_color=text_color,
                          hover_color=self._lighten_color(color, 85),
                          corner_radius=15, width=80, height=25).pack(side="right", padx=2)

    def _darken_color(self, hex_color, percent):
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        darker_rgb = tuple(max(0, c - int(c * percent / 100)) for c in rgb)
        return '#%02x%02x%02x' % darker_rgb

    def _lighten_color(self, hex_color, percent):
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        lighter_rgb = tuple(min(255, c + int((255 - c) * percent / 100)) for c in rgb)
        return '#%02x%02x%02x' % lighter_rgb