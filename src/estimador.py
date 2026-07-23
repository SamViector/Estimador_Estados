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
        
        # Teste Qui-Quadrado (Análise Global)
        if not chi2_analysis(net, chi2_prob_false=0.05):
            print(" -> [BAD DATA] ✅ Teste Qui-Quadrado aprovado. Distribuição de resíduos aceitável.")
            return True
        
        # Se houve alarme no Qui-Quadrado, aciona o teste LNR
        print(" -> [BAD DATA] 🚨 Alarme no Teste Qui-Quadrado! Iniciando varredura LNR...")
        medidas_antes = set(net.measurement.index)
        
        if remove_bad_data(net, init="flat", rn_max_threshold=limiar_lnr):
            removidas = medidas_antes - set(net.measurement.index)
            print(f" -> [BAD DATA] ✅ Purga concluída! {len(removidas)} medida(s) defeituosa(s) expurgada(s).")
            return True
        else:
            print(" -> [BAD DATA] ❌ O erro foi detectado, mas não houve redundância local para isolá-lo.")
            return False
            
    except Exception as erro:
        print(f" -> [ERRO CRÍTICO NO MOTOR WLS] Colapso matricial: {erro}")
        return False