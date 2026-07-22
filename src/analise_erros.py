# =========================================================
# ARQUIVO: src/analise_erros.py
# Módulo de Segurança do Centro de Operação
# =========================================================
from pandapower.estimation import chi2_analysis, remove_bad_data

def verificar_e_corrigir_erros(net):
    """
    Analisa os resultados do estimador WLS utilizando o Teste Qui-Quadrado.
    Se detetar um erro grosseiro (Bad Data), aciona a rotina do 
    Maior Resíduo Normalizado (LNR) para o localizar e remover.
    """
    print("\n[MÓDULO DE SEGURANÇA] A analisar a integridade das medições (Qui-Quadrado)...")
    
    # 1. Teste de Detecção Global
    tem_erro = chi2_analysis(net, chi2_prob_false=0.05)

    if tem_erro:
        print("  🚨 ALARME SCADA: Anomalia estatística detetada! (Possível Bad Data)")
        print("  -> A iniciar varredura LNR (Maior Resíduo Normalizado) para purga...")
        
        # 2. Teste de Identificação e Remoção
        # A função remove_bad_data apaga a medida falsa e RODA O ESTIMADOR NOVAMENTE
        sucesso_purga = remove_bad_data(net, init="flat", rn_max_threshold=3.0)
        
        if sucesso_purga:
            print("  ✅ SUCESSO: O algoritmo identificou, isolou e removeu a medida defeituosa!")
            print("  -> O Estado da rede foi recalculado automaticamente de forma segura.")
            return True
        else:
            print("  ❌ FALHA CRÍTICA: Erro detetado, mas não houve redundância suficiente para purgar.")
            return False
    else:
        print("  ✅ FILTRO APROVADO: Nenhuma anomalia grave detetada. Dados SCADA confiáveis.")
        return True