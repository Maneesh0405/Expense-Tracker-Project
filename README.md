# Expense Tracker

A simple expense tracking application built with Python (Flask) and SQLite. This is a Python implementation of a typical MERN stack expense tracker.

## Features

- Add, view, edit, and delete expenses
- Categorize expenses
- View total expenses
- Simple and clean user interface

## Technologies Used

- Python 3.x
- Flask (Web Framework)
- SQLite (Database)
- HTML/CSS/JavaScript (Frontend)

## Prerequisites

Make sure you have Python 3.x installed on your system.

## Installation

1. Clone or download this repository

2. Navigate to the project directory:
   ```
   cd path/to/expense-tracker
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

## Running the Application

1. Start the Flask server:
   ```
   python app.py
   ```

2. Open `index.html` in your web browser to use the application

## API Endpoints

- `GET /api/expenses` - Get all expenses
- `POST /api/expenses` - Add a new expense
- `PUT /api/expenses/<id>` - Update an expense
- `DELETE /api/expenses/<id>` - Delete an expense

## Project Structure

```
expense-tracker/
│
├── app.py              # Flask application
├── requirements.txt    # Python dependencies
├── index.html          # Frontend interface
├── expenses.db         # SQLite database (created automatically)
└── README.md           # This file
```

## Usage

1. Enter the amount, description, and category of your expense
2. Click "Add Expense" to save it
3. View your expenses in the list below
4. Edit or delete expenses using the buttons next to each item
5. See your total expenses at the top

## License

This project is open source and available under the MIT License.