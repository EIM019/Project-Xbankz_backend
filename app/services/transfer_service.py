from flask import current_app
from app.utils.database import db_transaction
from app.services.fraud_service import detect_fraud, should_flag_transaction
from app.services.limits_service import check_transfer_limits, update_transfer_limits
from app.services.audit_service import log_audit
from decimal import Decimal
import json

def get_account_balance(account_id):
    """Get current balance of an account"""
    with db_transaction() as cursor:
        cursor.execute("""
            SELECT balance
            FROM BankAccounts
            WHERE account_id = ? AND is_active = 1
        """, account_id)
        
        result = cursor.fetchone()
        if not result:
            return None
        return float(result[0])

def process_internal_transfer(from_account_id, to_account_id, amount, description, user_id):
    """Process an internal transfer (instant)"""
    amount_decimal = Decimal(str(amount))
    
    # Validate accounts
    from_balance = get_account_balance(from_account_id)
    to_balance = get_account_balance(to_account_id)
    
    if from_balance is None:
        return False, "Source account not found or inactive"
    if to_balance is None:
        return False, "Destination account not found or inactive"
    if from_account_id == to_account_id:
        return False, "Cannot transfer to the same account"
    
    # Check balance
    if from_balance < amount:
        return False, "Insufficient balance"
    
    # Check limits
    limits_ok, limits_error = check_transfer_limits(user_id, amount)
    if not limits_ok:
        return False, limits_error
    
    # Fraud detection
    fraud_flags = detect_fraud(user_id, from_account_id, amount)
    fraud_flags_json = json.dumps(fraud_flags) if fraud_flags else None
    status = 'flagged' if should_flag_transaction(fraud_flags) else 'completed'
    
    # Process transfer in transaction
    try:
        with db_transaction() as cursor:
            # Debit from account
            cursor.execute("""
                UPDATE BankAccounts
                SET balance = balance - ?
                WHERE account_id = ?
            """, amount_decimal, from_account_id)
            
            # Credit to account
            cursor.execute("""
                UPDATE BankAccounts
                SET balance = balance + ?
                WHERE account_id = ?
            """, amount_decimal, to_account_id)
            
            # Create transaction record
            cursor.execute("""
                INSERT INTO Transactions (from_account_id, to_account_id, amount, transaction_type, status, description, fraud_flags)
                OUTPUT INSERTED.transaction_id
                VALUES (?, ?, ?, 'internal', ?, ?, ?)
            """, from_account_id, to_account_id, amount_decimal, status, description, fraud_flags_json)
            
            transaction_id = cursor.fetchone()[0]
            
            # Update limits
            update_transfer_limits(user_id, amount)
            
            log_audit(user_id, 'INTERNAL_TRANSFER', 'Transaction', transaction_id, {
                'from_account': from_account_id,
                'to_account': to_account_id,
                'amount': float(amount),
                'status': status
            })
        
        if status == 'flagged':
            return True, "Transfer completed but flagged for review", transaction_id
        return True, "Transfer completed successfully", transaction_id
    
    except Exception as e:
        return False, f"Transfer failed: {str(e)}", None

def create_interbank_transfer(from_account_id, to_account_number, amount, description, user_id):
    """Create an interbank transfer (requires admin approval)"""
    amount_decimal = Decimal(str(amount))
    
    # Validate source account
    from_balance = get_account_balance(from_account_id)
    if from_balance is None:
        return False, "Source account not found or inactive"
    
    # Check balance
    if from_balance < amount:
        return False, "Insufficient balance"
    
    # Check limits
    limits_ok, limits_error = check_transfer_limits(user_id, amount)
    if not limits_ok:
        return False, limits_error
    
    # Fraud detection
    fraud_flags = detect_fraud(user_id, from_account_id, amount)
    fraud_flags_json = json.dumps(fraud_flags) if fraud_flags else None
    status = 'flagged' if should_flag_transaction(fraud_flags) else 'pending'
    
    # Create pending transaction
    try:
        with db_transaction() as cursor:
            cursor.execute("""
                INSERT INTO Transactions (from_account_id, to_account_id, amount, transaction_type, status, description, fraud_flags)
                OUTPUT INSERTED.transaction_id
                VALUES (?, NULL, ?, 'interbank', ?, ?, ?)
            """, from_account_id, amount_decimal, status, description, fraud_flags_json)
            
            transaction_id = cursor.fetchone()[0]
            
            log_audit(user_id, 'INTERBANK_TRANSFER_CREATED', 'Transaction', transaction_id, {
                'from_account': from_account_id,
                'to_account_number': to_account_number,
                'amount': float(amount),
                'status': status
            })
        
        return True, "Interbank transfer created and pending approval", transaction_id
    
    except Exception as e:
        return False, f"Failed to create transfer: {str(e)}", None

def approve_interbank_transfer(transaction_id, admin_user_id, to_account_id):
    """Approve and process an interbank transfer"""
    with db_transaction() as cursor:
        # Get transaction details
        cursor.execute("""
            SELECT from_account_id, amount, status, user_id
            FROM Transactions
            WHERE transaction_id = ? AND transaction_type = 'interbank' AND status = 'pending'
        """, transaction_id)
        
        result = cursor.fetchone()
        if not result:
            return False, "Transaction not found or not pending"
        
        from_account_id, amount, status, user_id = result
        
        # Check if destination account exists (for interbank, we assume it exists externally)
        # In a real system, this would validate with the external bank
        # For now, we'll just mark it as completed
        
        # Debit from account
        cursor.execute("""
            UPDATE BankAccounts
            SET balance = balance - ?
            WHERE account_id = ?
        """, amount, from_account_id)
        
        # Update transaction
        cursor.execute("""
            UPDATE Transactions
            SET status = 'completed',
                to_account_id = ?,
                approved_by = ?,
                approved_at = GETDATE()
            WHERE transaction_id = ?
        """, to_account_id, admin_user_id, transaction_id)
        
        # Update limits
        update_transfer_limits(user_id, float(amount))
        
        log_audit(admin_user_id, 'INTERBANK_TRANSFER_APPROVED', 'Transaction', transaction_id, {
            'transaction_id': transaction_id,
            'user_id': user_id
        })
    
    return True, "Transfer approved and processed"

def reject_interbank_transfer(transaction_id, admin_user_id):
    """Reject an interbank transfer"""
    with db_transaction() as cursor:
        cursor.execute("""
            UPDATE Transactions
            SET status = 'rejected',
                approved_by = ?,
                approved_at = GETDATE()
            WHERE transaction_id = ? AND status = 'pending'
        """, admin_user_id, transaction_id)
        
        if cursor.rowcount == 0:
            return False, "Transaction not found or not pending"
        
        log_audit(admin_user_id, 'INTERBANK_TRANSFER_REJECTED', 'Transaction', transaction_id, {
            'transaction_id': transaction_id
        })
    
    return True, "Transfer rejected"
