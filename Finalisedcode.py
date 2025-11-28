import sqlite3
import bcrypt
import customtkinter as ctk
from tkinter import messagebox, filedialog
import datetime
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from collections import Counter
import os
import json

# For image support
from PIL import Image, ImageTk

# Global Simulated Date Setting
SIMULATED_DATE = datetime.datetime(2025, 3, 18, 22, 31, 15)

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# Define the folder for storing quiz JSON files.
QUIZ_DIR = "quizzes"
if not os.path.exists(QUIZ_DIR):
    os.makedirs(QUIZ_DIR)

def get_db_connection():
    try:
        conn = sqlite3.connect("users.db")
        return conn
    except sqlite3.Error as e:
        print("Database connection error:", e)
        return None

def create_database():
    conn = get_db_connection()
    if conn is None:
        return
    cursor = conn.cursor()
    # Creating users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        account_type TEXT NOT NULL CHECK(account_type IN ('Student', 'Teacher'))
    );
    """)
    # Creating results table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        attempt_date DATETIME NOT NULL,
        correct_list TEXT NOT NULL,
        total_questions INTEGER NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)
    conn.commit()
    conn.close()

def record_quiz_result(user_id, correct_list, total_questions):
    conn = get_db_connection()
    if conn is None:
        messagebox.showerror("Error", "Unable to connect to database.")
        return False
    cursor = conn.cursor()
    now = SIMULATED_DATE if SIMULATED_DATE else datetime.datetime.now()
    attempt_date = now.strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO results (user_id, attempt_date, correct_list, total_questions)
    VALUES (?, ?, ?, ?)
    """, (user_id, attempt_date, correct_list, total_questions))
    conn.commit()
    conn.close()
    return True

