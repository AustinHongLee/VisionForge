"""VisionForge 服務層（userland/服務）。

依賴方向：app → core（合法）。core 永不反向依賴 app（D13，由
scripts/check_forbidden_imports.py 強制：visionforge_app 在 FORBIDDEN_ROOTS）。
"""
