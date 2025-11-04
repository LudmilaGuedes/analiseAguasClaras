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
options.add_argument("--ignore-certificate-errors") 
options.add_argument("--disable-blink-features=AutomationControlled") 

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
    try:
        element = wait.until(EC.element_to_be_clickable((by, value)))
        element.click()

        search_field = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, "select2-search__field")))
        search_field.send_keys(texto)

        search_field.send_keys(Keys.ENTER)
    except Exception as e:
        print(f"Erro ao preencher filtro: {e}")
       
        raise e 

# Loop por valor médio 
for valor in valores_medios:
    print(f"\nIniciando busca para valor médio: R$ {valor:,}")
    try:
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
    except Exception as e:
        print(f"Erro ao configurar a busca para R$ {valor}. Pulando este valor... Erro: {e}")
        continue # Pula para o próximo valor_medio

    # Lista para guardar dados dos imóveis desta busca
    lst_imoveis = []

    # Loop para navegar pelas páginas 
    while True:
        print("   Coletando dados da página...")
        
        try:
            resultado = wait.until(EC.presence_of_element_located((By.ID, "resultadoDaBuscaDeImoveis")))
            # Espera os elementos 'a' (links) dentro do resultado
            elementos = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//div[@id='resultadoDaBuscaDeImoveis']//a[contains(@href, '/imovel/')]")))
        except Exception as e:
            print(f"   Erro ao localizar resultados ou fim da busca. {e}")
            break

        if not elementos:
            print("   Nenhum anúncio encontrado na página.")
            break

        for elem in elementos:
            try:
                # 1. Título
                titulo = elem.find_element(By.CLASS_NAME, 'ellipse-text').text

                # 2. Preço
                preco = elem.find_element(By.CLASS_NAME, 'body-large').text

                # 3. Quartos
                quartos_xpath = ".//div[contains(text(), 'Quarto') and contains(@class, 'rounded-pill')]"
                quartos_elem = elem.find_element(By.XPATH, quartos_xpath)
                quartos_texto = quartos_elem.text
                quartos_num = int(quartos_texto.split(' ')[0])

        
                # 4. Metragem
                metragem_texto = np.nan 
                try:
                    metragem_elem = elem.find_element(By.XPATH, ".//div[contains(@class, 'web-view') and contains(text(), 'm²')]")
                    metragem_texto = metragem_elem.text
                except:
                    pass 

                # 5. Vagas
                vagas_texto = np.nan 
                try:
                    vagas_elem = elem.find_element(By.XPATH, ".//div[contains(@class, 'rounded-pill') and (contains(text(), 'Vaga') or contains(text(), 'Vagas'))]")
                    vagas_texto = vagas_elem.text
                except:
                    pass 

                imovel = {
                    'titulo': titulo,
                    'preco': preco,
                    'quartos': quartos_num,
                    'metragem': metragem_texto, 
                    'vagas': vagas_texto        
                }

                lst_imoveis.append(imovel)

            except Exception as e:

                continue

        print(f"   {len(elementos)} anúncios processados nesta página.")

        # Navegação para próxima página 
        try:
            botao_proximo = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'span.btn.next')))
            classes = botao_proximo.get_attribute("class")

            # Verifica se é a última página (botão desabilitado)
            if "disabled" in classes:
                print(f"\nÚltima página alcançada para valor médio R$ {valor:,}.")
                break 

            driver.execute_script("arguments[0].click();", botao_proximo)
            sleep(2) 
        except Exception as e:
            print(f"Erro ao tentar ir para a próxima página. {e}")
            break # Sai do loop 'while True'

    # Fim da paginação 

    # Cria DataFrame com os dados coletados para este valor médio
    df = pd.DataFrame(lst_imoveis)
    # Remove duplicatas de 'titulo' DENTRO desta busca
    df = df.drop_duplicates(subset=['titulo'], keep='first') 
    print(f"{len(df)} imóveis únicos coletados para R$ {valor:,}.")

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


