import bcrypt

class Hash:
    @staticmethod
    def _truncate_password(password: str) -> bytes:
        """Truncate password to 72 bytes (bcrypt's limit) and return as bytes."""
        return password.encode('utf-8')[:72]
    
    @staticmethod
    def bcrypt(password: str) -> str:
        """Hash a password using bcrypt."""
        password_bytes = Hash._truncate_password(password)
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash."""
        password_bytes = Hash._truncate_password(plain_password)
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
