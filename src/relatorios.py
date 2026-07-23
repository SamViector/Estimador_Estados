import pandas as pd

def exibir_quadro_medidas(net):
    """Imprime a tabela de entrada (Z e Covariância)."""
    df = pd.DataFrame({
        'ID': net.measurement.index,
        'Tipo': net.measurement['measurement_type'],
        'Elemento': net.measurement['element_type'] + " " + net.measurement['element'].astype(str),
        'Valor (pu)': net.measurement['value'],
        'Desvio Padrão (σ)': net.measurement['std_dev'],
        'Covariância (R)': net.measurement['std_dev'] ** 2
    })
    print("\n" + "="*70 + "\n TABELA DE MEDIÇÕES SCADA (VETOR Z)\n" + "="*70)
    print(df.to_string(index=False))

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