# PARTE 2: LIMPEZA E PROCESSAMENTO INICIAL DOS DADOS (MODIFICADA)

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

    # Converte metragem para string para poder limpar
    df_limpo['metragem'] = df_limpo['metragem'].astype(str)

    # Limpa caracteres ( m², vírgula, espaços)
    df_limpo['metragem'] = df_limpo['metragem'].str.replace(' m²', '', regex=False).str.replace(',', '.', regex=False).str.strip()

    # Converte metragem para número
    df_limpo['metragem'] = pd.to_numeric(df_limpo['metragem'], errors='coerce')

    # Converte vagas para string para poder limpar
    df_limpo['vagas'] = df_limpo['vagas'].astype(str)

    # Pega só o primeiro número (ex: "2 Vagas" -> "2")
    df_limpo['vagas'] = df_limpo['vagas'].str.split(' ').str[0]

    # Converte vagas para número
    df_limpo['vagas'] = pd.to_numeric(df_limpo['vagas'], errors='coerce')

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
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Salva os arquivos .xlsx intermediários 
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
        sleep(1) # Respeita o limite de taxa do Nominatim
        if location:
            return location.latitude, location.longitude
    except:
        pass
    return np.nan, np.nan


def adicionar_coordenadas(df):
    print(f"Geocodificando {len(df)} endereços... (Isso pode levar tempo)")
    coords = df['titulo'].apply(geocodificar_endereco)
    df[['latitude', 'longitude']] = pd.DataFrame(coords.tolist(), index=df.index)
    return df

def adicionar_distancia_metro(df, estacoes):
    def menor_distancia(row):
        if pd.isna(row["latitude"]):
            return np.nan
        coord_imovel = (row["latitude"], row["longitude"])
        distancias = [geodesic(coord_imovel, coord_metro).km for coord_metro in estacoes.values() if coord_metro]
        return min(distancias) if distancias else np.nan
    
    print("Calculando distâncias até o metrô...")
    df["distancia_metro_km"] = df.apply(menor_distancia, axis=1)
    return df

estacoes_metro = {
    "Arniqueiras": geocodificar_endereco("Estação Arniqueiras, Águas Claras, Brasília - DF"),
    "Águas Claras": geocodificar_endereco("Estação Águas Claras, Brasília - DF"),
    "Concessionárias": geocodificar_endereco("Estação Concessionárias, Águas Claras, Brasília - DF"),
    "Estrada Parque": geocodificar_endereco("Estação Estrada Parque, Águas Claras, Brasília - DF")
}
print(f"Estações geocodificadas: {estacoes_metro}")

def preparar_dataframe(df):
    print(f"Processando DataFrame com {len(df)} linhas...")
    df = adicionar_coordenadas(df)
    df = df.dropna(subset=["latitude", "longitude"])
    print(f"-> {len(df)} imóveis geocodificados com sucesso.")
    df = adicionar_distancia_metro(df, estacoes_metro)
    return df

# Aplicando a preparação final
df500_final = preparar_dataframe(df500_limpo)
df800_final = preparar_dataframe(df800_limpo)
df120_final = preparar_dataframe(df120_limpo)
df1500_final = preparar_dataframe(df1500_limpo)
df2200_final = preparar_dataframe(df2200_limpo)

# Filtro de quartos (estava no seu original)
df500_final = df500_final[df500_final['quartos'] <= 5]
df800_final = df800_final[df800_final['quartos'] <= 5]
df120_final = df120_final[df120_final['quartos'] <= 5]
df1500_final = df1500_final[df1500_final['quartos'] <= 5]
df2200_final = df2200_final[df2200_final['quartos'] <= 5]

# Remoção de colunas de geolocalização (estava no seu original)
colunas_para_remover = ['latitude', 'longitude']

df500_final2 = df500_final.drop(columns=colunas_para_remover)
df800_final2 = df800_final.drop(columns=colunas_para_remover)
df120_final2 = df120_final.drop(columns=colunas_para_remover)
df1500_final2 = df1500_final.drop(columns=colunas_para_remover)
df2200_final2 = df2200_final.drop(columns=colunas_para_remover)

# Salva os arquivos .xlsx FINAIS
df500_final2.to_excel(os.path.join(output_dir, "imoveis_500k.xlsx"), index=False)
df800_final2.to_excel(os.path.join(output_dir, "imoveis_800k.xlsx"), index=False)
df120_final2.to_excel(os.path.join(output_dir, "imoveis_1200k.xlsx"), index=False)
df1500_final2.to_excel(os.path.join(output_dir, "imoveis_1500k.xlsx"), index=False)
df2200_final2.to_excel(os.path.join(output_dir, "imoveis_2200k.xlsx"), index=False)




