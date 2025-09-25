"""
API Data Service for managing temporary storage of API requests and responses.
Handles session-based data flow: upload → processing → results.
"""
import os
import uuid
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime, timedelta, timedelta
import shutil

from config.settings import settings
from utils.logging_config import get_logger
from models.data_models import ApiSession, ApiSessionStatus


class ApiDataService:
    """Service for managing temporary API data storage and sessions."""

    def __init__(self, logger=None):
        self.logger = logger or get_logger("ApiDataService")
        self.project_root = Path(__file__).parent.parent.parent

        # Directory paths
        self.incoming_dir = self.project_root / settings.api_input_dir
        self.processing_dir = self.project_root / "data/api/processing"
        self.results_dir = self.project_root / settings.api_output_dir

        # Ensure directories exist
        self._ensure_directories()

        # Session storage (in-memory for now, could be moved to database later)
        self.sessions: Dict[str, ApiSession] = {}

    def _ensure_directories(self):
        """Ensure all required directories exist."""
        for dir_path in [self.incoming_dir, self.processing_dir, self.results_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def create_session(self, client_info: Optional[Dict[str, Any]] = None) -> str:
        """Create a new API session with unique ID."""
        session_id = str(uuid.uuid4())

        session = ApiSession(
            session_id=session_id,
            status=ApiSessionStatus.CREATED,
            created_at=datetime.now(),
            client_info=client_info or {},
            files=[],
            metadata={}
        )

        self.sessions[session_id] = session
        self.logger.info(f"Created new API session: {session_id}")

        return session_id

    def get_session(self, session_id: str) -> Optional[ApiSession]:
        """Get session by ID."""
        return self.sessions.get(session_id)

    def update_session_status(self, session_id: str, status: ApiSessionStatus,
                            metadata: Optional[Dict[str, Any]] = None):
        """Update session status and optional metadata."""
        if session_id in self.sessions:
            self.sessions[session_id].status = status
            self.sessions[session_id].updated_at = datetime.now()

            if metadata:
                self.sessions[session_id].metadata.update(metadata)

            self.logger.info(f"Updated session {session_id} status to {status}")

    def store_uploaded_file(self, session_id: str, file_content: bytes,
                          filename: str, content_type: str = "application/octet-stream") -> str:
        """Store an uploaded file in the session's incoming directory."""
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")

        # Create session subdirectory
        session_incoming_dir = self.incoming_dir / session_id
        session_incoming_dir.mkdir(exist_ok=True)

        # Generate unique filename to avoid conflicts
        file_extension = Path(filename).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = session_incoming_dir / unique_filename

        # Write file
        with open(file_path, 'wb') as f:
            f.write(file_content)

        # Update session
        file_info = {
            "original_filename": filename,
            "stored_filename": unique_filename,
            "content_type": content_type,
            "size": len(file_content),
            "uploaded_at": datetime.now().isoformat()
        }

        self.sessions[session_id].files.append(file_info)
        self.update_session_status(session_id, ApiSessionStatus.FILES_UPLOADED)

        self.logger.info(f"Stored uploaded file for session {session_id}: {filename} -> {unique_filename}")

        return str(file_path)

    def get_session_files(self, session_id: str) -> List[Dict[str, Any]]:
        """Get list of files for a session."""
        if session_id not in self.sessions:
            return []

        return self.sessions[session_id].files

    def move_to_processing(self, session_id: str, data: Any) -> str:
        """Move session data to processing stage."""
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")

        # Create processing subdirectory
        session_processing_dir = self.processing_dir / session_id
        session_processing_dir.mkdir(exist_ok=True)

        # Store processing data (could be DataFrame, dict, etc.)
        processing_file = session_processing_dir / "processing_data.json"

        # Convert data to serializable format
        if hasattr(data, 'to_dict'):  # DataFrame
            serializable_data = data.to_dict('records')
        elif hasattr(data, 'dict'):  # Pydantic model
            serializable_data = data.dict()
        else:
            serializable_data = data

        with open(processing_file, 'w') as f:
            json.dump({
                "session_id": session_id,
                "data": serializable_data,
                "processed_at": datetime.now().isoformat()
            }, f, indent=2, default=str)

        self.update_session_status(session_id, ApiSessionStatus.PROCESSING,
                                 {"processing_file": str(processing_file)})

        self.logger.info(f"Moved session {session_id} to processing stage")

        return str(processing_file)

    def store_results(self, session_id: str, results: Any,
                     result_files: Optional[List[str]] = None) -> str:
        """Store final results for a session."""
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")

        # Create results subdirectory
        session_results_dir = self.results_dir / session_id
        session_results_dir.mkdir(exist_ok=True)

        # Store results data
        results_file = session_results_dir / "results.json"

        # Convert results to serializable format
        if hasattr(results, 'to_dict'):  # DataFrame
            serializable_results = results.to_dict('records')
        elif hasattr(results, 'dict'):  # Pydantic model
            serializable_results = results.dict()
        else:
            serializable_results = results

        results_data = {
            "session_id": session_id,
            "results": serializable_results,
            "completed_at": datetime.now().isoformat(),
            "result_files": result_files or []
        }

        with open(results_file, 'w') as f:
            json.dump(results_data, f, indent=2, default=str)

        # Copy any result files to results directory
        if result_files:
            for result_file in result_files:
                if os.path.exists(result_file):
                    shutil.copy2(result_file, session_results_dir)

        self.update_session_status(session_id, ApiSessionStatus.COMPLETED,
                                 {"results_file": str(results_file)})

        self.logger.info(f"Stored results for session {session_id}")

        return str(results_file)

    def get_results(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get results for a completed session."""
        if session_id not in self.sessions:
            return None

        session = self.sessions[session_id]
        if session.status != ApiSessionStatus.COMPLETED:
            return None

        results_file = self.results_dir / session_id / "results.json"
        if not results_file.exists():
            return None

        try:
            with open(results_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error reading results for session {session_id}: {e}")
            return None

    def cleanup_session(self, session_id: str, force: bool = False):
        """Clean up temporary data for a session."""
        if session_id not in self.sessions:
            return

        session = self.sessions[session_id]

        # Only cleanup completed sessions unless forced
        if not force and session.status not in [ApiSessionStatus.COMPLETED, ApiSessionStatus.ERROR]:
            self.logger.warning(f"Not cleaning up active session {session_id} (status: {session.status})")
            return

        # Remove session directories
        for base_dir in [self.incoming_dir, self.processing_dir, self.results_dir]:
            session_dir = base_dir / session_id
            if session_dir.exists():
                shutil.rmtree(session_dir)
                self.logger.info(f"Removed session directory: {session_dir}")

        # Remove from memory
        del self.sessions[session_id]
        self.logger.info(f"Cleaned up session {session_id}")

    def cleanup_expired_sessions(self, max_age_hours: int = 24):
        """Clean up sessions older than specified hours."""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        expired_sessions = []

        for session_id, session in self.sessions.items():
            if session.created_at < cutoff_time:
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            self.logger.info(f"Cleaning up expired session: {session_id}")
            self.cleanup_session(session_id, force=True)

        return len(expired_sessions)

    def cleanup_completed_sessions(self, max_age_hours: int = 1):
        """Clean up completed sessions older than specified hours."""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        old_completed_sessions = []

        for session_id, session in self.sessions.items():
            if (session.status in [ApiSessionStatus.COMPLETED, ApiSessionStatus.ERROR] and
                session.created_at < cutoff_time):
                old_completed_sessions.append(session_id)

        for session_id in old_completed_sessions:
            self.logger.info(f"Cleaning up old completed session: {session_id}")
            self.cleanup_session(session_id, force=True)

        return len(old_completed_sessions)

    def get_storage_stats(self):
        """Get storage statistics for API data."""
        stats = {
            "active_sessions": len(self.sessions),
            "total_sessions_created": len(self.sessions),  # In a real implementation, this would be persistent
            "storage_used": 0,
            "oldest_session": None
        }

        if self.sessions:
            oldest_session = min(self.sessions.values(), key=lambda s: s.created_at)
            stats["oldest_session"] = oldest_session.created_at.isoformat()

            # Calculate approximate storage used
            for session in self.sessions.values():
                # Count files
                session_dir = self.incoming_dir / session.session_id
                if session_dir.exists():
                    for file_path in session_dir.rglob('*'):
                        if file_path.is_file():
                            stats["storage_used"] += file_path.stat().st_size

        return stats

    def list_active_sessions(self) -> List[Dict[str, Any]]:
        """List all active sessions with their status."""
        return [
            {
                "session_id": session.session_id,
                "status": session.status.value,
                "created_at": session.created_at.isoformat(),
                "files_count": len(session.files),
                "client_info": session.client_info
            }
            for session in self.sessions.values()
        ]