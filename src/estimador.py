import pandas as pd

from pandapower.estimation import estimate, chi2_analysis, remove_bad_data


def executar_pipeline_wls(net, limiar_lnr=3.5):
    """
    [ETAPA 5 e 6: ESTIMAÇÃO E BAD DATA] Executa o WLS, avalia o Qui-Quadrado e purga erros.
    """
    print(" -> [WLS] A iniciar cálculo iterativo (Gauss-Newton)...")
    try:
        sucesso = estimate(net, init="flat")
        if not sucesso:
            print(" -> [WLS] ❌ Falha na convergência do algoritmo!")
            return False
        
        print(" -> [WLS] ✅ Estimação convergida com sucesso!")

        # =====================================================================
        # 🔍 DIAGNÓSTICO DETALHADO: RANKING DO MAIOR RESÍDUO NORMALIZADO (LNR)
        # =====================================================================
        
        lista_residuos = []
        for idx, row in net.measurement.iterrows():
            m_type = row['measurement_type']
            e_type = row['element_type']
            elem = row['element']
            val_z = row['value']
            std_dev = row['std_dev']
            
            # Captura o valor estimado h(x)
            if e_type == "bus":
                nome_elem = net.bus.at[elem, 'name'][:7]
                if m_type == "v":
                    h_val = net.res_bus_est.at[elem, 'vm_pu']
                    grandeza = "Tensão (V)"
                elif m_type in ["p", "q"]:
                    col = 'p_mw' if m_type == "p" else 'q_mvar'
                    h_val = -net.res_bus_est.at[elem, col]
                    grandeza = "Injeção P" if m_type == "p" else "Injeção Q"
            elif e_type == "line":
                nome_elem = net.line.at[elem, 'name']
                side = row['side']
                col = f"{m_type}_{side}_mw" if m_type == "p" else f"{m_type}_{side}_mvar"
                h_val = net.res_line_est.at[elem, col]
                grandeza = "Fluxo P" if m_type == "p" else "Fluxo Q"
                
            r_bruto = abs(val_z - h_val)
            r_norm = r_bruto / std_dev  # Resíduo normalizado em sigmas (σ)
            
            lista_residuos.append({
                'ID': idx,
                'Elemento': f"{grandeza} - {nome_elem}",
                'Lido SCADA (z)': val_z,
                'Estimado h(x)': h_val,
                'Desvio (σ)': std_dev,
                'Erro Bruto': r_bruto,
                'Resíduo Norm. (r_N)': r_norm
            })
            
        df_diag = pd.DataFrame(lista_residuos).sort_values(by='Resíduo Norm. (r_N)', ascending=False)
        pior_medida = df_diag.iloc[0]
        
        print("\n" + "="*75)
        print(" 🚨 RELATÓRIO DE INSPEÇÃO SCADA - MEDIDA COM MAIOR ERRO DETECTADO")
        print("="*75)
        print(f" -> Medidor Suspeito (1º no Ranking) : {pior_medida['Elemento']} (ID: {pior_medida['ID']})")
        print(f" -> Valor Lido no SCADA (z)          : {pior_medida['Lido SCADA (z)']:.5f} pu")
        print(f" -> Valor Reconstruído WLS h(x)      : {pior_medida['Estimado h(x)']:.5f} pu")
        print(f" -> Erro Bruto Absoluto |z - h(x)|   : {pior_medida['Erro Bruto']:.5f} pu")
        print(f" -> Resíduo Normalizado (Gravidade)  : {pior_medida['Resíduo Norm. (r_N)']:.2f} σ (Limiar usual = 3.0 σ)")
        print("="*75 + "\n")
        # =====================================================================
        
        # Teste Qui-Quadrado (Análise Global)
        if not chi2_analysis(net, chi2_prob_false=0.05):
            print(" -> [BAD DATA] ✅ Teste Qui-Quadrado aprovado. Distribuição de resíduos aceitável.")
            return True
        
        print(" -> [BAD DATA] 🚨 Alarme no Teste Qui-Quadrado! Iniciando varredura LNR...")
        
        # 1. Tira uma cópia de segurança das medições ANTES da purga
        medidas_antes = net.measurement.copy()
        indices_antes = set(medidas_antes.index)
        
        # 2. Executa a remoção automática de Bad Data
        sucesso_purga = remove_bad_data(net, init="flat", rn_max_threshold=limiar_lnr)
        
        if sucesso_purga:
            # 3. Descobre quais índices desaparecidos foram expurgados
            indices_depois = set(net.measurement.index)
            indices_removidos = sorted(list(indices_antes - indices_depois))
            
            print(f" -> [BAD DATA] ✅ Purga concluída! {len(indices_removidos)} medida(s) defeituosa(s) expurgada(s):\n")
            
            # 4. Imprime o relatório detalhado das medidas removidas
            print("="*85)
            print(" 🗑️  RELATÓRIO DE AUDITORIA SCADA - MEDIDAS EXPURGADAS (LNR)")
            print("="*85)
            print(f" {'ID':<3} | {'Grandeza':<14} | {'Elemento':<20} | {'Valor Lido (z)':<15} | {'Desvio (σ)':<10}")
            print("-" * 85)
            
            for idx in indices_removidos:
                row = medidas_antes.loc[idx]
                m_type = row['measurement_type']
                e_type = row['element_type']
                elem_idx = row['element']
                val_z = row['value']
                std_dev = row['std_dev']
                
                # Mapeia o nome amigável do elemento
                if e_type == "bus":
                    nome_elem = net.bus.at[elem_idx, 'name'] if 'name' in net.bus.columns else f"Barra {elem_idx+1}"
                elif e_type == "line":
                    nome_elem = net.line.at[elem_idx, 'name'] if 'name' in net.line.columns else f"Linha {elem_idx+1}"
                else:
                    nome_elem = f"{e_type} {elem_idx}"
                
                # Mapeia a grandeza
                if m_type == "v":
                    grandeza = "Tensão (V)"
                    unidade = "pu"
                elif m_type == "p":
                    grandeza = "Pot. Ativa (P)"
                    unidade = "MW" if e_type == "line" or abs(val_z) > 1.5 else "pu"
                elif m_type == "q":
                    grandeza = "Pot. Reat. (Q)"
                    unidade = "MVAr" if e_type == "line" or abs(val_z) > 1.5 else "pu"
                else:
                    grandeza = m_type.upper()
                    unidade = ""
                
                str_valor = f"{val_z:.4f} {unidade}"
                print(f" {idx:3d} | {grandeza:<14} | {nome_elem:<20} | {str_valor:<15} | {std_dev:.4f}")
            
            print("="*85 + "\n")
            return True
        else:
            print(" -> [BAD DATA] ❌ O erro foi detectado, mas não houve redundância local para isolá-lo.")
            return False
            
    except Exception as erro:
        print(f" -> [ERRO CRÍTICO NO MOTOR WLS] Colapso matricial: {erro}")
        return False