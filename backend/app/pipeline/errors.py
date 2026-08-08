class PipelineStageFailed(Exception):
    """Raised when a pipeline stage exhausts its retries. Caught by the
    runner (app/pipeline/runner.py) to stop the chain for this lead without
    crashing the rest of the batch."""

    def __init__(self, stage: str, message: str):
        super().__init__(f"{stage} failed: {message}")
        self.stage = stage
