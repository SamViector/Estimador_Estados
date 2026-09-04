import pandas as pd

def exibir_quadro_medidas(net):
    """
    Exibe a tabela do vetor de medições SCADA (Z) mapeando os índices 
    dos elementos para seus nomes reais (ex: Barra 1, Linha 1-2).
    """
    elementos_nomeados = []

    # Varre as medições e busca o nome real cadastrado na topologia
    for idx, row in net.measurement.iterrows():
        e_type = row['element_type']
        elem_idx = row['element']

        if e_type == "bus":
            if 'name' in net.bus.columns and pd.notna(net.bus.at[elem_idx, 'name']):
                nome = net.bus.at[elem_idx, 'name']
            else:
                nome = f"Barra {elem_idx + 1}"
        elif e_type == "line":
            if 'name' in net.line.columns and pd.notna(net.line.at[elem_idx, 'name']):
                nome = net.line.at[elem_idx, 'name']
            else:
                nome = f"Linha {elem_idx + 1}"
        else:
            nome = f"{e_type} {elem_idx}"

        elementos_nomeados.append(nome)

    # Cria o DataFrame para exibição
    df_scada = pd.DataFrame({
        'ID': net.measurement.index,
        'Tipo': net.measurement['measurement_type'],
        'Elemento': elementos_nomeados,
        'Valor': net.measurement['value'],
        'Desvio Padrão (σ)': net.measurement['std_dev'],
        'Covariância (R)': net.measurement['std_dev'] ** 2
    })

    print("\n" + "="*70)
    print(" TABELA DE MEDIÇÕES SCADA (VETOR Z)")
    print("="*70)
    print(df_scada.to_string(index=False, float_format='{:.6f}'.format))

def exibir_comparacao_finais(net):
    """Imprime comparação exata entre Módulo e Ângulo Verdadeiro vs Estimado."""
    df_v = pd.DataFrame({
        'Barra': [f"Barra {i+1}" for i in range(len(net.bus))],
        'V_Real (pu)': net.res_bus['vm_pu'].values,
        'V_Est (pu)': net.res_bus_est['vm_pu'].values,
        'Erro Abs': abs(net.res_bus['vm_pu'].values - net.res_bus_est['vm_pu'].values)
    })
    print("\n" + "="*60 + "\n PERFIL DE TENSÃO (ESTIMADO vs VERDADEIRO)\n" + "="*60)
    print(df_v.to_string(index=False))

def exibir_tabelas_comparacao_estados(net):
    """
    [CÉLULA 3 e 4] Exibe as tabelas comparativas das variáveis de estado 
    (Magnitude e Ângulo de Tensão) entre o Fluxo de Carga Real e o Estimado.
    """
    barras = [f"Barra {i+1}" for i in range(len(net.bus))]
    
    # 1. Tabela de Magnitude de Tensão (pu)
    df_tensao = pd.DataFrame({
        'Barra': barras,
        'Valor Estimado': net.res_bus_est['vm_pu'].values,
        'Real': net.res_bus['vm_pu'].values
    })
    df_tensao['Erro Absolute'] = abs(df_tensao['Valor Estimado'] - df_tensao['Real'])
    
    print("\n" + "="*55)
    print(" TABELA 1: COMPARAÇÃO - MAGNITUDE DE TENSÃO (pu)")
    print("="*55)
    print(df_tensao.to_string(index=False, float_format='{:.6f}'.format))

    # 2. Tabela de Ângulo de Tensão (graus)
    df_angulo = pd.DataFrame({
        'Barra': barras,
        'Valor Estimado': net.res_bus_est['va_degree'].values,
        'Real': net.res_bus['va_degree'].values
    })
    df_angulo['Erro Absoluto'] = abs(df_angulo['Valor Estimado'] - df_angulo['Real'])

    print("\n" + "="*55)
    print(" TABELA 2: COMPARAÇÃO - ÂNGULO DE TENSÃO (graus)")
    print("="*55)
    print(df_angulo.to_string(index=False, float_format='{:.6f}'.format))


def exibir_tabela_residuos(net):
    """
    [CÉLULA 5] Exibe a comparação detalhada do vetor de medidas:
    Valor Real, Valor Medido SCADA (z) e Valor Estimado WLS h(x).
    """
    medicoes, mensurado_z, estimado_hx, real_hx = [], [], [], []

    for idx, row in net.measurement.iterrows():
        m_type = row['measurement_type']
        e_type = row['element_type']
        element = row['element']
        mensurado_z.append(row['value'])

        # Mapeamento limpo de grandezas
        if e_type == "bus":
            nome_elem = net.bus.at[element, 'name'][:7]
            if m_type == "v":
                h_val = net.res_bus_est.at[element, 'vm_pu']
                r_val = net.res_bus.at[element, 'vm_pu']
                nome = f"Tensão (V) - {nome_elem}"
            elif m_type in ["p", "q"]:
                # Inversão de sinal: Injeção = -Demanda
                col = 'p_mw' if m_type == "p" else 'q_mvar'
                h_val = -net.res_bus_est.at[element, col]
                r_val = -net.res_bus.at[element, col]
                grandeza = "Ativa (P)" if m_type == "p" else "Reat. (Q)"
                nome = f"Injeção {grandeza} - {nome_elem}"

        elif e_type == "line":
            nome_elem = net.line.at[element, 'name']
            side = row['side']
            col = f"{m_type}_{side}_mw" if m_type == "p" else f"{m_type}_{side}_mvar"
            h_val = net.res_line_est.at[element, col]
            r_val = net.res_line.at[element, col]
            grandeza = "Ativo (P)" if m_type == "p" else "Reat. (Q)"
            nome = f"Fluxo {grandeza} - {nome_elem}"

        medicoes.append(nome)
        estimado_hx.append(h_val)
        real_hx.append(r_val)

    df_res = pd.DataFrame({
        'Medição / Grandeza': medicoes,
        'Real (pu)': real_hx,
        'Mensurado z (pu)': mensurado_z,
        'Estimado h(x) (pu)': estimado_hx
    })
    
    # Cálculo do resíduo bruto |z - h(x)|
    df_res['Resíduo |z - h(x)|'] = abs(df_res['Mensurado z (pu)'] - df_res['Estimado h(x) (pu)'])

    print("\n" + "="*95)
    print(" TABELA 3: COMPARAÇÃO DE MEDIÇÕES - ANÁLISE DE RESÍDUOS |z - h(x)|")
    print("="*95)
    print(df_res.to_string(index=False, float_format='{:.5f}'.format))