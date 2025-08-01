# report_filters/hourly_filter.py

import customtkinter as ctk
import db_manager
from persian_chart_utils import process_persian_text_for_matplotlib
import tkinter as tk
from datetime import datetime, timedelta

class HourlyFilterFrame(ctk.CTkFrame):
    def __init__(self, master, on_change_callback=None, fg_color="transparent", **kwargs):
        super().__init__(master, fg_color=fg_color, **kwargs)
        self.on_change_callback = on_change_callback
        
        # Default mode changed to "hourly_segmentation"
        self.current_mode_var = ctk.StringVar(value="hourly_segmentation")
        self.segment_count_var = ctk.StringVar(value="2") # Default for session segmentation

        # self.granularity_var and related components are removed
        self.selected_time_segments_vars = {} # Still needed internally for get_selection of granular modes
        self.all_custom_times_var = ctk.BooleanVar(value=True) # Will be removed in next iteration, or adapted if needed

        self.available_session_details = {} 
        self.selected_session_keys = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3)

        self.session_filter_hint_label = ctk.CTkLabel(self, 
                                                      text=process_persian_text_for_matplotlib("توجه: ساعات قابل انتخاب بر اساس سشن‌های انتخابی شما در تب 'سشن‌های معاملاتی' فیلتر شده‌اند."),
                                                      font=("Vazirmatn", 11), text_color="gray50", anchor="e", wraplength=300)
        self.session_filter_hint_label.grid(row=0, column=0, columnspan=2, padx=5, pady=(5, 10), sticky="ew")

        self.mode_label = ctk.CTkLabel(self, text=process_persian_text_for_matplotlib("::"), font=("Vazirmatn", 12))
        self.mode_label.grid(row=1, column=0, padx=5, pady=5, sticky="e")

        self.radio_button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.radio_button_frame.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.radio_button_frame.grid_columnconfigure(0, weight=1)

        self.radio_full_session = ctk.CTkRadioButton(self.radio_button_frame,
                                                    text=process_persian_text_for_matplotlib("سشن کامل"),
                                                    variable=self.current_mode_var,
                                                    value="full_session",
                                                    command=self._on_mode_change,
                                                    font=("Vazirmatn", 11),
                                                    radiobutton_width=20, radiobutton_height=20,
                                                    border_width_checked=6, border_color="#3B8ED0",
                                                    fg_color="#3B8ED0", hover_color="#1F6AA5")
        self.radio_full_session.grid(row=0, column=0, sticky="e", padx=10, pady=2)

        self.radio_session_segmentation = ctk.CTkRadioButton(self.radio_button_frame,
                                                            text=process_persian_text_for_matplotlib("تفکیک سشن"),
                                                            variable=self.current_mode_var,
                                                            value="session_segmentation",
                                                            command=self._on_mode_change,
                                                            font=("Vazirmatn", 11),
                                                            radiobutton_width=20, radiobutton_height=20,
                                                            border_width_checked=6, border_color="#3B8ED0",
                                                            fg_color="#3B8ED0", hover_color="#1F6AA5")
        self.radio_session_segmentation.grid(row=1, column=0, sticky="e", padx=10, pady=2)

        # New Radio Buttons for Granular Segmentation
        self.radio_hourly_segmentation = ctk.CTkRadioButton(self.radio_button_frame,
                                                            text=process_persian_text_for_matplotlib("تفکیک ساعتی"),
                                                            variable=self.current_mode_var,
                                                            value="hourly_segmentation", # New value
                                                            command=self._on_mode_change,
                                                            font=("Vazirmatn", 11),
                                                            radiobutton_width=20, radiobutton_height=20,
                                                            border_width_checked=6, border_color="#3B8ED0",
                                                            fg_color="#3B8ED0", hover_color="#1F6AA5")
        self.radio_hourly_segmentation.grid(row=2, column=0, sticky="e", padx=10, pady=2)

        self.radio_half_hourly_segmentation = ctk.CTkRadioButton(self.radio_button_frame,
                                                                 text=process_persian_text_for_matplotlib("تفکیک نیم ساعتی"),
                                                                 variable=self.current_mode_var,
                                                                 value="half_hourly_segmentation", # New value
                                                                 command=self._on_mode_change,
                                                                 font=("Vazirmatn", 11),
                                                                 radiobutton_width=20, radiobutton_height=20,
                                                                 border_width_checked=6, border_color="#3B8ED0",
                                                                 fg_color="#3B8ED0", hover_color="#1F6AA5")
        self.radio_half_hourly_segmentation.grid(row=3, column=0, sticky="e", padx=10, pady=2)

        self.radio_quarter_hourly_segmentation = ctk.CTkRadioButton(self.radio_button_frame,
                                                                     text=process_persian_text_for_matplotlib("تفکیک یک ربعی"),
                                                                     variable=self.current_mode_var,
                                                                     value="quarter_hourly_segmentation", # New value
                                                                     command=self._on_mode_change,
                                                                     font=("Vazirmatn", 11),
                                                                     radiobutton_width=20, radiobutton_height=20,
                                                                     border_width_checked=6, border_color="#3B8ED0",
                                                                     fg_color="#3B8ED0", hover_color="#1F6AA5")
        self.radio_quarter_hourly_segmentation.grid(row=4, column=0, sticky="e", padx=10, pady=2)
        
        # Sub-frames for each mode
        self.mode_content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.mode_content_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=10, sticky="nsew")
        self.mode_content_frame.grid_columnconfigure(0, weight=1)
        self.mode_content_frame.grid_rowconfigure(0, weight=1)

        # Full Session Content
        self.full_session_frame = ctk.CTkFrame(self.mode_content_frame, fg_color="transparent")
        self.full_session_label = ctk.CTkLabel(self.full_session_frame, 
                                               text=process_persian_text_for_matplotlib("در این حالت، کل بازه سشن(های) انتخاب شده در تب 'سشن‌های معاملاتی' در نظر گرفته می‌شود."),
                                               font=("Vazirmatn", 11), wraplength=350, anchor="e")
        self.full_session_label.pack(padx=10, pady=20)

        # Session Segmentation Content
        self.session_segmentation_frame = ctk.CTkFrame(self.mode_content_frame, fg_color="transparent")
        self.session_segmentation_frame.grid_columnconfigure(0, weight=1)
        self.session_segmentation_frame.grid_columnconfigure(1, weight=1)

        self.segment_count_label = ctk.CTkLabel(self.session_segmentation_frame, 
                                                 text=process_persian_text_for_matplotlib("تعداد قسمت‌ها برای هر سشن:"),
                                                 font=("Vazirmatn", 11))
        self.segment_count_label.grid(row=0, column=1, padx=5, pady=5, sticky="e")

        self.segment_count_optionmenu = ctk.CTkOptionMenu(self.session_segmentation_frame,
                                                          variable=self.segment_count_var,
                                                          values=["2", "3", "4"],
                                                          command=self._on_segment_count_change,
                                                          font=("Vazirmatn", 11))
        self.segment_count_optionmenu.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.calculated_segments_display = ctk.CTkLabel(self.session_segmentation_frame,
                                                        text=process_persian_text_for_matplotlib("بخش‌های محاسبه شده:"),
                                                        font=("Vazirmatn", 10, "italic"), text_color="gray50", wraplength=350, anchor="e", justify="right")
        self.calculated_segments_display.grid(row=1, column=0, columnspan=2, padx=5, pady=(5,0), sticky="ew")

        # New: Granular Segmentation Content (replaces custom_hour_minute_frame)
        self.granular_segmentation_frame = ctk.CTkFrame(self.mode_content_frame, fg_color="transparent")
        self.granular_segmentation_frame.grid_columnconfigure(0, weight=1)
        self.granular_segmentation_frame.grid_columnconfigure(1, weight=1)

        self.granular_segments_display = ctk.CTkLabel(self.granular_segmentation_frame,
                                                      text=process_persian_text_for_matplotlib("بازه(های) زمانی محاسبه شده:"),
                                                      font=("Vazirmatn", 10, "italic"), text_color="gray50", wraplength=350, anchor="e", justify="right")
        self.granular_segments_display.grid(row=0, column=0, columnspan=2, padx=5, pady=(5,0), sticky="ew")

        # Initial display setup
        self._show_current_mode_frame()
        
        self.reload_hourly_data(selected_sessions_from_main=None, initial_load=True)

    def _on_mode_change(self):
        self._show_current_mode_frame()
        self._update_calculated_segments_display()
        self._update_granular_segmentation_display() # New call for granular modes
        if self.on_change_callback:
            self.on_change_callback()

    def _on_segment_count_change(self, new_value):
        self._update_calculated_segments_display()
        if self.on_change_callback:
            self.on_change_callback()
    
    # _on_granularity_change and related commands are removed.

    # _on_custom_time_checkbox_change and _toggle_all_custom_times are removed.

    def _show_current_mode_frame(self):
        self.full_session_frame.grid_forget()
        self.session_segmentation_frame.grid_forget()
        self.granular_segmentation_frame.grid_forget() # New frame

        current_mode = self.current_mode_var.get()
        if current_mode == "full_session":
            self.full_session_frame.grid(row=0, column=0, sticky="nsew")
        elif current_mode == "session_segmentation":
            self.session_segmentation_frame.grid(row=0, column=0, sticky="nsew")
        elif current_mode in ["hourly_segmentation", "half_hourly_segmentation", "quarter_hourly_segmentation"]: # New modes
            self.granular_segmentation_frame.grid(row=0, column=0, sticky="nsew")

    def reload_hourly_data(self, selected_sessions_from_main=None, initial_load=False):
        """
        This function reloads hourly filter options,
        especially based on the selected sessions from ReportSelectionWindow.
        """
        user_tz_name = db_manager.get_default_timezone()
        self.available_session_details = db_manager.get_session_times_with_display_utc(user_tz_name)

        if selected_sessions_from_main:
            self.selected_session_keys = selected_sessions_from_main
            
            if selected_sessions_from_main == "همه":
                sessions_text = process_persian_text_for_matplotlib("همه سشن‌ها")
                active_sessions_for_display = list(self.available_session_details.values())
            elif isinstance(selected_sessions_from_main, list) and selected_sessions_from_main:
                active_sessions_for_display = [self.available_session_details[key] for key in self.selected_session_keys if key in self.available_session_details]
                display_sessions_texts = []
                local_session_names_map = {
                    'ny': 'Newyork', 'sydney': 'Sydney', 'tokyo': 'Tokyo', 'london': 'London'
                }
                for details in active_sessions_for_display:
                    session_key_for_display = next((k for k,v in self.available_session_details.items() if v == details), None)
                    session_display_name = local_session_names_map.get(session_key_for_display, session_key_for_display.capitalize() if session_key_for_display else "")
                    display_sessions_texts.append(f"{session_display_name} ({details['start_display']} - {details['end_display']})")
                sessions_text = process_persian_text_for_matplotlib(", ".join(display_sessions_texts))
            else:
                sessions_text = process_persian_text_for_matplotlib("هیچ سشنی انتخاب نشده است.")
                active_sessions_for_display = []
            
            self.session_filter_hint_label.configure(text=process_persian_text_for_matplotlib(f"توجه: ساعات قابل انتخاب بر اساس سشن‌های انتخابی شما ({sessions_text}) در تب 'سشن‌های معاملاتی' فیلتر شده‌اند."))
        else:
            # If selected_sessions_from_main is None (e.g., during initial load or full reset)
            self.selected_session_keys = [] # Ensure it's an empty list
            self.session_filter_hint_label.configure(text=process_persian_text_for_matplotlib("توجه: ساعات قابل انتخاب بر اساس سشن‌های انتخابی شما در تب 'سشن‌های معاملاتی' فیلتر شده‌اند. (در حال حاضر هیچ سشنی انتخاب نشده است.)")) #
            active_sessions_for_display = []

        # Update the calculated segments display based on new session data
        self._update_calculated_segments_display()
        # Update granular segmentation display based on new session data
        self._update_granular_segmentation_display()

    def _update_calculated_segments_display(self):
        """Calculates and updates the display for segmented sessions."""
        if self.current_mode_var.get() == "session_segmentation":
            segments_to_show = []
            try:
                num_segments = int(self.segment_count_var.get())
                if num_segments < 2: # Ensure at least 2 segments for meaningful split
                    num_segments = 2

                sessions_to_segment = []
                if self.selected_session_keys == "همه":
                    sessions_to_segment = list(self.available_session_details.values())
                elif isinstance(self.selected_session_keys, list) and self.selected_session_keys:
                    sessions_to_segment = [self.available_session_details[key] for key in self.selected_session_keys if key in self.available_session_details]
                
                if not sessions_to_segment:
                    self.calculated_segments_display.configure(text=process_persian_text_for_matplotlib("لطفاً در تب 'سشن‌های معاملاتی' حداقل یک سشن را انتخاب کنید."))
                    return

                # Define local session names map for display purposes
                local_session_names_map = {
                    'ny': 'Newyork', 'sydney': 'Sydney', 'tokyo': 'Tokyo', 'london': 'London'
                }

                for session in sessions_to_segment:
                    start_time_str = session['start_display']
                    end_time_str = session['end_display']
                    
                    session_key_for_display = next((k for k, v in self.available_session_details.items() if v == session), None)
                    session_name = local_session_names_map.get(session_key_for_display, session_key_for_display.capitalize() if session_key_for_display else "")


                    start_minutes = self._time_to_minutes(start_time_str)
                    end_minutes = self._time_to_minutes(end_time_str)

                    # Handle overnight sessions (e.g., 23:00 - 03:00)
                    if end_minutes <= start_minutes:
                        end_minutes += (24 * 60) # Add a day's worth of minutes

                    total_duration = end_minutes - start_minutes
                    segment_duration = total_duration / num_segments

                    segment_texts = []
                    for i in range(num_segments):
                        segment_start_minutes = start_minutes + (i * segment_duration)
                        segment_end_minutes = start_minutes + ((i + 1) * segment_duration)
                        
                        # Ensure segments don't go past actual end time for the last segment
                        if i == num_segments - 1:
                            segment_end_minutes = end_minutes
                            
                        segment_start_time_str = self._minutes_to_time(int(segment_start_minutes))
                        segment_end_time_str = self._minutes_to_time(int(segment_end_minutes))
                        segment_texts.append(f"{segment_start_time_str}-{segment_end_time_str}")
                    
                    segments_to_show.append(f"{session_name}: {process_persian_text_for_matplotlib(', ').join(segment_texts)}")
                
                self.calculated_segments_display.configure(text=process_persian_text_for_matplotlib("بخش‌های محاسبه شده:") + "\n" + process_persian_text_for_matplotlib('\n').join(segments_to_show))

            except ValueError:
                self.calculated_segments_display.configure(text=process_persian_text_for_matplotlib("خطا در محاسبه. لطفاً مقادیر معتبر وارد کنید."))
            except Exception as e:
                self.calculated_segments_display.configure(text=process_persian_text_for_matplotlib(f"خطا در تفکیک: {e}"))
        else:
            self.calculated_segments_display.configure(text="")

    def _update_granular_segmentation_display(self): # Renamed from _update_custom_time_checkboxes
        """Calculates and updates the display for granular segmentation modes (hourly, half-hourly, quarter-hourly)."""
        if self.current_mode_var.get() not in ["hourly_segmentation", "half_hourly_segmentation", "quarter_hourly_segmentation"]:
            self.granular_segments_display.configure(text="")
            return

        active_session_intervals_minutes = []
        
        if self.selected_session_keys == "همه":
            sessions_to_use = list(self.available_session_details.values())
        elif isinstance(self.selected_session_keys, list) and self.selected_session_keys:
            sessions_to_use = [self.available_session_details[key] for key in self.selected_session_keys if key in self.available_session_details]
        else:
            # If no sessions are selected, display appropriate message
            self.granular_segments_display.configure(text=process_persian_text_for_matplotlib("لطفاً در تب 'سشن‌های معاملاتی' حداقل یک سشن را انتخاب کنید.")) #
            return

        for session in sessions_to_use:
            start_minutes = self._time_to_minutes(session['start_display'])
            end_minutes = self._time_to_minutes(session['end_display'])
            if end_minutes <= start_minutes:
                end_minutes += (24 * 60)
            active_session_intervals_minutes.append((start_minutes, end_minutes))
        
        if not active_session_intervals_minutes:
            self.granular_segments_display.configure(text=process_persian_text_for_matplotlib("هیچ سشنی برای نمایش ساعات پیدا نشد."))
            return

        granularity_value_map = {
            "hourly_segmentation": 60,
            "half_hourly_segmentation": 30,
            "quarter_hourly_segmentation": 15
        }
        step_minutes = granularity_value_map.get(self.current_mode_var.get(), 60) # Get step based on current mode

        all_possible_segments = set()
        
        events = []
        for s_start, s_end in active_session_intervals_minutes:
            events.append((s_start, 1))
            events.append((s_end, -1))
        events.sort()

        active_count = 0
        current_intersection_start = -1
        
        continuous_active_intervals = []
        for time_point, event_type in events:
            if event_type == 1: # Start of an interval
                if active_count == 0:
                    current_intersection_start = time_point
                active_count += 1
            else: # End of an interval
                active_count -= 1
                if active_count == 0 and current_intersection_start != -1:
                    continuous_active_intervals.append((current_intersection_start, time_point))
                    current_intersection_start = -1
        
        for interval_start, interval_end in continuous_active_intervals:
            current_time = interval_start
            while current_time < interval_end:
                segment_start_minutes = current_time
                segment_end_minutes = min(current_time + step_minutes, interval_end)
                
                segment_str = f"{self._minutes_to_time(int(segment_start_minutes))}-{self._minutes_to_time(int(segment_end_minutes))}"
                all_possible_segments.add((segment_start_minutes, segment_end_minutes, segment_str))
                current_time += step_minutes
        
        sorted_segments_str = sorted([s[2] for s in list(all_possible_segments)]) # Extract only string for display/storage
        
        # This is the list that will be used by get_selection for granular modes
        self.selected_time_segments_vars = {s: ctk.BooleanVar(value=True) for s in sorted_segments_str} # Always all selected for these modes

        # Update display text for granular modes
        if sorted_segments_str:
            display_text = process_persian_text_for_matplotlib("بازه(های) زمانی محاسبه شده:") + "\n"
            display_text += process_persian_text_for_matplotlib(", ").join(sorted_segments_str)
            self.granular_segments_display.configure(text=display_text)
        else:
            self.granular_segments_display.configure(text=process_persian_text_for_matplotlib("هیچ بازه‌ای برای این سشن‌ها و تفکیک زمانی یافت نشد."))


    def _time_to_minutes(self, time_str):
        """Converts 'HH:MM' string to total minutes from midnight."""
        h, m = map(int, time_str.split(':'))
        return h * 60 + m

    def _minutes_to_time(self, total_minutes):
        """Converts total minutes from midnight to 'HH:MM' string (handles values > 24 hours)."""
        total_minutes = total_minutes % (24 * 60)
        h = total_minutes // 60
        m = total_minutes % 60
        return f"{h:02d}:{m:02d}"

    def get_selection(self):
        current_mode = self.current_mode_var.get()
        selection_data = {"mode": current_mode}

        if current_mode == "full_session":
            selection_data["sessions"] = self.selected_session_keys
            
        elif current_mode == "session_segmentation":
            segments_list = []
            try:
                num_segments = int(self.segment_count_var.get())
                if num_segments < 2:
                    num_segments = 2
                
                sessions_to_segment = []
                if self.selected_session_keys == "همه":
                    sessions_to_segment = list(self.available_session_details.values())
                elif isinstance(self.selected_session_keys, list) and self.selected_session_keys:
                    sessions_to_segment = [self.available_session_details[key] for key in self.selected_session_keys if key in self.available_session_details]

                local_session_names_map = {
                    'ny': 'Newyork', 'sydney': 'Sydney', 'tokyo': 'Tokyo', 'london': 'London'
                }

                for session in sessions_to_segment:
                    start_time_str = session['start_display']
                    end_time_str = session['end_display']

                    start_minutes = self._time_to_minutes(start_time_str)
                    end_minutes = self._time_to_minutes(end_time_str)

                    if end_minutes <= start_minutes:
                        end_minutes += (24 * 60)

                    total_duration = end_minutes - start_minutes
                    segment_duration = total_duration / num_segments

                    for i in range(num_segments):
                        segment_start_minutes = start_minutes + (i * segment_duration)
                        segment_end_minutes = start_minutes + ((i + 1) * segment_duration)
                        if i == num_segments - 1:
                            segment_end_minutes = end_minutes

                        session_key_for_segment = next((k for k, v in self.available_session_details.items() if v == session), None)

                        segments_list.append({
                            "session_key": session_key_for_segment,
                            "start": self._minutes_to_time(int(segment_start_minutes)),
                            "end": self._minutes_to_time(int(segment_end_minutes))
                        })
                selection_data["segments"] = segments_list
                selection_data["segment_count"] = num_segments

            except ValueError:
                selection_data["segments"] = []
                selection_data["segment_count"] = None
            except Exception as e:
                print(f"Error getting session segmentation: {e}")
                selection_data["segments"] = []
                selection_data["segment_count"] = None

        elif current_mode in ["hourly_segmentation", "half_hourly_segmentation", "quarter_hourly_segmentation"]:
            # For these modes, all calculated segments are implicitly selected
            # No need for individual checkbox values, just calculate based on step_minutes
            
            granularity_value_map = {
                "hourly_segmentation": 60,
                "half_hourly_segmentation": 30,
                "quarter_hourly_segmentation": 15
            }
            step_minutes = granularity_value_map.get(current_mode, 60)

            active_session_intervals_minutes = []
            if self.selected_session_keys == "همه":
                sessions_to_use = list(self.available_session_details.values())
            elif isinstance(self.selected_session_keys, list) and self.selected_session_keys:
                sessions_to_use = [self.available_session_details[key] for key in self.selected_session_keys if key in self.available_session_details]
            else:
                sessions_to_use = [] # No sessions selected

            all_intervals_for_granular_mode = []
            for session in sessions_to_use:
                start_minutes = self._time_to_minutes(session['start_display'])
                end_minutes = self._time_to_minutes(session['end_display'])
                if end_minutes <= start_minutes:
                    end_minutes += (24 * 60)
                all_intervals_for_granular_mode.append((start_minutes, end_minutes))
            
            # Combine all session intervals into a single sorted list of events
            events = []
            for s_start, s_end in all_intervals_for_granular_mode:
                events.append((s_start, 1)) # 1 for start
                events.append((s_end, -1)) # -1 for end
            events.sort() # Sort by time

            active_count = 0
            current_intersection_start = -1
            continuous_active_intervals = []
            for time_point, event_type in events:
                if event_type == 1: # Start of an interval
                    if active_count == 0:
                        current_intersection_start = time_point
                    active_count += 1
                else: # End of an interval
                    active_count -= 1
                    if active_count == 0 and current_intersection_start != -1:
                        continuous_active_intervals.append((current_intersection_start, time_point))
                        current_intersection_start = -1
            
            selected_custom_intervals = []
            for interval_start, interval_end in continuous_active_intervals:
                current_time = interval_start
                while current_time < interval_end:
                    segment_start_minutes = current_time
                    segment_end_minutes = min(current_time + step_minutes, interval_end)
                    
                    selected_custom_intervals.append({
                        "start": self._minutes_to_time(int(segment_start_minutes)),
                        "end": self._minutes_to_time(int(segment_end_minutes))
                    })
                    current_time += step_minutes

            selection_data["intervals"] = selected_custom_intervals
            selection_data["granularity"] = step_minutes
        
        return selection_data

    def set_selection(self, mode, segments=None, intervals=None, granularity=None): # Renamed custom_intervals to intervals for granular modes
        self.current_mode_var.set(mode)
        self._show_current_mode_frame()
        
        if mode == "session_segmentation":
            if segments is not None:
                if isinstance(segments, int):
                    self.segment_count_var.set(str(segments))
                # If segments is a list of actual segments (from template load),
                # no specific UI update for individual segments is needed here beyond setting the mode.
            else: # If segments is None, it means a reset or no segments are provided
                self.segment_count_var.set("2") # Reset to default for session segmentation

        elif mode in ["hourly_segmentation", "half_hourly_segmentation", "quarter_hourly_segmentation"]:
            # For these modes, we just need to ensure the mode is set correctly,
            # and the display will update via _update_granular_segmentation_display().
            # The 'intervals' parameter is not used to set individual checkboxes here
            # because they are always "all selected" for these modes.
            # We also don't explicitly set granularity here as it's determined by the mode.
            pass # No specific action needed beyond setting the mode
            
        self._update_calculated_segments_display()
        self._update_granular_segmentation_display() # Ensure granular display is updated if mode changes
        # No need to call on_change_callback here directly.