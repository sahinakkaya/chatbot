"""
Test configuration for AI Consumer tests.
Disables retry logic to make tests run faster.
"""

import pytest
from unittest.mock import patch


def no_retry_decorator(*args, **kwargs):
    """A decorator that does nothing - just returns the original function"""

    def decorator(func):
        return func

    # Handle both @retry and @retry(...) syntax
    if len(args) == 1 and callable(args[0]):
        return args[0]
    return decorator


# Patch retry BEFORE importing the dependencies module
# This ensures the decorator is disabled when the class is defined
pytest_plugins = []

# Apply the patch at module level before any imports
patch("tenacity.retry", no_retry_decorator).start()
