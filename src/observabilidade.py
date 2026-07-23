def analisar_observabilidade(net):
    """
    [ETAPA 4: OBSERVABILIDADE] Verifica o critério numérico e topológico M >= 2N - 1.
    """
    num_barras = len(net.bus)
    var_estado = (2 * num_barras) - 1 # V e Theta (menos referência angular)
    num_medidas = len(net.measurement)
    redundancia = num_medidas - var_estado

    print(f" -> [OBSERVABILIDADE] Barras: {num_barras} | Variáveis de Estado: {var_estado} | Medidas Ativas: {num_medidas}")
    
    if num_medidas < var_estado:
        print(" -> [OBSERVABILIDADE] ❌ ALERTA CRÍTICO: Sistema INOBSERVÁVEL (Falta de redundância)!")
        return False, redundancia
    elif redundancia == 0:
        print(" -> [OBSERVABILIDADE] ⚠️ ALERTA: Sistema estritamente observável. Todas as medidas são CRÍTICAS!")
        return True, redundancia
    else:
        print(f" -> [OBSERVABILIDADE] ✅ Sistema plenamente OBSERVÁVEL (Índice de Redundância: +{redundancia}).")
        return True, redundancia