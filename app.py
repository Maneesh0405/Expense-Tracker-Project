from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
import os
import hashlib
import io
import base64
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import numpy as np
from collections import defaultdict

# For PDF generation (optional dependency)
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import Table, TableStyle
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("Warning: reportlab not available. PDF generation will be disabled.")

app = Flask(__name__, static_folder='.')
CORS(app)

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'

# Check if running on Vercel
if os.environ.get('VERCEL'):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/expenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat()
        }

# Expense model
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'amount': self.amount,
            'description': self.description,
            'category': self.category,
            'date': self.date.isoformat()
        }

# Income model
class Income(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'amount': self.amount,
            'description': self.description,
            'date': self.date.isoformat()
        }

# Create tables
with app.app_context():
    db.create_all()

# Utility function to hash passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Serve the frontend
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

def get_current_user_id():
    user_id = request.headers.get('User-Id')
    if not user_id:
        # For backward compatibility or testing, unauthenticated access might be allowed 
        # but for this specific fix we want to enforce it or return None
        return None
    try:
        return int(user_id)
    except ValueError:
        return None

@app.route('/<path:path>')
def static_files(path):
    if os.path.exists(os.path.join('.', path)):
        return send_from_directory('.', path)
    else:
        return send_from_directory('.', 'index.html')  # For SPA routing

