from dataclasses import dataclass


@dataclass
class ObjectStore:
    """
    Future S3-compatible adapter.
    Stub only: upload/download contracts will be implemented in API phase.
    """

    endpoint: str = ""

    def upload_file(self, local_path: str, object_key: str) -> str:
        raise NotImplementedError

    def download_file(self, object_key: str, local_path: str) -> None:
        raise NotImplementedError

