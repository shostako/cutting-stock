"""ソルバ核の例外. api.py がこれを JSON エラーコードへ写像する（M4）."""

from __future__ import annotations


class SolverError(Exception):
    """全ソルバ例外の基底. code は API のエラーコードに対応."""

    code = "ERROR"

    def __init__(self, message: str = "") -> None:
        super().__init__(message)
        self.message = message


class InvalidInput(SolverError):
    code = "INVALID_INPUT"


class PieceTooLong(SolverError):
    """ピース長 + カット代が原材料長を超える（Model A で物理的に切り出せない）."""

    code = "PIECE_TOO_LONG"


class Infeasible(SolverError):
    code = "INFEASIBLE"
