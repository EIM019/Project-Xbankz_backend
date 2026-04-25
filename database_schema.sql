-- xBankz Database Schema for SQL Server

-- Users Table
CREATE TABLE Users (
    user_id INT IDENTITY(1,1) PRIMARY KEY,
    username NVARCHAR(50) UNIQUE NOT NULL,
    email NVARCHAR(100) UNIQUE NOT NULL,
    password_hash NVARCHAR(255) NOT NULL,
    role NVARCHAR(20) NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    failed_login_attempts INT DEFAULT 0,
    account_locked_until DATETIME NULL,
    created_at DATETIME DEFAULT GETDATE(),
    last_login DATETIME NULL
);

-- BankAccounts Table
CREATE TABLE BankAccounts (
    account_id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL,
    account_number NVARCHAR(20) UNIQUE NOT NULL,
    account_type NVARCHAR(50) NOT NULL DEFAULT 'checking',
    balance DECIMAL(18,2) DEFAULT 0.00 CHECK (balance >= 0),
    created_at DATETIME DEFAULT GETDATE(),
    is_active BIT DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

-- Transactions Table
CREATE TABLE Transactions (
    transaction_id INT IDENTITY(1,1) PRIMARY KEY,
    from_account_id INT NULL,
    to_account_id INT NULL,
    amount DECIMAL(18,2) NOT NULL CHECK (amount > 0),
    transaction_type NVARCHAR(20) NOT NULL CHECK (transaction_type IN ('internal', 'interbank', 'deposit', 'withdrawal')),
    status NVARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('completed', 'pending', 'rejected', 'flagged')),
    description NVARCHAR(500) NULL,
    fraud_flags NVARCHAR(MAX) NULL, -- JSON string
    created_at DATETIME DEFAULT GETDATE(),
    approved_by INT NULL,
    approved_at DATETIME NULL,
    FOREIGN KEY (from_account_id) REFERENCES BankAccounts(account_id),
    FOREIGN KEY (to_account_id) REFERENCES BankAccounts(account_id),
    FOREIGN KEY (approved_by) REFERENCES Users(user_id)
);

-- OTPSessions Table
CREATE TABLE OTPSessions (
    otp_id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL,
    otp_code NVARCHAR(10) NOT NULL,
    expires_at DATETIME NOT NULL,
    used BIT DEFAULT 0,
    created_at DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

-- AuditLog Table
CREATE TABLE AuditLog (
    audit_id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NULL,
    action NVARCHAR(100) NOT NULL,
    resource_type NVARCHAR(50) NULL,
    resource_id INT NULL,
    details NVARCHAR(MAX) NULL, -- JSON string
    ip_address NVARCHAR(45) NULL,
    created_at DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE SET NULL
);

-- UserLimits Table
CREATE TABLE UserLimits (
    limit_id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT UNIQUE NOT NULL,
    daily_limit DECIMAL(18,2) DEFAULT 10000.00,
    monthly_limit DECIMAL(18,2) DEFAULT 50000.00,
    daily_used DECIMAL(18,2) DEFAULT 0.00,
    monthly_used DECIMAL(18,2) DEFAULT 0.00,
    last_reset_date DATE DEFAULT CAST(GETDATE() AS DATE),
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IX_BankAccounts_UserID ON BankAccounts(user_id);
CREATE INDEX IX_Transactions_FromAccount ON Transactions(from_account_id);
CREATE INDEX IX_Transactions_ToAccount ON Transactions(to_account_id);
CREATE INDEX IX_Transactions_CreatedAt ON Transactions(created_at);
CREATE INDEX IX_Transactions_Status ON Transactions(status);
CREATE INDEX IX_OTPSessions_UserID ON OTPSessions(user_id);
CREATE INDEX IX_OTPSessions_ExpiresAt ON OTPSessions(expires_at);
CREATE INDEX IX_AuditLog_UserID ON AuditLog(user_id);
CREATE INDEX IX_AuditLog_CreatedAt ON AuditLog(created_at);
