# OCR Computer Science H446 Coursework Project

## Overview
This project is my submission for the OCR H446 Computer Science NEA. It’s a complete learning and quiz platform that brings together user accounts, quizzes, analytics, and a clean UI. I built it with a focus on modular design so the codebase is easy to understand, maintain, and expand.

The system features multiple pages (login, dashboard, quiz browser, teacher tools, etc.) that all connect through a main window, making the flow feel like a proper application rather than a collection of scripts.

## Features
### Authentication System
- Users can create accounts and log in
- Passwords are securely hashed
- Includes an account management page
- Supports signing in/out without restarting the program

### Dashboard
- Shows personalised statistics for each user
- Displays:
  - Success rate (%)
  - Average attempts per question
  - Daily performance over time
- Includes a graph that visualises 2–5 days of user results

### Quiz Browser
- Allows users to search and browse quizzes
- Includes filtering options (topic, difficulty)
- Quizzes can be started or resumed

### Teacher User Browser
- Teachers can view all user accounts
- Inspect student performance and statistics
- Basic account management tools for teachers

### Analytics System
- Tracks quiz attempts and outcomes
- Calculates key statistics automatically
- Stores daily performance logs for the dashboard graph

### Database Module
Stores:
- User accounts
- Quiz data
- Attempt history
- Analytics summaries

The database structure was designed to be easy to edit and expand if new features are added later.

## Project Architecture
/project_root
│
├── main.py                # Main entry point
├── database.py            # Data storage and loading
├── auth.py                # Login, sign-up, account settings
├── dashboard.py           # Stats and analytics logic
├── quiz_browser.py        # Quiz searching and browsing
├── user_browser.py        # Teacher-only tools
│
├── ui/                    # All UI windows
│   ├── login_window.py
│   ├── dashboard_window.py
│   ├── quiz_browser_window.py
│   ├── user_browser_window.py
│   ├── manage_account_window.py
│   └── components/        # Reusable UI elements
│
├── assets/                # Icons/images
├── data/                  # Database files / logs
└── docs/                  # Flowcharts, diagrams, notes

## Dashboard Graph
The dashboard includes a small performance graph that updates automatically based on saved data. It shows between 2 and 5 days of results, depending on how long the user has been active.

The graph visualises:
- Attempts per day
- Correct vs incorrect answers
- Success rate (%)

## Testing
I tested the project through:
- Unit tests for the more important logic (database, analytics, authentication)
- Manual testing of the UI to make sure all windows link together correctly
- Checking analytics results to make sure success rates and averages were calculated properly

## How to Run
1. Install the required Python packages:
pip install -r requirements.txt

2. Start the program:
python main.py

3. Use the UI to create an account, log in, and explore the system.

## Possible Future Improvements
Here are some features I’d like to add if I continue working on this:
- AI-powered quiz recommendations
- Dynamic question difficulty
- Teacher/admin quiz creation tools
- Exportable reports (CSV, PDF)
- A more polished, modern UI

## Documentation
All design notes, diagrams, and planning documents are stored in the docs/ folder.
