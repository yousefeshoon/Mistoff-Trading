# فایل: error_widget_table.py

import tkinter as tk
from tkinter import ttk
import sqlite3

def calculate_error_stats():
    try:
        conn = sqlite3.connect("trades.db")
        cursor = conn.cursor()

        cursor.execute("SELECT errors FROM trades")
        all_errors = cursor.fetchall()
        conn.close()

        error_counts = {}
        total_errors = 0

        for row in all_errors:
            if row[0]:
                errors = row[0].split(",")
                for error in errors:
                    cleaned = error.strip()
                    if cleaned:
                        error_counts[cleaned] = error_counts.get(cleaned, 0) + 1
                        total_errors += 1

        return error_counts, total_errors
    except Exception as e:
        print("Database error:", e)
        return {}, 0

def create_always_on_top_widget():
    error_counts, total_errors = calculate_error_stats()
    if total_errors == 0:
        return

    root = tk.Tk()
    root.title("درصد خطاها")
    root.geometry("300x400+50+50")
    root.attributes('-topmost', True)
    root.resizable(False, False)

    tree = ttk.Treeview(root, columns=("error", "percent"), show="headings", height=15)
    tree.heading("error", text="نوع خطا", anchor="center")
    tree.heading("percent", text="درصد", anchor="center")
    tree.column("error", anchor="center", width=180)
    tree.column("percent", anchor="center", width=80)

    for error, count in error_counts.items():
        percent = round((count / total_errors) * 100, 1)
        tree.insert("", tk.END, values=(error, f"{percent}%"))

    tree.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    root.mainloop()

if __name__ == "__main__":
    create_always_on_top_widget()
