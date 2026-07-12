"""
test_hashing.py — Unit Tests for Password Hashing
-------------------------------------------------
Tests the get_password_hash and verify_password functions.
"""

from app.core.auth.hashing import get_password_hash, verify_password

def test_password_hashing():
    """
    Test that a password can be hashed and verified correctly,
    and that a wrong password fails verification.
    """
    password = "supersecretpassword123!"
    
    # 1. Hash the password
    hashed = get_password_hash(password)
    
    # The hash should not be the same as the plain text
    assert hashed != password
    
    # 2. Verify the correct password
    assert verify_password(password, hashed) is True
    
    # 3. Verify that an incorrect password fails
    assert verify_password("wrongpassword", hashed) is False

def test_password_hashing_is_unique():
    """
    Bcrypt uses a random 'salt' every time it hashes.
    This means hashing the exact same password twice should produce
    two completely DIFFERENT hashes (but both will still verify correctly).
    """
    password = "hello_world"
    
    hash1 = get_password_hash(password)
    hash2 = get_password_hash(password)
    
    # The hashes must be different
    assert hash1 != hash2
    
    # Both must still verify the original password
    assert verify_password(password, hash1) is True
    assert verify_password(password, hash2) is True
