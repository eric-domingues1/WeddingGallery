from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import os
import uuid
import boto3
from botocore.client import Config

app = FastAPI()

# ── Cloudflare R2 ──
R2_ENDPOINT    = os.getenv("R2_ENDPOINT", "https://c24f97a539b9cb2385e79a0bc990cb02.r2.cloudflarestorage.com")
R2_ACCESS_KEY  = os.getenv("R2_ACCESS_KEY", "3b2154f85ec68a407d1edc4586cd7a0a")
R2_SECRET_KEY  = os.getenv("R2_SECRET_KEY", "2026e022f4d993554ce92676f356bda54be37724a045ce275ef292430b570032")
R2_BUCKET      = os.getenv("R2_BUCKET", "fotos-casamento")
R2_PUBLIC_URL  = os.getenv("R2_PUBLIC_URL", "https://pub-8e0f54c96bfc4b609dd5535b3b3351be.r2.dev")

s3 = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    config=Config(signature_version="s3v4"),
    region_name="auto",
)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "mp4", "mov", "avi"}
MAX_SIZE_MB = 100

CONTENT_TYPES = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg",
    "png": "image/png", "webp": "image/webp",
    "mp4": "video/mp4", "mov": "video/quicktime", "avi": "video/x-msvideo",
}


@app.get("/", response_class=HTMLResponse)
def home():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.post("/upload")
async def upload(files: list[UploadFile] = File(...)):
    uploaded = []
    errors = []

    for file in files:
        ext = file.filename.lower().rsplit(".", 1)[-1] if "." in file.filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            errors.append(f"{file.filename}: formato não suportado")
            continue

        conteudo = await file.read()
        tamanho_mb = len(conteudo) / (1024 * 1024)

        if tamanho_mb > MAX_SIZE_MB:
            errors.append(f"{file.filename}: arquivo maior que 100MB")
            continue

        nome_unico = f"{uuid.uuid4()}_{file.filename}"
        content_type = CONTENT_TYPES.get(ext, "application/octet-stream")

        s3.put_object(
            Bucket=R2_BUCKET,
            Key=nome_unico,
            Body=conteudo,
            ContentType=content_type,
        )

        uploaded.append(nome_unico)

    return JSONResponse({"uploaded": len(uploaded), "errors": errors})


@app.get("/galeria", response_class=HTMLResponse)
def galeria():
    with open("templates/galeria.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/api/fotos")
def listar_fotos():
    try:
        resp = s3.list_objects_v2(Bucket=R2_BUCKET)
        arquivos = []
        for obj in sorted(resp.get("Contents", []), key=lambda x: x["LastModified"], reverse=True):
            nome = obj["Key"]
            ext = nome.lower().rsplit(".", 1)[-1] if "." in nome else ""
            base_url = R2_PUBLIC_URL.rstrip("/") if R2_PUBLIC_URL else f"{R2_ENDPOINT}/{R2_BUCKET}"
            url = f"{base_url}/{nome}"
            if ext in {"jpg", "jpeg", "png", "webp"}:
                arquivos.append({"url": url, "tipo": "imagem"})
            elif ext in {"mp4", "mov", "avi"}:
                arquivos.append({"url": url, "tipo": "video"})
        return JSONResponse(arquivos)
    except Exception as e:
        return JSONResponse([], status_code=200)


app.mount("/static", StaticFiles(directory="static"), name="static")
