import pandas as pd
from pandapower.estimation import estimate, chi2_analysis

def exibir_tabela_medidas(net):
    """
    Lê a matriz de medidas atual do pandapower e imprime o Vetor Z e a 
    Covariância R formatados para análise do SCADA.
    """
    print("\n" + "="*65)
    print(" TABELA DE DADOS MEDIDOS (VETOR Z E COVARIÂNCIA)")
    print("="*65)

    num_medicao, grandeza, valor_pu, covariancia = [], [], [], []

    # Iterando sobre as medições configuradas para gerar a tabela
    for i, (idx, row) in enumerate(net.measurement.iterrows()):
        m_type = row['measurement_type']
        e_type = row['element_type']
        element = row['element']

        num_medicao.append(i + 1)
        valor_pu.append(row['value'])
        # Covariância (R) = variância = desvio padrão ao quadrado
        covariancia.append(row['std_dev'] ** 2)

        if e_type == "bus":
            nome_elemento = net.bus.at[element, 'name'][:7] # Pega apenas "Barra X"
            if m_type == "v":
                nome = f"Tensão (V) - {nome_elemento}"
            elif m_type == "p":
                nome = f"Injeção Ativa (P) - {nome_elemento}"
            elif m_type == "q":
                nome = f"Injeção Reat. (Q) - {nome_elemento}"

        elif e_type == "line":
            nome_elemento = net.line.at[element, 'name']
            if m_type == "p":
                nome = f"Fluxo Ativo (P) - {nome_elemento}"
            elif m_type == "q":
                nome = f"Fluxo Reat. (Q) - {nome_elemento}"

        grandeza.append(nome)

    df_medidas = pd.DataFrame({
        'Nº da Medição': num_medicao,
        'Grandeza Mensurada': grandeza,
        'Valor (pu)': valor_pu,
        'Covariância': covariancia
    })

    # Formatando para exibir a covariância com 6 casas decimais
    pd.options.display.float_format = '{:.6f}'.format
    print(df_medidas.to_string(index=False))
    pd.reset_option('display.float_format')


def exibir_tabelas_comparacao(net):
    """
    Compara o Estado Verdadeiro com o Estado Estimado, separando
    a análise em Magnitude de Tensão (pu) e Ângulo (graus).
    """
    # Para garantir que os erros muito pequenos (ex: 0.00001) sejam visíveis
    pd.options.display.float_format = '{:.6f}'.format

    # ---------------------------------------------------------
    # TABELA 1: MAGNITUDE DE TENSÃO
    # ---------------------------------------------------------
    print("\n" + "="*55)
    print(" TABELA DE COMPARAÇÃO - MAGNITUDE DE TENSÃO (pu)")
    print("="*55)

    df_tensao = pd.DataFrame()
    df_tensao['Barra'] = ['Barra 1', 'Barra 2', 'Barra 3', 'Barra 4']
    df_tensao['Valor Estimado'] = net.res_bus_est['vm_pu'].values
    df_tensao['Real'] = net.res_bus['vm_pu'].values
    df_tensao['Erro'] = abs(df_tensao['Valor Estimado'] - df_tensao['Real'])

    print(df_tensao.to_string(index=False))

    # ---------------------------------------------------------
    # TABELA 2: ÂNGULO DE TENSÃO
    # ---------------------------------------------------------
    print("\n" + "="*55)
    print(" TABELA DE COMPARAÇÃO - ÂNGULO DE TENSÃO (graus)")
    print("="*55)

    df_angulo = pd.DataFrame()
    df_angulo['Barra'] = ['Barra 1', 'Barra 2', 'Barra 3', 'Barra 4']
    df_angulo['Valor Estimado'] = net.res_bus_est['va_degree'].values
    df_angulo['Real'] = net.res_bus['va_degree'].values
    df_angulo['Erro'] = abs(df_angulo['Valor Estimado'] - df_angulo['Real'])

    print(df_angulo.to_string(index=False))
    
    # Restaura a formatação padrão do pandas
    pd.reset_option('display.float_format')

