// Determine API URL based on environment (safe for plain browser runtime)
const API_BASE_URL = (function() {
    // Allow an explicit global to be set (useful when injecting at deploy time)
    if (window.__API_BASE__) return window.__API_BASE__;

    // Local development default
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        return 'http://localhost:5000/api';
    }

    // If the app was built with an env-replacer that defines process.env, use it safely
    try {
        if (typeof process !== 'undefined' && process.env && process.env.REACT_APP_API_URL) {
            return process.env.REACT_APP_API_URL;
        }
    } catch (e) {}

    // Default to same origin + /api for production static hosting
    return `${window.location.origin}/api`;
})();

let currentTab = 'expense';
let editingId = null;
let currentUser = null;

// DOM Elements
const loginPage = document.getElementById('login-page');
const registerPage = document.getElementById('register-page');
const app = document.getElementById('app');
const loginForm = document.getElementById('login-form');
const registerForm = document.getElementById('register-form');
const showRegisterLink = document.getElementById('show-register');
const showLoginLink = document.getElementById('show-login');
const logoutBtn = document.getElementById('logout-btn');
const currentUserSpan = document.getElementById('current-user');

// Navigation
const dashboardLink = document.getElementById('dashboard-link');
const transactionsLink = document.getElementById('transactions-link');
const reportsLink = document.getElementById('reports-link');

// Set today's date as default
document.getElementById('date').valueAsDate = new Date();

// Page Navigation
showRegisterLink.addEventListener('click', (e) => {
    e.preventDefault();
    loginPage.classList.remove('active');
    registerPage.classList.add('active');
});

showLoginLink.addEventListener('click', (e) => {
    e.preventDefault();
    registerPage.classList.remove('active');
    loginPage.classList.add('active');
});

// Show different sections
function showSection(sectionId) {
    // Hide all sections
    document.querySelectorAll('.section').forEach(section => {
        section.classList.remove('active');
    });

    // Show requested section
    document.getElementById(sectionId).classList.add('active');
}

// Navigation event listeners
dashboardLink.addEventListener('click', (e) => {
    e.preventDefault();
    document.querySelectorAll('nav ul li a').forEach(link => link.classList.remove('active'));
    dashboardLink.classList.add('active');
    showSection('dashboard-section');
});

transactionsLink.addEventListener('click', (e) => {
    e.preventDefault();
    document.querySelectorAll('nav ul li a').forEach(link => link.classList.remove('active'));
    transactionsLink.classList.add('active');
    showSection('transactions-section');
    loadTransactions(); // Load transactions when switching to this section
});



reportsLink.addEventListener('click', (e) => {
    e.preventDefault();
    document.querySelectorAll('nav ul li a').forEach(link => link.classList.remove('active'));
    reportsLink.classList.add('active');
    showSection('reports-section');
    loadIncomeSourcesReportChart();
    loadExpenseCategoriesReportChart();
});

// Tab switching
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        currentTab = tab.dataset.tab;

        // Show/hide category field based on tab
        document.querySelector('.expense-fields').style.display =
            currentTab === 'expense' ? 'block' : 'none';

        // Update form submit button text
        document.querySelector('#transaction-form button').textContent =
            `Add ${currentTab.charAt(0).toUpperCase() + currentTab.slice(1)}`;

        loadTransactions();
    });
});

// Login Form
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;

    try {
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();

        if (response.ok) {
            currentUser = data.user;
            localStorage.setItem('user', JSON.stringify(currentUser));
            currentUserSpan.textContent = currentUser.username;
            loginPage.classList.remove('active');
            app.classList.add('active');
            loadDashboardData();
        } else {
            alert('Login failed: ' + data.error);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Network error. Please try again.');
    }
});

