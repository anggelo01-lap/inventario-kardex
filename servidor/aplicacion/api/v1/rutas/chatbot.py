from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from aplicacion.api.dependencias import get_current_user
from aplicacion.nucleo.base_datos import get_db
from aplicacion.modelos.usuario import User
from aplicacion.esquemas.chatbot import (
    ChatbotConsultaIn,
    ChatbotConsultaOut,
    ChatbotMessageIn,
    ChatbotMessageOut,
    ChatbotResolveOptionIn,
    ChatbotSuggestionOut,
)
from aplicacion.servicios.servicio_chatbot import (
    listar_sugerencias_chatbot,
    procesar_mensaje_chatbot,
    responder_consulta_inventario,
    resolver_opcion_chatbot,
)

router = APIRouter(prefix="/chatbot", tags=["chatbot"])


@router.post("/consultar", response_model=ChatbotConsultaOut)
def post_consulta(
    payload: ChatbotConsultaIn,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    respuesta, intent, confianza, producto_id, producto_nombre = responder_consulta_inventario(
        db,
        payload.pregunta,
        historial=payload.historial,
        contexto_producto_id=payload.contexto_producto_id,
        contexto_producto_nombre=payload.contexto_producto_nombre,
    )
    return ChatbotConsultaOut(
        respuesta=respuesta,
        intent=intent,
        confianza=confianza,
        contexto_producto_id=producto_id,
        contexto_producto_nombre=producto_nombre,
    )


@router.post("/message", response_model=ChatbotMessageOut)
def post_message(
    payload: ChatbotMessageIn,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = procesar_mensaje_chatbot(
        db,
        message=payload.message,
        session_id=payload.session_id,
        user_id=payload.user_id,
        historial=payload.historial,
        contexto_producto_id=payload.contexto_producto_id,
        contexto_producto_nombre=payload.contexto_producto_nombre,
    )
    return ChatbotMessageOut(**result)


@router.post("/resolve-option", response_model=ChatbotMessageOut)
def post_resolve_option(
    payload: ChatbotResolveOptionIn,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = resolver_opcion_chatbot(
        db,
        session_id=payload.session_id,
        user_id=payload.user_id,
        selected_option_id=payload.selected_option_id,
    )
    return ChatbotMessageOut(**result)


@router.get("/suggestions", response_model=list[ChatbotSuggestionOut])
def get_suggestions(
    _: User = Depends(get_current_user),
):
    suggestions = listar_sugerencias_chatbot()
    return [ChatbotSuggestionOut(**item) for item in suggestions]
