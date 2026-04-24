from dataclasses import dataclass, field


@dataclass
class AppSettings:
    min_width: int
    min_height: int
    jpeg_quality: int

    use_ai: bool
    use_threads: bool
    max_workers: int

    ai_exe_path: str
    ai_model: str
    ai_scale: int

    keep_original_if_no_resize: bool
    overwrite_files: bool

    auto_style_analysis: bool = False
    advanced_monitoring: bool = True
    save_settings: bool = True

    ai_gpu_id: int = 0
    ai_tile_size: int = 128
    ai_thread_config: str = "1:1:1"
    ai_cooldown_seconds: float = 0.5


@dataclass
class ProcessingStats:
    total_count: int = 0
    done_count: int = 0

    copied_count: int = 0
    processed_count: int = 0
    error_count: int = 0

    copied_files: list[str] = field(default_factory=list)
    processed_files: list[str] = field(default_factory=list)
    error_files: list[str] = field(default_factory=list)

    def total_percent(self) -> int:
        if self.total_count <= 0:
            return 0
        return int(self.done_count / self.total_count * 100)

    def copied_percent(self) -> int:
        if self.total_count <= 0:
            return 0
        return int(self.copied_count / self.total_count * 100)

    def processed_percent(self) -> int:
        if self.total_count <= 0:
            return 0
        return int(self.processed_count / self.total_count * 100)

    def error_percent(self) -> int:
        if self.total_count <= 0:
            return 0
        return int(self.error_count / self.total_count * 100)

    def add_copied(self, filename: str):
        self.done_count += 1
        self.copied_count += 1
        self.copied_files.append(filename)

    def add_processed(self, filename: str):
        self.done_count += 1
        self.processed_count += 1
        self.processed_files.append(filename)

    def add_error(self, filename: str):
        self.done_count += 1
        self.error_count += 1
        self.error_files.append(filename)


@dataclass
class ProcessResult:
    status: str
    output_path: str | None = None
    error: str | None = None

    @property
    def is_copied(self) -> bool:
        return self.status == "copied"

    @property
    def is_processed(self) -> bool:
        return self.status == "processed"

    @property
    def is_error(self) -> bool:
        return self.status == "error"

    @property
    def is_cancelled(self) -> bool:
        return self.status == "cancelled"