def exibir_tabela_residuos(net):
    """
    Gera e imprime uma tabela comparativa detalhada das grandezas elétricas elétricas
    calculando os resíduos brutos entre o medido z e o recalculado h(x).
    """
    print("\n" + "="*95)
    print(" TABELA DE COMPARAÇÃO DE MEDIÇÕES - ANÁLISE DE RESÍDUOS |z - h(x)|")
    print("="*95)

    medicoes, mensurado_z, estimado_hx, real_hx = [], [], [], []

    for idx, row in net.measurement.iterrows():
        m_type = row['measurement_type']
        e_type = row['element_type']
        element = row['element']
        mensurado_z.append(row['value'])

        if e_type == "bus":
            nome_elemento = net.bus.at[element, 'name'][:7]
            if m_type == "v":
                h_val = net.res_bus_est.at[element, 'vm_pu']
                r_val = net.res_bus.at[element, 'vm_pu']
                nome = f"Tensão (V) - {nome_elemento}"
            elif m_type == "p":
                # Demanda WLS deve ser invertida para se comparar com a injeção
                h_val = -net.res_bus_est.at[element, 'p_mw']
                r_val = -net.res_bus.at[element, 'p_mw']
                nome = f"Injeção Ativa (P) - {nome_elemento}"
            elif m_type == "q":
                h_val = -net.res_bus_est.at[element, 'q_mvar']
                r_val = -net.res_bus.at[element, 'q_mvar']
                nome = f"Injeção Reat. (Q) - {nome_elemento}"

        elif e_type == "line":
            nome_elemento = net.line.at[element, 'name']
            side = row['side']
            if m_type == "p":
                h_val = net.res_line_est.at[element, f'p_{side}_mw']
                r_val = net.res_line.at[element, f'p_{side}_mw']
                nome = f"Fluxo Ativo (P) - {nome_elemento}"
            elif m_type == "q":
                h_val = net.res_line_est.at[element, f'q_{side}_mvar']
                r_val = net.res_line.at[element, f'q_{side}_mvar']
                nome = f"Fluxo Reat. (Q) - {nome_elemento}"

        medicoes.append(nome)
        estimado_hx.append(h_val)
        real_hx.append(r_val)

    df_residuos = pd.DataFrame({
        'Medição / Grandeza': medicoes,
        'Real (pu)': real_hx,
        'Mensurado z (pu)': mensurado_z,
        'Estimado h(x) (pu)': estimado_hx
    })

    # Calcula a diferença absoluta (vetor de resíduos)
    df_residuos['Resíduo |z - h(x)|'] = abs(df_residuos['Mensurado z (pu)'] - df_residuos['Estimado h(x) (pu)'])

    # Formatando para exibir os resultados com 5 casas decimais
    pd.options.display.float_format = '{:.5f}'.format
    print(df_residuos.to_string(index=False))
    pd.reset_option('display.float_format')


def obter_medida_maior_erro(net):
    """
    Varre todas as medições ativas, calcula o resíduo bruto |z - h(x)| 
    e o resíduo ponderado |z - h(x)| / std_dev, retornando a medida 
    com o maior desvio em relação ao modelo elétrico.
    """
    maior_residuo_ponderado = -1.0
    medida_campea = None

    for idx, row in net.measurement.iterrows():
        m_type = row['measurement_type']
        e_type = row['element_type']
        element = row['element']
        val_z = row['value']
        std_dev = row['std_dev']

        # Extrai h(x) estimado do WLS
        if e_type == "bus":
            nome_elem = net.bus.at[element, 'name'][:7]
            if m_type == "v":
                h_val = net.res_bus_est.at[element, 'vm_pu']
                nome = f"Tensão (V) - {nome_elem}"
            elif m_type == "p":
                h_val = -net.res_bus_est.at[element, 'p_mw']
                nome = f"Injeção Ativa (P) - {nome_elem}"
            elif m_type == "q":
                h_val = -net.res_bus_est.at[element, 'q_mvar']
                nome = f"Injeção Reat. (Q) - {nome_elem}"

        elif e_type == "line":
            nome_elem = net.line.at[element, 'name']
            side = row['side']
            if m_type == "p":
                h_val = net.res_line_est.at[element, f'p_{side}_mw']
                nome = f"Fluxo Ativo (P) - {nome_elem}"
            elif m_type == "q":
                h_val = net.res_line_est.at[element, f'q_{side}_mvar']
                nome = f"Fluxo Reat. (Q) - {nome_elem}"

        # Resíduo Bruto r = |z - h(x)|
        r_bruto = abs(val_z - h_val)
        
        # Resíduo Ponderado r_w = |z - h(x)| / sigma
        r_ponderado = r_bruto / std_dev

        if r_ponderado > maior_residuo_ponderado:
            maior_residuo_ponderado = r_ponderado
            medida_campea = {
                'id': idx,
                'nome': nome,
                'tipo': m_type,
                'valor_z': val_z,
                'estimado_hx': h_val,
                'residuo_bruto': r_bruto,
                'residuo_ponderado': r_ponderado,
                'std_dev': std_dev
            }

    return medida_campea


