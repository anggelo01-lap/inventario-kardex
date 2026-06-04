from collections.abc import Generator
from pathlib import Path
from threading import Barrier, Lock, Thread

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from aplicacion.nucleo.configuracion import get_settings
from aplicacion.nucleo.base_datos import get_db
from aplicacion.nucleo.seguridad import hash_password
from aplicacion.excepciones import StockInsuficienteError
from aplicacion.principal import app
from aplicacion.modelos.categoria import Categoria
from aplicacion.modelos.movimiento import Movimiento
from aplicacion.modelos.producto import Producto
from aplicacion.modelos.usuario import User
from aplicacion.esquemas.movimiento import MovimientoCreate
from aplicacion.servicios.servicio_inicializacion import seed_admin_user
from aplicacion.servicios.servicio_movimiento import registrar_movimiento


@pytest.fixture()
def client(tmp_path: Path, testing_session_local) -> Generator[TestClient]:
    with testing_session_local() as db:
        db.add_all(
            [
                User(
                    username="angel",
                    full_name="Angel Admin",
                    email="angel@example.com",
                    hashed_password=hash_password("123456"),
                    is_active=True,
                    role="admin",
                ),
                User(
                    username="operador",
                    full_name="Olga Operadora",
                    email="operador@example.com",
                    hashed_password=hash_password("123456"),
                    is_active=True,
                    role="usuario",
                ),
                User(
                    username="inactivo",
                    full_name="Ines Inactiva",
                    email="inactivo@example.com",
                    hashed_password=hash_password("123456"),
                    is_active=False,
                    role="usuario",
                ),
            ]
        )
        db.commit()

    def override_get_db() -> Generator[Session]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    settings = get_settings()
    original_media_root = settings.media_root
    settings.media_root = str(tmp_path / "subidas")

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    settings.media_root = original_media_root


def _auth_headers(
    client: TestClient,
    *,
    username: str = "angel",
    password: str = "123456",
) -> dict[str, str]:
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _crear_categoria(client: TestClient, headers: dict[str, str], nombre: str) -> dict:
    resp = client.post(
        "/api/v1/categorias",
        headers=headers,
        json={"nombre": nombre, "descripcion": f"Descripcion {nombre}"},
    )
    assert resp.status_code == 201
    return resp.json()


def _crear_proveedor(client: TestClient, headers: dict[str, str], nombre: str) -> dict:
    resp = client.post(
        "/api/v1/proveedores",
        headers=headers,
        json={"nombre": nombre, "contacto": "Laura", "telefono": "999999999"},
    )
    assert resp.status_code == 201
    return resp.json()


def _crear_cliente(client: TestClient, headers: dict[str, str], nombre: str) -> dict:
    resp = client.post(
        "/api/v1/clientes",
        headers=headers,
        json={"nombre": nombre, "documento": "12345678"},
    )
    assert resp.status_code == 201
    return resp.json()


def _crear_producto(
    client: TestClient,
    headers: dict[str, str],
    *,
    categoria_id: int,
    codigo: str,
    nombre: str,
    tipo: str = "producto",
    stock_inicial: int = 10,
    stock_minimo: int = 1,
    precio: float = 10.0,
) -> dict:
    resp = client.post(
        "/api/v1/productos",
        headers=headers,
        json={
            "codigo": codigo,
            "nombre": nombre,
            "descripcion": f"Descripcion {nombre}",
            "categoria_id": categoria_id,
            "tipo": tipo,
            "stock_inicial": stock_inicial,
            "stock_minimo": stock_minimo,
            "precio": precio,
        },
    )
    assert resp.status_code == 201
    return resp.json()


def test_auth_login_ok(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "angel", "password": "123456"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str) and data["access_token"]


