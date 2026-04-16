"""
银行网银权限预审 Demo — FastAPI 入口
"""
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.routers import settings, audit

# === 创建 FastAPI 应用 ===
app = FastAPI(
    title="银行网银权限预审系统",
    description="三方交叉比对：E-Flow 电子流 × Word 申请表 × 证件 OCR",
    version="0.1.0",
)

# === 注册路由 ===
app.include_router(settings.router)
app.include_router(audit.router)

# === 静态文件 (前端) ===
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
if FRONTEND_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(str(FRONTEND_DIR / "index.html"))


# === 健康检查 ===
@app.get("/api/health")
def health():
    return {"status": "ok", "version": app.version}


# === 启动入口 ===
if __name__ == "__main__":
    import uvicorn

    # 确保上传目录存在
    upload_dir = Path(__file__).parent.parent / "uploads"
    upload_dir.mkdir(exist_ok=True)

    print("=" * 50)
    print("  银行网银权限预审 Demo")
    print("  http://localhost:8000")
    print("=" * 50)

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
