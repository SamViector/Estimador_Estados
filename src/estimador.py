import pandas as pd
from pandapower.estimation import estimate, chi2_analysis, remove_bad_data

# Importa o seu novo módulo de IA do arquivo ia_preditiva.py
from src.ia_preditiva import recuperar_observabilidade_com_ia

def executar_pipeline_wls(net, limiar_lnr=3.5, modo_interativo=True):
    """
    [ETAPA 5 e 6: ESTIMAÇÃO E BAD DATA] Executa o WLS, avalia o Qui-Quadrado e purga erros.
    Se o sistema colapsar por falta de redundância, pergunta ao utilizador se deseja acionar a IA.
    """
    print(" -> [WLS] A iniciar cálculo iterativo (Gauss-Newton)...")
    
    try:
        sucesso = estimate(net, init="flat")
    except Exception as e:
        print(f" -> [WLS] ❌ Falha na convergência do algoritmo inicial! Erro: {e}")
        return False
        
    if not sucesso:
        print(" -> [WLS] ❌ Falha na convergência do algoritmo inicial!")
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
        
        if e_type == "bus":
            nome_elem = net.bus.at[elem, 'name'][:7] if 'name' in net.bus.columns else f"B{elem}"
            if m_type == "v":
                h_val = net.res_bus_est.at[elem, 'vm_pu']
                grandeza = "Tensão (V)"
            elif m_type in ["p", "q"]:
                col = 'p_mw' if m_type == "p" else 'q_mvar'
                h_val = -net.res_bus_est.at[elem, col]
                grandeza = "Injeção P" if m_type == "p" else "Injeção Q"
        elif e_type == "line":
            nome_elem = net.line.at[elem, 'name'] if 'name' in net.line.columns else f"L{elem}"
            side = row['side']
            col = f"{m_type}_{side}_mw" if m_type == "p" else f"{m_type}_{side}_mvar"
            h_val = net.res_line_est.at[elem, col]
            grandeza = "Fluxo P" if m_type == "p" else "Fluxo Q"
            
        r_bruto = abs(val_z - h_val)
        r_norm = r_bruto / std_dev  
        
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
    print(f" -> Valor Lido no SCADA (z)          : {pior_medida['Lido SCADA (z)']:.5f}")
    print(f" -> Valor Reconstruído WLS h(x)      : {pior_medida['Estimado h(x)']:.5f}")
    print(f" -> Erro Bruto Absoluto |z - h(x)|   : {pior_medida['Erro Bruto']:.5f}")
    print(f" -> Resíduo Normalizado (Gravidade)  : {pior_medida['Resíduo Norm. (r_N)']:.2f} σ (Limiar usual = 3.0 σ)")
    print("="*75 + "\n")
    
    # =====================================================================
    # 🛡️ PROTEÇÃO E EXPURGO
    # =====================================================================
    if not chi2_analysis(net, chi2_prob_false=0.05):
        print(" -> [BAD DATA] ✅ Teste Qui-Quadrado aprovado. Distribuição de resíduos aceitável.")
        return True
    
    print(" -> [BAD DATA] 🚨 Alarme no Teste Qui-Quadrado! Iniciando varredura LNR...")
    
    medidas_antes = net.measurement.copy()
    indices_antes = set(medidas_antes.index)
    
    # ---> AQUI ESTÁ A BLINDAGEM CONTRA O ERRO DO PANDAPOWER <---
    sucesso_purga = False
    try:
        sucesso_purga = remove_bad_data(net, init="flat", rn_max_threshold=limiar_lnr)
    except Exception as e:
        print(" -> [BAD DATA] ⚠️ O motor do pandapower colapsou ao tentar remover a medida (Matriz Singular).")
        sucesso_purga = False  # Força o código a ir para a IA
    
    if sucesso_purga:
        indices_depois = set(net.measurement.index)
        indices_removidos = sorted(list(indices_antes - indices_depois))
        
        print(f" -> [BAD DATA] ✅ Purga concluída! {len(indices_removidos)} medida(s) defeituosa(s) expurgada(s):\n")
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
            if e_type == "bus":
                nome_elem = net.bus.at[elem_idx, 'name'] if 'name' in net.bus.columns else f"Barra {elem_idx+1}"
            elif e_type == "line":
                nome_elem = net.line.at[elem_idx, 'name'] if 'name' in net.line.columns else f"Linha {elem_idx+1}"
            else:
                nome_elem = f"{e_type} {elem_idx}"
            grandeza = "Tensão (V)" if m_type == "v" else ("Pot. Ativa (P)" if m_type == "p" else "Pot. Reat. (Q)")
            print(f" {idx:3d} | {grandeza:<14} | {nome_elem:<20} | {val_z:<15.4f} | {std_dev:.4f}")
        print("="*85 + "\n")
        return True
        
    # =================================================================
    # 🤖 INTEGRAÇÃO DO DIGITAL TWIN (IA) COM OPÇÃO INTERATIVA
    # =================================================================
    else:
        print(" -> [BAD DATA] ❌ O sistema perdeu a observabilidade ou quebrou a matriz Jacobiana!")
        
        if modo_interativo:
            print("\n ⚠️ ALERTA DO CENTRO DE CONTROLO: SISTEMA INOBSERVÁVEL")
            print(" Deseja acionar o Módulo de Inteligência Artificial (Digital Twin) para restaurar a rede?")
            
            while True:
                escolha = input(" Ativar IA Preditiva? (S/N): ").strip().upper()
                if escolha == 'S':
                    ativar_ia = True
                    break
                elif escolha == 'N':
                    ativar_ia = False
                    break
                else:
                    print(" ⚠️ Digite S para Sim ou N para Não.")
        else:
            ativar_ia = True
            
        if ativar_ia:
            indices_agora = set(net.measurement.index)
            indices_removidos_falha = sorted(list(indices_antes - indices_agora))
            
            # Failsafe: se a biblioteca pandapower não tirou ninguém antes de explodir, 
            # o nosso código retira o pior medidor "à força" para a IA poder preencher a lacuna
            if len(indices_removidos_falha) == 0:
                pior_id = pior_medida['ID']
                net.measurement.drop(pior_id, inplace=True)
                indices_removidos_falha = [pior_id]
                print(f" -> [SISTEMA] Medidor suspeito (ID {pior_id}) isolado manualmente para substituição.")
            
            recuperar_observabilidade_com_ia(net, medidas_antes, indices_removidos_falha)
            
            print("\n -> [WLS] A recalcular estimador utilizando as predições do Digital Twin...")
            
            try:
                sucesso_recuperacao = estimate(net, init="flat")
            except Exception:
                sucesso_recuperacao = False
                
            if sucesso_recuperacao:
                print(" -> [WLS] ✅ SUCESSO! A Inteligência Artificial estabilizou a rede e o fluxo convergiu.")
                return True
            else:
                print(" -> [WLS] ❌ Falha Crítica: Mesmo com a injeção da IA, a rede não convergiu.")
                return False
        else:
            print("\n -> [SISTEMA] Operação abortada pelo utilizador. O sistema permanecerá inobservável.")
            return False