# 📸 WeddingGallery *(Galeria de Casamento)*

Aplicação web para convidados enviarem e visualizarem fotos e vídeos de casamentos, com galeria estilo mural e lightbox com swipe.

> Projeto desenvolvido com apoio de IA — e muito aprendizado no processo. 🤝

---

## 🎥 Demonstração

![WeddingGallery Demo](docs/demo.gif)

## ✨ Funcionalidades

- Upload de fotos e vídeos diretamente pelo celular ou computador
- Compressão automática de imagens antes do envio
- Galeria em mural com carregamento lazy
- Lightbox com swipe (igual stories do Instagram)
- Filtros por fotos e vídeos
- Botão de download e compartilhamento de cada foto
- Banner de capa com foto dos noivos
- Layout responsivo para mobile

---

## 🛠️ Tecnologias

- **Python** + **FastAPI** — backend e API
- **Cloudflare R2** — armazenamento de fotos e vídeos
- **HTML/CSS/JavaScript** — frontend sem frameworks
- **Uvicorn** — servidor ASGI

---

## 🚀 Como rodar localmente

### 1. Clone o repositório

```bash
git clone https://github.com/eric-domingues1/fotos-casamento.git
cd fotos-casamento
```

### 2. Crie e ative o ambiente virtual

```bash
python -m venv venv

# Windows
.\venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto:

```env
R2_ENDPOINT=https://SEU_ACCOUNT_ID.r2.cloudflarestorage.com
R2_ACCESS_KEY=sua_access_key
R2_SECRET_KEY=sua_secret_key
R2_BUCKET=nome-do-bucket
R2_PUBLIC_URL=https://seu-dominio-publico.r2.dev
```

> ⚠️ Nunca suba o arquivo `.env` para o GitHub. Ele já está no `.gitignore`.

### 5. Inicie o servidor

```bash
uvicorn main:app --reload
```

Acesse em: [http://localhost:8000](http://localhost:8000)

---

## 📁 Estrutura do projeto

```
fotos-casamento/
├── main.py              # Backend FastAPI
├── requirements.txt     # Dependências Python
├── .env                 # Variáveis de ambiente (não versionado)
├── .gitignore
├── templates/
│   ├── index.html       # Página de upload
│   └── galeria.html     # Galeria de fotos
└── static/
    └── capa.jpg         # Foto de capa dos noivos
```

---

## 📚 O que aprendi neste projeto

- Integração com **Cloudflare R2** usando boto3 (compatível com S3)
- Boas práticas de segurança: variáveis de ambiente com `.env` e `.gitignore`
- Como **remover credenciais expostas** do histórico do Git com `git filter-repo`
- Upload de arquivos com **FastAPI** e `python-multipart`
- Compressão de imagens no browser com **Canvas API**
- Swipe touch em lightbox com eventos `touchstart` e `touchend`

---

## 👤 Autor

**Eric Domingues** — [@eric-domingues1](https://github.com/eric-domingues1)