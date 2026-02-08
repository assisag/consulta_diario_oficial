import os
import sys
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import fitz  # PyMuPDF

# -------------------------
# 1️⃣ Baixar PDF do Diário Oficial
# -------------------------
def baixar_diario_oficial(data, pasta_saida):
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

    response = session.post(post_url, data=payload)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    pdf_href = None
    for a in soup.find_all("a", href=True):
        if "md_epubli_memoria_arquivo.php" in a["href"]:
            pdf_href = a["href"]
            break

    if not pdf_href:
        raise RuntimeError(f"PDF do Diário Oficial não encontrado para a data {data}.")

    pdf_url = urljoin(post_url, pdf_href)
    print(f"PDF do Diário Oficial encontrado para {data}")

    pdf_response = session.get(pdf_url)
    pdf_response.raise_for_status()

    if not os.path.exists(pasta_saida):
        os.makedirs(pasta_saida)

    filename = f"{pasta_saida}/diario_oficial_{pasta_saida}.pdf"
    with open(filename, "wb") as f:
        f.write(pdf_response.content)

    print(f"PDF baixado com sucesso na pasta: {pasta_saida}")
    return filename

# -------------------------
# 2️⃣ Ler arquivo entrada.txt
# -------------------------
def ler_entrada(arquivo):
    pessoas = []
    with open(arquivo, "r", encoding="utf-8") as f:
        for i, linha in enumerate(f, start=1):
            linha = linha.strip()
            if not linha:
                continue

            parts = linha.split(";")
            if len(parts) < 2:
                print(f"Atenção: linha {i} ignorada (formato incorreto): {linha}")
                continue

            nome, rf = parts[0].strip(), parts[1].strip()
            if not nome or not rf:
                print(f"Atenção: linha {i} ignorada (nome ou RF vazio): {linha}")
                continue

            pessoas.append({"nome": nome, "rf": rf})

    print(f"{len(pessoas)} pessoas lidas com sucesso do arquivo '{arquivo}'")
    return pessoas

# -------------------------
# 3️⃣ Procurar pessoas no PDF e salvar páginas destacando
# -------------------------
def procurar_e_salvar(pdf_path, pessoas, pasta_saida):
    print("Procurando pessoas no Diário Oficial...")
    doc = fitz.open(pdf_path)
    resultado = []

    for pessoa in pessoas:
        nome = pessoa["nome"]
        rf = pessoa["rf"]
        paginas_encontradas = []

        nome_upper = nome.upper()
        rf_digits = re.sub(r'\D', '', rf)

        for i, page in enumerate(doc, start=1):
            texto = page.get_text()
            texto_normalizado = " ".join(texto.split()).upper()
            numeros_texto = re.sub(r'\D', '', texto_normalizado)

            if nome_upper in texto_normalizado and rf_digits in numeros_texto:
                paginas_encontradas.append(i)

                # Copia a página original
                novo_pdf = fitz.open()
                novo_pdf.insert_pdf(doc, from_page=i-1, to_page=i-1)
                pagina = novo_pdf[0]

                # Destacar o nome da pessoa
                for inst in pagina.search_for(nome, quads=True, flags=fitz.TEXT_DEHYPHENATE):
                    pagina.add_highlight_annot(inst)
                
                # Destacar o rf
                for inst in pagina.search_for(rf, quads=True, flags=fitz.TEXT_DEHYPHENATE):
                    pagina.add_highlight_annot(inst)

                # Salvar arquivo seguro substituindo barras
                rf_seguro = rf.replace("/", "-")
                filename = f"{pasta_saida}/{nome}_{rf_seguro}_pagina_{i}.pdf"
                novo_pdf.save(filename)
                novo_pdf.close()

        if paginas_encontradas:
            if len(paginas_encontradas) == 1:
                texto_paginas = f"na página {paginas_encontradas[0]}"
            else:
                texto_paginas = f"nas páginas {paginas_encontradas}"
            print(f"Encontrado: {nome} (RF: {rf}) {texto_paginas}")

            resultado.append({
                "nome": nome,
                "rf": rf,
                "paginas": paginas_encontradas,
                "qtde": len(paginas_encontradas)
            })
        else:
            print(f"Não encontrado: {nome} (RF: {rf})")

    doc.close()
    print(f"{len(resultado)} pessoas encontradas no dia {data_para_site}")
    return resultado

# -------------------------
# 4️⃣ Criar PDF sumário com links (apenas nomes e páginas)
# -------------------------
def criar_sumario(resultado, pasta_saida):
    output_pdf = f"{pasta_saida}/SUMARIO.pdf"
    doc = fitz.open()  # PDF vazio

    altura_pagina = 842  # altura A4
    y = 50
    margem = 50
    espaco_linha = 20

    # Primeira página: sumário
    pagina = doc.new_page()
    pagina.insert_text((margem, y), "Sumário de Pessoas Encontradas", fontsize=14, fontname="helv")
    y += 40

    # Agora adiciona cada pessoa
    for item in resultado:
        if item['qtde'] == 1:
            paginas_texto = f"Página: {item['paginas'][0]}"
        else:
            paginas_texto = f"Páginas: {item['paginas']}"

        texto = f"{item['nome']}, RF: {item['rf']}, Qtde: {item['qtde']}, {paginas_texto}"
        pagina.insert_text((margem, y), texto, fontsize=12, fontname="helv")
        y += espaco_linha

    doc.save(output_pdf)
    doc.close()
    print(f"Sumário criado: {output_pdf}")

# -------------------------
# 5️⃣ LOOP PRINCIPAL INTERATIVO
# -------------------------
if __name__ == "__main__":
    import ctypes
    ctypes.windll.kernel32.SetConsoleTitleW("Consulta Diário Oficial SP")

    print("="*70)
    print("         Consulta Diário Oficial SP - para meu amor Samanta \u2764        ")
    print("="*70)

    while True:
        # Perguntar a data
        data_input = input("\nDigite a data do Diário Oficial (DD/MM/AAAA ou DD-MM-AAAA): ").strip()

        # Validar data
        try:
            dt = datetime.strptime(data_input, "%d/%m/%Y")
        except ValueError:
            try:
                dt = datetime.strptime(data_input, "%d-%m-%Y")
            except ValueError:
                print("Data inválida. Use o formato DD/MM/AAAA ou DD-MM-AAAA")
                continue  # volta pro começo do loop

        pasta_saida = dt.strftime("%Y-%m-%d")
        data_para_site = dt.strftime("%d/%m/%Y")

        try:
            pdf_diario = baixar_diario_oficial(data_para_site, pasta_saida)
        except Exception as e:
            print(f"Erro ao baixar PDF: {e}")
            continue

        pessoas = ler_entrada("entrada.txt")
        resultado = procurar_e_salvar(pdf_diario, pessoas, pasta_saida)

        if resultado:
            criar_sumario(resultado, pasta_saida)

        # Perguntar se quer consultar outra data
        while True:
            escolha = input("\nDeseja consultar outra data? (S/N): ").strip().upper()
            if escolha == "S":
                break  # volta pro começo do loop principal
            elif escolha == "N":
                print("Encerrando o programa...")
                sys.exit(0)
            else:
                print("Opção inválida. Digite 'S' para sim ou 'N' para não.")
