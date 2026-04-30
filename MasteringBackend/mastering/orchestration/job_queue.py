from datetime import datetime, timezone

from mastering.contracts.jobs import JobRecord, JobStatus


def set_job_status(job: JobRecord, status: JobStatus, error_message: str | None = None) -> JobRecord:
    job.status = status
    job.error_message = error_message
    job.updated_at = datetime.now(timezone.utc)
    return job

