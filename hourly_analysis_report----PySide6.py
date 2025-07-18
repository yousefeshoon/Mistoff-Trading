# hourly_analysis_report.py (تبدیل شده به PySide6)

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QFrame, QSizePolicy, QLineEdit, QComboBox, QCheckBox, 
    QScrollArea, QSplitter
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas 
import db_manager
import pytz
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import numpy as np 

import matplotlib.font_manager as fm 

# <<< ایمپورت‌های لازم برای اصلاح متن فارسی در Matplotlib (دوباره اضافه شد)
import arabic_reshaper
from bidi import algorithm as bidi
# >>>

# تابع پردازش متن فارسی از فایل پیکربندی ایمپورت شده است (اما برای Matplotlib اینجا هم نیاز داریم)
# from matplotlib_persian_config import process_persian_text_for_matplotlib # این خط دیگر لازم نیست

# <<< تعریف تابع apply_persian_reshaping_and_bidi در اینجا
def apply_persian_reshaping_and_bidi(text):
    if not text:
        return ""
    reshaped_text = arabic_reshaper.reshape(text)
    bidi_text = bidi.get_display(reshaped_text)
    return bidi_text
# >>>

# تنظیمات عمومی Qt برای پشتیبانی از RTL
QApplication.setLayoutDirection(Qt.RightToLeft) 

# --- تنظیمات فونت فارسی برای Matplotlib (بخش تست مستقل) ---
FONT_NAME = None
persian_fonts_candidates = [
    "Vazirmatn", "IRANSans", "B Nazanin", "Nika", "Arial" 
]

for font_candidate in persian_fonts_candidates:
    font_paths = fm.findfont(font_candidate)
    if font_paths:
        if isinstance(font_paths, list):
            if font_paths: 
                FONT_NAME = font_candidate
                break
        else:
            FONT_NAME = font_candidate
            break

if FONT_NAME:
    plt.rcParams['font.family'] = FONT_NAME
    plt.rcParams['font.sans-serif'] = FONT_NAME
    plt.rcParams['axes.unicode_minus'] = False 
else:
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial'] 
    plt.rcParams['axes.unicode_minus'] = False 
# --- پایان تنظیمات فونت فارسی برای Matplotlib ---


