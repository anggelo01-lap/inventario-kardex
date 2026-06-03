"""Excepciones de dominio del inventario."""


class ProductoNoEncontradoError(Exception):
    pass


class ProductoEnUsoError(Exception):
    pass


class StockInsuficienteError(Exception):
    pass


class TipoMovimientoInvalidoError(Exception):
    pass


class CantidadInvalidaError(Exception):
    pass


class CategoriaNoEncontradaError(Exception):
    pass


class TipoProductoInvalidoError(Exception):
    pass


class UsuarioDuplicadoError(Exception):
    def __init__(self, campo: str) -> None:
        self.campo = campo
        super().__init__(campo)


class PasswordInvalidaError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)