# Auth Routes
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    
    # Validate required fields
    if not all(key in data for key in ('username', 'email', 'password')):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Check if user already exists
    if User.query.filter_by(username=data['username']).first() or User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Username or email already exists'}), 400
    
    # Create new user
    user = User(
        username=data['username'],
        email=data['email'],
        password_hash=hash_password(data['password'])
    )
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({'message': 'User registered successfully'}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    
    # Validate required fields
    if not all(key in data for key in ('username', 'password')):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Find user
    user = User.query.filter_by(username=data['username']).first()
    if not user or user.password_hash != hash_password(data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    return jsonify({
        'message': 'Login successful',
        'user': user.to_dict()
    })

# Expense Routes
@app.route('/api/expenses', methods=['GET'])
def get_expenses():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
        
    expenses = Expense.query.filter_by(user_id=user_id).all()
    return jsonify([expense.to_dict() for expense in expenses])

@app.route('/api/expenses', methods=['POST'])
def add_expense():
    data = request.get_json()
    
    # Validate required fields
    if not all(key in data for key in ('amount', 'description', 'category')):
        return jsonify({'error': 'Missing required fields'}), 400
    
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
        
    expense = Expense(
        user_id=user_id,
        amount=data['amount'],
        description=data['description'],
        category=data['category']
    )
    
    # Handle date if provided
    if 'date' in data and data['date']:
        try:
            # Handle different date formats
            if isinstance(data['date'], str):
                if 'Z' in data['date']:
                    expense.date = datetime.fromisoformat(data['date'].replace('Z', '+00:00'))
                else:
                    expense.date = datetime.fromisoformat(data['date'])
            else:
                expense.date = data['date']
        except (ValueError, TypeError) as e:
            # Use default date if parsing fails
            pass
    
    db.session.add(expense)
    db.session.commit()
    
    return jsonify(expense.to_dict()), 201

@app.route('/api/expenses/<int:id>', methods=['PUT'])
def update_expense(id):
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    expense = Expense.query.filter_by(id=id, user_id=user_id).first_or_404()
    data = request.get_json()
    
    expense.amount = data.get('amount', expense.amount)
    expense.description = data.get('description', expense.description)
    expense.category = data.get('category', expense.category)
    # Ensure date is updated if provided
    if 'date' in data:
        try:
            # Handle different date formats
            if isinstance(data['date'], str):
                if 'Z' in data['date']:
                    expense.date = datetime.fromisoformat(data['date'].replace('Z', '+00:00'))
                else:
                    expense.date = datetime.fromisoformat(data['date'])
            else:
                expense.date = data['date']
        except (ValueError, TypeError) as e:
            # Keep existing date if parsing fails
            pass
    
    db.session.commit()
    
    return jsonify(expense.to_dict())

@app.route('/api/expenses/<int:id>', methods=['DELETE'])
def delete_expense(id):
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    expense = Expense.query.filter_by(id=id, user_id=user_id).first_or_404()
    db.session.delete(expense)
    db.session.commit()
    
    return jsonify({'message': 'Expense deleted successfully'})

# Income Routes
@app.route('/api/income', methods=['GET'])
def get_income():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    incomes = Income.query.filter_by(user_id=user_id).all()
    return jsonify([income.to_dict() for income in incomes])

@app.route('/api/income', methods=['POST'])
def add_income():
    data = request.get_json()
    
    # Validate required fields
    if not all(key in data for key in ('amount', 'description')):
        return jsonify({'error': 'Missing required fields'}), 400
    
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
        
    income = Income(
        user_id=user_id,
        amount=data['amount'],
        description=data['description']
    )
    
    # Handle date if provided
    if 'date' in data and data['date']:
        try:
            # Handle different date formats
            if isinstance(data['date'], str):
                if 'Z' in data['date']:
                    income.date = datetime.fromisoformat(data['date'].replace('Z', '+00:00'))
                else:
                    income.date = datetime.fromisoformat(data['date'])
            else:
                income.date = data['date']
        except (ValueError, TypeError) as e:
            # Use default date if parsing fails
            pass
    
    db.session.add(income)
    db.session.commit()
    
    return jsonify(income.to_dict()), 201

@app.route('/api/income/<int:id>', methods=['PUT'])
def update_income(id):
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    income = Income.query.filter_by(id=id, user_id=user_id).first_or_404()
    data = request.get_json()
    
    income.amount = data.get('amount', income.amount)
    income.description = data.get('description', income.description)
    # Ensure date is updated if provided
    if 'date' in data:
        try:
            # Handle different date formats
            if isinstance(data['date'], str):
                if 'Z' in data['date']:
                    income.date = datetime.fromisoformat(data['date'].replace('Z', '+00:00'))
                else:
                    income.date = datetime.fromisoformat(data['date'])
            else:
                income.date = data['date']
        except (ValueError, TypeError) as e:
            # Keep existing date if parsing fails
            pass
    
    db.session.commit()
    
    return jsonify(income.to_dict())

@app.route('/api/income/<int:id>', methods=['DELETE'])
def delete_income(id):
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    income = Income.query.filter_by(id=id, user_id=user_id).first_or_404()
    db.session.delete(income)
    db.session.commit()
    
    return jsonify({'message': 'Income deleted successfully'})

# Dashboard data
@app.route('/api/dashboard', methods=['GET'])
def get_dashboard_data():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    # Get all expenses and income for the user
    expenses = Expense.query.filter_by(user_id=user_id).all()
    incomes = Income.query.filter_by(user_id=user_id).all()
    
    # Calculate totals
    total_expenses = sum(expense.amount for expense in expenses)
    total_income = sum(income.amount for income in incomes)
    balance = total_income - total_expenses
    
    # Expenses by category
    category_totals = {}
    for expense in expenses:
        if expense.category in category_totals:
            category_totals[expense.category] += expense.amount
        else:
            category_totals[expense.category] = expense.amount
    
    # Recent transactions (last 5)
    recent_expenses = Expense.query.filter_by(user_id=user_id).order_by(Expense.date.desc()).limit(5).all()
    recent_income = Income.query.filter_by(user_id=user_id).order_by(Income.date.desc()).limit(5).all()
    
    # Combine and sort recent transactions
    all_recent = []
    for expense in recent_expenses:
        all_recent.append({
            'type': 'expense',
            'amount': expense.amount,
            'description': expense.description,
            'category': expense.category,
            'date': expense.date.isoformat()
        })
    
    for income in recent_income:
        all_recent.append({
            'type': 'income',
            'amount': income.amount,
            'description': income.description,
            'category': 'Income',
            'date': income.date.isoformat()
        })
    
    # Sort by date
    all_recent.sort(key=lambda x: x['date'], reverse=True)
    all_recent = all_recent[:5]  # Limit to 5 most recent
    
    return jsonify({
        'balance': balance,
        'totalIncome': total_income,
        'totalExpenses': total_expenses,
        'categoryTotals': category_totals,
        'recentTransactions': all_recent
    })

# Generate pie chart for expenses by category
@app.route('/api/chart/expense-categories', methods=['GET'])
def get_expense_categories_chart():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'image': None})
    expenses = Expense.query.filter_by(user_id=user_id).all()
    
    # Group expenses by category
    category_totals = {}
    for expense in expenses:
        if expense.category in category_totals:
            category_totals[expense.category] += expense.amount
        else:
            category_totals[expense.category] = expense.amount
    
    if not category_totals:
        return jsonify({'image': None})
    
    # Create pie chart
    categories = list(category_totals.keys())
    amounts = list(category_totals.values())
    
    # Define colors for each category
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9']
    
    plt.figure(figsize=(10, 8))
    plt.pie(amounts, labels=categories, autopct='%1.1f%%', colors=colors[:len(categories)], startangle=90)
    plt.title('Expenses by Category', fontsize=16, pad=20)
    plt.axis('equal')
    
    # Save plot to a PNG image in memory
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', bbox_inches='tight')
    img_buffer.seek(0)
    
    # Encode the image in base64
    img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
    
    # Close the figure to free memory
    plt.close()
    
    return jsonify({'image': img_base64})