def remove_bad_data(net, init="flat", rn_max_threshold=3.0):
    """
    Implementa o algoritmo LNR (Largest Normalized Residual) para detecção 
    e remoção iterativa de erros grosseiros em medições.
    
    O algoritmo:
    1. Executa estimação WLS
    2. Calcula resíduos normalizados para todas as medições
    3. Remove a medida com maior resíduo normalizado (se > threshold)
    4. Re-estima e repete até passar no χ² ou não haver mais medidas
    
    Parâmetros:
    -----------
    net : pandapower network
        Rede elétrica com medições
    init : str
        Inicialização do algoritmo WLS ("flat" ou "dc")
    rn_max_threshold : float
        Limiar para remover uma medida (em sigmas). Padrão: 3.0
    
    Retorna:
    --------
    bool
        True se convergiu sem erros, False se falhou (perda de observabilidade)
    """
    
    MAX_ITERACOES = 10
    MIN_MEDIDAS = 7  # Mínimo de medições para manter observabilidade
    iteracao = 0
    
    while iteracao < MAX_ITERACOES:
        iteracao += 1
        
        # Verifica limite mínimo de medições
        if len(net.measurement) < MIN_MEDIDAS:
            print(f"❌ LIMITE MÍNIMO ATINGIDO: Apenas {len(net.measurement)} medidas restantes.")
            print(f"   Remover mais medidas comprometeria a observabilidade do sistema.")
            return False
        
        # Executa estimação WLS
        try:
            sucesso = estimate(net, init=init)
            if not sucesso:
                print(f"❌ [ITERAÇÃO {iteracao}] WLS não convergiu.")
                return False
        except Exception as e:
            print(f"❌ [ITERAÇÃO {iteracao}] Erro na estimação WLS: {e}")
            return False
        
        # Verifica χ² para detectar erros grosseiros
        tem_erro_grosseiro = chi2_analysis(net, chi2_prob_false=0.05)
        
        if not tem_erro_grosseiro:
            # ✅ Sucesso: nenhum erro grosseiro detectado
            print(f"✅ [ITERAÇÃO {iteracao}] Teste χ² PASSOU - Nenhum erro grosseiro detectado.")
            return True
        
        # 🚨 Erro grosseiro detectado: encontra e remove a medida com maior resíduo
        medida_pior = obter_medida_maior_erro(net)
        
        if medida_pior is None:
            print(f"❌ [ITERAÇÃO {iteracao}] Não foi possível calcular resíduos.")
            return False
        
        # Verifica se o resíduo ponderado ultrapassa o threshold
        if medida_pior['residuo_ponderado'] < rn_max_threshold:
            print(f"⚠️  [ITERAÇÃO {iteracao}] Resíduo max ({medida_pior['residuo_ponderado']:.2f}σ) < threshold ({rn_max_threshold}σ)")
            print(f"    Parando iterações (erro muito pequeno para remover).")
            return True
        
        # Remove a medida com maior resíduo
        print(f"🔄 [ITERAÇÃO {iteracao}] REMOVENDO: {medida_pior['nome']}")
        print(f"   └─ Resíduo Ponderado: {medida_pior['residuo_ponderado']:.2f}σ (threshold: {rn_max_threshold}σ)")
        net.measurement.drop(medida_pior['id'], inplace=True)
    
    print(f"❌ Limite de {MAX_ITERACOES} iterações atingido sem convergência.")
    return False