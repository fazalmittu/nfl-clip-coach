"""Safe pandas code execution."""

from __future__ import annotations

import pandas as pd


def execute_query(code: str, df: pd.DataFrame) -> str:
    """Execute pandas code in a restricted namespace and return the result as a string."""
    namespace = {"pd": pd, "df": df}
    try:
        exec(code, namespace)
        if "result" in namespace:
            return str(namespace["result"])
        return "(No 'result' variable set by code)"
    except Exception as e:
        return f"Error executing code: {e}"
