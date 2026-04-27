from enum import Enum


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ImportSourceType(str, Enum):
    TXT = "txt"
    CSV = "csv"
    JSON = "json"
    XLSX = "xlsx"


class ImportStatus(str, Enum):
    PREVIEWED = "previewed"
    COMMITTED = "committed"
    FAILED = "failed"


class MemoryType(str, Enum):
    SESSION = "session"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    INSTRUCTION = "instruction"


class ConnectorPlatform(str, Enum):
    FEISHU = "feishu"


class ConnectorStatus(str, Enum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    ERROR = "error"


class ProviderType(str, Enum):
    DEEPSEEK = "deepseek"
    OPENAI_COMPATIBLE = "openai_compatible"
    OLLAMA = "ollama"
    LOCAL_ADAPTER = "local_adapter"


class SkillStatus(str, Enum):
    DISABLED = "disabled"
    ACTIVE = "active"


class FineTuneBackend(str, Enum):
    LOCAL_LORA = "local_lora"
    LOCAL_QLORA = "local_qlora"


class FineTuneJobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ConversationStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
