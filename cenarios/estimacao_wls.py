import sys
import os
import warnings
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pandapower.estimation import estimate, chi2_analysis
from src.sistema_eletrico import criar_sistema_4barras
from src.medidas import adicionar_medidas_base

# Importe a nova função de resíduos aqui!
from src.tabelas import exibir_tabela_medidas, exibir_tabelas_comparacao, exibir_tabela_residuos, obter_medida_maior_erro, remove_bad_data
pd.options.mode.chained_assignment = None
warnings.filterwarnings("ignore", module="pandapower")

def main():
    print("=========================================================")
    print("  CENÁRIO 1: ESTIMADOR WLS COM SCADA NORMAL (SEM FALHAS) ")
    print("=========================================================\n")
    
    # 1. Cria a rede elétrica
    net, b1, b2, b3, b4 = criar_sistema_4barras()
    
    # 2. Instala os medidores SCADA
    print("-> A instalar medidores e simular ruído de telecomunicações...")
    adicionar_medidas_base(net, b1, b2, b3, b4)
    
    # 👉 3. MOSTRAR A TABELA DO VETOR Z E MATRIZ R ANTES DE ESTIMAR
    exibir_tabela_medidas(net)
    
    # 4. Executa o Estimador de Estados
    print("\n-> A executar o algoritmo WLS (Newton-Gauss)...")
    sucesso = estimate(net, init="flat")
    
    if sucesso:
        print("✅ Estimação WLS convergida com sucesso!\n")
        
        # 1. IDENTIFICAÇÃO PRÉVIA DA MEDIDA COM MAIOR ERRO
        pior_medida = obter_medida_maior_erro(net)
        
        print("="*75)
        print(" 🔍 DIAGNÓSTICO DE RESÍDUOS DO ESTIMADOR WLS")
        print("="*75)
        print(f" -> Medida com Maior Resíduo Ponderado: {pior_medida['nome']}")
        print(f" -> Valor Mensurado (z) : {pior_medida['valor_z']:.5f} pu")
        print(f" -> Valor Estimado h(x) : {pior_medida['estimado_hx']:.5f} pu")
        print(f" -> Resíduo Bruto |z-h|  : {pior_medida['residuo_bruto']:.5f} pu")
        print(f" -> Resíduo Ponderado   : {pior_medida['residuo_ponderado']:.2f} sigmas (σ={pior_medida['std_dev']})")
        print("="*75 + "\n")

        # 2. Teste Qui-Quadrado
        tem_erro_grosseiro = chi2_analysis(net, chi2_prob_false=0.05)
        
        if not tem_erro_grosseiro:
            print("✅ Verificação Aprovada: O Teste Qui-Quadrado (X²) não detetou erros grosseiros.")
        else:
            print("🚨 ALARME: O Teste Qui-Quadrado (X²) detetou a presença de Erros Grosseiros!")
            print("-> A iniciar tentativa de remoção da medida defeituosa (LNR)...\n")
            
            medidas_antes = net.measurement.copy()
            indices_antes = set(medidas_antes.index)
            
            # 3. BLINDAGEM DE SEGURANÇA (TRY / EXCEPT)
            try:
                sucesso_purga = remove_bad_data(net, init="flat", rn_max_threshold=3.0)
                
                if sucesso_purga:
                    indices_depois = set(net.measurement.index)
                    indices_removidos = indices_antes - indices_depois
                    
                    print("✅ SUCESSO NA PURGA: Medida(s) isolada(s) e removida(s):")
                    for idx in indices_removidos:
                        medida_ruim = medidas_antes.loc[idx]
                        print(f"   ❌ [REMOVIDA] Medidor ID {idx} | Tipo: '{medida_ruim['measurement_type']}' | Valor: {medida_ruim['value']:.5f} pu")
                    print("\n-> O Estado da rede foi recalculado automaticamente com sucesso.\n")
                else:
                    print("❌ FALHA: Erro detetado, mas o LNR não convergiu para uma remoção limpa.\n")
                    
            except Exception as erro:
                print("!"*75)
                print(" 🚨 ALERTA: NÃO FOI POSSÍVEL PURGAR A MEDIDA (PERDA DE OBSERVABILIDADE)")
                print("!"*75)
                print(f" -> Culpado Identificado pelo Diagnóstico : {pior_medida['nome']}")
                print(" -> Causa Numérica do Colapso            : A medida expurgada é uma MEDIDA CRÍTICA.")
                print("    Removê-la reduz o total de equações abaixo do mínimo necessário (7 medidas).")
                print(f" -> Detalhe técnico do pandapower        : {erro}\n")

        # Exibe as tabelas comparativas
        exibir_tabelas_comparacao(net)
        exibir_tabela_residuos(net)
        
    else:
        print("❌ Falha na convergência do Estimador.")

if __name__ == "__main__":
    main()