def test_auth_login_rejects_inactive_user(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "inactivo", "password": "123456"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Credenciales invalidas"


def test_dashboard_requires_auth(client: TestClient) -> None:
    resp = client.get("/api/v1/tablero/resumen")
    assert resp.status_code == 401


def test_dashboard_resumen_uses_real_movements(client: TestClient) -> None:
    headers = _auth_headers(client)
    categoria = _crear_categoria(client, headers, "Dashboard")
    producto = _crear_producto(
        client,
        headers,
        categoria_id=categoria["id"],
        codigo="DSH-001",
        nombre="Producto Dashboard",
        stock_inicial=12,
        stock_minimo=2,
        precio=10.0,
    )

    salida = client.post(
        "/api/v1/movimientos",
        headers=headers,
        json={
            "producto_id": producto["id"],
            "tipo": "salida",
            "cantidad": 3,
            "costo_unitario": 6,
            "motivo": "Venta dashboard",
        },
    )
    assert salida.status_code == 201

    resp = client.get("/api/v1/tablero/resumen?periodo=7d&agrupar_por=dia", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["ventas_estimadas"]["valor"] == 30.0
    assert body["cantidad_vendida"]["valor"] == 3.0
    assert body["ganancia_estimada"]["valor"] == 12.0
    assert body["top_productos_cantidad"][0]["codigo"] == "DSH-001"
    assert body["top_productos_monto"][0]["total_monto"] == 30.0
    assert body["movimientos_recientes"][0]["producto_codigo"] == "DSH-001"
    assert body["serie_ventas"][0]["valor"] == 30.0


def test_health_returns_db_status_and_request_id(client: TestClient) -> None:
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["estado"] == "activo"
    assert data["database"] == "ok"
    assert "X-Request-ID" in resp.headers


def test_seed_admin_user_creates_admin(db_session: Session) -> None:
    user, created = seed_admin_user(
        db_session,
        username="root",
        email="root@example.com",
        full_name="Root Admin",
        password="Admin12345",
    )
    assert created is True
    assert user.role == "admin"
    assert user.is_active is True


def test_seed_admin_user_updates_existing_user(db_session: Session) -> None:
    db_session.add(
        User(
            username="root",
            full_name="Viejo",
            email="root@example.com",
            hashed_password=hash_password("123456"),
            is_active=False,
            role="usuario",
        )
    )
    db_session.commit()

    user, created = seed_admin_user(
        db_session,
        username="root",
        email="root@example.com",
        full_name="Root Admin",
        password="Admin12345",
    )
    assert created is False
    assert user.full_name == "Root Admin"
    assert user.role == "admin"
    assert user.is_active is True


def test_categoria_create_and_list(client: TestClient) -> None:
    headers = _auth_headers(client)
    create = client.post(
        "/api/v1/categorias",
        headers=headers,
        json={"nombre": "Repuestos", "descripcion": "Repuestos motos"},
    )
    assert create.status_code == 201

    listed = client.get("/api/v1/categorias", headers=headers)
    assert listed.status_code == 200
    categorias = listed.json()
    assert any(c["nombre"] == "Repuestos" for c in categorias)


def test_categoria_update_requires_admin(client: TestClient) -> None:
    admin_headers = _auth_headers(client)
    user_headers = _auth_headers(client, username="operador")
    categoria = _crear_categoria(client, admin_headers, "Seguridad")

    resp = client.put(
        f"/api/v1/categorias/{categoria['id']}",
        headers=user_headers,
        json={"nombre": "Seguridad industrial"},
    )
    assert resp.status_code == 403


def test_producto_create_with_categoria(client: TestClient) -> None:
    headers = _auth_headers(client)
    categoria = _crear_categoria(client, headers, "Insumos")

    create_producto = client.post(
        "/api/v1/productos",
        headers=headers,
        json={
            "codigo": "INS-001",
            "nombre": "Lubricante",
            "descripcion": "Spray",
            "categoria_id": categoria["id"],
            "tipo": "insumo",
            "stock_inicial": 10,
            "stock_minimo": 2,
            "precio": 35.5,
        },
    )
    assert create_producto.status_code == 201
    body = create_producto.json()
    assert body["categoria_id"] == categoria["id"]
    assert body["tipo"] == "insumo"


def test_producto_can_store_image_and_provider(client: TestClient) -> None:
    headers = _auth_headers(client)
    categoria = _crear_categoria(client, headers, "Visuales")
    proveedor = _crear_proveedor(client, headers, "Proveedor Imagen")

    resp = client.post(
        "/api/v1/productos",
        headers=headers,
        json={
            "codigo": "IMG-001",
            "nombre": "Producto con imagen",
            "descripcion": "Con proveedor",
            "categoria_id": categoria["id"],
            "proveedor_id": proveedor["id"],
            "tipo": "producto",
            "image_url": "https://ejemplo.com/imagen.png",
            "stock_inicial": 4,
            "stock_minimo": 1,
            "precio": 9.5,
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["image_url"] == "https://ejemplo.com/imagen.png"
    assert body["proveedor"]["nombre"] == "Proveedor Imagen"


def test_producto_upload_image_returns_local_media_url(client: TestClient) -> None:
    headers = _auth_headers(client)
    settings = get_settings()

    resp = client.post(
        "/api/v1/productos/upload-imagen",
        headers=headers,
        files={"file": ("casco.png", b"\x89PNG\r\n\x1a\nfake-image", "image/png")},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["image_url"].startswith("/subidas/productos/")
    relative_media_path = Path(body["image_url"].removeprefix("/subidas/"))
    stored_file = settings.media_root_path / relative_media_path
    assert stored_file.exists()


def test_movimiento_salida_stock_insuficiente_returns_400(client: TestClient) -> None:
    headers = _auth_headers(client)
    categoria = _crear_categoria(client, headers, "Productos")
    producto = _crear_producto(
        client,
        headers,
        categoria_id=categoria["id"],
        codigo="PROD-001",
        nombre="Casco",
        stock_inicial=1,
        stock_minimo=0,
        precio=120.0,
    )

    salida = client.post(
        "/api/v1/movimientos",
        headers=headers,
        json={"producto_id": producto["id"], "tipo": "salida", "cantidad": 5},
    )
    assert salida.status_code == 400
    assert salida.json()["detail"] == "Stock insuficiente"


def test_movimiento_can_link_cliente_and_audit_stock(client: TestClient) -> None:
    headers = _auth_headers(client)
    categoria = _crear_categoria(client, headers, "Clientes")
    cliente = _crear_cliente(client, headers, "Cliente Demo")
    producto = _crear_producto(
        client,
        headers,
        categoria_id=categoria["id"],
        codigo="CLT-001",
        nombre="Producto cliente",
        stock_inicial=8,
        stock_minimo=2,
        precio=30.0,
    )

    resp = client.post(
        "/api/v1/movimientos",
        headers=headers,
        json={
            "producto_id": producto["id"],
            "cliente_id": cliente["id"],
            "tipo": "salida",
            "cantidad": 3,
            "motivo": "Venta mostrador",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["cliente_id"] == cliente["id"]
    assert body["stock_anterior"] == 8
    assert body["stock_posterior"] == 5


def test_usuario_solo_ve_sus_movimientos_en_listado_y_paginado(client: TestClient) -> None:
    admin_headers = _auth_headers(client, username="angel")
    user_headers = _auth_headers(client, username="operador")

    categoria = _crear_categoria(client, admin_headers, "Roles Movimientos")
    producto = _crear_producto(
        client,
        admin_headers,
        categoria_id=categoria["id"],
        codigo="ROL-001",
        nombre="Producto Roles",
        stock_inicial=50,
        stock_minimo=0,
        precio=10.0,
    )

    resp_admin_create = client.post(
        "/api/v1/movimientos",
        headers=admin_headers,
        json={"producto_id": producto["id"], "tipo": "entrada", "cantidad": 2, "motivo": "Admin crea"},
    )
    assert resp_admin_create.status_code == 201

    resp_user_create = client.post(
        "/api/v1/movimientos",
        headers=user_headers,
        json={"producto_id": producto["id"], "tipo": "entrada", "cantidad": 3, "motivo": "Usuario crea"},
    )
    assert resp_user_create.status_code == 201

    user_list = client.get("/api/v1/movimientos?limit=50", headers=user_headers)
    assert user_list.status_code == 200
    user_items = user_list.json()
    assert len(user_items) >= 1
    assert all(row["usuario_username"] == "operador" for row in user_items)

    user_page = client.get("/api/v1/movimientos/paginado?page=1&page_size=50", headers=user_headers)
    assert user_page.status_code == 200
    user_page_items = user_page.json()["items"]
    assert len(user_page_items) >= 1
    assert all(row["usuario_username"] == "operador" for row in user_page_items)

    admin_list = client.get("/api/v1/movimientos?limit=50", headers=admin_headers)
    assert admin_list.status_code == 200
    admin_items = admin_list.json()
    usernames = {row["usuario_username"] for row in admin_items}
    assert "angel" in usernames
    assert "operador" in usernames


def test_chatbot_answers_stock_and_daily_entries(client: TestClient) -> None:
    headers = _auth_headers(client)
    categoria = _crear_categoria(client, headers, "Chatbot")
    producto = _crear_producto(
        client,
        headers,
        categoria_id=categoria["id"],
        codigo="BOT-001",
        nombre="Casco Bot",
        stock_inicial=6,
        stock_minimo=2,
        precio=99.0,
    )

    entrada = client.post(
        "/api/v1/movimientos",
        headers=headers,
        json={"producto_id": producto["id"], "tipo": "entrada", "cantidad": 2, "motivo": "Reposicion"},
    )
    assert entrada.status_code == 201

    stock_resp = client.post(
        "/api/v1/chatbot/consultar",
        headers=headers,
        json={"pregunta": "cuanto stock hay de casco bot"},
    )
    assert stock_resp.status_code == 200
    assert "stock actual" in stock_resp.json()["respuesta"].lower()

    daily_resp = client.post(
        "/api/v1/chatbot/consultar",
        headers=headers,
        json={"pregunta": "cuantas entradas hubo hoy"},
    )
    assert daily_resp.status_code == 200
    assert "ingresaron" in daily_resp.json()["respuesta"].lower()


def test_chatbot_can_follow_product_context(client: TestClient) -> None:
    headers = _auth_headers(client)
    categoria = _crear_categoria(client, headers, "Chatbot Contexto")
    producto = _crear_producto(
        client,
        headers,
        categoria_id=categoria["id"],
        codigo="CTX-001",
        nombre="Casco Contexto",
        stock_inicial=5,
        stock_minimo=1,
        precio=149.0,
    )

    primera = client.post(
        "/api/v1/chatbot/consultar",
        headers=headers,
        json={"pregunta": "cuanto stock hay de casco contexto"},
    )
    assert primera.status_code == 200
    body = primera.json()
    assert body["contexto_producto_id"] == producto["id"]

    segunda = client.post(
        "/api/v1/chatbot/consultar",
        headers=headers,
        json={
            "pregunta": "y su precio?",
            "contexto_producto_id": body["contexto_producto_id"],
            "contexto_producto_nombre": body["contexto_producto_nombre"],
            "historial": [
                {"role": "user", "text": "cuanto stock hay de casco contexto"},
                {"role": "assistant", "text": body["respuesta"]},
            ],
        },
    )
    assert segunda.status_code == 200
    assert "149.00" in segunda.json()["respuesta"]


def test_movimiento_cantidad_cero_returns_400(client: TestClient) -> None:
    headers = _auth_headers(client)
    categoria = _crear_categoria(client, headers, "Cantidades")
    producto = _crear_producto(
        client,
        headers,
        categoria_id=categoria["id"],
        codigo="CNT-001",
        nombre="Producto cantidad",
    )

    resp = client.post(
        "/api/v1/movimientos",
        headers=headers,
        json={"producto_id": producto["id"], "tipo": "entrada", "cantidad": 0},
    )
    assert resp.status_code == 400
    assert "cantidad" in resp.json()["detail"].lower()


def test_movimiento_tipo_invalido_returns_400(client: TestClient) -> None:
    headers = _auth_headers(client)
    categoria = _crear_categoria(client, headers, "Tipos")
    producto = _crear_producto(
        client,
        headers,
        categoria_id=categoria["id"],
        codigo="TIP-001",
        nombre="Producto tipo",
    )

    resp = client.post(
        "/api/v1/movimientos",
        headers=headers,
        json={"producto_id": producto["id"], "tipo": "inventado", "cantidad": 1},
    )
    assert resp.status_code == 400
    assert "tipo" in resp.json()["detail"].lower()


def test_kardex_filtrado_por_producto(client: TestClient) -> None:
    headers = _auth_headers(client)
    categoria = _crear_categoria(client, headers, "Filtros")
    producto = _crear_producto(
        client,
        headers,
        categoria_id=categoria["id"],
        codigo="REP-100",
        nombre="Filtro de aceite",
        tipo="repuesto",
        stock_inicial=10,
        stock_minimo=1,
        precio=50.0,
    )

    mov = client.post(
        "/api/v1/movimientos",
        headers=headers,
        json={"producto_id": producto["id"], "tipo": "entrada", "cantidad": 4},
    )
    assert mov.status_code == 201

    kardex = client.get(
        f"/api/v1/movimientos?producto_id={producto['id']}&limit=50",
        headers=headers,
    )
    assert kardex.status_code == 200
    rows = kardex.json()
    assert len(rows) >= 1
    assert all(r["producto_id"] == producto["id"] for r in rows)


def test_admin_can_list_users(client: TestClient) -> None:
    headers = _auth_headers(client)
    resp = client.get("/api/v1/usuarios", headers=headers)
    assert resp.status_code == 200
    usernames = [row["username"] for row in resp.json()]
    assert "angel" in usernames
    assert "operador" in usernames


def test_non_admin_cannot_list_users(client: TestClient) -> None:
    headers = _auth_headers(client, username="operador")
    resp = client.get("/api/v1/usuarios", headers=headers)
    assert resp.status_code == 403


def test_admin_cannot_demote_self(client: TestClient) -> None:
    headers = _auth_headers(client)
    resp = client.patch(
        "/api/v1/usuarios/1/rol",
        headers=headers,
        json={"role": "usuario"},
    )
    assert resp.status_code == 400
    assert "administrador" in resp.json()["detail"]


def test_admin_cannot_deactivate_self(client: TestClient) -> None:
    headers = _auth_headers(client)
    resp = client.patch(
        "/api/v1/usuarios/1/activo",
        headers=headers,
        json={"is_active": False},
    )
    assert resp.status_code == 400
    assert "propio usuario" in resp.json()["detail"]


def test_admin_can_update_other_user_role_and_active(client: TestClient) -> None:
    headers = _auth_headers(client)

    role_resp = client.patch(
        "/api/v1/usuarios/2/rol",
        headers=headers,
        json={"role": "admin"},
    )
    assert role_resp.status_code == 200
    assert role_resp.json()["role"] == "admin"

    active_resp = client.patch(
        "/api/v1/usuarios/2/activo",
        headers=headers,
        json={"is_active": False},
    )
    assert active_resp.status_code == 200
    assert active_resp.json()["is_active"] is False


def test_export_productos_requires_auth(client: TestClient) -> None:
    resp = client.get("/api/v1/export/productos.xlsx")
    assert resp.status_code == 401


def test_export_productos_returns_xlsx(client: TestClient) -> None:
    headers = _auth_headers(client)
    categoria = _crear_categoria(client, headers, "Exportables")
    _crear_producto(
        client,
        headers,
        categoria_id=categoria["id"],
        codigo="EXP-001",
        nombre="Producto exportable",
    )

    resp = client.get("/api/v1/export/productos.xlsx", headers=headers)
    assert resp.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in resp.headers["content-type"]
    assert len(resp.content) > 0


def test_non_admin_cannot_export_productos(client: TestClient) -> None:
    headers = _auth_headers(client, username="operador")
    resp = client.get("/api/v1/export/productos.xlsx", headers=headers)
    assert resp.status_code == 403


def test_export_movimientos_returns_pdf(client: TestClient) -> None:
    headers = _auth_headers(client)
    categoria = _crear_categoria(client, headers, "PDF")
    producto = _crear_producto(
        client,
        headers,
        categoria_id=categoria["id"],
        codigo="PDF-001",
        nombre="Producto PDF",
    )
    mov = client.post(
        "/api/v1/movimientos",
        headers=headers,
        json={"producto_id": producto["id"], "tipo": "entrada", "cantidad": 2},
    )
    assert mov.status_code == 201

    resp = client.get("/api/v1/export/movimientos.pdf", headers=headers)
    assert resp.status_code == 200
    assert "application/pdf" in resp.headers["content-type"]
    assert len(resp.content) > 0


def test_non_admin_cannot_export_movimientos_pdf(client: TestClient) -> None:
    headers = _auth_headers(client, username="operador")
    resp = client.get("/api/v1/export/movimientos.pdf", headers=headers)
    assert resp.status_code == 403


def test_db_constraint_rejects_negative_stock(db_session: Session) -> None:
    categoria = Categoria(nombre="Integridad", descripcion="Prueba")
    db_session.add(categoria)
    db_session.commit()
    db_session.refresh(categoria)

    producto = Producto(
        codigo="NEG-001",
        nombre="Producto invalido",
        descripcion="Integridad",
        categoria_id=categoria.id,
        tipo="producto",
        stock_actual=-1,
        stock_minimo=0,
        precio=10,
    )
    db_session.add(producto)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_db_constraint_rejects_invalid_movimiento_tipo(db_session: Session) -> None:
    categoria = Categoria(nombre="Integridad mov", descripcion="Prueba")
    usuario = User(
        username="tester",
        full_name="Tester DB",
        email="tester@example.com",
        hashed_password=hash_password("123456"),
        is_active=True,
        role="admin",
    )
    producto = Producto(
        codigo="MOV-001",
        nombre="Producto mov",
        descripcion="Integridad",
        categoria_id=1,
        tipo="producto",
        stock_actual=5,
        stock_minimo=0,
        precio=10,
    )
    db_session.add(categoria)
    db_session.add(usuario)
    db_session.commit()
    db_session.refresh(categoria)
    producto.categoria_id = categoria.id
    db_session.add(producto)
    db_session.commit()
    db_session.refresh(producto)
    db_session.refresh(usuario)

    movimiento = Movimiento(
        producto_id=producto.id,
        usuario_id=usuario.id,
        tipo="otro",
        cantidad=1,
    )
    db_session.add(movimiento)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_db_constraint_rejects_invalid_producto_tipo(db_session: Session) -> None:
    categoria = Categoria(nombre="Integridad producto", descripcion="Prueba")
    db_session.add(categoria)
    db_session.commit()
    db_session.refresh(categoria)

    producto = Producto(
        codigo="BAD-TIPO",
        nombre="Producto tipo invalido",
        descripcion="Integridad",
        categoria_id=categoria.id,
        tipo="otro",
        stock_actual=1,
        stock_minimo=0,
        precio=10,
    )
    db_session.add(producto)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_db_constraint_rejects_invalid_user_role(db_session: Session) -> None:
    user = User(
        username="rolebad",
        full_name="Role Bad",
        email="rolebad@example.com",
        hashed_password=hash_password("123456"),
        is_active=True,
        role="superadmin",
    )
    db_session.add(user)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_concurrent_salidas_do_not_duplicate_discount(testing_session_local) -> None:
    with testing_session_local() as db:
        categoria = Categoria(nombre="Concurrente", descripcion="Prueba")
        usuario = User(
            username="concurrente",
            full_name="Usuario Concurrente",
            email="concurrente@example.com",
            hashed_password=hash_password("123456"),
            is_active=True,
            role="admin",
        )
        db.add_all([categoria, usuario])
        db.commit()
        db.refresh(categoria)
        db.refresh(usuario)

        producto = Producto(
            codigo="CON-001",
            nombre="Producto concurrente",
            descripcion="Stock unico",
            categoria_id=categoria.id,
            tipo="producto",
            stock_actual=1,
            stock_minimo=0,
            precio=10,
        )
        db.add(producto)
        db.commit()
        db.refresh(producto)
        producto_id = producto.id
        usuario_id = usuario.id

    barrier = Barrier(2)
    lock = Lock()
    results: list[str] = []

    def worker() -> None:
        db = testing_session_local()
        try:
            barrier.wait()
            try:
                registrar_movimiento(
                    db,
                    usuario_id,
                    MovimientoCreate(producto_id=producto_id, tipo="salida", cantidad=1),
                )
                outcome = "ok"
            except StockInsuficienteError:
                outcome = "insuficiente"
            with lock:
                results.append(outcome)
        finally:
            db.close()

    threads = [Thread(target=worker), Thread(target=worker)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(results) == ["insuficiente", "ok"]

    with testing_session_local() as db:
        producto = db.query(Producto).filter(Producto.id == producto_id).first()
        assert producto is not None
        assert producto.stock_actual == 0

        movimientos = db.query(Movimiento).filter(Movimiento.producto_id == producto_id).all()
        assert len(movimientos) == 1
