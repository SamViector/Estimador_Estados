import pandas as pd
from pandapower.estimation import estimate, chi2_analysis, remove_bad_data

# Importa o seu novo módulo de IA do arquivo ia_preditiva.py
from src.ia_preditiva import recuperar_observabilidade_com_ia

def executar_pipeline_wls(net, limiar_lnr=3.5, modo_interativo=True):
    """
    [ETAPA 5 e 6: ESTIMAÇÃO E BAD DATA] Executa o WLS, avalia o Qui-Quadrado e purga erros.
    Se o sistema colapsar por falta de redundância ou excesso de erros (Breakdown Point), 
    aciona o Filtro de Plausibilidade e a Inteligência Artificial.
    """
    print(" -> [WLS] A iniciar cálculo iterativo (Gauss-Newton)...")
    
    try:
        sucesso = estimate(net, init="flat")
    except Exception:
        sucesso = False
        
    # =====================================================================
    # 🛡️ PROTOCOLO DE EMERGÊNCIA: FILTRO DE PLAUSIBILIDADE + IA
    # =====================================================================
    if not sucesso or not hasattr(net, 'res_bus_est') or net.res_bus_est.empty:
        print(" -> [WLS] ❌ Falha Crítica: O algoritmo divergiu na iteração inicial (Breakdown Point)!")
        print(" -> [SCADA] Acionando Filtro de Plausibilidade Física (Limit Checker)...")
        
        medidas_antes = net.measurement.copy()
        indices_absurdos = []
        
        # Varredura para encontrar violações grosseiras das Leis da Física
        for idx, row in medidas_antes.iterrows():
            val = row['value']
            m_type = row['measurement_type']
            
            # Limites: Tensão fora de 0.75 a 1.25 pu | Potências maiores que 1.2 pu (120 MW)
            if m_type == 'v' and (val < 0.75 or val > 1.25):
                indices_absurdos.append(idx)
            elif m_type in ['p', 'q'] and abs(val) > 250.0:  # 250 MW ou MVAr
                indices_absurdos.append(idx)
                
        if len(indices_absurdos) > 0:
            print(f" -> [SCADA] Foram detetados {len(indices_absurdos)} sensores com leituras fisicamente impossíveis!")
            
            if modo_interativo:
                print("\n ⚠️ ALERTA DO CENTRO DE CONTROLO: COLAPSO MATRICIAL EMINENTE")
                print(" Deseja acionar o Módulo de Inteligência Artificial para substituir os sensores mortos?")
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
                # O SCADA expurga os sensores queimados antes do WLS
                net.measurement.drop(indices_absurdos, inplace=True)
                
                # A IA entra em cena para gerar os dados físicos daqueles sensores
                recuperar_observabilidade_com_ia(net, medidas_antes, indices_absurdos)
                
                print("\n -> [WLS] A recalcular estimador utilizando as predições da IA...")
                try:
                    sucesso_recuperacao = estimate(net, init="flat")
                    if not hasattr(net, 'res_bus_est') or net.res_bus_est.empty:
                        sucesso_recuperacao = False
                except Exception:
                    sucesso_recuperacao = False
                    
                if sucesso_recuperacao:
                    print(" -> [WLS] ✅ SUCESSO! A Inteligência Artificial ressuscitou a rede a partir do zero!")
                    return True
                else:
                    print(" -> [WLS] ❌ Falha Crítica: Mesmo com IA, a rede está irrecuperável.")
                    return False
            else:
                print("\n -> [SISTEMA] Operação abortada. O sistema colapsou.")
                return False
        else:
            print(" -> [SCADA] ❌ O Filtro não encontrou anomalias extremas evidentes. Colapso matemático total.")
            return False

    print(" -> [WLS] ✅ Estimação convergida com sucesso inicial!")

    # =====================================================================
    # 🔍 DIAGNÓSTICO DETALHADO E LNR (Fluxo Normal)
    # =====================================================================
    lista_residuos = []
    for idx, row in net.measurement.iterrows():
        m_type = row['measurement_type']
        e_type = row['element_type']
        elem = row['element']
        val_z = row['value']
        std_dev = row['std_dev']
        
        if e_type == "bus":
            nome_elem = str(net.bus.at[elem, 'name'])[:7] if 'name' in net.bus.columns and pd.notna(net.bus.at[elem, 'name']) else f"B{elem}"
            if m_type == "v":
                h_val = net.res_bus_est.at[elem, 'vm_pu']
                grandeza = "Tensão (V)"
            elif m_type in ["p", "q"]:
                col = 'p_mw' if m_type == "p" else 'q_mvar'
                h_val = net.res_bus_est.at[elem, col]
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
            'ID': idx, 'Elemento': f"{grandeza} - {nome_elem}",
            'Lido SCADA (z)': val_z, 'Estimado h(x)': h_val,
            'Desvio (σ)': std_dev, 'Erro Bruto': r_bruto, 'Resíduo Norm. (r_N)': r_norm
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
    print(f" -> Resíduo Normalizado (Gravidade)  : {pior_medida['Resíduo Norm. (r_N)']:.2f} σ")
    print("="*75 + "\n")
    
    if not chi2_analysis(net, chi2_prob_false=0.05):
        print(" -> [BAD DATA] ✅ Teste Qui-Quadrado aprovado. Distribuição de resíduos aceitável.")
        return True
    
    print(" -> [BAD DATA] 🚨 Alarme no Teste Qui-Quadrado! Iniciando varredura LNR...")
    
    medidas_antes = net.measurement.copy()
    indices_antes = set(medidas_antes.index)
    
    try:
        sucesso_purga = remove_bad_data(net, init="flat", rn_max_threshold=limiar_lnr)
    except Exception:
        sucesso_purga = False  
    
    if sucesso_purga:
        indices_depois = set(net.measurement.index)
        indices_removidos = sorted(list(indices_antes - indices_depois))
        print(f" -> [BAD DATA] ✅ Purga concluída! {len(indices_removidos)} medida(s) defeituosa(s) expurgada(s).")
        return True
    else:
        print(" -> [BAD DATA] ❌ O LNR expurgou medidas e quebrou a matriz Jacobiana (Inobservabilidade)!")
        if modo_interativo:
            print("\n ⚠️ ALERTA DO CENTRO DE CONTROLO: SISTEMA INOBSERVÁVEL")
            while True:
                escolha = input(" Ativar IA Preditiva? (S/N): ").strip().upper()
                if escolha in ['S', 'N']: break
            ativar_ia = (escolha == 'S')
        else:
            ativar_ia = True
            
        if ativar_ia:
            indices_agora = set(net.measurement.index)
            indices_removidos_falha = sorted(list(indices_antes - indices_agora))
            if len(indices_removidos_falha) == 0:
                pior_id = pior_medida['ID']
                net.measurement.drop(pior_id, inplace=True)
                indices_removidos_falha = [pior_id]
            recuperar_observabilidade_com_ia(net, medidas_antes, indices_removidos_falha)
            print("\n -> [WLS] A recalcular estimador utilizando as predições do Digital Twin...")
            try:
                if estimate(net, init="flat") and not net.res_bus_est.empty:
                    print(" -> [WLS] ✅ SUCESSO! A Inteligência Artificial estabilizou a rede e o fluxo convergiu.")
                    return True
            except Exception: pass
            print(" -> [WLS] ❌ Falha Crítica: Mesmo com a injeção da IA, a rede não convergiu.")
            return False
        else:
            print("\n -> [SISTEMA] Operação abortada pelo utilizador.")
            return False