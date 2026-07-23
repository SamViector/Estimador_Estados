import numpy as np
import pandapower as pp

def simular_medidor(valor_real, desvio_padrao):
    """Adiciona ruído gaussiano ao valor verdadeiro do fluxo de carga."""
    return valor_real + np.random.normal(0, desvio_padrao)

def instalar_medidas_scada(net):
    """[ETAPA 1: SCADA] Instala conjunto redundante de medições elétricas."""
    net.measurement.drop(net.measurement.index, inplace=True)
    b1, b2, b3, b4 = 0, 1, 2, 3

    # Medidores de Tensão (V) - Desvio: 0.4%
    pp.create_measurement(net, "v", "bus", simular_medidor(net.res_bus.at[b1, 'vm_pu'], 0.004), 0.004, b1, name="V1")
    pp.create_measurement(net, "v", "bus", simular_medidor(net.res_bus.at[b2, 'vm_pu'], 0.004), 0.004, b2, name="V2")

    # Injeções de Potência (P, Q) - Desvio: 0.002 pu
    for b in [b2, b3, b4]:
        pp.create_measurement(net, "p", "bus", simular_medidor(-net.res_bus.at[b, 'p_mw'], 0.002), 0.002, b, name=f"P{b+1}")
        if b != b4: # Q4 não medido para testar redundância cruzada
            pp.create_measurement(net, "q", "bus", simular_medidor(-net.res_bus.at[b, 'q_mvar'], 0.002), 0.002, b, name=f"Q{b+1}")

    # Fluxos de Linha (P, Q) - Desvio: 0.001 pu
    for idx, linha in net.line.iterrows():
        pp.create_measurement(net, "p", "line", simular_medidor(net.res_line.at[idx, 'p_from_mw'], 0.001), 0.001, idx, side="from", name=f"P_{linha['name']}")
        pp.create_measurement(net, "q", "line", simular_medidor(net.res_line.at[idx, 'q_from_mvar'], 0.001), 0.001, idx, side="from", name=f"Q_{linha['name']}")

def pre_filtrar_medidas(net):
    """
    [ETAPA 3: PRÉ-FILTRAGEM] Remove erros de hardware óbvios antes do cálculo numérico.
    Ex: Tensões negativas ou magnitudes excessivamente absurdas (> 5.0 pu).
    """
    medidas_iniciais = len(net.measurement)
    # Filtra tensões negativas ou maiores que 1.5 pu
    filtro_v = (net.measurement.measurement_type == 'v') & ((net.measurement.value < 0.0) | (net.measurement.value > 1.5))
    # Filtra potências absurdas (> 10 pu)
    filtro_pq = (net.measurement.measurement_type.isin(['p', 'q'])) & (net.measurement.value.abs() > 10.0)
    
    invalidas = net.measurement[filtro_v | filtro_pq].index
    if len(invalidas) > 0:
        print(f" -> [PRÉ-FILTRO] ⚠️ {len(invalidas)} medida(s) com erro absurdo de hardware eliminada(s)!")
        net.measurement.drop(invalidas, inplace=True)
    else:
        print(" -> [PRÉ-FILTRO] ✅ Nenhuma anomalia bruta de hardware detectada nas leituras iniciais.")
    return len(net.measurement)