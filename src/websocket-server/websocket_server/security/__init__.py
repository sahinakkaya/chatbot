"""Security package for WebSocket server"""

from websocket_server.security.input_validator import InputValidator, InputValidationError

__all__ = ["InputValidator", "InputValidationError"]
