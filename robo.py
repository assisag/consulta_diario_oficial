import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def baixar_diario_oficial(data):
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": "https://diariooficial.prefeitura.sp.gov.br/"
    })

    post_url = "https://diariooficial.prefeitura.sp.gov.br/md_epubli_controlador.php?acao=edicao_consultar"

    payload = {
        "acao": "edicao_consultar",
        "hdnDtaEdicao": data,
        "hdnTipoEdicao": "C",
        "hdnBolEdicaoGerada": "false",
        "hdnIdEdicao": "",
        "hdnInicio": "0",
        "hdnFormato": "A"
    }

    # 1️⃣ POST
    response = session.post(post_url, data=payload)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    pdf_href = None

    # 2️⃣ Método 1 — href conhecido do backend (mais seguro)
    for a in soup.find_all("a", href=True):
        if "md_epubli_memoria_arquivo.php" in a["href"]:
            pdf_href = a["href"]
            break

    # 3️⃣ Método 2 — texto do link
    if not pdf_href:
        link = soup.find("a", string=lambda t: t and "PDF" in t.upper())
        if link and link.get("href"):
            pdf_href = link["href"]

    # 4️⃣ Método 3 — fallback genérico
    if not pdf_href:
        for a in soup.find_all("a", target="_blank", href=True):
            if ".php?" in a["href"]:
                pdf_href = a["href"]
                break

    if not pdf_href:
        raise RuntimeError("Link do PDF não encontrado no HTML retornado.")

    pdf_url = urljoin(post_url, pdf_href)
    print("Link do PDF encontrado:")
    print(pdf_url)

    # 5️⃣ Download do PDF real
    pdf_response = session.get(pdf_url)
    pdf_response.raise_for_status()

    filename = f"diario_oficial_sp_{data.replace('/', '-')}.pdf"
    with open(filename, "wb") as f:
        f.write(pdf_response.content)

    print(f"PDF salvo com sucesso: {filename}")


if __name__ == "__main__":
    baixar_diario_oficial("06/02/2026")
