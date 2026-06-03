from pydantic import BaseModel, Field


class ChatbotHistorialItem(BaseModel):
    role: str
    text: str


class ChatbotContextIn(BaseModel):
    almacen_id: int | None = None
    fecha_desde: str | None = None
    fecha_hasta: str | None = None


class ChatbotMessageIn(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    session_id: str = Field(min_length=1, max_length=120)
    user_id: int
    context: ChatbotContextIn | None = None
    historial: list[ChatbotHistorialItem] = Field(default_factory=list)
    contexto_producto_id: int | None = None
    contexto_producto_nombre: str | None = None


class ChatbotOption(BaseModel):
    id: int
    label: str


class ChatbotMessageOut(BaseModel):
    status: str
    intent: str
    answer: str
    data: dict | None = None
    options: list[ChatbotOption] = Field(default_factory=list)
    confidence: float
    trace_id: str
    session_id: str
    contexto_producto_id: int | None = None
    contexto_producto_nombre: str | None = None


class ChatbotResolveOptionIn(BaseModel):
    session_id: str = Field(min_length=1, max_length=120)
    selected_option_id: int
    user_id: int


class ChatbotSuggestionOut(BaseModel):
    id: str
    label: str


class ChatbotConsultaIn(BaseModel):
    pregunta: str
    historial: list[ChatbotHistorialItem] = Field(default_factory=list)
    contexto_producto_id: int | None = None
    contexto_producto_nombre: str | None = None


class ChatbotConsultaOut(BaseModel):
    respuesta: str
    intent: str
    confianza: float
    contexto_producto_id: int | None = None
    contexto_producto_nombre: str | None = None
