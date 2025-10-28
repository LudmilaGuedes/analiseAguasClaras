import pandas as pd
import numpy as np
from time import sleep
import glob
import os
import re

# Libs para Análise e Visualização
import statsmodels.api as sm
import seaborn as sns
import matplotlib.pyplot as plt

# Libs para Web Scraping 
from selenium import webdriver
from selenium.webdriver.common.by import By 
from selenium.webdriver.common.keys import Keys 
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC 

# Libs para Geolocalização
from geopy.geocoders import Nominatim 
from geopy.distance import geodesic 



# PARTE 1: WEB SCRAPING 

# Configurações do Navegador
options = webdriver.ChromeOptions()
options.add_argument("--ignore-certificate-errors") # Ignora erros 
options.add_argument("--disable-blink-features=AutomationControlled") # Tenta mascarar automação

# Inicializa o driver do Chrome
driver = webdriver.Chrome(options=options)
driver.delete_all_cookies() 

# Acessa o site 
url = 'https://www.dfimoveis.com.br/'
driver.get(url)

wait = WebDriverWait(driver, 10)

# Parâmetros para a busca
tipo = "VENDA"
tipos = "APARTAMENTO"
estado = "DF"
cidade = "AGUAS CLARAS"

# Lista de valores médios para iterar
valores_medios = [500000, 800000, 1200000, 1500000, 2200000]

# preencher filtros dropdown 
def preencher_filtro(by, value, texto):
   
    element = wait.until(EC.element_to_be_clickable((by, value)))
    element.click()

    search_field = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "select2-search__field")))
    search_field.send_keys(texto)

    search_field.send_keys(Keys.ENTER)

# Loop por valor médio 
for valor in valores_medios:
    print(f"\nIniciando busca para valor médio: R$ {valor:,}")
    driver.get(url) 
    sleep(2) 

    # Preenche os filtros de busca
    preencher_filtro(By.ID, 'select2-negocios-container', tipo)
    preencher_filtro(By.ID, 'select2-tipos-container', tipos)
    preencher_filtro(By.ID, 'select2-estados-container', estado)
    preencher_filtro(By.ID, 'select2-cidades-container', cidade)

    # Preenche o campo de valor médio
    campo_valor = wait.until(EC.element_to_be_clickable((By.ID, "valorMedio")))
    campo_valor.clear()
    campo_valor.send_keys(str(valor))

    # Clica no botão de busca principal
    busca = wait.until(EC.element_to_be_clickable((By.ID, "botaoDeBusca")))
    busca.click()

    # Lista para guardar dados dos imóveis desta busca
    lst_imoveis = []

    # Loop para navegar pelas páginas 
    while True:
        print("  Coletando dados da página...")
       
        resultado = wait.until(EC.presence_of_element_located((By.ID, "resultadoDaBuscaDeImoveis")))

        elementos = resultado.find_elements(By.TAG_NAME, 'a')

        for elem in elementos:
            try:

                titulo = elem.find_element(By.CLASS_NAME, 'ellipse-text').text

                preco = elem.find_element(By.CLASS_NAME, 'body-large').text

                quartos_xpath = ".//div[contains(text(), 'Quarto') and contains(@class, 'rounded-pill')]"
                quartos_elem = elem.find_element(By.XPATH, quartos_xpath)
                quartos_texto = quartos_elem.text
                quartos_num = int(quartos_texto.split(' ')[0])

                imovel = {
                    'titulo': titulo,
                    'preco': preco,
                    'quartos': quartos_num
                }

                lst_imoveis.append(imovel)

            except Exception as e:
                # Se algo falhar, ignora e continua
                continue

        print(f"    {len(elementos)} anúncios processados nesta página.")


        # Navegação para próxima página 

        botao_proximo = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'span.btn.next')))
        classes = botao_proximo.get_attribute("class")

        # Verifica se é a última página (botão desabilitado)
        if "disabled" in classes:
            print(f"\nÚltima página alcançada para valor médio R$ {valor:,}.")
            break 

        driver.execute_script("arguments[0].click();", botao_proximo)
        sleep(2) 

    # Fim da paginação 

    # Cria DataFrame com os dados coletados para este valor médio
    df = pd.DataFrame(lst_imoveis)
    print(f"imóveis coletados para R$ {valor:,}.")

    if valor == 500000:
        df500 = df
    elif valor == 800000:
        df800 = df
    elif valor == 1200000:
        df120 = df
    elif valor == 1500000:
        df1500 = df
    elif valor == 2200000:
        df2200 = df

