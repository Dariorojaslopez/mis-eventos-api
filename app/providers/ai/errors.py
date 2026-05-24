"""Errores de la capa de proveedores IA (sin detalles sensibles hacia HTTP)."""


class AIProviderError(Exception):
    """Fallo al invocar un proveedor de IA."""

    def __init__(
        self, message: str = "AI provider request failed", *, provider: str | None = None
    ) -> None:
        self.provider = provider
        super().__init__(message)