# PARTE 4: ANÁLISE DE REGRESSÃO E COMPILAÇÃO DE RESULTADOS

caminho_dos_arquivos = os.path.join(output_dir, "imoveis_*.xlsx")

# Lista todos os arquivos que correspondem ao padrão
lista_de_arquivos = sorted(glob.glob(caminho_dos_arquivos))

if not lista_de_arquivos:
     print(f"Nenhum arquivo 'imoveis_*.xlsx' encontrado em '{output_dir}'.")
else:
    lista_resultados = []
    resultados_modelos = {}
    
    # Define as variáveis independentes que queremos usar
    colunas_independentes = ['distancia_metro_km', 'quartos', 'metragem', 'vagas']

    # Loop para cada Excel final 
    for arquivo in lista_de_arquivos:
        nome_base = os.path.basename(arquivo).replace('.xlsx', '')
        print(f"\nProcessando regressão para: {nome_base}")

        try:
            df = pd.read_excel(arquivo)
            
            # remove linhas com NaNs NAS COLUNAS da regressão
            colunas_regressao = ['preco'] + colunas_independentes
            df_completo = df[colunas_regressao].dropna()
            

            # variável dependente 
            y = df_completo['preco']
            # variáveis independentes 
            X = df_completo[colunas_independentes]
            # intercessao
            X = sm.add_constant(X, prepend=False) # Adiciona a constante (intercepto)

            # Roda a Regressão Linear Múltipla
            modelo = sm.OLS(y, X).fit()

            # Armazena o objeto do modelo completo (opcional)
            resultados_modelos[nome_base] = modelo

            # Monta o dicionário de resultados
            resultado_linha = {
                'modelo_nome': nome_base,
                'No. Observations': int(modelo.nobs), 
                'R-squared': modelo.rsquared, 
                
                'Coef (dist_km)': modelo.params.get('distancia_metro_km'),
                'P-valor (dist_km)': modelo.pvalues.get('distancia_metro_km'), 
                
                'Coef (quartos)': modelo.params.get('quartos'),
                'P-valor (quartos)': modelo.pvalues.get('quartos'), 
                
                'Coef (metragem)': modelo.params.get('metragem'),
                'P-valor (metragem)': modelo.pvalues.get('metragem'), 
                
                'Coef (vagas)': modelo.params.get('vagas'),
                'P-valor (vagas)': modelo.pvalues.get('vagas'),
                
                'Coef (const)': modelo.params.get('const'),
                'P-valor (const)': modelo.pvalues.get('const')
            }

            lista_resultados.append(resultado_linha)
        
        except Exception as e:
            print(f"   Erro ao processar o arquivo {nome_base}: {e}")


    # PARTE 5: DATAFRAME COM O RESUMO DAS ANÁLISES
    
    if not lista_resultados:
        print("Nenhum resultado de regressão foi gerado. Encerrando.")
    else:
    
        df_resultados = pd.DataFrame(lista_resultados)

        df_resultados = df_resultados.set_index('modelo_nome')
        
        # Arredondamento para melhor visualização
        df_resultados['R-squared'] = df_resultados['R-squared'].round(3)
        
        df_resultados['P-valor (dist_km)'] = df_resultados['P-valor (dist_km)'].round(3)
        df_resultados['Coef (dist_km)'] = df_resultados['Coef (dist_km)'].round(2)
        
        df_resultados['P-valor (quartos)'] = df_resultados['P-valor (quartos)'].round(3)
        df_resultados['Coef (quartos)'] = df_resultados['Coef (quartos)'].round(2)
        
        df_resultados['P-valor (metragem)'] = df_resultados['P-valor (metragem)'].round(3)
        df_resultados['Coef (metragem)'] = df_resultados['Coef (metragem)'].round(2)
        
        df_resultados['P-valor (vagas)'] = df_resultados['P-valor (vagas)'].round(3)
        df_resultados['Coef (vagas)'] = df_resultados['Coef (vagas)'].round(2)

        df_resultados['P-valor (const)'] = df_resultados['P-valor (const)'].round(3)
        df_resultados['Coef (const)'] = df_resultados['Coef (const)'].round(2)


        caminho_saida_resumo = os.path.join(output_dir, "resumo_regressoesMultipla.xlsx")
        
        df_resultados.to_excel(caminho_saida_resumo)

        print(f"Resultados da regressão salvos em: {caminho_saida_resumo}")
    





