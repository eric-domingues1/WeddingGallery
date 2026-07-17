from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import json
import uuid
import boto3
from botocore.client import Config
from dotenv import load_dotenv
from fastapi.responses import HTMLResponse

load_dotenv()

app = FastAPI()

# IMPORTANTE: o mount do /static precisa vir ANTES das rotas dinâmicas
# /{casal}/{codigo}, senão "/static/algo.jpg" seria interpretado como
# casal="static", codigo="algo.jpg" e nunca chegaria nos arquivos estáticos.
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# ── Cloudflare R2 ──
R2_ENDPOINT = os.getenv("R2_ENDPOINT")
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY")
R2_BUCKET = os.getenv("R2_BUCKET")
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL")

s3 = boto3.client(
    "s3",
    endpoint_url=R2_ENDPOINT,
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    config=Config(signature_version="s3v4"),
    region_name="auto",
)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "mp4", "mov", "avi"}
MAX_SIZE_MB = 400
CONTENT_TYPES = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg",
    "png": "image/png", "webp": "image/webp",
    "mp4": "video/mp4", "mov": "video/quicktime", "avi": "video/x-msvideo",
}

CASAIS_PATH = "casais.json"


# ── Casais ──
def carregar_casais() -> dict:
    with open(CASAIS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_casal(casal: str, codigo: str) -> dict:
    """Valida se o slug+código existem e batem. Impede que alguém 'adivinhe'
    a URL de outro casal só pelo slug, ou acesse com código errado."""
    casais = carregar_casais()
    dados = casais.get(casal)
    if not dados or dados["codigo"] != codigo:
        raise HTTPException(status_code=404, detail="Galeria não encontrada")
    return dados


def prefixo(casal: str, codigo: str) -> str:
    return f"{casal}/{codigo}/"


# ── Páginas ──
@app.get("/", response_class=HTMLResponse)
def raiz(request: Request):
    return templates.TemplateResponse(request, "em-breve.html", {})


@app.get("/{casal}/{codigo}")
def home(request: Request, casal: str, codigo: str):
    dados = get_casal(casal, codigo)
    return templates.TemplateResponse(
        request,
        "index.html",
        {"casal": casal, "codigo": codigo, **dados},
    )


@app.get("/{casal}/{codigo}/galeria")
def galeria(request: Request, casal: str, codigo: str):
    dados = get_casal(casal, codigo)
    return templates.TemplateResponse(
        request,
        "galeria.html",
        {"casal": casal, "codigo": codigo, **dados},
    )


@app.get("/{casal}/{codigo}/admin")
def admin(request: Request, casal: str, codigo: str):
    dados = get_casal(casal, codigo)
    return templates.TemplateResponse(
        request,
        "admin.html",
        {"casal": casal, "codigo": codigo, **dados},
    )


# ── Login do admin (valida a senha sem precisar "testar" um delete) ──
@app.post("/api/{casal}/{codigo}/admin/login")
def admin_login(casal: str, codigo: str, x_admin_senha: str = Header(None)):
    dados = get_casal(casal, codigo)
    senha_admin = os.getenv(dados["senha_admin_env"])

    if not x_admin_senha or x_admin_senha != senha_admin:
        raise HTTPException(status_code=401, detail="Senha inválida")
    return {"status": "ok"}


# ── Upload ──
@app.post("/{casal}/{codigo}/upload")
async def upload(casal: str, codigo: str, files: list[UploadFile] = File(...)):
    get_casal(casal, codigo)

    uploaded = []
    errors = []

    for file in files:
        try:
            print(f"\n========== NOVO UPLOAD ==========")
            print(f"Arquivo: {file.filename}")

            ext = file.filename.lower().rsplit(".", 1)[-1] if "." in file.filename else ""

            if ext not in ALLOWED_EXTENSIONS:
                msg = f"{file.filename}: formato não suportado"
                print(msg)
                errors.append(msg)
                continue

            # Descobre o tamanho do arquivo
            file.file.seek(0, 2)
            tamanho = file.file.tell()
            file.file.seek(0)

            tamanho_mb = tamanho / (1024 * 1024)

            print(f"Tamanho: {tamanho_mb:.2f} MB")

            if tamanho_mb > MAX_SIZE_MB:
                msg = f"{file.filename}: arquivo maior que {MAX_SIZE_MB}MB"
                print(msg)
                errors.append(msg)
                continue

            nome_unico = f"{prefixo(casal, codigo)}{uuid.uuid4()}_{file.filename}"

            content_type = CONTENT_TYPES.get(
                ext,
                file.content_type or "application/octet-stream"
            )

            print("Enviando para o Cloudflare R2...")

            s3.upload_fileobj(
                Fileobj=file.file,
                Bucket=R2_BUCKET,
                Key=nome_unico,
                ExtraArgs={
                    "ContentType": content_type
                }
            )

            print("✅ Upload concluído!")

            uploaded.append(nome_unico)

        except Exception as e:
            print("❌ ERRO NO UPLOAD:")
            print(type(e).__name__)
            print(str(e))

            errors.append(f"{file.filename}: {str(e)}")

    return JSONResponse({
        "uploaded": len(uploaded),
        "errors": errors
    })

# ── Listar fotos (filtradas por casal) ──
@app.get("/api/{casal}/{codigo}/fotos")
def listar_fotos(casal: str, codigo: str):
    get_casal(casal, codigo)
    try:
        resp = s3.list_objects_v2(Bucket=R2_BUCKET, Prefix=prefixo(casal, codigo))
        arquivos = []
        for obj in sorted(resp.get("Contents", []), key=lambda x: x["LastModified"], reverse=True):
            nome = obj["Key"]
            ext = nome.lower().rsplit(".", 1)[-1] if "." in nome else ""
            base_url = R2_PUBLIC_URL.rstrip("/") if R2_PUBLIC_URL else f"{R2_ENDPOINT}/{R2_BUCKET}"
            url = f"{base_url}/{nome}"
            arquivo = nome.split("/")[-1]  # nome do arquivo sem o prefixo casal/codigo/

            if ext in {"jpg", "jpeg", "png", "webp"}:
                arquivos.append({"url": url, "tipo": "imagem", "arquivo": arquivo})
            elif ext in {"mp4", "mov", "avi"}:
                arquivos.append({"url": url, "tipo": "video", "arquivo": arquivo})

        return JSONResponse(arquivos)
    except Exception:
        return JSONResponse([], status_code=200)


# ── Excluir foto (só o admin do próprio casal) ──
@app.delete("/api/{casal}/{codigo}/fotos/{arquivo}")
def deletar_foto(casal: str, codigo: str, arquivo: str, x_admin_senha: str = Header(None)):
    dados = get_casal(casal, codigo)

    senha_admin = os.getenv(dados["senha_admin_env"])

    if not x_admin_senha or x_admin_senha != senha_admin:
        raise HTTPException(status_code=401, detail="Senha de admin inválida")

    key = f"{prefixo(casal, codigo)}{arquivo}"
    s3.delete_object(Bucket=R2_BUCKET, Key=key)
    return {"status": "ok"}