class HourlyAnalysisReportWindow(QMainWindow): 
    def __init__(self, parent_root=None, open_toplevel_windows_list_UNUSED=None): 
        super().__init__(parent_root) 
        self.setWindowTitle("گزارش آنالیز ساعتی تریدها") 
        
        # <<< تغییر: 20% بزرگ‌تر کردن ابعاد پنجره
        screen_width = QApplication.primaryScreen().size().width()
        screen_height = QApplication.primaryScreen().size().height()

        initial_width = int(screen_width * 0.80) 
        initial_height = int(screen_height * 0.80) 

        self.setGeometry(0, 0, int(initial_width * 1.20), int(initial_height * 1.20)) # 20% بزرگتر
        self.center_window() # متد جدید برای مرکز کردن پنجره
        # >>>

        self.central_widget = QWidget() 
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget) 

        # --- PanedWindow معادل QSplitter ---
        self.main_splitter = QSplitter(Qt.Horizontal) 
        self.main_layout.addWidget(self.main_splitter)

        # پنل فیلترها (سمت راست)
        self.filter_panel = QFrame(self) 
        self.filter_panel.setFrameShape(QFrame.StyledPanel)
        self.filter_panel.setFrameShadow(QFrame.Raised)
        self.filter_panel_layout = QVBoxLayout(self.filter_panel) 
        self.filter_panel.setStyleSheet("background-color: white; border-radius: 10px;") 
        self.filter_panel_layout.setAlignment(Qt.AlignTop | Qt.AlignRight) 

        self.main_splitter.addWidget(self.filter_panel)
        self.main_splitter.setStretchFactor(0, 0) 
        self.main_splitter.setStretchFactor(1, 1) 


        # پنل محتوای اصلی (سمت چپ)
        self.content_panel = QFrame(self) 
        self.content_panel_layout = QVBoxLayout(self.content_panel) 
        self.content_panel.setStyleSheet("background-color: #F0F2F5;") 

        self.main_splitter.addWidget(self.content_panel)

        # تنظیم اولیه عرض پنل فیلترها
        self.resizeEvent = self.on_window_resized 
        self.initial_resize_done = False 


        # --- ویجت‌های داخل filter_panel ---
        title_font = QFont("Segoe UI", 13, QFont.Bold)
        self.filter_title = QLabel("تنظیم فیلترها", self.filter_panel) 
        self.filter_title.setFont(title_font)
        self.filter_title.setStyleSheet("color: #202124;")
        self.filter_title.setAlignment(Qt.AlignRight) 
        self.filter_panel_layout.addWidget(self.filter_title)
        self.filter_panel_layout.addSpacing(15)

        # فیلتر تاریخ
        date_label_font = QFont("Segoe UI", 10, QFont.Bold)
        date_label_style = "color: #5F6368;"
        self.date_range_label = QLabel("بازه تاریخی:", self.filter_panel)
        self.date_range_label.setFont(date_label_font)
        self.date_range_label.setStyleSheet(date_label_style)
        self.date_range_label.setAlignment(Qt.AlignRight)
        self.filter_panel_layout.addWidget(self.date_range_label)
        
        self.date_frame = QFrame(self.filter_panel)
        self.date_frame_layout = QHBoxLayout(self.date_frame)
        self.date_frame_layout.setContentsMargins(0,0,0,0) 
        self.date_frame_layout.setAlignment(Qt.AlignRight) 
        
        self.from_date_label = QLabel("از:", self.date_frame)
        self.from_date_label.setAlignment(Qt.AlignRight)
        self.date_frame_layout.addWidget(self.from_date_label)
        self.from_date_entry = QLineEdit(self.date_frame) 
        self.from_date_entry.setText((datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
        self.from_date_entry.textChanged.connect(self.update_report_data) 
        self.date_frame_layout.addWidget(self.from_date_entry)

        self.to_date_label = QLabel("تا:", self.date_frame)
        self.to_date_label.setAlignment(Qt.AlignRight)
        self.date_frame_layout.addWidget(self.to_date_label)
        self.to_date_entry = QLineEdit(self.date_frame) 
        self.to_date_entry.setText(datetime.now().strftime('%Y-%m-%d'))
        self.to_date_entry.textChanged.connect(self.update_report_data) 
        self.date_frame_layout.addWidget(self.to_date_entry)

        self.filter_panel_layout.addWidget(self.date_frame)
        self.filter_panel_layout.addSpacing(10)


        # فیلتر نوع ترید
        self.trade_type_label = QLabel("نوع ترید:", self.filter_panel)
        self.trade_type_label.setFont(date_label_font)
        self.trade_type_label.setStyleSheet(date_label_style)
        self.trade_type_label.setAlignment(Qt.AlignRight)
        self.filter_panel_layout.addWidget(self.trade_type_label)
        
        self.trade_type_combobox = QComboBox(self.filter_panel) 
        trade_type_options_display = ["همه", "Profit", "Loss", "RF"]
        self.trade_type_combobox.addItems(trade_type_options_display)
        self.trade_type_combobox.setCurrentText("همه") 
        self.trade_type_combobox.currentTextChanged.connect(self.update_report_data) 
        self.filter_panel_layout.addWidget(self.trade_type_combobox)
        self.filter_panel_layout.addSpacing(10)


        # فیلتر نوع خطا
        self.error_filter_label = QLabel("فیلتر خطاها:", self.filter_panel)
        self.error_filter_label.setFont(date_label_font)
        self.error_filter_label.setStyleSheet(date_label_style)
        self.error_filter_label.setAlignment(Qt.AlignRight)
        self.filter_panel_layout.addWidget(self.error_filter_label)

        self.error_scroll_area = QScrollArea(self.filter_panel) 
        self.error_scroll_area.setWidgetResizable(True)
        # <<< استایل برای QScrollArea و QCheckBox برای نمایش بهتر تیک
        self.error_scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: white; /* پس‌زمینه اسکرول‌اریا */
            }
            QScrollArea > QWidget > QWidget { /* محتوای داخل اسکرول‌اریا */
                background-color: white;
            }
            QCheckBox::indicator {
                width: 15px; /* اندازه مربع چک‌باکس */
                height: 15px;
                border: 1px solid #5F6368; /* رنگ حاشیه */
                border-radius: 3px;
                background-color: white; /* پس‌زمینه مربع */
            }
            QCheckBox::indicator:checked {
                background-color: #4285F4; /* رنگ پس‌زمینه وقتی تیک خورده */
                border: 1px solid #4285F4;
                /* image: url(check_mark.png); */ /* یک عکس تیک مارک اگر بخواهیم (باید فایل check_mark.png موجود باشد) */
            }
            QCheckBox {
                spacing: 5px; /* فاصله متن از چک‌باکس */
                padding-right: 5px; /* برای راستچین کردن متن چک‌باکس */
                text-align: right; /* متن را راستچین می‌کند */
            }
        """)
        # >>>

        self.error_scroll_area_content = QWidget()
        self.error_scroll_area_content_layout = QVBoxLayout(self.error_scroll_area_content)
        self.error_scroll_area_content_layout.setAlignment(Qt.AlignTop | Qt.AlignRight) 
        self.error_scroll_area.setWidget(self.error_scroll_area_content)
        
        self.all_errors = db_manager.get_all_errors()
        self.error_filter_vars = {} 
        
        self.all_errors_checkbox = QCheckBox("همه خطاها", self.error_scroll_area_content) 
        self.all_errors_checkbox.setChecked(True)
        self.all_errors_checkbox.stateChanged.connect(self.toggle_all_errors_and_update) 
        self.error_scroll_area_content_layout.addWidget(self.all_errors_checkbox)

        for error_name in self.all_errors:
            checkbox = QCheckBox(error_name, self.error_scroll_area_content) 
            checkbox.setChecked(True)
            checkbox.stateChanged.connect(self.update_report_data) 
            self.error_filter_vars[error_name] = checkbox
            self.error_scroll_area_content_layout.addWidget(checkbox)
        
        self.filter_panel_layout.addWidget(self.error_scroll_area)
        self.filter_panel_layout.addStretch(1) 

        # دکمه اعمال فیلترها
        self.apply_filters_button = QPushButton("اعمال فیلترها", self.filter_panel) 
        self.apply_filters_button.setStyleSheet("""
            QPushButton {
                background-color: #4285F4;
                color: white;
                font-weight: bold;
                border-radius: 5px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #3367D6;
            }
        """)
        self.apply_filters_button.clicked.connect(self.update_report_data) 
        self.filter_panel_layout.addWidget(self.apply_filters_button)


        # --- ویجت‌های داخل content_panel ---
        self.content_panel_layout.setContentsMargins(10, 10, 10, 10) 

        self.current_tz_label = QLabel(self.content_panel)
        self.current_tz_label.setStyleSheet("color: #5F6368; font-style: italic;")
        self.current_tz_label.setAlignment(Qt.AlignRight)
        self.content_panel_layout.addWidget(self.current_tz_label)
        self.update_timezone_display() 

        # فریم برای نمودارها
        self.charts_frame = QFrame(self.content_panel)
        self.charts_frame.setStyleSheet("background-color: white; border-radius: 10px;")
        self.charts_frame_layout = QHBoxLayout(self.charts_frame)
        self.content_panel_layout.addWidget(self.charts_frame)
        self.charts_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding) 

        # نمودار خطی (Hourly Trend)
        self.line_chart_container = QFrame(self.charts_frame)
        self.line_chart_container_layout = QVBoxLayout(self.line_chart_container)
        self.line_chart_container_layout.setContentsMargins(10,10,10,10)
        self.charts_frame_layout.addWidget(self.line_chart_container)

        self.line_chart_title = QLabel("روند تریدها در ساعات روز (تعداد)", self.line_chart_container)
        self.line_chart_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.line_chart_title.setStyleSheet("color: #202124;")
        self.line_chart_title.setAlignment(Qt.AlignRight) 
        self.line_chart_container_layout.addWidget(self.line_chart_title)
        
        self.fig_line, self.ax_line = plt.subplots(figsize=(6, 4), dpi=100)
        self.canvas_line = FigureCanvas(self.fig_line)
        self.line_chart_container_layout.addWidget(self.canvas_line)

        # نمودار دایره‌ای (Error Distribution)
        self.pie_chart_container = QFrame(self.charts_frame)
        self.pie_chart_container_layout = QVBoxLayout(self.pie_chart_container)
        self.pie_chart_container_layout.setContentsMargins(10,10,10,10)
        self.charts_frame_layout.addWidget(self.pie_chart_container)

        self.pie_chart_title = QLabel("توزیع خطاهای منتخب (درصد)", self.pie_chart_container)
        self.pie_chart_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.pie_chart_title.setStyleSheet("color: #202124;")
        self.pie_chart_title.setAlignment(Qt.AlignRight) 
        self.pie_chart_container_layout.addWidget(self.pie_chart_title)

        self.fig_pie, self.ax_pie = plt.subplots(figsize=(6, 6), dpi=100) 
        self.canvas_pie = FigureCanvas(self.fig_pie)
        self.pie_chart_container_layout.addWidget(self.canvas_pie)


        # فریم برای Summary Cards
        self.summary_cards_frame = QFrame(self.content_panel)
        self.summary_cards_frame.setStyleSheet("background-color: #F0F2F5;")
        self.summary_cards_layout = QHBoxLayout(self.summary_cards_frame)
        self.content_panel_layout.addWidget(self.summary_cards_frame)

        self.summary_cards_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed) 
        self.summary_cards_layout.setContentsMargins(0,0,0,0) 

        self.summary_labels = {}
        # _create_summary_card حالا یک تاپل (QFrame, QLabel) برمی‌گرداند
        total_card, total_label = self._create_summary_card(self.summary_cards_frame, "کل تریدها", "0")
        self.summary_labels['total_trades'] = total_label
        self.summary_cards_layout.addWidget(total_card) 

        profit_card, profit_label = self._create_summary_card(self.summary_cards_frame, "تریدهای سودده", "0")
        self.summary_labels['profit_trades'] = profit_label
        self.summary_cards_layout.addWidget(profit_card)

        loss_card, loss_label = self._create_summary_card(self.summary_cards_frame, "تریدهای زیان‌ده", "0")
        self.summary_labels['loss_trades'] = loss_label
        self.summary_cards_layout.addWidget(loss_card)

        rf_card, rf_label = self._create_summary_card(self.summary_cards_frame, "تریدهای ریسک‌فری", "0")
        self.summary_labels['rf_trades'] = rf_label
        self.summary_cards_layout.addWidget(rf_card)
        
        self.update_report_data() 
    
    # <<< متد جدید برای مرکز کردن پنجره
    def center_window(self):
        qr = self.frameGeometry()
        cp = QApplication.primaryScreen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())
    # >>>

    def on_window_resized(self, event):
        if not self.initial_resize_done:
            self.initial_resize_done = True
            total_width = self.width()
            filter_pane_width = int(total_width * 0.20)
            self.main_splitter.setSizes([filter_pane_width, total_width - filter_pane_width])
        super().resizeEvent(event) # فراخوانی متد والد


    # --- متدهای کمکی برای ساخت ویجت‌ها (داخلی کلاس) ---
    def _create_summary_card(self, parent, title, initial_value):
        card_frame = QFrame(parent)
        card_frame.setStyleSheet("background-color: white; border-radius: 10px; padding: 10px;")
        card_layout = QVBoxLayout(card_frame)
        card_layout.setAlignment(Qt.AlignRight) 
        
        title_label = QLabel(title, card_frame)
        title_label.setFont(QFont("Segoe UI", 11)) 
        title_label.setStyleSheet("color: #5F6368;")
        title_label.setAlignment(Qt.AlignRight)
        card_layout.addWidget(title_label)

        value_label = QLabel(initial_value, card_frame)
        value_label.setFont(QFont("Segoe UI", 24, QFont.Bold)) 
        value_label.setStyleSheet("color: #202124;")
        value_label.setAlignment(Qt.AlignRight)
        card_layout.addWidget(value_label)
        
        return card_frame, value_label 

    def update_summary_cards(self, total, profit, loss, rf): 
        self.summary_labels['total_trades'].setText(str(total)) 
        self.summary_labels['profit_trades'].setText(str(profit))
        self.summary_labels['loss_trades'].setText(str(loss))
        self.summary_labels['rf_trades'].setText(str(rf))

    # --- متدهای مدیریت رویدادها و آپدیت داده‌ها (داخلی کلاس) ---
    def update_timezone_display(self):
        current_tz_name = db_manager.get_default_timezone()
        self.current_tz_label.setText(f"⏰ منطقه زمانی فعال شما: {current_tz_name}") 

    def toggle_all_errors_and_update(self, state): 
        is_checked = self.all_errors_checkbox.isChecked() 
        for error_name, checkbox in self.error_filter_vars.items():
            checkbox.setChecked(is_checked)
        self.update_report_data() 

    def update_report_data(self): 
        start_date_str = self.from_date_entry.text()
        end_date_str = self.to_date_entry.text()
        selected_trade_type_display = self.trade_type_combobox.currentText()
        
        if selected_trade_type_display == "همه":
            selected_trade_type_db = "همه"
        elif selected_trade_type_display == "Profit":
            selected_trade_type_db = "Profit"
        elif selected_trade_type_display == "Loss":
            selected_trade_type_db = "Loss"
        elif selected_trade_type_display == "RF":
            selected_trade_type_db = "RF"
        else:
            selected_trade_type_db = "همه" 

        selected_errors_filter = []
        if not self.all_errors_checkbox.isChecked(): 
            for error_name, checkbox in self.error_filter_vars.items():
                if checkbox.isChecked():
                    selected_errors_filter.append(error_name)

        try:
            start_date_dt = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date_dt = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            if start_date_dt > end_date_dt:
                messagebox.showwarning("خطا در تاریخ", "تاریخ شروع نمی‌تواند بعد از تاریخ پایان باشد.") 
                return 
        except ValueError:
            messagebox.showwarning("خطا در تاریخ", "فرمت تاریخ نامعتبر است. لطفاً از فرمت YYYY-MM-DD استفاده کنید.") 
            return

        all_relevant_trades = db_manager.get_trades_for_hourly_analysis(
            start_date_str, end_date_str, selected_trade_type_db 
        )
        
        filtered_trades_for_analysis = []
        for trade in all_relevant_trades:
            if not selected_errors_filter: 
                filtered_trades_for_analysis.append(trade)
            elif trade['errors']:
                trade_errors_list = [e.strip() for e in trade['errors'].split(',') if e.strip()]
                if any(err_filter in trade_errors_list for err_filter in selected_errors_filter):
                    filtered_trades_for_analysis.append(trade)

        hourly_profit_loss_rf_counts = defaultdict(lambda: Counter())
        all_filtered_errors_for_pie = [] 
        
        total_trades_count = len(filtered_trades_for_analysis)
        profit_count = 0
        loss_count = 0
        rf_count = 0

        current_display_timezone = pytz.timezone(db_manager.get_default_timezone())

        for trade in filtered_trades_for_analysis:
            try:
                utc_naive_dt = datetime.strptime(f"{trade['date']} {trade['time']}", "%Y-%m-%d %H:%M")
                utc_aware_dt = pytz.utc.localize(utc_naive_dt)
                display_aware_dt = utc_aware_dt.astimezone(current_display_timezone)
                
                hour_in_display_tz = display_aware_dt.hour
                
                hourly_profit_loss_rf_counts[hour_in_display_tz][trade['profit']] += 1
                
                if trade['profit'] == 'Profit':
                    profit_count += 1
                elif trade['profit'] == 'Loss':
                    loss_count += 1
                elif trade['profit'] == 'RF':
                    rf_count += 1

                if trade['errors']:
                    trade_errors_list = [e.strip() for e in trade['errors'].split(',') if e.strip()]
                    for err in trade_errors_list:
                        if not selected_errors_filter or err in selected_errors_filter:
                            all_filtered_errors_for_pie.append(err)

            except Exception as e:
                print(f"Error processing trade {trade.get('id')}: {e}")
                continue
        
        error_frequency_counts = Counter(all_filtered_errors_for_pie)

        self._update_line_chart(hourly_profit_loss_rf_counts, total_trades_count) 
        self._update_pie_chart(error_frequency_counts) 
        self.update_summary_cards(total_trades_count, profit_count, loss_count, rf_count)

    def _update_line_chart(self, hourly_data, total_trades_in_range): 
        self.ax_line.clear()
        
        hours = list(range(24))
        profit_counts = [hourly_data.get(h, {}).get('Profit', 0) for h in hours]
        loss_counts = [hourly_data.get(h, {}).get('Loss', 0) for h in hours]
        rf_counts = [hourly_data.get(h, {}).get('RF', 0) for h in hours]
        
        if total_trades_in_range == 0:
            self.ax_line.text(0.5, 0.5, apply_persian_reshaping_and_bidi("داده‌ای برای نمایش نمودار وجود ندارد."), horizontalalignment='center', verticalalignment='center', transform=self.ax_line.transAxes, fontsize=10, color='gray', fontproperties=fm.FontProperties(family=plt.rcParams['font.family'][0])) 
            self.ax_line.set_xticks([])
            self.ax_line.set_yticks([])
            self.canvas_line.draw()
            return
        
        bar_width = 0.8
        self.ax_line.bar(hours, profit_counts, bar_width, label=apply_persian_reshaping_and_bidi("سودده"), color='#66BB6A') 
        self.ax_line.bar(hours, loss_counts, bar_width, bottom=profit_counts, label=apply_persian_reshaping_and_bidi("زیان‌ده"), color='#EF5350') 
        self.ax_line.bar(hours, rf_counts, bar_width, bottom=[profit_counts[i] + loss_counts[i] for i in range(24)], label=apply_persian_reshaping_and_bidi("ریسک‌فری"), color='#42A5F5') 

        self.ax_line.set_title(apply_persian_reshaping_and_bidi("تعداد تریدها بر اساس ساعت روز"), fontsize=12, fontproperties=fm.FontProperties(family=plt.rcParams['font.family'][0]))
        self.ax_line.set_xlabel(apply_persian_reshaping_and_bidi("ساعت (به وقت محلی)"), fontsize=10, fontproperties=fm.FontProperties(family=plt.rcParams['font.family'][0]))
        self.ax_line.set_ylabel(apply_persian_reshaping_and_bidi("تعداد تریدها"), fontsize=10, fontproperties=fm.FontProperties(family=plt.rcParams['font.family'][0]))
        
        self.ax_line.set_xticks(hours[::2]) 
        self.ax_line.set_xlim(-1, 24) 
        
        self.ax_line.legend(loc='upper left', prop=fm.FontProperties(family=plt.rcParams['font.family'][0])) 
        self.ax_line.grid(True, linestyle='--', alpha=0.6, axis='y') 
        
        for i, total in enumerate([profit_counts[j] + loss_counts[j] + rf_counts[j] for j in range(24)]):
            if total > 0:
                self.ax_line.text(hours[i], total + 0.5, str(total), ha='center', va='bottom', fontsize=8, fontproperties=fm.FontProperties(family=plt.rcParams['font.family'][0]))

        self.fig_line.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1) 
        self.canvas_line.draw() 

    def _update_pie_chart(self, error_counts): 
        self.ax_pie.clear()
        
        labels_raw = [] 
        sizes = []
        sorted_error_counts = sorted(error_counts.items(), key=lambda item: item[1], reverse=True)
        
        other_count = 0
        display_limit = 5 
        
        for i, (error, count) in enumerate(sorted_error_counts):
            if i < display_limit:
                labels_raw.append(f"{error}") 
                sizes.append(count)
            else:
                other_count += count
        
        if other_count > 0:
            labels_raw.append("متفرقه") 
            sizes.append(other_count)

        if not sizes:
            self.ax_pie.text(0.5, 0.5, apply_persian_reshaping_and_bidi("داده‌ای برای نمایش نمودار دایره‌ای وجود ندارد."), horizontalalignment='center', verticalalignment='center', transform=self.ax_pie.transAxes, fontsize=10, color='gray', fontproperties=fm.FontProperties(family=plt.rcParams['font.family'][0])) 
            self.ax_pie.set_xticks([])
            self.ax_pie.set_yticks([])
            self.canvas_pie.draw()
            return

        processed_labels_for_pie_chart = [apply_persian_reshaping_and_bidi(label) for label in labels_raw] 
        processed_labels_for_legend = [apply_persian_reshaping_and_bidi(f"{l_raw} ({s})") for l_raw, s in zip(labels_raw, sizes)] 

        num_colors = len(processed_labels_for_pie_chart)
        if num_colors <= 10:
            colors = plt.cm.get_cmap('tab10')(range(num_colors))
        elif num_colors <= 20:
            colors = plt.cm.get_cmap('tab20')(range(num_colors))
        else:
            colors = plt.cm.get_cmap('viridis')(np.linspace(0, 1, num_colors))
        
        wedges, texts, autotexts = self.ax_pie.pie(sizes, autopct='%1.1f%%', startangle=90, textprops={'fontsize': 8, 'fontproperties': fm.FontProperties(family=plt.rcParams['font.family'][0])}, colors=colors, pctdistance=0.85, labels=processed_labels_for_pie_chart) 
        self.ax_pie.axis('equal')  
        
        self.ax_pie.set_title(apply_persian_reshaping_and_bidi("توزیع خطاهای منتخب"), fontsize=12, fontproperties=fm.FontProperties(family=plt.rcParams['font.family'][0]))
        
        self.ax_pie.legend(wedges, processed_labels_for_legend, 
                     title=apply_persian_reshaping_and_bidi("خطاها"), 
                     loc="upper left", # <<< تغییر موقعیت
                     bbox_to_anchor=(1, 0, 0.5, 1),
                     prop=fm.FontProperties(family=plt.rcParams['font.family'][0])) 
        
        for autotexts_single in autotexts: # تکرار نام autotexts با متغیر حلقه
            autotexts_single.set_color('white') 
            autotexts_single.set_fontsize(9)
            autotexts_single.set_weight('bold')
            autotexts_single.set_fontproperties(fm.FontProperties(family=plt.rcParams['font.family'][0]))


        self.fig_pie.subplots_adjust(left=0.1, right=0.7, top=0.9, bottom=0.1) 
        self.canvas_pie.draw()


# --- تابع اصلی برای نمایش پنجره (خارج از کلاس) ---
# این تابع برای ادغام با برنامه اصلی tkinter استفاده می‌شود.
# اگر parent_root از Tkinter باشد، باید یک QApplication جداگانه برای PySide6 ایجاد شود.
# این حالت پیچیده‌تر است و ممکن است باعث مشکلاتی شود.
# فعلاً فرض بر این است که این پنجره به صورت مستقل تست می‌شود.

def show_hourly_analysis_report_window(parent_root, open_toplevel_windows_list_UNUSED):
    # PySide6 نیاز به QApplication دارد.
    app = QApplication.instance() 
    if not app:
        app = QApplication([]) 

    # اگر parent_root از Tkinter باشد، در اینجا به None تغییر می‌دهیم
    # زیرا پنجره PySide6 نمی‌تواند فرزند مستقیم پنجره Tkinter باشد.
    # مدیریت پنجره‌های باز دیگر در حال حاضر غیرفعال است (OPEN_TOPLEVEL_WINDOWS_UNUSED)
    report_window = HourlyAnalysisReportWindow(None, open_toplevel_windows_list_UNUSED) 
    report_window.show()
    # در حالت ادغام با Tkinter، app.exec() نباید فراخوانی شود،
    # چون Tkinter خودش mainloop دارد. این خط فقط برای تست مستقل است.
    # app.exec() 


# برای تست مستقل (PySide6)
if __name__ == "__main__":
    app = QApplication([]) 

    class MockDBManager:
        def get_default_timezone(self):
            return 'Asia/Tehran' 

        def get_all_errors(self):
            return ["ورود زودهنگام", "Overtrading", "نقض قوانین", "بدون برنامه", "احساساتی", "حرکات ناگهانی", "عدم مدیریت ریسک", "روانشناسی", "مدیریت سرمایه", "انتظار بیجا", "ریسک به ریوارد نامناسب"] 
        
        def get_trades_for_hourly_analysis(self, start_date_str, end_date_str, trade_type_filter):
            mock_trades = [
                {'id': 1, 'date': '2025-07-14', 'time': '02:00', 'profit': 'Profit', 'errors': '', 'original_timezone': 'UTC'}, 
                {'id': 2, 'date': '2025-07-14', 'time': '05:00', 'profit': 'Loss', 'errors': 'Overtrading, نقض قوانین', 'original_timezone': 'UTC'}, 
                {'id': 3, 'date': '2025-07-14', 'time': '08:00', 'profit': 'Profit', 'errors': '', 'original_timezone': 'UTC'}, 
                {'id': 4, 'date': '2025-07-14', 'time': '10:00', 'profit': 'RF', 'errors': 'بدون برنامه', 'original_timezone': 'UTC'}, 
                {'id': 5, 'date': '2025-07-14', 'time': '13:00', 'profit': 'Loss', 'errors': 'ورود زودهنگام, احساساتی', 'original_timezone': 'UTC'}, 
                {'id': 6, 'date': '2025-07-14', 'time': '16:00', 'profit': 'Profit', 'errors': '', 'original_timezone': 'UTC'}, 
                {'id': 7, 'date': '2025-07-14', 'time': '19:00', 'profit': 'Loss', 'errors': 'Overtrading', 'original_timezone': 'UTC'}, 
                {'id': 8, 'date': '2025-07-14', 'time': '22:00', 'profit': 'Profit', 'errors': '', 'original_timezone': 'UTC'}, 

                {'id': 9, 'date': '2025-07-15', 'time': '03:00', 'profit': 'Profit', 'errors': '', 'original_timezone': 'UTC'}, 
                {'id': 10, 'date': '2025-07-15', 'time': '06:00', 'profit': 'Loss', 'errors': 'نقض قوانین, حرکات ناگهانی', 'original_timezone': 'UTC'}, 
                {'id': 11, 'date': '2025-07-15', 'time': '09:00', 'profit': 'Profit', 'errors': '', 'original_timezone': 'UTC'}, 
                {'id': 12, 'date': '2025-07-15', 'time': '11:00', 'profit': 'RF', 'errors': 'بدون برنامه', 'original_timezone': 'UTC'}, 
                {'id': 13, 'date': '2025-07-15', 'time': '14:00', 'profit': 'Loss', 'errors': 'ورود زودهنگام, عدم مدیریت ریسک', 'original_timezone': 'UTC'}, 
                {'id': 14, 'date': '2025-07-15', 'time': '17:00', 'profit': 'Profit', 'errors': '', 'original_timezone': 'UTC'}, 
                {'id': 15, 'date': '2025-07-15', 'time': '20:00', 'profit': 'Loss', 'errors': 'Overtrading', 'original_timezone': 'UTC'}, 

                {'id': 16, 'date': '2025-07-16', 'time': '07:00', 'profit': 'Profit', 'errors': '', 'original_timezone': 'UTC'},
                {'id': 17, 'date': '2025-07-16', 'time': '09:00', 'profit': 'Loss', 'errors': 'روانشناسی', 'original_timezone': 'UTC'},
                {'id': 18, 'date': '2025-07-16', 'time': '10:00', 'profit': 'RF', 'errors': 'مدیریت سرمایه', 'original_timezone': 'UTC'},
                {'id': 19, 'date': '2025-07-16', 'time': '13:00', 'profit': 'Profit', 'errors': '', 'original_timezone': 'UTC'},
                {'id': 20, 'date': '2025-07-16', 'time': '15:00', 'profit': 'Loss', 'errors': 'انتظار بیجا, ریسک به ریوارد نامناسب', 'original_timezone': 'UTC'},

            ]
            
            filtered_by_date = []
            start_dt = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date_str, "%Y-%m-%d").date()

            for trade in mock_trades:
                trade_date = datetime.strptime(trade['date'], "%Y-%m-%d").date()
                if start_dt <= trade_date <= end_dt:
                    if trade_type_filter == "همه" or trade['profit'] == trade_type_filter:
                        filtered_by_date.append(trade)
            
            return filtered_by_date

    db_manager = MockDBManager()

    window = HourlyAnalysisReportWindow() 
    window.show()
    app.exec()