# PARTE 6 - GRAFICOS


output_dir = "dados_final"
caminho_dos_arquivos = os.path.join(output_dir, "imoveis_*.xlsx")
lista_de_arquivos = sorted(glob.glob(caminho_dos_arquivos))

# Variável para guardar o DataFrame total
df_total = None

# arregar todos os arquivos finais em um único DataFrame
if not lista_de_arquivos:
    print(f"ERRO: Nenhum arquivo 'imoveis_*.xlsx' encontrado em '{output_dir}'.")
else:
    try:
        lista_dfs = []
        for arquivo in lista_de_arquivos:
            df_temp = pd.read_excel(arquivo)
            lista_dfs.append(df_temp)
        
        df_total = pd.concat(lista_dfs, ignore_index=True)
        print(f"Dados de {len(lista_de_arquivos)} arquivos carregados. Total de {len(df_total)} imóveis para plotar.")
        
        # Define o estilo dos gráficos
        sns.set_style("whitegrid")

    except Exception as e:
        print(f"Erro ao carregar os dados: {e}")

if df_total is not None:
    try:
        print("\nGerando Gráfico 1: Histograma de Preços...")
        plt.figure(figsize=(10, 6))
        
        # Filtra valores extremos para melhor visualização
        sns.histplot(df_total[df_total['preco'] < 4000000]['preco'], kde=True, bins=50)
        
        plt.title('Distribuição dos Preços dos Imóveis (Até R$ 4M)', fontsize=16)
        plt.xlabel('Preço (R$)', fontsize=12)
        plt.ylabel('metragem', fontsize=12)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Salva o arquivo de imagem
        path_saida_1 = os.path.join(output_dir, 'grafico_1_histograma_precos.png')
        plt.savefig(path_saida_1)
    
        
        print(f"Gráfico 1 salvo em: {path_saida_1}")
        
    except Exception as e:
        print(f"ERRO ao gerar gráfico 1: {e}")
else:
    print("\nPulando Gráfico 1 (dados não foram carregados).")



if df_total is not None:
    try:
        print("\nGerando Gráfico 2: Preço por Quartos...")
        plt.figure(figsize=(10, 6))
        
        sns.boxplot(x='quartos', y='preco', data=df_total)
        
        plt.title('Distribuição de Preço por Número de Quartos', fontsize=16)
        plt.xlabel('Número de Quartos', fontsize=12)
        plt.ylabel('Preço (R$)', fontsize=12)
        plt.tight_layout()
        
        # Salva o arquivo de imagem
        path_saida_2 = os.path.join(output_dir, 'grafico_2_boxplot_quartos.png')
        plt.savefig(path_saida_2)

        
        print(f"Gráfico 2 salvo em: {path_saida_2}")

    except Exception as e:
        print(f"ERRO ao gerar gráfico 2: {e}")
else:
    print("\nPulando Gráfico 2 (dados não foram carregados).")

print("\n--- Processo de gráficos concluído! ---")


if df_total is not None:
    try:
        print("\nGerando Gráfico 4: Mapa de Calor de Correlação...")
        plt.figure(figsize=(10, 8))
    
        colunas_corr = ['preco', 'quartos', 'metragem', 'vagas', 'distancia_metro_km']
        df_corr = df_total[colunas_corr].dropna() # Remove linhas com NaN
        
        # 2. Calcula a matriz de correlação
        matriz_corr = df_corr.corr()
        
        # 3. Desenha o mapa de calor (heatmap)
        sns.heatmap(matriz_corr, 
                    annot=True,    
                    cmap='coolwarm',  
                    fmt='.2f')        # Formata os números para 2 casas decimais
                    
        plt.title('Mapa de Calor das Correlações', fontsize=16)
        plt.tight_layout()
        
        # Salva o arquivo de imagem
        path_saida_4 = os.path.join(output_dir, 'grafico_4_heatmap_correlacao.png')
        plt.savefig(path_saida_4)
 
        print(f"Gráfico 4 salvo em: {path_saida_4}")

    except Exception as e:
        print(f"ERRO ao gerar gráfico 4: {e}")
