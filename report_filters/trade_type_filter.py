# report_filters/trade_type_filter.py

import customtkinter as ctk
from persian_chart_utils import process_persian_text_for_matplotlib

class TradeTypeFilterFrame(ctk.CTkFrame):
    def __init__(self, master, on_change_callback=None, fg_color="transparent", **kwargs):
        super().__init__(master, fg_color=fg_color, **kwargs)
        self.on_change_callback = on_change_callback
        self.trade_type_var = ctk.StringVar(value="همه") # Default to "همه"

        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(self, text=process_persian_text_for_matplotlib("نوع ترید:"), font=("Vazirmatn", 12))
        self.label.grid(row=0, column=0, padx=5, pady=5, sticky="e")

        trade_types = [
            ("همه گزینه‌ها", "همه"),
            ("سودده", "Profit"),
            ("زیان‌ده", "Loss"),
            ("ریسک فری", "RF")
        ]

        # Use a frame to hold radio buttons for better layout control
        radio_button_frame = ctk.CTkFrame(self, fg_color="transparent")
        radio_button_frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        radio_button_frame.grid_columnconfigure(0, weight=1)

        for i, (display_text, value) in enumerate(trade_types):
            radio_btn = ctk.CTkRadioButton(radio_button_frame,
                                           text=process_persian_text_for_matplotlib(display_text),
                                           variable=self.trade_type_var,
                                           value=value,
                                           command=self._on_trade_type_change,
                                           font=("Vazirmatn", 11),
                                           radiobutton_width=20,
                                           radiobutton_height=20,
                                           border_width_checked=6,
                                           border_color="#3B8ED0",
                                           fg_color="#3B8ED0",
                                           hover_color="#1F6AA5",
                                           text_color_disabled="gray50")
            radio_btn.grid(row=i, column=0, sticky="e", padx=10, pady=2) # Right-aligned

    def _on_trade_type_change(self):
        if self.on_change_callback:
            self.on_change_callback()

    def get_selection(self):
        return self.trade_type_var.get()

    def set_selection(self, value):
        self.trade_type_var.set(value)
        # No need to call on_change_callback here directly.