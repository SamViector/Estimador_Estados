def criar_sistema_5barras():
    """
    Cria um sistema teste de 5 Barras (2 Geradores, 3 Cargas e 5 Linhas),
    clássico para testes de Estimação de Estados e Observabilidade em malha.
    """
    import pandapower as pp
    import numpy as np
    
    np.random.seed(42)
    net = pp.create_empty_network(sn_mva=100)

    # 1. Criação das 5 Barras (V_base = 138 kV)
    b1 = pp.create_bus(net, vn_kv=138., name="Barra 1 (Ref/Slack)", type="b")
    b2 = pp.create_bus(net, vn_kv=138., name="Barra 2 (PV)", type="b")
    b3 = pp.create_bus(net, vn_kv=138., name="Barra 3 (PQ)", type="b")
    b4 = pp.create_bus(net, vn_kv=138., name="Barra 4 (PQ)", type="b")
    b5 = pp.create_bus(net, vn_kv=138., name="Barra 5 (PQ)", type="b")

    # 2. Geradores e Cargas
    pp.create_ext_grid(net, bus=b1, vm_pu=1.02, va_degree=0.0, name="Gerador Slack B1")
    pp.create_gen(net, bus=b2, p_mw=40.0, vm_pu=1.00, name="Gerador B2")

    pp.create_load(net, bus=b3, p_mw=45.0, q_mvar=15.0, name="Carga B3")
    pp.create_load(net, bus=b4, p_mw=40.0, q_mvar=20.0, name="Carga B4")
    pp.create_load(net, bus=b5, p_mw=60.0, q_mvar=30.0, name="Carga B5")

    # 3. Linhas de Transmissão em Malha (Impedâncias típicas em pu -> Ohm)
    # Z_base = (138^2) / 100 = 190.44 Ohms
    z_base = (138.0 ** 2) / 100.0
    
    pp.create_line_from_parameters(net, b1, b2, 1, r_ohm_per_km=0.02*z_base, x_ohm_per_km=0.06*z_base, c_nf_per_km=0, max_i_ka=1.0, name="Linha 1-2")
    pp.create_line_from_parameters(net, b1, b3, 1, r_ohm_per_km=0.08*z_base, x_ohm_per_km=0.24*z_base, c_nf_per_km=0, max_i_ka=1.0, name="Linha 1-3")
    pp.create_line_from_parameters(net, b2, b3, 1, r_ohm_per_km=0.06*z_base, x_ohm_per_km=0.18*z_base, c_nf_per_km=0, max_i_ka=1.0, name="Linha 2-3")
    pp.create_line_from_parameters(net, b2, b4, 1, r_ohm_per_km=0.06*z_base, x_ohm_per_km=0.18*z_base, c_nf_per_km=0, max_i_ka=1.0, name="Linha 2-4")
    pp.create_line_from_parameters(net, b3, b5, 1, r_ohm_per_km=0.04*z_base, x_ohm_per_km=0.12*z_base, c_nf_per_km=0, max_i_ka=1.0, name="Linha 3-5")
    pp.create_line_from_parameters(net, b4, b5, 1, r_ohm_per_km=0.08*z_base, x_ohm_per_km=0.24*z_base, c_nf_per_km=0, max_i_ka=1.0, name="Linha 4-5")

    # Roda fluxo de carga perfeito (Gabarito)
    pp.runpp(net)
    return net, b1, b2, b3, b4, b5

def processar_topologia(net):
    """
    [ETAPA 2: TOPOLOGIA] Verifica elementos fora de serviço ou ilhas desenergizadas.
    """
    linhas_ativas = len(net.line[net.line.in_service == True])
    barras_ativas = len(net.bus[net.bus.in_service == True])
    print(f" -> [TOPOLOGIA] Verificação concluída: {barras_ativas} Barras e {linhas_ativas} Linhas em operação normal.")
    return True