driver.quit()
print("\n--- PARTE 1: Web Scraping Concluído ---")


# PARTE 2: LIMPEZA E PROCESSAMENTO INICIAL DOS DADOS

def limpar_dataframe(df):

    # Remove linhas com "Sob Consulta" 
    df_limpo = df[~df['preco'].str.contains("Sob Consulta", case=False, na=False)].copy()

    # Filtra apenas títulos com "AGUAS CLARAS"
    df_limpo = df_limpo[df_limpo['titulo'].str.contains("AGUAS CLARAS", case=False, na=False)]

    # Limpa caracteres da string de preço
    df_limpo["preco"] = df_limpo["preco"].str.replace(r'A partir de |R\$|\.|\s', '', regex=True).str.replace(',', '.', regex=True)

    # Converte preço para número
    df_limpo["preco"] = pd.to_numeric(df_limpo["preco"], errors='coerce')

    # Remove linhas onde o preço ficou NaN
    df_limpo = df_limpo.dropna(subset=["preco"])

    return df_limpo

df500_limpo = limpar_dataframe(df500)
df800_limpo = limpar_dataframe(df800)
df120_limpo = limpar_dataframe(df120)
df1500_limpo = limpar_dataframe(df1500)
df2200_limpo = limpar_dataframe(df2200)

def melhoras_endereco(df):

    # Remove espaços no início/fim
    titulos_limpos = df['titulo'].astype(str).str.strip()
    # Converte para Title Case
    titulos_limpos = titulos_limpos.str.title()
    # Adiciona acento em Águas Claras
    titulos_limpos = titulos_limpos.str.replace("Aguas Claras", "Águas Claras")
    # Remove espaços duplos
    titulos_limpos = titulos_limpos.apply(lambda x: re.sub(r'\s+', ' ', x))
    # Adiciona cidade no final
    df['titulo'] = titulos_limpos + ", Brasília - DF"

    return df

df500_limpo = melhoras_endereco(df500_limpo)
df800_limpo = melhoras_endereco(df800_limpo)
df120_limpo = melhoras_endereco(df120_limpo)
df1500_limpo = melhoras_endereco(df1500_limpo)
df2200_limpo = melhoras_endereco(df2200_limpo)

# diretório de saída
output_dir = "dados_final" 

df500_limpo.to_excel(os.path.join(output_dir, "500k1.xlsx"), index=False)
df800_limpo.to_excel(os.path.join(output_dir, "800k1.xlsx"), index=False)
df120_limpo.to_excel(os.path.join(output_dir, "1200k1.xlsx"), index=False)
df1500_limpo.to_excel(os.path.join(output_dir, "1500k1.xlsx"), index=False)
df2200_limpo.to_excel(os.path.join(output_dir, "2200k1.xlsx"), index=False)



# PARTE 3: GEOLOCALIZAÇÃO E PREPARAÇÃO DE DADOS

geolocator = Nominatim(user_agent="analise_imoveis_app_v3")

def geocodificar_endereco(endereco):
    try:
        location = geolocator.geocode(endereco)
        sleep(1) 
        if location:
            return location.latitude, location.longitude
    except:
        pass
    return np.nan, np.nan


def adicionar_coordenadas(df):
    coords = df['titulo'].apply(geocodificar_endereco)
    df[['latitude', 'longitude']] = pd.DataFrame(coords.tolist(), index=df.index)
    return df

def adicionar_distancia_metro(df, estacoes):
    def menor_distancia(row):
        coord_imovel = (row["latitude"], row["longitude"])
        distancias = [geodesic(coord_imovel, coord_metro).km for coord_metro in estacoes.values() if coord_metro]
        return min(distancias) if distancias else np.nan
    df["distancia_metro_km"] = df.apply(menor_distancia, axis=1)
    return df

estacoes_metro = {
    "Arniqueiras": geocodificar_endereco("Estação Arniqueiras, Águas Claras, Brasília - DF"),
    "Águas Claras": geocodificar_endereco("Estação Águas Claras, Brasília - DF"),
    "Concessionárias": geocodificar_endereco("Estação Concessionárias, Águas Claras, Brasília - DF"),
    "Estrada Parque": geocodificar_endereco("Estação Estrada Parque, Águas Claras, Brasília - DF")
}

def preparar_dataframe(df):
    print(f"Processando DataFrame com {len(df)} linhas...")
    df = adicionar_coordenadas(df)
    df = df.dropna(subset=["latitude", "longitude"])
    print(f"-> {len(df)} imóveis geocodificados.")
    df = adicionar_distancia_metro(df, estacoes_metro)
    return df

