from app.models import Base  # noqa: F401
from app.models import Connector, ConnectorConversationMapping, ConnectorDelivery, Conversation, FineTuneJob, ImportJob, Memory, Message, ModelProvider  # noqa: F401
from app.models import MemoryCandidate, MemoryEpisode, MemoryFact, MemoryRevision  # noqa: F401
from app.models import NormalizedMessage, Persona, RelationshipState, Skill, SkillInvocation, User, UserProfile  # noqa: F401

target_metadata = Base.metadata
