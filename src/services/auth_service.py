"""
Authentication Service for DBSyncr
Handles JWT token generation, validation, and user management.
"""
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt
from src.models.data_models import User, UserCreate, UserRole, TokenData
from config.settings import settings
from utils.logging_config import get_logger


class AuthService:
    """Service for handling authentication and authorization."""

    def __init__(self):
        self.logger = get_logger("AuthService")
        # Try bcrypt first, fallback to pbkdf2 if bcrypt fails
        try:
            self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            # Test that bcrypt works
            test_hash = self.pwd_context.hash("test")
            self.pwd_context.verify("test", test_hash)
        except Exception as e:
            self.logger.warning(f"Bcrypt context failed: {e}. Using pbkdf2_sha256 fallback.")
            self.pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

        # JWT settings
        self.secret_key = settings.secret_key
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30  # 30 minutes

        # In-memory user store (replace with database in production)
        self.users: Dict[str, User] = {}
        self._create_default_admin()

    def _create_default_admin(self):
        """Create default admin user."""
        admin_user = UserCreate(
            username="admin",
            email="admin@dbsyncr.local",
            password="admin123",
            full_name="System Administrator",
            role=UserRole.ADMIN
        )
        self.create_user(admin_user)

        # Add default test user for integration tests
        test_user = UserCreate(
            username="testuser",
            email="testuser@dbsyncr.local",
            password="testpassword123",
            full_name="Test User",
            role=UserRole.USER
        )
        self.create_user(test_user)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Hash a password."""
        return self.pwd_context.hash(password)

    def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        if user_data.username in self.users:
            raise ValueError(f"User {user_data.username} already exists")

        user = User(
            id=str(len(self.users) + 1),
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            role=user_data.role,
            hashed_password=self.get_password_hash(user_data.password),
            created_at=datetime.utcnow()
        )

        self.users[user.username] = user
        self.logger.info(f"Created user: {user.username}")
        return user

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user."""
        self.logger.info(f"Authenticating user: {username}")
        self.logger.info(f"Available users: {list(self.users.keys())}")
        user = self.users.get(username)
        self.logger.info(f"User found: {user is not None}")
        if not user:
            return None
        if user.disabled:
            return None
        if not self.verify_password(password, user.hashed_password or ''):
            self.logger.info("Password verification failed")
            return None
        self.logger.info("Authentication successful")
        return user

    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)

        to_encode.update({"exp": expire})
        # Ensure sub is a string
        if "sub" in to_encode:
            to_encode["sub"] = str(to_encode["sub"])
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def verify_token(self, token: str) -> Optional[TokenData]:
        """Verify and decode a JWT token."""
        try:
            self.logger.info(f"Verifying token: {token[:20]}...")
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            self.logger.info(f"Decoded payload: {payload}")
            username: str = payload.get("sub")
            role: str = payload.get("role")
            self.logger.info(f"Extracted user_id: {username}, role: {role}")
            if username is None:
                return None
            return TokenData(username=username, role=UserRole(role) if role else None)
        except JWTError as e:
            self.logger.error(f"JWT verification failed: {e}")
            return None

    def get_user(self, username: str) -> Optional[User]:
        """Get a user by username."""
        return self.users.get(username)

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get a user by ID."""
        for user in self.users.values():
            if user.id == user_id:
                return user
        return None

    def update_user(self, username: str, updates: Dict[str, Any]) -> Optional[User]:
        """Update user information."""
        user = self.users.get(username)
        if not user:
            return None

        for key, value in updates.items():
            if hasattr(user, key):
                setattr(user, key, value)

        user.updated_at = datetime.now()
        self.users[username] = user
        return user

    def change_password(self, username: str, current_password: str, new_password: str) -> bool:
        """Change user password."""
        user = self.authenticate_user(username, current_password)
        if not user:
            return False

        user.__dict__['hashed_password'] = self.get_password_hash(new_password)
        user.updated_at = datetime.now()
        return True

    def get_current_user(self, token: str) -> Optional[User]:
        """Get current user from JWT token."""
        token_data = self.verify_token(token)
        if not token_data or not token_data.username:
            return None
        return self.get_user(token_data.username)