# Generate pie chart for income by source/description
@app.route('/api/chart/income-sources', methods=['GET'])
def get_income_sources_chart():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'image': None})
    incomes = Income.query.filter_by(user_id=user_id).all()
    
    # Group income by description/source
    income_sources = {}
    for income in incomes:
        source = income.description if income.description else 'Unspecified'
        if source in income_sources:
            income_sources[source] += income.amount
        else:
            income_sources[source] = income.amount
    
    if not income_sources:
        return jsonify({'image': None})
    
    # Create pie chart
    sources = list(income_sources.keys())
    amounts = list(income_sources.values())
    
    # Define colors for each source
    colors = ['#4cc9f0', '#4361ee', '#3a0ca3', '#7209b7', '#f72585', '#4895ef', '#4cc9f0', '#f8961e', '#90be6d', '#f9c74f']
    
    plt.figure(figsize=(10, 8))
    plt.pie(amounts, labels=sources, autopct='%1.1f%%', colors=colors[:len(sources)], startangle=90)
    plt.title('Income by Source', fontsize=16, pad=20)
    plt.axis('equal')
    
    # Save plot to a PNG image in memory
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', bbox_inches='tight')
    img_buffer.seek(0)
    
    # Encode the image in base64
    img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
    
    # Close the figure to free memory
    plt.close()
    
    return jsonify({'image': img_base64})

# Generate bar chart for income by month
@app.route('/api/chart/income-by-month', methods=['GET'])
def get_income_by_month_chart():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'image': None})
    incomes = Income.query.filter_by(user_id=user_id).all()
    
    if not incomes:
        return jsonify({'image': None})
    
    # Group income by month
    monthly_income = defaultdict(float)
    for income in incomes:
        month_key = income.date.strftime('%Y-%m')
        monthly_income[month_key] += income.amount
    
    if not monthly_income:
        return jsonify({'image': None})
    
    # Sort by month
    months = sorted(monthly_income.keys())
    amounts = [monthly_income[month] for month in months]
    
    # Create bar chart
    plt.figure(figsize=(12, 6))
    bars = plt.bar(range(len(months)), amounts, color='#4cc9f0')
    plt.xlabel('Month')
    plt.ylabel('Income ($)')
    plt.title('Monthly Income')
    plt.xticks(range(len(months)), months, rotation=45)
    
    # Add value labels on bars
    for i, bar in enumerate(bars):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'${amounts[i]:.2f}',
                ha='center', va='bottom')
    
    plt.tight_layout()
    
    # Save plot to a PNG image in memory
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', bbox_inches='tight')
    img_buffer.seek(0)
    
    # Encode the image in base64
    img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
    
    # Close the figure to free memory
    plt.close()
    
    return jsonify({'image': img_base64})