// Register Form
registerForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const username = document.getElementById('register-username').value;
    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;

    try {
        const response = await fetch(`${API_BASE_URL}/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, email, password })
        });

        const data = await response.json();

        if (response.ok) {
            alert('Registration successful! Please login.');
            registerPage.classList.remove('active');
            loginPage.classList.add('active');
        } else {
            alert('Registration failed: ' + data.error);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Network error. Please try again.');
    }
});

// Logout
logoutBtn.addEventListener('click', () => {
    currentUser = null;
    localStorage.removeItem('user');
    app.classList.remove('active');
    loginPage.classList.add('active');
});

// Form submission
document.getElementById('transaction-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const amount = document.getElementById('amount').value;
    const description = document.getElementById('description').value;
    const date = document.getElementById('date').value;
    const category = document.getElementById('category').value;

    if (!amount || !description || !date || (currentTab === 'expense' && !category)) {
        alert('Please fill in all required fields');
        return;
    }

    const transactionData = {
        amount: parseFloat(amount),
        description: description,
        date: date
    };

    if (currentTab === 'expense') {
        transactionData.category = category;
    }

    try {
        let response;
        if (editingId) {
            // Update existing transaction
            const endpoint = currentTab === 'expense' ? 'expenses' : 'income';
            response = await fetch(`${API_BASE_URL}/${endpoint}/${editingId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'User-Id': currentUser ? currentUser.id : ''
                },
                body: JSON.stringify(transactionData)
            });
        } else {
            // Add new transaction
            const endpoint = currentTab === 'expense' ? 'expenses' : 'income';
            response = await fetch(`${API_BASE_URL}/${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'User-Id': currentUser ? currentUser.id.toString() : ''
                },
                body: JSON.stringify(transactionData)
            });
        }

        if (response.ok) {
            document.getElementById('transaction-form').reset();
            document.getElementById('date').valueAsDate = new Date();
            editingId = null;
            document.querySelector('#transaction-form button').textContent =
                `Add ${currentTab.charAt(0).toUpperCase() + currentTab.slice(1)}`;
            loadDashboardData();
            loadTransactions();
        } else {
            const error = await response.json();
            alert('Error: ' + (error.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Network error. Please try again.');
    }
});

// Load dashboard data
async function loadDashboardData() {
    try {
        if (!currentUser) return;
        const headers = { 'User-Id': currentUser.id };
        const response = await fetch(`${API_BASE_URL}/dashboard`, { headers });
        const data = await response.json();

        document.getElementById('total-income').textContent = `$${data.totalIncome.toFixed(2)}`;
        document.getElementById('total-expenses').textContent = `$${data.totalExpenses.toFixed(2)}`;
        document.getElementById('balance').textContent = `$${data.balance.toFixed(2)}`;

        // Update recent transactions on dashboard (mixed)
        const recentDashboardContainer = document.getElementById('recent-transactions-dashboard');
        if (data.recentTransactions.length > 0) {
            recentDashboardContainer.innerHTML = data.recentTransactions.map(transaction => `
                <div class="transaction-item">
                    <div class="transaction-info">
                        <div class="transaction-title">${transaction.description}</div>
                        <div class="transaction-category">${transaction.category}</div>
                        <div class="transaction-date">${new Date(transaction.date).toLocaleDateString()}</div>
                    </div>
                    <div class="transaction-amount ${transaction.type}">
                        ${transaction.type === 'income' ? '+' : '-'}$${transaction.amount.toFixed(2)}
                    </div>
                </div>
            `).join('');
        } else {
            recentDashboardContainer.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-exchange-alt"></i>
                    <h3>No transactions yet</h3>
                    <p>Add your first transaction to get started</p>
                </div>
            `;
        }

        // Get all income and expense transactions separately
        const incomeResponse = await fetch(`${API_BASE_URL}/income`, { headers });
        const expenseResponse = await fetch(`${API_BASE_URL}/expenses`, { headers });
        const allIncome = await incomeResponse.json();
        const allExpenses = await expenseResponse.json();

        // Update income transactions in dashboard
        const incomeContainer = document.getElementById('income-transactions-dashboard');
        if (allIncome.length > 0) {
            // Sort by date descending and take last 5
            const sortedIncome = [...allIncome].sort((a, b) => new Date(b.date) - new Date(a.date)).slice(0, 5);
            incomeContainer.innerHTML = sortedIncome.map(income => `
                <div class="transaction-small">
                    <div class="transaction-small-info">
                        <h4>${income.description}</h4>
                        <p>Income • ${new Date(income.date).toLocaleDateString()}</p>
                    </div>
                    <div class="transaction-amount income">
                        +$${income.amount.toFixed(2)}
                    </div>
                </div>
            `).join('');
        } else {
            incomeContainer.innerHTML = `
                <div class="empty-state">
                    <p>No income transactions</p>
                </div>
            `;
        }

        // Update expense transactions in dashboard
        const expenseContainer = document.getElementById('expense-transactions-dashboard');
        if (allExpenses.length > 0) {
            // Sort by date descending and take last 5
            const sortedExpenses = [...allExpenses].sort((a, b) => new Date(b.date) - new Date(a.date)).slice(0, 5);
            expenseContainer.innerHTML = sortedExpenses.map(expense => `
                <div class="transaction-small">
                    <div class="transaction-small-info">
                        <h4>${expense.description}</h4>
                        <p>${expense.category} • ${new Date(expense.date).toLocaleDateString()}</p>
                    </div>
                    <div class="transaction-amount expense">
                        -$${expense.amount.toFixed(2)}
                    </div>
                </div>
            `).join('');
        } else {
            expenseContainer.innerHTML = `
                <div class="empty-state">
                    <p>No expense transactions</p>
                </div>
            `;
        }

        // Update categories summary
        const categoriesContainer = document.getElementById('categories-summary');
        const categories = Object.entries(data.categoryTotals);
        if (categories.length > 0) {
            categoriesContainer.innerHTML = categories.map(([category, amount], index) => {
                const colors = ['#4361ee', '#3a0ca3', '#4cc9f0', '#f72585', '#7209b7', '#4895ef', '#4cc9f0'];
                const color = colors[index % colors.length];

                return `
                    <div class="category-item">
                        <div class="category-name">
                            <div class="category-color" style="background-color: ${color}"></div>
                            <span>${category}</span>
                        </div>
                        <div class="category-amount">$${amount.toFixed(2)}</div>
                    </div>
                `;
            }).join('');
        } else {
            categoriesContainer.innerHTML = `
                <div class="empty-state">
                    <p>No expense categories yet</p>
                </div>
            `;
        }

        // Load income sources chart
        loadIncomeSourcesChart();
        // Load daily expenses chart
        loadDailyExpensesChart();
    } catch (error) {
        console.error('Error loading dashboard data:', error);
    }
}

