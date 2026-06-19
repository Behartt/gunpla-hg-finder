# 🚀 Como publicar o Gunpla HG Finder como site (GRÁTIS)

## Opção 1: Streamlit Community Cloud (Recomendado - Mais Fácil)

### Passo a passo:

1. **Crie uma conta gratuita no Streamlit Cloud**
   - Acesse: https://streamlit.io/cloud
   - Faça login com sua conta Google ou GitHub

2. **Prepare o código**
   - Baixe esta pasta completa usando o botão "Files" no canto superior direito
   - Ou faça upload destes arquivos para um repositório GitHub público

3. **Faça o deploy**
   - No Streamlit Cloud, clique em "New app"
   - Se usou GitHub: conecte seu repositório
   - Se baixou os arquivos: use a opção "From existing repo" ou "Paste GitHub URL"
   
   Configure:
   - Main file path: `app.py`
   - Python version: 3.11
   
4. **Pronto!** 🎉
   - O Streamlit vai gerar uma URL pública tipo: `https://seuapp.streamlit.app`
   - Você pode acessar de qualquer dispositivo (celular, tablet, computador)

---

## Opção 2: Hugging Face Spaces (Alternativa)

1. Crie conta em: https://huggingface.co/join
2. Vá em "Spaces" → "Create new Space"
3. Escolha "Streamlit" como SDK
4. Faça upload dos arquivos: `app.py`, `requirements.txt`, `.streamlit/config.toml`
5. Faça upload da pasta `output/` com o catálogo e imagens
6. Seu app estará online em: `https://huggingface.co/spaces/SEUUSERNAME/gunpla-finder`

---

## Opção 3: Rodar localmente e compartilhar com ngrok

Se você tem um computador que pode deixar ligado:

```bash
# 1. Instale o ngrok (https://ngrok.com)
# 2. Rode o app:
streamlit run app.py

# 3. Em outro terminal, rode:
ngrok http 8501

# 4. O ngrok vai te dar uma URL pública temporária
```

---

## ⚠️ Importante para o deploy

Certifique-se de que estes arquivos estão incluídos:
- ✅ `app.py` (o app principal)
- ✅ `requirements.txt` (dependências)
- ✅ `output/hg_kits_catalog.json` (catálogo com 429 kits)
- ✅ `output/images/` (pasta com as 429 imagens)
- ✅ `.streamlit/config.toml` (configuração do tema)

O arquivo `output/owned_kits.json` será criado automaticamente quando você marcar kits.

---

## 📱 Acesso pelo celular

Depois do deploy, basta acessar a URL do seu app no navegador do celular!

Exemplos:
- Streamlit Cloud: `https://seuapp.streamlit.app`
- Hugging Face: `https://huggingface.co/spaces/seu-username/gunpla-finder`

---

## 💡 Dicas

- O Streamlit Community Cloud é 100% gratuito e muito fácil
- Não precisa saber programação para fazer o deploy
- O app roda 24/7 online
- Você pode compartilhar a URL com amigos