# Generate line chart for expense trends
@app.route('/api/chart/expense-trends', methods=['GET'])
def get_expense_trends_chart():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'image': None})
    expenses = Expense.query.filter_by(user_id=user_id).all()
    
    if not expenses:
        return jsonify({'image': None})
    
    # Group expenses by month
    monthly_expenses = defaultdict(float)
    for expense in expenses:
        month_key = expense.date.strftime('%Y-%m')
        monthly_expenses[month_key] += expense.amount
    
    if not monthly_expenses:
        return jsonify({'image': None})
    
    # Sort by month
    months = sorted(monthly_expenses.keys())
    amounts = [monthly_expenses[month] for month in months]
    
    # Create line chart
    plt.figure(figsize=(12, 6))
    plt.plot(range(len(months)), amounts, marker='o', linewidth=2, markersize=8, color='#f72585')
    plt.fill_between(range(len(months)), amounts, alpha=0.3, color='#f72585')
    plt.xlabel('Month')
    plt.ylabel('Expenses ($)')
    plt.title('Monthly Expense Trends')
    plt.xticks(range(len(months)), months, rotation=45)
    plt.grid(True, alpha=0.3)
    
    # Add value labels on points
    for i, amount in enumerate(amounts):
        plt.annotate(f'${amount:.2f}',
                    (i, amount),
                    textcoords="offset points",
                    xytext=(0,10),
                    ha='center')
    
    plt.tight_layout()
    
    # Save plot to a PNG image in memory
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', bbox_inches='tight')
    img_buffer.seek(0)
    
    # Encode the image in base64
    img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
    
    # Close the figure to free memory
    plt.close()
    
    return jsonify({'image': img_base64})

# Generate daily expense tracking chart
@app.route('/api/chart/daily-expenses', methods=['GET'])
def get_daily_expenses_chart():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'image': None})
    expenses = Expense.query.filter_by(user_id=user_id).all()
    
    if not expenses:
        return jsonify({'image': None})
    
    # Group expenses by date
    daily_expenses = defaultdict(float)
    for expense in expenses:
        date_key = expense.date.strftime('%Y-%m-%d')
        daily_expenses[date_key] += expense.amount
    
    if not daily_expenses:
        return jsonify({'image': None})
    
    # Sort by date and get last 7 days
    dates = sorted(daily_expenses.keys())[-7:]  # Last 7 days
    amounts = [daily_expenses[date] for date in dates]
    
    # Create bar chart
    plt.figure(figsize=(12, 6))
    bars = plt.bar(range(len(dates)), amounts, color='#f72585')
    plt.xlabel('Date')
    plt.ylabel('Expenses ($)')
    plt.title('Daily Expenses (Last 7 Days)')
    plt.xticks(range(len(dates)), dates, rotation=45)
    
    # Add value labels on bars
    for i, bar in enumerate(bars):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'${amounts[i]:.2f}',
                ha='center', va='bottom')
    
    plt.tight_layout()
    
    # Save plot to a PNG image in memory
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', bbox_inches='tight')
    img_buffer.seek(0)
    
    # Encode the image in base64
    img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
    
    # Close the figure to free memory
    plt.close()
    
    return jsonify({'image': img_base64})