// Load income sources chart
async function loadIncomeSourcesChart() {
    try {
        if (!currentUser) return;
        const headers = { 'User-Id': currentUser.id };
        const response = await fetch(`${API_BASE_URL}/chart/income-sources`, { headers });
        const data = await response.json();

        const chartImage = document.getElementById('income-sources-chart');
        const noChartMessage = document.getElementById('no-income-sources-chart');

        if (data.image) {
            chartImage.src = `data:image/png;base64,${data.image}`;
            chartImage.style.display = 'block';
            noChartMessage.style.display = 'none';
        } else {
            chartImage.style.display = 'none';
            noChartMessage.style.display = 'block';
        }
    } catch (error) {
        console.error('Error loading income sources chart:', error);
        document.getElementById('income-sources-chart').style.display = 'none';
        document.getElementById('no-income-sources-chart').style.display = 'block';
    }
}

// Load daily expenses chart
async function loadDailyExpensesChart() {
    try {
        if (!currentUser) return;
        const headers = { 'User-Id': currentUser.id };
        const response = await fetch(`${API_BASE_URL}/chart/daily-expenses`, { headers });
        const data = await response.json();

        const chartImage = document.getElementById('daily-expenses-chart');
        const noChartMessage = document.getElementById('no-daily-expenses-chart');

        if (data.image) {
            chartImage.src = `data:image/png;base64,${data.image}`;
            chartImage.style.display = 'block';
            noChartMessage.style.display = 'none';
        } else {
            chartImage.style.display = 'none';
            noChartMessage.style.display = 'block';
        }
    } catch (error) {
        console.error('Error loading daily expenses chart:', error);
        document.getElementById('daily-expenses-chart').style.display = 'none';
        document.getElementById('no-daily-expenses-chart').style.display = 'block';
    }
}

// Load income sources report chart
async function loadIncomeSourcesReportChart() {
    try {
        if (!currentUser) return;
        const headers = { 'User-Id': currentUser.id };
        const response = await fetch(`${API_BASE_URL}/chart/income-sources`, { headers });
        const data = await response.json();

        const chartImage = document.getElementById('income-sources-report-chart');
        const noChartMessage = document.getElementById('no-income-sources-report-chart');

        if (data.image) {
            chartImage.src = `data:image/png;base64,${data.image}`;
            chartImage.style.display = 'block';
            noChartMessage.style.display = 'none';
        } else {
            chartImage.style.display = 'none';
            noChartMessage.style.display = 'block';
        }
    } catch (error) {
        console.error('Error loading income sources report chart:', error);
        document.getElementById('income-sources-report-chart').style.display = 'none';
        document.getElementById('no-income-sources-report-chart').style.display = 'block';
    }
}

