import numpy as np
import pandapower as pp

def simular_medidor(valor_real, desvio_padrao):
    """Adiciona ruído gaussiano ao valor verdadeiro do fluxo de carga."""
    return valor_real + np.random.normal(0, desvio_padrao)

def instalar_medidas_scada_4barras(net):
    """[ETAPA 1: SCADA] Instala conjunto redundante de medições elétricas."""
    net.measurement.drop(net.measurement.index, inplace=True)
    b1, b2, b3, b4 = 0, 1, 2, 3

    # Medidores de Tensão (V) - Desvio: 0.4%
    pp.create_measurement(net, "v", "bus", simular_medidor(net.res_bus.at[b1, 'vm_pu'], 0.004), 0.004, b1, name="V1")
    pp.create_measurement(net, "v", "bus", simular_medidor(net.res_bus.at[b2, 'vm_pu'], 0.004), 0.004, b2, name="V2")

# Injeções de Potência (P, Q) - Desvio: 0.002 pu
    for b in [b2, b3, b4]:
    # Potência ativa (P)
        pp.create_measurement(net, "p", "bus", simular_medidor(net.res_bus.at[b, 'p_mw'], 1),  1,b,name=f"P{b+1}")
    # Potência reativa (Q) 
        pp.create_measurement(net, "q", "bus",simular_medidor(net.res_bus.at[b, 'q_mvar'], 1), 1,b,name=f"Q{b+1}")

    # Fluxos de Linha (P, Q) - Desvio: 0.001 pu
    for idx, linha in net.line.iterrows():
        pp.create_measurement(net, "p", "line", simular_medidor(net.res_line.at[idx, 'p_from_mw'], 0.8), 0.8, idx, side="from", name=f"P_{linha['name']}")
        pp.create_measurement(net, "q", "line", simular_medidor(net.res_line.at[idx, 'q_from_mvar'], 0.8), 0.8, idx, side="from", name=f"Q_{linha['name']}")

def instalar_medidas_scada_5barras(net):
    """
    Instala medidores SCADA no sistema de 5 barras com precisão proporcional (2%)
    e piso de 0.005 pu, pulando a injeção da Barra Slack para evitar conflito numérico.
    """
    net.measurement.drop(net.measurement.index, inplace=True)
    b1, b2, b3, b4, b5 = 0, 1, 2, 3, 4

     # Medidores de Tensão (V) - Desvio: 0.4%
    pp.create_measurement(net, "v", "bus", simular_medidor(net.res_bus.at[b1, 'vm_pu'], 0.004), 0.004, b1, name="V1")
    pp.create_measurement(net, "v", "bus", simular_medidor(net.res_bus.at[b2, 'vm_pu'], 0.004), 0.004, b2, name="V2")
    pp.create_measurement(net, "v", "bus", simular_medidor(net.res_bus.at[b3, 'vm_pu'], 0.004), 0.004, b3, name="V3")
    pp.create_measurement(net, "v", "bus", simular_medidor(net.res_bus.at[b4, 'vm_pu'], 0.004), 0.004, b4, name="V4")
    pp.create_measurement(net, "v", "bus", simular_medidor(net.res_bus.at[b5, 'vm_pu'], 0.004), 0.004, b5, name="V5")
    
 # Injeções de Potência (P, Q) - Desvio: 0.002 pu
    for b in [b2, b3, b4, b5]:
        # Potência ativa (P)
        pp.create_measurement(net, "p", "bus", simular_medidor(-net.res_bus.at[b, 'p_mw'], 0.002), 0.002, b, name=f"P{b+1}")
        # Potência reativa (Q) 
        pp.create_measurement(net, "q", "bus", simular_medidor(-net.res_bus.at[b, 'q_mvar'], 0.002), 0.002, b, name=f"Q{b+1}")

    # Fluxos de Linha (P, Q) - Desvio: 0.001 pu
    for idx, linha in net.line.iterrows():
        pp.create_measurement(net, "p", "line", simular_medidor(net.res_line.at[idx, 'p_from_mw'], 0.001), 0.001, idx, side="from", name=f"P_{linha['name']}")
        pp.create_measurement(net, "q", "line", simular_medidor(net.res_line.at[idx, 'q_from_mvar'], 0.001), 0.001, idx, side="from", name=f"Q_{linha['name']}")

    print(f" -> [SCADA] {len(net.measurement)} medidores alocados com sucesso na rede de 5 Barras!")

def pre_filtrar_medidas(net):
    """
    [ETAPA 3: PRÉ-FILTRAGEM] Remove erros de hardware óbvios antes do cálculo numérico.
    Ex: Tensões negativas ou magnitudes excessivamente absurdas (> 5.0 pu).
    """
    medidas_iniciais = len(net.measurement)
    # Filtra tensões negativas ou maiores que 1.5 pu
    filtro_v = (net.measurement.measurement_type == 'v') & ((net.measurement.value < 0.0) | (net.measurement.value > 1.5))
    # Filtra potências absurdas (> 10 pu)
    filtro_pq = (net.measurement.measurement_type.isin(['p', 'q'])) & (net.measurement.value.abs() > 250)
    
    invalidas = net.measurement[filtro_v | filtro_pq].index
    if len(invalidas) > 0:
        print(f" -> [PRÉ-FILTRO] ⚠️ {len(invalidas)} medida(s) com erro absurdo de hardware eliminada(s)!")
        net.measurement.drop(invalidas, inplace=True)
    else:
        print(" -> [PRÉ-FILTRO] ✅ Nenhuma anomalia bruta de hardware detectada nas leituras iniciais.")
    return len(net.measurement)


def instalar_medidas_scada_generico(net, desvio_v=0.004, desvio_p=1, desvio_q=1):
    """
    Instala medidas SCADA automaticamente para qualquer topologia (ex: IEEE 14, 30).
    Roda o fluxo de carga real e adiciona ruído gaussiano estatístico.
    """
    np.random.seed(42)
    pp.runpp(net) # Obtém o Estado Verdadeiro base
    
    # Limpa medidas antigas se existirem
    net.measurement.drop(net.measurement.index, inplace=True)

    # 1. Medidas de Tensão (V) em todas as Barras
    for bus_id in net.bus.index:
        v_real = net.res_bus.at[bus_id, 'vm_pu']
        v_med = v_real + np.random.normal(0, desvio_v)
        pp.create_measurement(net, "v", "bus", value=v_med, std_dev=desvio_v, element=bus_id)

    # 2. Medidas de Injeção (P, Q) em todas as Barras
    for bus_id in net.bus.index:
        p_real = -net.res_bus.at[bus_id, 'p_mw']
        q_real = -net.res_bus.at[bus_id, 'q_mvar']
        pp.create_measurement(net, "p", "bus", value=p_real + np.random.normal(0, desvio_p), std_dev=desvio_p, element=bus_id)
        pp.create_measurement(net, "q", "bus", value=q_real + np.random.normal(0, desvio_q), std_dev=desvio_q, element=bus_id)

    # 3. Medidas de Fluxo (P, Q) nas Linhas (Lado 'from')
    for line_id in net.line.index:
        p_from = net.res_line.at[line_id, 'p_from_mw']
        q_from = net.res_line.at[line_id, 'q_from_mvar']
        pp.create_measurement(net, "p", "line", value=p_from + np.random.normal(0, desvio_p), std_dev=desvio_p, element=line_id, side="from")
        pp.create_measurement(net, "q", "line", value=q_from + np.random.normal(0, desvio_q), std_dev=desvio_q, element=line_id, side="from")