else:
    print("\nPulando Gráfico 4 (dados não foram carregados).")


































    # ===================================================================
    # --- NOVA PARTE 6 ADICIONADA ABAIXO ---
    # ===================================================================


    # PARTE 6: GERAÇÃO DE GRÁFICOS EXPLORATÓRIOS

    print(f"\n--- INICIANDO PARTE 6: Geração de Gráficos ---")
    
    # 1. Carregar todos os arquivos finais em um único DataFrame
    try:
        lista_dfs = []
        for arquivo in lista_de_arquivos:
            df_temp = pd.read_excel(arquivo)
            # Adiciona uma coluna para saber de qual modelo o dado veio
            df_temp['modelo_origem'] = os.path.basename(arquivo).replace('.xlsx', '')
            lista_dfs.append(df_temp)
        
        df_total = pd.concat(lista_dfs, ignore_index=True)
        print(f"Dados de {len(lista_de_arquivos)} arquivos carregados. Total de {len(df_total)} imóveis para plotar.")

        # Define o estilo dos gráficos
        sns.set_style("whitegrid")
        
        # 2. Gráfico 1: Histograma de Preços
        print("Gerando Gráfico 1: Histograma de Preços...")
        plt.figure(figsize=(10, 6))
        # Remove valores muito extremos (ex: > 4 milhões) para melhor visualização
        sns.histplot(df_total[df_total['preco'] < 4000000]['preco'], kde=True, bins=50)
        plt.title('Distribuição dos Preços dos Imóveis (Até R$ 4M)', fontsize=16)
        plt.xlabel('Preço (R$)', fontsize=12)
        plt.ylabel('Contagem', fontsize=12)
        plt.gca().xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'R$ {x:,.0f}'))
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'grafico_1_histograma_precos.png'))
        plt.close()

        # 3. Gráfico 2: Boxplot de Preço por Número de Quartos
        print("Gerando Gráfico 2: Preço por Quartos...")
        plt.figure(figsize=(10, 6))
        sns.boxplot(x='quartos', y='preco', data=df_total)
        plt.title('Distribuição de Preço por Número de Quartos', fontsize=16)
        plt.xlabel('Número de Quartos', fontsize=12)
        plt.ylabel('Preço (R$)', fontsize=12)
        plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'R$ {x:,.0f}'))
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'grafico_2_boxplot_quartos.png'))
        plt.close()

        # 4. Gráfico 3: Gráfico de Dispersão de Preço vs. Metragem
        print("Gerando Gráfico 3: Preço vs. Metragem...")
        plt.figure(figsize=(10, 6))
        # Limita a metragem para melhor visualização (ex: até 500 m²)
        df_plot = df_total[(df_total['metragem'] <= 500) & (df_total['preco'] < 4000000)]
        sns.scatterplot(x='metragem', y='preco', data=df_plot, alpha=0.5, hue='modelo_origem')
        plt.title('Preço vs. Metragem (Até 500 m²)', fontsize=16)
        plt.xlabel('Metragem (m²)', fontsize=12)
        plt.ylabel('Preço (R$)', fontsize=12)
        plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'R$ {x:,.0f}'))
        plt.gca().xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f} m²'))
        plt.legend(title='Grupo de Valor')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'grafico_3_dispersao_metragem.png'))
        plt.close()

        # 5. Gráfico 4: Gráfico de Dispersão de Preço vs. Distância do Metrô
        print("Gerando Gráfico 4: Preço vs. Distância do Metrô...")
        plt.figure(figsize=(10, 6))
        # Limita a distância para melhor visualização (ex: até 5 km)
        df_plot_dist = df_total[df_total['distancia_metro_km'] <= 5]
        sns.scatterplot(x='distancia_metro_km', y='preco', data=df_plot_dist, alpha=0.5, hue='quartos', palette='viridis')
        plt.title('Preço vs. Distância do Metrô (Até 5 km)', fontsize=16)
        plt.xlabel('Distância até o Metrô (km)', fontsize=12)
        plt.ylabel('Preço (R$)', fontsize=12)
        plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'R$ {x:,.0f}'))
        plt.gca().xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.1f} km'))
        plt.legend(title='Nº Quartos')
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'grafico_4_dispersao_distancia.png'))
        plt.close()

        print(f"\n--- PARTE 6: Gráficos salvos em '{output_dir}' ---")

    except Exception as e:
        print(f"Erro ao gerar gráficos: {e}")
        print("Verifique se os arquivos 'imoveis_*.xlsx' existem em 'dados_final'.")

print("\n--- SCRIPT COMPLETO FINALIZADO (com gráficos) ---")








