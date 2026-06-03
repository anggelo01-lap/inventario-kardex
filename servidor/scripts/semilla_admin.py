import argparse
import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from aplicacion.nucleo.base_datos import SessionLocal
from aplicacion.modelos.categoria import Categoria  # noqa: F401
from aplicacion.modelos.cliente import Cliente  # noqa: F401
from aplicacion.modelos.movimiento import Movimiento  # noqa: F401
from aplicacion.modelos.producto import Producto  # noqa: F401
from aplicacion.modelos.proveedor import Proveedor  # noqa: F401
from aplicacion.modelos.usuario import User  # noqa: F401
from aplicacion.servicios.servicio_inicializacion import seed_admin_user


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Crea o actualiza un usuario admin inicial.")
    parser.add_argument("--username", default=os.getenv("ADMIN_USERNAME", "admin"))
    parser.add_argument("--email", default=os.getenv("ADMIN_EMAIL", "admin@example.com"))
    parser.add_argument("--full-name", default=os.getenv("ADMIN_FULL_NAME", "Administrador"))
    parser.add_argument("--password", default=os.getenv("ADMIN_PASSWORD", "Admin12345"))
    return parser


def main() -> int:
    args = build_parser().parse_args()
    db = SessionLocal()
    try:
        user, created = seed_admin_user(
            db,
            username=args.username.strip(),
            email=args.email.strip().lower(),
            full_name=args.full_name.strip(),
            password=args.password,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1
    finally:
        db.close()

    action = "creado" if created else "actualizado"
    print(f"Admin {action}: username={user.username} email={user.email} role={user.role}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
