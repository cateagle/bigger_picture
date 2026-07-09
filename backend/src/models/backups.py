from datetime import datetime

from pydantic import BaseModel, Field


class BackupInfo(BaseModel):
    """A single database backup file in the backup directory."""

    filename: str = Field(description="Backup zip filename, e.g. db_backup_2026-07-09T10:45:03.zip.")
    size_bytes: int = Field(description="Size of the zip file in bytes.")
    created_at: datetime | None = Field(
        description="Timestamp parsed from the filename (UTC). Null if the filename doesn't match the expected db_backup_<timestamp>.zip pattern, e.g. a file added by hand."
    )


class BackupListResponse(BaseModel):
    backups: list[BackupInfo] = Field(
        description="All backups currently in the backup directory, newest first."
    )