df500_final = preparar_dataframe(df500_limpo)
df800_final = preparar_dataframe(df800_limpo)
df120_final = preparar_dataframe(df120_limpo)
df1500_final = preparar_dataframe(df1500_limpo)
df2200_final = preparar_dataframe(df2200_limpo)

df500_final = df500_final[df500_final['quartos'] <= 5]
df800_final = df800_final[df800_final['quartos'] <= 5]
df120_final = df120_final[df120_final['quartos'] <= 5]
df1500_final = df1500_final[df1500_final['quartos'] <= 5]
df2200_final = df2200_final[df2200_final['quartos'] <= 5]

colunas_para_remover = ['latitude', 'longitude']

df500_final2 = df500_final.drop(columns=colunas_para_remover)
df800_final2 = df800_final.drop(columns=colunas_para_remover)
df120_final2 = df120_final.drop(columns=colunas_para_remover)
df1500_final2 = df1500_final.drop(columns=colunas_para_remover)
df2200_final2 = df2200_final.drop(columns=colunas_para_remover)


df500_final2.to_excel("dados_final/imoveis_500k.xlsx", index=False)
df800_final2.to_excel("dados_final/imoveis_800k.xlsx", index=False)
df120_final2.to_excel("dados_final/imoveis_1200k.xlsx", index=False)
df1500_final2.to_excel("dados_final/imoveis_1500k.xlsx", index=False)
df2200_final2.to_excel("dados_final/imoveis_2200k.xlsx", index=False)



# PARTE 4: ANÁLISE DE REGRESSÃO E COMPILAÇÃO DE RESULTADOS

caminho_dos_arquivos = os.path.join(output_dir, "imoveis_*.xlsx")

# Lista todos os arquivos que correspondem ao padrão
lista_de_arquivos = sorted(glob.glob(caminho_dos_arquivos))

lista_resultados = []
resultados_modelos = {}

# Loop para cada Excel final 
for arquivo in lista_de_arquivos:

    nome_base = os.path.basename(arquivo).replace('.xlsx', '')

    try:
        df = pd.read_excel(arquivo)

        # variável dependente 
        y = df['preco']

        # variáveis independentes 
        X = df[['distancia_metro_km', 'quartos']]

        # intercessao
        x = sm.add_constant(X)

        # Regressão Linear Múltipla
        modelo = sm.OLS(y, x).fit()

        # Armazena o objeto do modelo completo (opcional)
        resultados_modelos[nome_base] = modelo

        resultado_linha = {
            'modelo_nome': nome_base,
            'No. Observations': int(modelo.nobs), # Número de observações 
            'R-squared': modelo.rsquared, # Coeficiente de determinação 
            'Coef (dist_km)': modelo.params.get('distancia_metro_km'), # Coeficiente da distância
            'P-valor (dist_km)': modelo.pvalues.get('distancia_metro_km'), # P-valor da distância 
            'Coef (quartos)': modelo.params.get('quartos'), # Coeficiente dos quartos
            'P-valor (quartos)': modelo.pvalues.get('quartos') # P-valor dos quartos 
        }

        lista_resultados.append(resultado_linha)
    
    except Exception as e:
        print(f"Erro ao processar o arquivo")



# PARTE 5: DATAFRAME COM O RESUMO DAS ANÁLISES

if not lista_resultados:
    print("Nenhum resultado de regressão foi gerado. Encerrando.")
else:
    # Converte a lista de dicionários de resultados em um DataFrame Pandas
    df_resultados = pd.DataFrame(lista_resultados)

    # Define a coluna 'modelo_nome' como o índice do DataFrame
    df_resultados = df_resultados.set_index('modelo_nome')

    df_resultados['R-squared'] = df_resultados['R-squared'].round(3)
    df_resultados['P-valor (dist_km)'] = df_resultados['P-valor (dist_km)'].round(3)
    df_resultados['Coef (dist_km)'] = df_resultados['Coef (dist_km)'].round(2)
    df_resultados['P-valor (quartos)'] = df_resultados['P-valor (quartos)'].round(3)
    df_resultados['Coef (quartos)'] = df_resultados['Coef (quartos)'].round(2)

    caminho_do_arquivo = "C:\\Ludmila\\faculdade\\inferencia_estatistica\\webScraping\\dados_final\\resumo_regressoes.xlsx"
    df_resultado = pd.read_excel(caminho_do_arquivo)
   