// Load expense categories report chart
async function loadExpenseCategoriesReportChart() {
    try {
        if (!currentUser) return;
        const headers = { 'User-Id': currentUser.id };
        const response = await fetch(`${API_BASE_URL}/chart/expense-categories`, { headers });
        const data = await response.json();

        const chartImage = document.getElementById('expense-categories-report-chart');
        const noChartMessage = document.getElementById('no-expense-categories-report-chart');

        if (data.image) {
            chartImage.src = `data:image/png;base64,${data.image}`;
            chartImage.style.display = 'block';
            noChartMessage.style.display = 'none';
        } else {
            chartImage.style.display = 'none';
            noChartMessage.style.display = 'block';
        }
    } catch (error) {
        console.error('Error loading expense categories report chart:', error);
        document.getElementById('expense-categories-report-chart').style.display = 'none';
        document.getElementById('no-expense-categories-report-chart').style.display = 'block';
    }
}

// Load transactions
async function loadTransactions() {
    try {
        if (!currentUser) return;
        const headers = { 'User-Id': currentUser.id };
        const endpoint = currentTab === 'expense' ? 'expenses' : 'income';
        const response = await fetch(`${API_BASE_URL}/${endpoint}`, { headers });
        const transactions = await response.json();

        const transactionsList = document.getElementById('transactions-list');
        if (transactions.length > 0) {
            transactionsList.innerHTML = transactions.map(transaction => `
                <div class="transaction-item">
                    <div class="transaction-info">
                        <div class="transaction-title">${transaction.description}</div>
                        <div class="transaction-category">${transaction.category || 'Income'}</div>
                        <div class="transaction-date">${new Date(transaction.date).toLocaleDateString()}</div>
                    </div>
                    <div class="transaction-amount ${currentTab}">
                        ${currentTab === 'income' ? '+' : '-'}$${transaction.amount.toFixed(2)}
                    </div>
                    <div class="transaction-actions">
                        <button class="action-btn btn-warning" onclick="editTransaction(${transaction.id})">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="action-btn btn-danger" onclick="deleteTransaction(${transaction.id})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            `).join('');
        } else {
            transactionsList.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-exchange-alt"></i>
                    <h3>No ${currentTab}s yet</h3>
                    <p>Add your first ${currentTab} to get started</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading transactions:', error);
        document.getElementById('transactions-list').innerHTML = '<p>Error loading transactions. Please try again.</p>';
    }
}

// Load expense chart
async function loadExpenseChart() {
    try {
        const headers = { 'User-Id': currentUser ? currentUser.id : '' };
        const response = await fetch(`${API_BASE_URL}/chart/expense-categories`, { headers });
        const data = await response.json();

        const chartImage = document.getElementById('expense-chart');
        const noChartMessage = document.getElementById('no-chart-message');

        if (data.image) {
            chartImage.src = `data:image/png;base64,${data.image}`;
            chartImage.style.display = 'block';
            noChartMessage.style.display = 'none';
        } else {
            chartImage.style.display = 'none';
            noChartMessage.style.display = 'block';
        }
    } catch (error) {
        console.error('Error loading chart:', error);
        document.getElementById('expense-chart').style.display = 'none';
        document.getElementById('no-chart-message').style.display = 'block';
    }
}

// Load income by month chart
async function loadIncomeByMonthChart() {
    try {
        const headers = { 'User-Id': currentUser ? currentUser.id : '' };
        const response = await fetch(`${API_BASE_URL}/chart/income-by-month`, { headers });
        const data = await response.json();

        const chartImage = document.getElementById('income-monthly-chart');
        const noChartMessage = document.getElementById('no-income-chart-message');

        if (data.image) {
            chartImage.src = `data:image/png;base64,${data.image}`;
            chartImage.style.display = 'block';
            noChartMessage.style.display = 'none';
        } else {
            chartImage.style.display = 'none';
            noChartMessage.style.display = 'block';
        }
    } catch (error) {
        console.error('Error loading income chart:', error);
        document.getElementById('income-monthly-chart').style.display = 'none';
        document.getElementById('no-income-chart-message').style.display = 'block';
    }
}

// Load expense trends chart
async function loadExpenseTrendsChart() {
    try {
        const headers = { 'User-Id': currentUser ? currentUser.id : '' };
        const response = await fetch(`${API_BASE_URL}/chart/expense-trends`, { headers });
        const data = await response.json();

        const chartImage = document.getElementById('expense-trends-chart');
        const noChartMessage = document.getElementById('no-trends-chart-message');

        if (data.image) {
            chartImage.src = `data:image/png;base64,${data.image}`;
            chartImage.style.display = 'block';
            noChartMessage.style.display = 'none';
        } else {
            chartImage.style.display = 'none';
            noChartMessage.style.display = 'block';
        }
    } catch (error) {
        console.error('Error loading trends chart:', error);
        document.getElementById('expense-trends-chart').style.display = 'none';
        document.getElementById('no-trends-chart-message').style.display = 'block';
    }
}

// Load income vs expenses comparison chart
async function loadIncomeVsExpensesChart() {
    try {
        const headers = { 'User-Id': currentUser ? currentUser.id : '' };
        const response = await fetch(`${API_BASE_URL}/chart/income-vs-expenses`, { headers });
        const data = await response.json();

        const chartImage = document.getElementById('comparison-chart');
        const noChartMessage = document.getElementById('no-comparison-chart-message');

        if (data.image) {
            chartImage.src = `data:image/png;base64,${data.image}`;
            chartImage.style.display = 'block';
            noChartMessage.style.display = 'none';
        } else {
            chartImage.style.display = 'none';
            noChartMessage.style.display = 'block';
        }
    } catch (error) {
        console.error('Error loading comparison chart:', error);
        document.getElementById('comparison-chart').style.display = 'none';
        document.getElementById('no-comparison-chart-message').style.display = 'block';
    }
}

// Edit transaction
async function editTransaction(id) {
    try {
        if (!currentUser) return;
        const headers = { 'User-Id': currentUser.id };
        const endpoint = currentTab === 'expense' ? 'expenses' : 'income';
        const response = await fetch(`${API_BASE_URL}/${endpoint}/${id}`, { headers });
        const transaction = await response.json();

        document.getElementById('amount').value = transaction.amount;
        document.getElementById('description').value = transaction.description;
        document.getElementById('date').value = transaction.date.split('T')[0];

        if (currentTab === 'expense') {
            document.getElementById('category').value = transaction.category;
        }

        editingId = id;
        document.querySelector('#transaction-form button').textContent = `Update ${currentTab.charAt(0).toUpperCase() + currentTab.slice(1)}`;

        // Scroll to form
        document.querySelector('.transaction-form').scrollIntoView({ behavior: 'smooth' });
    } catch (error) {
        console.error('Error loading transaction:', error);
        alert('Error loading transaction data');
    }
}

// Delete transaction
async function deleteTransaction(id) {
    if (!confirm(`Are you sure you want to delete this ${currentTab}?`)) {
        return;
    }

    try {
        const endpoint = currentTab === 'expense' ? 'expenses' : 'income';
        const response = await fetch(`${API_BASE_URL}/${endpoint}/${id}`, {
            method: 'DELETE',
            headers: {
                'User-Id': currentUser ? currentUser.id : ''
            }
        });

        if (response.ok) {
            loadDashboardData();
            loadTransactions();
        } else {
            alert('Error deleting transaction');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Network error. Please try again.');
    }
}

// Download PDF report
async function downloadPDFReport() {
    try {
        if (!currentUser) {
            alert('Please login first');
            return;
        }
        const headers = { 'User-Id': currentUser.id };
        const response = await fetch(`${API_BASE_URL}/report/pdf`, { headers });
        if (response.status === 501) {
            const data = await response.json();
            alert('PDF generation is not available: ' + data.error);
        } else if (response.ok) {
            // Create a blob URL for the PDF and trigger download
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'expense_report.pdf';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } else {
            alert('Error generating PDF report');
        }
    } catch (error) {
        console.error('Error downloading PDF:', error);
        alert('Network error. Please try again.');
    }
}

// Initialize
window.addEventListener('DOMContentLoaded', () => {
    // Check for saved session
    const savedUser = localStorage.getItem('user');
    if (savedUser) {
        try {
            currentUser = JSON.parse(savedUser);
            currentUserSpan.textContent = currentUser.username;
            loginPage.classList.remove('active');
            app.classList.add('active');
            loadDashboardData();
        } catch (e) {
            console.error('Error parsing saved user:', e);
            localStorage.removeItem('user');
        }
    }

    // Demo user creation removed to avoid auto-registering on page load
});
