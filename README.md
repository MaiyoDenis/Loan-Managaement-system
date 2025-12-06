<<<<<<< HEAD
loan
=======
# Loan Management System

A comprehensive loan management system built with FastAPI backend and React frontend, designed for financial institutions to manage loans, accounts, payments, and user administration.

## 🚀 Features

- **User Management**: Multi-role user system (Admin, Manager, Officer, etc.)
- **Loan Management**: Complete loan lifecycle from application to repayment
- **Account Management**: Savings and drawdown accounts
- **Payment Processing**: M-Pesa integration for payments
- **Analytics & Reporting**: Comprehensive business intelligence
- **Branch Management**: Multi-branch support
- **Inventory Management**: Track loan-related inventory
- **Notifications**: Automated notifications system
- **Risk Scoring**: Automated risk assessment for loan applications

## 🏗️ Project Structure

```
loan-management-system/
├── backend/                    # FastAPI backend
│   ├── app/                    # Main application
│   │   ├── api/v1/            # API endpoints (v1)
│   │   ├── core/              # Core functionality
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # Business logic services
│   │   ├── tasks/             # Background tasks
│   │   └── utils/             # Utility functions
│   ├── alembic/               # Database migrations
│   ├── myenv/                 # Virtual environment
│   ├── requirements.txt       # Production dependencies
│   ├── requirements-dev.txt   # Development dependencies
│   └── .gitignore            # Backend-specific ignore rules
├── frontend/                  # React frontend
│   ├── public/                # Static assets
│   ├── src/                   # Source code
│   │   ├── components/        # Reusable components
│   │   ├── contexts/          # React contexts
│   │   ├── pages/             # Page components
│   │   ├── services/          # API services
│   │   └── store.ts           # State management
│   ├── package.json           # Dependencies and scripts
│   └── .gitignore            # Frontend-specific ignore rules
├── .git/                      # Git repository
├── .gitignore                 # Root ignore rules
└── README.md                  # This file
```

## 🛠️ Tech Stack

### Backend
- **FastAPI**: Modern, fast web framework for building APIs
- **SQLAlchemy**: SQL toolkit and ORM
- **Alembic**: Database migration tool
- **Pydantic**: Data validation
- **PostgreSQL/SQLite**: Database (configurable)
- **Redis**: Caching and session storage
- **Celery**: Background task processing
- **Passlib**: Password hashing
- **JWT**: Authentication tokens

### Frontend
- **React**: UI library
- **TypeScript**: Type-safe JavaScript
- **Vite**: Build tool and dev server
- **Tailwind CSS**: Utility-first CSS framework
- **Axios**: HTTP client
- **React Router**: Client-side routing
- **Zustand**: State management

## 📋 Prerequisites

- Python 3.8+
- Node.js 16+
- PostgreSQL (optional, defaults to SQLite)

## 🚀 Quick Start

### Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv myenv
   source myenv/bin/activate  # On Windows: myenv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # For development
   ```

4. **Set up environment variables:**
   ```bash
   cp .env.example .env  # Create from template if available
   # Edit .env with your configuration
   ```

5. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

6. **Start the development server:**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

   The API will be available at `http://localhost:8000`
   - API Documentation: `http://localhost:8000/api/docs`
   - Alternative Docs: `http://localhost:8000/api/redoc`

### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Set up environment variables:**
   ```bash
   cp .env.example .env.local  # If available
   # Configure API base URL, etc.
   ```

4. **Start the development server:**
   ```bash
   npm run dev
   ```

   The app will be available at `http://localhost:5173`

## 🔧 Configuration

### Backend Configuration

Key configuration options in `backend/app/core/config.py`:

- `DATABASE_URL`: Database connection string
- `SECRET_KEY`: JWT secret key
- `BACKEND_CORS_ORIGINS`: Allowed CORS origins
- `ACCESS_TOKEN_EXPIRE_MINUTES`: JWT token expiration
- `DEFAULT_ADMIN_EMAIL`: Default admin email
- `DEFAULT_ADMIN_PASSWORD`: Default admin password

### Frontend Configuration

Environment variables in `frontend/.env.local`:

- `VITE_API_URL`: Backend API base URL (default: `http://localhost:8000/api/v1`)

## 🗄️ Database

The system supports multiple database backends:

- **SQLite** (default): For development and small deployments
- **PostgreSQL**: For production use

### Database Setup

1. **SQLite (Default):**
   - No additional setup required
   - Database file: `backend/loan_management.db`

2. **PostgreSQL:**
   - Install PostgreSQL
   - Create database and user
   - Update `DATABASE_URL` in config

### Migrations

Use Alembic for database schema changes:

```bash
cd backend
alembic revision --autogenerate -m "Migration message"
alembic upgrade head
```

## 🔐 Authentication

The system uses JWT (JSON Web Tokens) for authentication:

- **Login**: POST `/api/v1/auth/login`
- **Refresh**: POST `/api/v1/auth/refresh`
- **Verify**: GET `/api/v1/auth/verify-token`
- **Logout**: POST `/api/v1/auth/logout`

Default admin credentials:
- Username: `admin`
- Password: `admin123`

## 📊 API Endpoints

### Authentication
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/logout` - User logout
- `GET /api/v1/auth/me` - Get current user
- `POST /api/v1/auth/change-password` - Change password

### Users
- `GET /api/v1/users` - List users
- `POST /api/v1/users` - Create user
- `GET /api/v1/users/{id}` - Get user details
- `PUT /api/v1/users/{id}` - Update user
- `DELETE /api/v1/users/{id}` - Delete user

### Loans
- `GET /api/v1/loans` - List loans
- `POST /api/v1/loans` - Create loan
- `GET /api/v1/loans/{id}` - Get loan details
- `PUT /api/v1/loans/{id}` - Update loan
- `DELETE /api/v1/loans/{id}` - Delete loan

### Accounts
- `GET /api/v1/accounts/savings` - List savings accounts
- `GET /api/v1/accounts/drawdown` - List drawdown accounts
- `POST /api/v1/accounts/transfer` - Transfer funds
- `POST /api/v1/accounts/deposit` - Deposit funds

### And many more...

## 🧪 Testing

### Backend Testing

```bash
cd backend
pytest
```

### Frontend Testing

```bash
cd frontend
npm test
```

## 🚀 Deployment

### Backend Deployment

1. **Install production dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables for production**

3. **Use a production ASGI server:**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
   ```

### Frontend Deployment

1. **Build the application:**
   ```bash
   npm run build
   ```

2. **Serve the `dist` directory with any static file server**

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit changes: `git commit -am 'Add your feature'`
4. Push to branch: `git push origin feature/your-feature`
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For support and questions:
- Create an issue in the GitHub repository
- Check the API documentation at `/api/docs`
- Review the code comments and docstrings

## 🔄 Version History

- **v1.0.0**: Initial release with core loan management features
  - User management and authentication
  - Loan application and approval workflow
  - Account management (savings/drawdown)
  - Payment processing with M-Pesa integration
  - Analytics and reporting dashboard
  - Multi-branch support
  - Inventory management
  - Notification system
  - Risk scoring engine
