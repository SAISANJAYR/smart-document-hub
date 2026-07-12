"""
hashing.py — Password Hashing Utilities
---------------------------------------
Provides functions to hash passwords securely before saving them to the database,
and to verify plain-text passwords against their hashed versions during login.

CONCEPT: 
A hash function is a one-way mathematical algorithm. You can turn "password123" 
into a scrambled string like "$2b$12$e..." but you can NEVER reverse the scramble 
back to "password123". This is why databases can verify passwords without actually 
knowing what they are!
"""

import bcrypt

def get_password_hash(password: str) -> str:
    """
    Takes a plain-text password and returns its securely hashed version.
    """
    # bcrypt requires bytes, so we encode the password to utf-8.
    # gensalt() generates a random salt so identical passwords produce different hashes.
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(password_bytes, salt)
    return hashed_bytes.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compares a plain-text password attempt with the hashed password
    stored in the database. Returns True if they match.
    """
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)