# Generate comparison chart for income vs expenses
@app.route('/api/chart/income-vs-expenses', methods=['GET'])
def get_income_vs_expenses_chart():
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'image': None})
    expenses = Expense.query.filter_by(user_id=user_id).all()
    incomes = Income.query.filter_by(user_id=user_id).all()
    
    if not expenses and not incomes:
        return jsonify({'image': None})
    
    # Group by month
    monthly_data = defaultdict(lambda: {'income': 0, 'expense': 0})
    
    for income in incomes:
        month_key = income.date.strftime('%Y-%m')
        monthly_data[month_key]['income'] += income.amount
    
    for expense in expenses:
        month_key = expense.date.strftime('%Y-%m')
        monthly_data[month_key]['expense'] += expense.amount
    
    if not monthly_data:
        return jsonify({'image': None})
    
    # Sort by month
    months = sorted(monthly_data.keys())
    income_amounts = [monthly_data[month]['income'] for month in months]
    expense_amounts = [monthly_data[month]['expense'] for month in months]
    
    # Create comparison chart
    x = np.arange(len(months))
    width = 0.35
    
    plt.figure(figsize=(12, 6))
    plt.bar(x - width/2, income_amounts, width, label='Income', color='#4cc9f0')
    plt.bar(x + width/2, expense_amounts, width, label='Expenses', color='#f72585')
    
    plt.xlabel('Month')
    plt.ylabel('Amount ($)')
    plt.title('Monthly Income vs Expenses')
    plt.xticks(x, months, rotation=45)
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Add value labels on bars
    for i, (income, expense) in enumerate(zip(income_amounts, expense_amounts)):
        plt.text(i - width/2, income + max(income, expense) * 0.01,
                f'${income:.2f}',
                ha='center', va='bottom', fontsize=8)
        plt.text(i + width/2, expense + max(income, expense) * 0.01,
                f'${expense:.2f}',
                ha='center', va='bottom', fontsize=8)
    
    plt.tight_layout()
    
    # Save plot to a PNG image in memory
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', bbox_inches='tight')
    img_buffer.seek(0)
    
    # Encode the image in base64
    img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
    
    # Close the figure to free memory
    plt.close()
    
    return jsonify({'image': img_base64})

# Generate PDF report
@app.route('/api/report/pdf', methods=['GET'])
def generate_pdf_report():
    # Check if reportlab is available
    if not REPORTLAB_AVAILABLE:
        return jsonify({'error': 'PDF generation not available. reportlab library is not installed.'}), 501
    
    # Get current user
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    expenses = Expense.query.filter_by(user_id=user_id).all()
    incomes = Income.query.filter_by(user_id=user_id).all()
    
    # Calculate totals
    total_expenses = sum(expense.amount for expense in expenses)
    total_income = sum(income.amount for income in incomes)
    balance = total_income - total_expenses
    
    # Create PDF in memory
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Title
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 50, "Expense Tracker Report")
    
    # Date
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 70, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Summary
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 100, "Financial Summary")
    
    c.setFont("Helvetica", 12)
    c.drawString(70, height - 120, f"Total Income: ${total_income:.2f}")
    c.drawString(70, height - 140, f"Total Expenses: ${total_expenses:.2f}")
    c.drawString(70, height - 160, f"Balance: ${balance:.2f}")
    
    # Income table
    if incomes:
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 200, "Income Records")
        
        # Table data
        income_data = [["Date", "Description", "Amount"]]
        for income in incomes:
            income_data.append([
                income.date.strftime('%Y-%m-%d'),
                income.description,
                f"${income.amount:.2f}"
            ])
        
        # Create table
        income_table = Table(income_data)
        income_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        income_table.wrapOn(c, width, height)
        income_table.drawOn(c, 50, height - 200 - len(income_data) * 20 - 50)
    
    # Expense table
    if expenses:
        expense_start_y = height - 200 - len(incomes) * 20 - 100 if incomes else height - 200
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, expense_start_y, "Expense Records")
        
        # Table data
        expense_data = [["Date", "Description", "Category", "Amount"]]
        for expense in expenses:
            expense_data.append([
                expense.date.strftime('%Y-%m-%d'),
                expense.description,
                expense.category,
                f"${expense.amount:.2f}"
            ])
        
        # Create table
        expense_table = Table(expense_data)
        expense_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        expense_table.wrapOn(c, width, height)
        expense_table.drawOn(c, 50, expense_start_y - len(expense_data) * 20 - 50)
    
    c.save()
    
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='expense_report.pdf', mimetype='application/pdf')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')