def last_five_days_attempts(user_id, current_datetime=None):
    now = current_datetime if current_datetime else (SIMULATED_DATE if SIMULATED_DATE else datetime.datetime.now())
    conn = get_db_connection()
    if conn is None:
        return []
    cursor = conn.cursor()
    # Using '-4 days' so that today + previous 4 days yield 5 days total.
    query = """
    SELECT id, user_id, attempt_date, correct_list, total_questions
    FROM results
    WHERE user_id = ?
      AND date(attempt_date) >= date(?, '-4 days')
    ORDER BY attempt_date DESC;
    """
    cursor.execute(query, (user_id, now.strftime("%Y-%m-%d %H:%M:%S")))
    rows = cursor.fetchall()
    conn.close()
    
    processed = []
    for row in rows:
        try:
            attempt_dt = datetime.datetime.strptime(row[2], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        processed.append((row[0], row[1], attempt_dt, row[3], row[4]))
    return processed

def get_dashboard_data(user_id, current_datetime=None):
    results = last_five_days_attempts(user_id, current_datetime)
    if not results:
        today = (current_datetime.date() if current_datetime else datetime.datetime.today().date())
        return {today - datetime.timedelta(days=i): {"attempts": 0, "avg_percentage": 0} for i in range(5)}
    attempts_counter = Counter(r[2].date() for r in results)
    totals_per_day = {}
    for (rid, uid, attempt_dt, correct_list, total_q) in results:
        day = attempt_dt.date()
        try:
            correct = len(eval(correct_list))
        except Exception:
            correct = 0
        if day not in totals_per_day:
            totals_per_day[day] = {"correct": 0, "total": 0}
        totals_per_day[day]["correct"] += correct
        totals_per_day[day]["total"] += total_q
    dashboard_data = {}
    for day, vals in totals_per_day.items():
        avg = (vals["correct"] / vals["total"] * 100) if vals["total"] > 0 else 0
        dashboard_data[day] = {"attempts": attempts_counter[day], "avg_percentage": avg}
    return dashboard_data

def get_all_results(user_id):
    conn = get_db_connection()
    if conn is None:
        return []
    cursor = conn.cursor()
    query = """
    SELECT id, user_id, attempt_date, correct_list, total_questions
    FROM results
    WHERE user_id = ?
    ORDER BY attempt_date DESC;
    """
    cursor.execute(query, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    processed = []
    for row in rows:
        try:
            attempt_dt = datetime.datetime.strptime(row[2], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        processed.append((row[0], row[1], attempt_dt, row[3], row[4]))
    return processed

def show_dashboard(main_app, name=None):
    dash_win = ctk.CTkToplevel(main_app)
    dash_win.title("Dashboard")
    dash_win.geometry("800x600")
    
    header = ctk.CTkFrame(dash_win)
    header.pack(fill="x", pady=5)
    if name is not None:
        header_label = ctk.CTkLabel(header, text=f"Activity report for user {name}!", font=("Segoe UI", 20))
        header_label.pack(side="left", padx=10)
        if main_app.current_user and main_app.current_user["account_type"] == "Teacher":
            back_btn = ctk.CTkButton(header, text="Back", command=lambda: (dash_win.destroy(), main_app.open_user_browser()))
            back_btn.pack(side="right", padx=10)
    else:
        if main_app.current_user:
            header_label = ctk.CTkLabel(header, text=f"Welcome, {main_app.current_user['username']}!", font=("Segoe UI", 20))
            header_label.pack(side="left", padx=10)
        else:
            header_label = ctk.CTkLabel(header, text="Welcome!", font=("Segoe UI", 20))
            header_label.pack(side="left", padx=10)
    
    graph_frame = ctk.CTkFrame(dash_win, fg_color="#222222")
    graph_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    current_dt = SIMULATED_DATE if SIMULATED_DATE else datetime.datetime.now()
    data = get_dashboard_data(main_app.current_user["id"], current_dt)
    sorted_dates = sorted(data.keys())
    if len(sorted_dates) < 2:
        ctk.CTkLabel(graph_frame, text="Not enough data to display charts (min 2 days required).", font=("Segoe UI", 16)).pack(pady=20)
    else:
        date_labels = [d.strftime("%m-%d") for d in sorted_dates]
        attempts = [data[d]["attempts"] for d in sorted_dates]
        percentages = [data[d]["avg_percentage"] for d in sorted_dates]
        
        fig1 = Figure(figsize=(5, 4), dpi=100)
        ax1 = fig1.add_subplot(111)
        fig1.patch.set_facecolor("#222222")
        ax1.set_facecolor("#222222")
        for spine in ax1.spines.values():
            spine.set_color("white")
        ax1.bar(date_labels, attempts, color='royalblue')
        ax1.set_title("Attempts per Day", fontname="Segoe UI", fontsize=14, color="white")
        ax1.set_xlabel("Date", fontname="Segoe UI", fontsize=12, color="white")
        ax1.set_ylabel("Attempts", fontname="Segoe UI", fontsize=12, color="white")
        ax1.tick_params(axis='x', colors='white')
        ax1.tick_params(axis='y', colors='white')
        fig1.tight_layout()
        canvas1 = FigureCanvasTkAgg(fig1, master=graph_frame)
        canvas1.draw()
        canvas1.get_tk_widget().pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        fig2 = Figure(figsize=(5, 4), dpi=100)
        ax2 = fig2.add_subplot(111)
        fig2.patch.set_facecolor("#222222")
        ax2.set_facecolor("#222222")
        for spine in ax2.spines.values():
            spine.set_color("white")
        ax2.plot(date_labels, percentages, marker='o', color='darkgreen')
        ax2.set_title("Average Score (%) per Day", fontname="Segoe UI", fontsize=14, color="white")
        ax2.set_xlabel("Date", fontname="Segoe UI", fontsize=12, color="white")
        ax2.set_ylabel("Avg %", fontname="Segoe UI", fontsize=12, color="white")
        ax2.tick_params(axis='x', colors='white')
        ax2.tick_params(axis='y', colors='white')
        fig2.tight_layout()
        canvas2 = FigureCanvasTkAgg(fig2, master=graph_frame)
        canvas2.draw()
        canvas2.get_tk_widget().pack(side="right", fill="both", expand=True, padx=5, pady=5)
    
    footer = ctk.CTkFrame(dash_win)
    footer.pack(fill="x", pady=5)
    ctk.CTkLabel(footer, text="Dashboard Module", font=("Segoe UI", 12)).pack()

def show_past_results(main_app):
    past_win = ctk.CTkToplevel(main_app)
    past_win.title("Past Results")
    past_win.geometry("600x400")
    
    header = ctk.CTkFrame(past_win)
    header.pack(fill="x", pady=5)
    ctk.CTkLabel(header, text=f"Past Results for {main_app.current_user['username']}", font=("Segoe UI", 18)).pack(side="left", padx=10)
    
    scroll_frame = ctk.CTkScrollableFrame(past_win, width=500, height=250)
    scroll_frame.pack(padx=10, pady=10, fill="both", expand=True)
    
    results = get_all_results(main_app.current_user["id"])
    for row in results:
        attempt_dt = row[2]
        try:
            result_data = json.loads(row[3])
            correct = result_data.get("correct_count", 0)
        except Exception:
            correct = 0
        total = row[4]
        percentage = (correct / total * 100) if total > 0 else 0
        date_str = attempt_dt.strftime("%Y-%m-%d %H:%M:%S")
        text = f"Date: {date_str} | Score: {percentage:.0f}% ({correct}/{total})"
        ctk.CTkLabel(scroll_frame, text=text, font=("Segoe UI", 14)).pack(pady=5)
    
    footer = ctk.CTkFrame(past_win)
    footer.pack(fill="x", pady=10)
    ctk.CTkButton(footer, text="Close", command=past_win.destroy).pack(fill="x")

def get_all_users(search_query=None):
    conn = get_db_connection()
    if conn is None:
        return []
    cursor = conn.cursor()
    if search_query:
        cursor.execute("SELECT id, username, account_type FROM users WHERE username LIKE ?", (f"%{search_query}%",))
    else:
        cursor.execute("SELECT id, username, account_type FROM users")
    users = cursor.fetchall()
    conn.close()
    return [{"id": user[0], "username": user[1], "account_type": user[2]} for user in users]

def show_user_results(main_app, user):
    results_win = ctk.CTkToplevel(main_app)
    results_win.title(f"Past Results for {user['username']}")
    results_win.geometry("600x400")
    
    header = ctk.CTkFrame(results_win)
    header.pack(fill="x", pady=5)
    ctk.CTkLabel(header, text=f"Past Results for {user['username']}", font=("Segoe UI", 18)).pack(side="left", padx=10)
    
    scroll_frame = ctk.CTkScrollableFrame(results_win, width=500, height=250)
    scroll_frame.pack(padx=10, pady=10, fill="both", expand=True)
    
    results = get_all_results(user["id"])
    for row in results:
        attempt_dt = row[2]
        try:
            result_data = json.loads(row[3])
            correct = result_data.get("correct_count", 0)
        except Exception:
            correct = 0
        total = row[4]
        percentage = (correct / total * 100) if total > 0 else 0
        date_str = attempt_dt.strftime("%Y-%m-%d %H:%M:%S")
        text = f"Date: {date_str} | Score: {percentage:.0f}% ({correct}/{total})"
        ctk.CTkLabel(scroll_frame, text=text, font=("Segoe UI", 14)).pack(pady=5)
    
    footer = ctk.CTkFrame(results_win)
    footer.pack(fill="x", pady=10)
    ctk.CTkButton(footer, text="Close", command=results_win.destroy).pack(fill="x")

def show_user_browser(main_app):
    browser_win = ctk.CTkToplevel(main_app)
    browser_win.title("User Browser")
    browser_win.geometry("600x500")
    
    search_frame = ctk.CTkFrame(browser_win)
    search_frame.pack(fill="x", pady=5, padx=10)
    ctk.CTkLabel(search_frame, text="Search Users:", font=("Segoe UI", 14)).pack(side="left", padx=5)
    search_entry = ctk.CTkEntry(search_frame, placeholder_text="Enter username")
    search_entry.pack(side="left", padx=5, fill="x", expand=True)
    
    results_frame = ctk.CTkScrollableFrame(browser_win, width=580, height=350)
    results_frame.pack(padx=10, pady=10, fill="both", expand=True)
    
    def perform_search():
        for widget in results_frame.winfo_children():
            widget.destroy()
        query = search_entry.get().strip()
        users = get_all_users(query)
        if not users:
            ctk.CTkLabel(results_frame, text="No users found.", font=("Segoe UI", 14)).pack(pady=5)
        for user in users:
            user_frame = ctk.CTkFrame(results_frame)
            user_frame.pack(fill="x", pady=3, padx=5)
            info_text = f"Username: {user['username']} | Account Type: {user['account_type']}"
            ctk.CTkLabel(user_frame, text=info_text, font=("Segoe UI", 12)).pack(side="left", padx=5)
            ctk.CTkButton(user_frame, text="View Results", command=lambda u=user: show_user_results(main_app, u)).pack(side="right", padx=5)
    
    ctk.CTkButton(search_frame, text="Search", command=perform_search).pack(side="left", padx=5)
    
    def list_all_users():
        for widget in results_frame.winfo_children():
            widget.destroy()
        users = get_all_users()
        if not users:
            ctk.CTkLabel(results_frame, text="No users found.", font=("Segoe UI", 14)).pack(pady=5)
        for user in users:
            user_frame = ctk.CTkFrame(results_frame)
            user_frame.pack(fill="x", pady=3, padx=5)
            info_text = f"Username: {user['username']} | Account Type: {user['account_type']}"
            ctk.CTkLabel(user_frame, text=info_text, font=("Segoe UI", 12)).pack(side="left", padx=5)
            ctk.CTkButton(user_frame, text="View Results", command=lambda u=user: show_user_results(main_app, u)).pack(side="right", padx=5)
    
    list_all_users()
    
    footer = ctk.CTkFrame(browser_win)
    footer.pack(fill="x", pady=5)
    ctk.CTkButton(footer, text="Close", command=browser_win.destroy).pack(pady=5)

# -------------------- Quiz Module --------------------

def get_all_quizzes():
    """
    Reads all quiz JSON files from the QUIZ_DIR and returns a list of quiz dictionaries.
    """
    quizzes = []
    for filename in os.listdir(QUIZ_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(QUIZ_DIR, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    quiz_data = json.load(f)
                quiz_data["file_path"] = filepath  # Save file path if needed
                quizzes.append(quiz_data)
            except json.JSONDecodeError:
                print(f"Error reading quiz file {filename}")
    return quizzes

def upload_quiz():
    """
    Opens a file dialog for the user to select a quiz JSON file, and then copies it to QUIZ_DIR.
    """
    file_path = filedialog.askopenfilename(title="Select Quiz JSON", filetypes=[("JSON Files", "*.json")])
    if file_path:
        dest_path = os.path.join(QUIZ_DIR, os.path.basename(file_path))
        if os.path.exists(dest_path):
            messagebox.showerror("Error", "A quiz with this name already exists!")
            return
        try:
            with open(file_path, "r", encoding="utf-8") as src:
                quiz_data = src.read()
            with open(dest_path, "w", encoding="utf-8") as dst:
                dst.write(quiz_data)
            messagebox.showinfo("Upload", "Quiz uploaded successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to upload quiz: {e}")

def show_quiz_browser(main_app):
    """
    Displays the Quiz Browser window with:
      - 'Upload Quiz' button at the top
      - A search frame below it for filtering quizzes by name or author
      - A scrollable frame (fixed height) in the middle
      - A 'Close' button at the bottom
      - Automatic refresh of the quiz list after uploading or searching
    """
    qb_win = ctk.CTkToplevel(main_app)
    qb_win.title("Quiz Browser")
    qb_win.geometry("600x550")  # Slightly larger to accommodate all widgets

    def refresh_quiz_list(search_query=""):
        for widget in scroll_frame.winfo_children():
            widget.destroy()
        quizzes = get_all_quizzes()
        if search_query:
            search_query_lower = search_query.lower()
            quizzes = [q for q in quizzes if search_query_lower in q.get("name", "").lower() or 
                       search_query_lower in q.get("author", "").lower()]
        if not quizzes:
            ctk.CTkLabel(scroll_frame, text="No quizzes available.", font=("Segoe UI", 14)).pack(pady=10)
        else:
            for quiz in quizzes:
                quiz_frame = ctk.CTkFrame(scroll_frame)
                quiz_frame.pack(fill="x", pady=5, padx=5)
                info_text = (
                    f"Name: {quiz.get('name', 'N/A')} | "
                    f"Author: {quiz.get('author', 'N/A')} | "
                    f"Questions: {len(quiz.get('questions', []))} | "
                    f"Time: {quiz.get('time_limit', 'N/A')} mins"
                )
                ctk.CTkLabel(quiz_frame, text=info_text, font=("Segoe UI", 12)).pack(side="left", padx=5)
                ctk.CTkButton(
                    quiz_frame, text="Launch Quiz",
                    command=lambda q=quiz: launch_quiz(main_app, q)
                ).pack(side="right", padx=5)

    def upload_and_refresh():
        upload_quiz()
        refresh_quiz_list(search_entry.get().strip())

    # Top: Upload Quiz button
    upload_btn = ctk.CTkButton(qb_win, text="Upload Quiz", command=upload_and_refresh)
    upload_btn.pack(side="top", pady=5)

    # Search frame below upload button.
    search_frame = ctk.CTkFrame(qb_win)
    search_frame.pack(side="top", fill="x", pady=5, padx=10)
    search_entry = ctk.CTkEntry(search_frame, placeholder_text="Search by quiz name or author")
    search_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
    ctk.CTkButton(search_frame, text="Search", command=lambda: refresh_quiz_list(search_entry.get().strip())).pack(side="left")

    # Middle: Fixed-height scrollable frame
    scroll_frame = ctk.CTkScrollableFrame(qb_win, width=580, height=350)
    scroll_frame.pack(side="top", fill="x", padx=10, pady=(0,10))

    # Bottom: Footer with only the Close button
    footer = ctk.CTkFrame(qb_win)
    footer.pack(side="bottom", fill="x", pady=5)
    ctk.CTkButton(footer, text="Close", command=qb_win.destroy).pack(side="right", padx=5, pady=5)

    refresh_quiz_list()

def launch_quiz(main_app, quiz):
    launch_win = ctk.CTkToplevel(main_app)
    launch_win.title("Launch Quiz")
    launch_win.geometry("400x300")
    info_text = (f"Quiz: {quiz.get('name', 'N/A')}\n"
                 f"Author: {quiz.get('author', 'N/A')}\n"
                 f"Questions: {len(quiz.get('questions', []))}\n"
                 f"Time Limit: {quiz.get('time_limit', 'N/A')} mins")
    ctk.CTkLabel(launch_win, text=info_text, font=("Segoe UI", 14)).pack(pady=20)
    ctk.CTkButton(launch_win, text="Start Quiz", command=lambda: [launch_win.destroy(), execute_quiz(main_app, quiz)]).pack(pady=10)
    ctk.CTkButton(launch_win, text="Cancel", command=launch_win.destroy).pack(pady=10)

def execute_quiz(main_app, quiz):
    exec_win = ctk.CTkToplevel(main_app)
    exec_win.title("Quiz Execution")
    exec_win.geometry("600x500")
    
    questions = quiz.get("questions", [])
    total_questions = len(questions)
    user_answers = {}
    current_q_index = [0]  # Mutable holder for current index
    
    time_limit_minutes = quiz.get("time_limit", 0)
    total_time_sec = int(time_limit_minutes * 60) if time_limit_minutes else 0
    start_time = datetime.datetime.now()
    
    timer_label = ctk.CTkLabel(exec_win, text="", font=("Segoe UI", 14))
    timer_label.pack(pady=5)
    
    def update_timer():
        if total_time_sec > 0:
            elapsed = (datetime.datetime.now() - start_time).total_seconds()
            remaining = max(0, total_time_sec - int(elapsed))
            mins, secs = divmod(remaining, 60)
            timer_label.configure(text=f"Time Remaining: {int(mins):02d}:{int(secs):02d}")
            if remaining <= 0:
                finish_quiz()
            else:
                exec_win.after(1000, update_timer)
    if total_time_sec > 0:
        update_timer()
    
    content_frame = ctk.CTkFrame(exec_win)
    content_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    image_label = None
    
    question_label = ctk.CTkLabel(content_frame, text="", font=("Segoe UI", 16))
    question_label.pack(pady=10)
    
    options_frame = ctk.CTkFrame(content_frame)
    options_frame.pack(pady=10)
    
    answer_var = ctk.StringVar()
    
    def display_question(index):
        nonlocal image_label
        if image_label is not None:
            image_label.destroy()
            image_label = None
        
        if index < total_questions:
            q = questions[index]
            question_text = q.get("question", "No question text provided.")
            question_label.configure(text=question_text)
            for widget in options_frame.winfo_children():
                widget.destroy()
            if "image" in q and q["image"]:
                try:
                    img = Image.open(q["image"])
                    max_width = 400
                    if img.width > max_width:
                        ratio = max_width / img.width
                        img = img.resize((max_width, int(img.height * ratio)), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    image_label = ctk.CTkLabel(content_frame, image=photo, text="")
                    image_label.image = photo
                    image_label.pack(pady=5)
                except Exception as e:
                    print(f"Error loading image: {e}")
            options = q.get("options", [])
            if options:
                answer_var.set("")
                for opt in options:
                    ctk.CTkRadioButton(options_frame, text=opt, variable=answer_var, value=opt).pack(anchor="w", pady=2)
            else:
                entry = ctk.CTkEntry(options_frame, placeholder_text="Your answer here")
                entry.pack(fill="x", pady=2)
                options_frame.entry = entry
        else:
            finish_quiz()
    
    def next_question():
        index = current_q_index[0]
        q = questions[index]
        if q.get("options", []):
            user_answers[index] = answer_var.get()
        else:
            user_answers[index] = options_frame.entry.get()
        current_q_index[0] += 1
        display_question(current_q_index[0])
    
    def finish_quiz():
        # Ensure the answer of the current question is stored, if not already.
        if current_q_index[0] < total_questions:
            q = questions[current_q_index[0]]
            if q.get("options", []):
                user_answers[current_q_index[0]] = answer_var.get()
            else:
                user_answers[current_q_index[0]] = options_frame.entry.get()
        correct_count = 0
        for i, q in enumerate(questions):
            if user_answers.get(i, "").strip().lower() == q.get("answer", "").strip().lower():
                correct_count += 1
        result_data = {"correct_count": correct_count, "total_questions": total_questions}
        record_quiz_result(main_app.current_user["id"], json.dumps(result_data), total_questions)
        messagebox.showinfo("Quiz Completed", f"You scored {correct_count} out of {total_questions}. Your result has been stored in Past Results.")
        exec_win.destroy()
    
    nav_frame = ctk.CTkFrame(exec_win)
    nav_frame.pack(fill="x", pady=10)
    ctk.CTkButton(nav_frame, text="Next", command=next_question).pack(side="right", padx=5)
    ctk.CTkButton(nav_frame, text="Finish", command=finish_quiz).pack(side="right", padx=5)
    
    display_question(0)

# -------------------- End Quiz Module --------------------

def change_username(main_app, new_username):
    if len(new_username) < 5 or len(new_username) > 16:
        messagebox.showerror("Error", "Username must be between 5 and 16 characters.")
        return
    conn = get_db_connection()
    if conn is None:
        messagebox.showerror("Error", "Database connection error.")
        return
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (new_username,))
    if cursor.fetchone():
        messagebox.showerror("Error", "Username already exists. Please choose another.")
        conn.close()
        return
    cursor.execute("UPDATE users SET username = ? WHERE id = ?", (new_username, main_app.current_user["id"]))
    conn.commit()
    conn.close()
    main_app.current_user["username"] = new_username
    messagebox.showinfo("Success", "Username changed successfully!")

def change_password(main_app, new_password, confirm_password):
    if len(new_password) < 6:
        messagebox.showerror("Error", "New password must be at least 6 characters long.")
        return
    if new_password != confirm_password:
        messagebox.showerror("Error", "Password confirmation does not match.")
        return
    conn = get_db_connection()
    if conn is None:
        messagebox.showerror("Error", "Database connection error.")
        return
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM users WHERE id = ?", (main_app.current_user["id"],))
    row = cursor.fetchone()
    if not row:
        messagebox.showerror("Error", "User not found in database.")
        conn.close()
        return
    current_hashed = row[0]
    if bcrypt.checkpw(new_password.encode('utf-8'), current_hashed if isinstance(current_hashed, bytes) else current_hashed.encode('utf-8')):
        messagebox.showerror("Error", "New password cannot be the same as the old password.")
        conn.close()
        return
    new_hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
    cursor.execute("UPDATE users SET password = ? WHERE id = ?", (new_hashed, main_app.current_user["id"]))
    conn.commit()
    conn.close()
    messagebox.showinfo("Success", "Password changed successfully!")

def show_manage_account(main_app):
    manage_win = ctk.CTkToplevel(main_app)
    manage_win.title("Manage Account")
    manage_win.geometry("400x400")

    username_frame = ctk.CTkFrame(manage_win)
    username_frame.pack(fill="x", padx=10, pady=10)
    ctk.CTkLabel(username_frame, text="Change Username", font=("Segoe UI", 16)).pack(pady=5)
    new_username_entry = ctk.CTkEntry(username_frame, placeholder_text="New Username")
    new_username_entry.pack(pady=5, fill="x")
    ctk.CTkButton(username_frame, text="Change Username", command=lambda: change_username(main_app, new_username_entry.get().strip())).pack(pady=5)

    password_frame = ctk.CTkFrame(manage_win)
    password_frame.pack(fill="x", padx=10, pady=10)
    ctk.CTkLabel(password_frame, text="Change Password", font=("Segoe UI", 16)).pack(pady=5)
    new_password_entry = ctk.CTkEntry(password_frame, placeholder_text="New Password", show="*")
    new_password_entry.pack(pady=5, fill="x")
    confirm_password_entry = ctk.CTkEntry(password_frame, placeholder_text="Confirm New Password", show="*")
    confirm_password_entry.pack(pady=5, fill="x")
    ctk.CTkButton(password_frame, text="Change Password", command=lambda: change_password(main_app, new_password_entry.get(), confirm_password_entry.get())).pack(pady=5)

    footer = ctk.CTkFrame(manage_win)
    footer.pack(fill="x", pady=10)
    ctk.CTkButton(footer, text="Close", command=manage_win.destroy).pack(pady=5)

class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Main Menu")
        self.geometry("400x500")
        self.resizable(False, False)
        
        self.current_user = None
        
        ctk.CTkLabel(self, text="Main Menu", font=("Arial", 20)).pack(pady=20)
        ctk.CTkButton(self, text="Login / Sign Up", command=self.open_auth).pack(pady=10)
        ctk.CTkButton(self, text="Dashboard", command=self.open_dashboard).pack(pady=10)
        ctk.CTkButton(self, text="Past Results", command=self.open_past_results).pack(pady=10)
        ctk.CTkButton(self, text="Quiz Browser", command=self.open_quiz_browser).pack(pady=10)
        ctk.CTkButton(self, text="User Browser (Teachers Only)", command=self.open_user_browser).pack(pady=10)
        ctk.CTkButton(self, text="Manage Account", command=self.open_manage_account).pack(pady=10)
        ctk.CTkButton(self, text="Sign Out", command=self.sign_out).pack(pady=10)
        ctk.CTkButton(self, text="Simulate Quiz Run", command=self.simulate_quiz_run).pack(pady=10)
    
    def open_auth(self):
        LoginApp(self)

    def check_login_status(self):
        if not self.current_user:
            messagebox.showerror("Access Denied", "You must be logged in to access this section.")
            return False
        return True

    def open_dashboard(self):
        if self.check_login_status():
            show_dashboard(self, name=None)

    def open_past_results(self):
        if self.check_login_status():
            show_past_results(self)

    def open_quiz_browser(self):
        if self.check_login_status():
            show_quiz_browser(self)

    def open_user_browser(self):
        if self.check_login_status():
            if self.current_user["account_type"] == "Teacher":
                show_user_browser(self)
            else:
                messagebox.showerror("Access Denied", "Only accessible by teachers.")

    def open_manage_account(self):
        if self.check_login_status():
            show_manage_account(self)

    def sign_out(self):
        if not self.current_user:
            messagebox.showerror("Error", "You must be logged in before signing out.")
        else:
            self.current_user = None
            messagebox.showinfo("Sign Out", "You have been signed out.")

    def simulate_quiz_run(self):
        if not self.check_login_status():
            return
        import random
        total_questions = random.randint(3, 10)
        correct_count = random.randint(0, total_questions)
        result_data = {"correct_count": correct_count, "total_questions": total_questions}
        if record_quiz_result(self.current_user["id"], json.dumps(result_data), total_questions):
            messagebox.showinfo("Quiz Recorded", f"Recorded: {correct_count} correct out of {total_questions}")
        else:
            messagebox.showerror("Error", "Failed to record test result.")

class LoginApp(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Login / Sign Up")
        self.geometry("400x400")
        self.resizable(False, False)
        
        self.master = master
        self.is_sign_up_mode = False
        self.password_visible = ctk.BooleanVar(value=False)
        self.frame = None
        self.create_ui()
    
    def create_ui(self):
        if self.frame:
            self.frame.destroy()
        self.frame = ctk.CTkFrame(self)
        self.frame.pack(pady=50, padx=20, fill="both", expand=True)
        
        title = "Sign Up" if self.is_sign_up_mode else "Login"
        ctk.CTkLabel(self.frame, text=title, font=("Arial", 20)).pack(pady=10)
        
        self.username_entry = ctk.CTkEntry(self.frame, placeholder_text="Username")
        self.username_entry.pack(pady=5)
        
        self.password_entry = ctk.CTkEntry(self.frame, placeholder_text="Password", show="*")
        self.password_entry.pack(pady=5)
        
        ctk.CTkCheckBox(self.frame, text="Show Password", variable=self.password_visible, command=self.toggle_password).pack(pady=5)
        
        if self.is_sign_up_mode:
            ctk.CTkLabel(self.frame, text="Select Account Type:").pack(pady=5)
            self.account_type_var = ctk.StringVar(value="Student")
            self.account_type_menu = ctk.CTkOptionMenu(self.frame, variable=self.account_type_var, values=["Student", "Teacher"])
            self.account_type_menu.pack(pady=5)
        
        action_text = "Sign Up" if self.is_sign_up_mode else "Login"
        ctk.CTkButton(self.frame, text=action_text, command=self.handle_authentication).pack(pady=5)
        
        switch_text = "Already have an account? Login" if self.is_sign_up_mode else "Don't have an account? Sign Up"
        ctk.CTkButton(self.frame, text=switch_text, fg_color="transparent", text_color="blue", command=self.switch_mode).pack(pady=5)
    
    def toggle_password(self):
        self.password_entry.configure(show="" if self.password_visible.get() else "*")
    
    def switch_mode(self):
        self.is_sign_up_mode = not self.is_sign_up_mode
        self.create_ui()
    
    def handle_authentication(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not (5 <= len(username) <= 16):
            messagebox.showerror("Error", "Username must be between 5 and 16 characters.")
            return
        if len(password) < 6:
            messagebox.showerror("Error", "Password must be at least 6 characters long.")
            return
        
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        
        if self.is_sign_up_mode:
            account_type = self.account_type_var.get()
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            try:
                cursor.execute("INSERT INTO users (username, password, account_type) VALUES (?, ?, ?)",
                               (username, hashed_password, account_type))
                conn.commit()
                messagebox.showinfo("Success", f"Account Created Successfully as {account_type}!")
                self.switch_mode()
            except sqlite3.IntegrityError:
                messagebox.showerror("Error", "Username already exists.")
        else:
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            if user and bcrypt.checkpw(password.encode('utf-8'),
                                       user[2] if isinstance(user[2], bytes) else user[2].encode('utf-8')):
                self.master.current_user = {"username": user[1], "account_type": user[3], "id": user[0]}
                messagebox.showinfo("Login Successful", f"Welcome back, {user[1]}! Account Type: {user[3]}")
                self.destroy()
            else:
                messagebox.showerror("Error", "Invalid Username or Password")
        
        conn.close()

if __name__ == "__main__":
    create_database()
    app = MainApp()
    app.mainloop()
