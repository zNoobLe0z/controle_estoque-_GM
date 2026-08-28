import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime
import warnings

warnings.filterwarnings('ignore', category=UserWarning)

st.set_page_config(page_title="Controle de Estoque", layout="wide")

# ==========================================
# 1. BANCO DE DADOS (Conectado ao Supabase)
# ==========================================
def iniciar_banco():
    conn = psycopg2.connect(st.secrets["DB_URL"])
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS produtos (id SERIAL PRIMARY KEY, nome TEXT, categoria TEXT, quantidade INTEGER, estoque_minimo INTEGER, unidade TEXT DEFAULT 'un')''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS movimentacoes (id SERIAL PRIMARY KEY, produto TEXT, tipo TEXT, quantidade INTEGER, funcionario TEXT, empresa TEXT DEFAULT '-', data_retirada TEXT, motivo TEXT, data TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS agenda (id SERIAL PRIMARY KEY, data_hora TEXT, fornecedor TEXT, material TEXT, status TEXT, observacao TEXT)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (id SERIAL PRIMARY KEY, usuario TEXT UNIQUE, senha TEXT, cargo TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS categorias (id SERIAL PRIMARY KEY, nome TEXT UNIQUE)''')
    
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO usuarios (usuario, senha, cargo) VALUES ('engenheiro', '1234', 'Engenheiro')")
        cursor.execute("INSERT INTO usuarios (usuario, senha, cargo) VALUES ('adm', '1234', 'ADM')")
        cursor.execute("INSERT INTO usuarios (usuario, senha, cargo) VALUES ('NoobLe0', 'Leo29122003!', 'Dev')")
        
    cursor.execute("SELECT COUNT(*) FROM categorias")
    if cursor.fetchone()[0] == 0:
        categorias_padrao = [("Ferramentas",), ("Eletrônicos",), ("Limpeza",), ("Matéria Prima",), ("Outros",)]
        cursor.executemany("INSERT INTO categorias (nome) VALUES (%s)", categorias_padrao)
        
    conn.commit()
    conn.close()

try:
    iniciar_banco()
except Exception as e:
    st.error(f"Aguardando conexão com o banco de dados. Erro: {e}")

if 'logado' not in st.session_state:
    st.session_state['logado'] = False
if 'cargo' not in st.session_state:
    st.session_state['cargo'] = ""
if 'usuario_logado' not in st.session_state:
    st.session_state['usuario_logado'] = ""

# ==========================================
# 2. SISTEMA DE LOGIN 
# ==========================================
if not st.session_state['logado']:
    col_vazia1, col_centro, col_vazia2 = st.columns([1, 1, 1]) 
    with col_centro:
        st.title("🔒 Acesso Restrito")
        with st.form("form_login"):
            usuario = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            entrar = st.form_submit_button("Entrar")
            
            if entrar:
                conn = psycopg2.connect(st.secrets["DB_URL"])
                cursor = conn.cursor()
                cursor.execute("SELECT cargo FROM usuarios WHERE usuario = %s AND senha = %s", (usuario, senha))
                resultado = cursor.fetchone()
                conn.close()
                
                if resultado:
                    st.session_state['logado'] = True
                    st.session_state['cargo'] = resultado[0]
                    st.session_state['usuario_logado'] = usuario
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos!")

# ==========================================
# 3. O SISTEMA 
# ==========================================
if st.session_state['logado']:
    col_titulo, col_botao = st.columns([5, 1])
    with col_titulo:
        st.title("📦 Sistema de Controle de Estoque")
        st.caption(f"Logado como: {st.session_state['usuario_logado']} | Perfil: {st.session_state['cargo']}")
    with col_botao:
        if st.button("Sair / Logout", use_container_width=True):
            st.session_state['logado'] = False
            st.session_state['cargo'] = ""
            st.session_state['usuario_logado'] = ""
            st.rerun()

    if st.session_state['cargo'] == "Dev":
        aba1, aba2, aba3, aba4 = st.tabs(["📊 Estoque", "🔄 Entrada / Saída", "📅 Agenda", "⚙️ Configurações"])
    else:
        aba1, aba2, aba3 = st.tabs(["📊 Estoque", "🔄 Entrada / Saída", "📅 Agenda"])
        aba4 = None

    # --- ABA 1: ESTOQUE ---
    with aba1:
        col1, col2 = st.columns([1, 2])
        with col1:
            with st.expander("➕ Adicionar Nova Categoria"):
                with st.form("form_nova_categoria"):
                    nova_cat = st.text_input("Nome da Categoria")
                    if st.form_submit_button("Salvar Categoria") and nova_cat:
                        conn = psycopg2.connect(st.secrets["DB_URL"])
                        cursor = conn.cursor()
                        try:
                            cursor.execute("INSERT INTO categorias (nome) VALUES (%s)", (nova_cat,))
                            conn.commit()
                            st.success("Categoria adicionada!")
                            st.rerun()
                        except psycopg2.IntegrityError:
                            st.error("Esta categoria já existe.")
                        conn.close()

            st.subheader("Cadastrar Novo Material")
            conn = psycopg2.connect(st.secrets["DB_URL"])
            df_categorias = pd.read_sql_query('SELECT nome FROM categorias ORDER BY nome', conn)
            lista_categorias = df_categorias['nome'].tolist() if not df_categorias.empty else ["Geral"]
            
            with st.form("form_novo_produto"):
                nome_produto = st.text_input("Nome do Material")
                categoria = st.selectbox("Categoria", lista_categorias)
                
                lista_unidades = ["Unidade (un)", "Metro (m)", "Quilograma (kg)", "Sacos", "Rolos", "Caixas", "Litros (L)", "Gramas (g)", "Par", "Kit", "Metro Cúbico (m³)"]
                unidade = st.selectbox("Unidade de Medida", lista_unidades)
                estoque_minimo = st.number_input("Estoque Mínimo (Alerta)", min_value=1, step=1)
                
                submit_produto = st.form_submit_button("Cadastrar")
                if submit_produto and nome_produto:
                    unidade_curta = unidade.split("(")[1].replace(")", "") if "(" in unidade else unidade
                    cursor = conn.cursor()
                    cursor.execute('INSERT INTO produtos (nome, categoria, quantidade, estoque_minimo, unidade) VALUES (%s, %s, %s, %s, %s)', (nome_produto, categoria, 0, estoque_minimo, unidade_curta))
                    conn.commit()
                    st.success(f"'{nome_produto}' cadastrado com sucesso!")
                    st.rerun()
            conn.close()

        with col2:
            st.subheader("Inventário Atual")
            conn = psycopg2.connect(st.secrets["DB_URL"])
            df_produtos = pd.read_sql_query('SELECT id, nome, categoria, quantidade, estoque_minimo, unidade FROM produtos', conn)
            
            if not df_produtos.empty:
                # --- NOVOS FILTROS DINÂMICOS ---
                col_pesquisa, col_filtro = st.columns(2)
                with col_pesquisa:
                    termo_pesquisa = st.text_input("🔍 Buscar Material", "")
                with col_filtro:
                    opcoes_cat = ["Todas"] + sorted(df_produtos['categoria'].unique().tolist())
                    categoria_filtro = st.selectbox("📂 Filtrar por Categoria", opcoes_cat)
                
                # Aplicando os filtros
                if termo_pesquisa:
                    df_produtos = df_produtos[df_produtos['nome'].str.contains(termo_pesquisa, case=False, na=False)]
                if categoria_filtro != "Todas":
                    df_produtos = df_produtos[df_produtos['categoria'] == categoria_filtro]
                # --------------------------------

                def formatar_quantidade(linha):
                    unid = linha['unidade'] if pd.notna(linha['unidade']) else 'un'
                    texto_qtd = f"{linha['quantidade']} {unid}"
                    if linha['quantidade'] <= linha['estoque_minimo']:
                        return f"{texto_qtd} ❗"
                    return texto_qtd
                    
                df_produtos['Estoque Atual'] = df_produtos.apply(formatar_quantidade, axis=1)
                
                if not df_produtos.empty:
                    st.dataframe(df_produtos[['id', 'nome', 'categoria', 'Estoque Atual']], use_container_width=True, hide_index=True)
                else:
                    st.info("Nenhum material encontrado com esses filtros.")
                
                st.write("") 
                with st.expander("🗑️ Excluir Material"):
                    with st.form("form_excluir"):
                        item_excluir = st.selectbox("Selecione o item para apagar definitivamente", df_produtos['nome'].tolist())
                        btn_excluir = st.form_submit_button("🚨 Confirmar Exclusão")
                        
                        if btn_excluir:
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM produtos WHERE nome = %s", (item_excluir,))
                            conn.commit()
                            st.success(f"'{item_excluir}' foi removido do estoque!")
                            st.rerun()
            else:
                st.info("Nenhum material cadastrado ainda.")
            conn.close()

    # --- ABA 2: ENTRADA / SAÍDA ---
    with aba2:
        col_mov1, col_mov2 = st.columns([1, 2])
        
        with col_mov1:
            st.subheader("Registrar Movimentação")
            conn = psycopg2.connect(st.secrets["DB_URL"])
            df_nomes = pd.read_sql_query('SELECT nome FROM produtos', conn)
            lista_materiais = df_nomes['nome'].tolist() if not df_nomes.empty else []
            
            if not lista_materiais:
                st.warning("Cadastre um material na Aba 1 antes de registrar movimentações.")
            else:
                with st.form("form_movimentacao"):
                    material_selecionado = st.selectbox("Material", lista_materiais)
                    tipo_mov = st.radio("Tipo de Movimentação", ["Entrada", "Saída"], horizontal=True)
                    quantidade_mov = st.number_input("Quantidade", min_value=1, step=1)
                    
                    st.markdown("---")
                    data_retirada = st.date_input("Data da Retirada / Movimentação")
                    funcionario = st.text_input("Nome do Funcionário/Motorista")
                    empresa = st.text_input("Empresa (Terceirizada/Fornecedor)")
                    motivo = st.text_input("Observação / Destino")
                    
                    submit_mov = st.form_submit_button("Registrar no Estoque")
                    
                    if submit_mov:
                        if tipo_mov == "Saída" and (not funcionario or not empresa):
                            st.error("O nome do funcionário e a empresa são obrigatórios para registrar uma saída.")
                        else:
                            cursor = conn.cursor()
                            cursor.execute("SELECT quantidade, unidade FROM produtos WHERE nome = %s", (material_selecionado,))
                            resultado = cursor.fetchone()
                            estoque_atual = resultado[0]
                            unid_atual = resultado[1]
                            
                            if tipo_mov == "Saída" and quantidade_mov > estoque_atual:
                                st.error(f"Estoque insuficiente! Você só tem {estoque_atual} {unid_atual} de {material_selecionado}.")
                            else:
                                novo_estoque = estoque_atual + quantidade_mov if tipo_mov == "Entrada" else estoque_atual - quantidade_mov
                                data_ret_str = data_retirada.strftime('%d/%m/%Y')
                                cursor.execute("UPDATE produtos SET quantidade = %s WHERE nome = %s", (novo_estoque, material_selecionado))
                                cursor.execute("INSERT INTO movimentacoes (produto, tipo, quantidade, funcionario, empresa, data_retirada, motivo) VALUES (%s, %s, %s, %s, %s, %s, %s)", (material_selecionado, tipo_mov, quantidade_mov, funcionario, empresa, data_ret_str, motivo))
                                conn.commit()
                                st.success("Movimentação registrada com sucesso!")
                                st.rerun()

        with col_mov2:
            st.subheader("Histórico de Movimentações")
            conn = psycopg2.connect(st.secrets["DB_URL"])
            df_historico = pd.read_sql_query("SELECT data, tipo, produto, quantidade, funcionario, empresa, data_retirada, motivo FROM movimentacoes ORDER BY id DESC LIMIT 50", conn)
            
            if not df_historico.empty:
                df_historico.columns = ['Registro', 'Movimento', 'Material', 'Qtd', 'Funcionário', 'Empresa', 'Data Retirada', 'Obs']
                df_historico['Registro'] = pd.to_datetime(df_historico['Registro']).dt.strftime('%d/%m/%Y %H:%M')
                st.dataframe(df_historico, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhuma movimentação registrada ainda.")
            conn.close()

    # --- ABA 3: AGENDA ---
    with aba3:
        col_form, col_tabela = st.columns([1, 2.5])
        
        with col_form:
            st.subheader("Nova Solicitação de Entrega")
            with st.form("form_agenda"):
                data_agendamento = st.date_input("Data (Prevista/Alvo)")
                hora_agendamento = st.time_input("Hora (Prevista/Alvo)")
                fornecedor = st.text_input("Fornecedor")
                material_esperado = st.text_input("Material")
                
                status = st.selectbox("Status", ["Pendente de Alinhamento", "Agendado", "Recebido", "Cancelado"])
                observacao = st.text_area("Observações (Opcional)", placeholder="Ex: Falar com o responsável.")
                submit_agenda = st.form_submit_button("Lançar na Agenda")
                
                if submit_agenda:
                    if fornecedor and material_esperado:
                        data_hora_str = f"{data_agendamento.strftime('%d/%m/%Y')} às {hora_agendamento.strftime('%H:%M')}"
                        conn = psycopg2.connect(st.secrets["DB_URL"])
                        cursor = conn.cursor()
                        cursor.execute('INSERT INTO agenda (data_hora, fornecedor, material, status, observacao) VALUES (%s, %s, %s, %s, %s)', (data_hora_str, fornecedor, material_esperado, status, observacao))
                        conn.commit()
                        conn.close()
                        st.success("Solicitação salva!")
                        st.rerun()
                    else:
                        st.error("Preencha o Fornecedor e o Material!")

        with col_tabela:
            st.subheader("Gerenciar Agenda (Tabela Editável)")
            conn = psycopg2.connect(st.secrets["DB_URL"])
            df_agenda = pd.read_sql_query('SELECT id, data_hora, fornecedor, material, status, observacao FROM agenda ORDER BY id DESC', conn)
            
            if not df_agenda.empty:
                df_agenda.columns = ['ID', 'Data e Hora', 'Fornecedor', 'Material', 'Status', 'Observação']
                with st.form("form_edicao_tabela"):
                    df_editado = st.data_editor(df_agenda, use_container_width=True, hide_index=True, disabled=["ID"])
                    btn_salvar_edicao = st.form_submit_button("💾 Salvar Alterações da Tabela")
                    if btn_salvar_edicao:
                        cursor = conn.cursor()
                        for index, row in df_editado.iterrows():
                            cursor.execute("UPDATE agenda SET data_hora = %s, fornecedor = %s, material = %s, status = %s, observacao = %s WHERE id = %s", (row['Data e Hora'], row['Fornecedor'], row['Material'], row['Status'], row['Observação'], row['ID']))
                        conn.commit()
                        st.success("Alterações salvas com sucesso!")
                        st.rerun()
                
                st.write("")
                with st.expander("🗑️ Excluir Solicitação da Agenda"):
                    with st.form("form_excluir_agenda"):
                        opcoes_agenda = df_agenda.apply(lambda x: f"ID: {x['ID']} - {x['Material']} ({x['Fornecedor']})", axis=1).tolist()
                        item_excluir_agenda = st.selectbox("Selecione o agendamento para apagar", opcoes_agenda)
                        btn_excluir_agenda = st.form_submit_button("🚨 Confirmar Exclusão")
                        
                        if btn_excluir_agenda:
                            id_apagar = item_excluir_agenda.split(" ")[1] 
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM agenda WHERE id = %s", (id_apagar,))
                            conn.commit()
                            st.success("Agendamento excluído!")
                            st.rerun()
            else:
                st.info("Agenda livre. Nenhuma solicitação no momento.")
            conn.close()

    # --- ABA 4: CONFIGURAÇÕES (Apenas Dev) ---
    if aba4 is not None:
        with aba4:
            st.subheader("⚙️ Painel do Desenvolvedor - Gerenciar Usuários")
            col_u1, col_u2 = st.columns([1, 2])
            
            with col_u1:
                with st.form("form_novo_usuario"):
                    novo_user = st.text_input("Novo Usuário")
                    nova_senha = st.text_input("Senha", type="password")
                    novo_cargo = st.selectbox("Perfil", ["ADM", "Engenheiro", "Dev"])
                    
                    if st.form_submit_button("Criar Conta"):
                        if novo_user and nova_senha:
                            try:
                                conn = psycopg2.connect(st.secrets["DB_URL"])
                                cursor = conn.cursor()
                                cursor.execute("INSERT INTO usuarios (usuario, senha, cargo) VALUES (%s, %s, %s)", (novo_user, nova_senha, novo_cargo))
                                conn.commit()
                                conn.close()
                                st.success(f"Usuário '{novo_user}' criado com sucesso!")
                                st.rerun()
                            except psycopg2.IntegrityError:
                                st.error("Este nome de usuário já existe.")
                        else:
                            st.error("Preencha usuário e senha.")
                            
            with col_u2:
                conn = psycopg2.connect(st.secrets["DB_URL"])
                df_usuarios = pd.read_sql_query("SELECT id, usuario, cargo FROM usuarios", conn)
                st.dataframe(df_usuarios, use_container_width=True, hide_index=True)
                
                with st.expander("🗑️ Excluir Usuário"):
                    with st.form("form_excluir_usuario"):
                        user_del = st.selectbox("Selecione o usuário para apagar", df_usuarios['usuario'].tolist())
                        if st.form_submit_button("🚨 Confirmar Exclusão"):
                            if user_del == st.session_state['usuario_logado']:
                                st.error("Você não pode excluir sua própria conta ativa!")
                            else:
                                cursor = conn.cursor()
                                cursor.execute("DELETE FROM usuarios WHERE usuario = %s", (user_del,))
                                conn.commit()
                                st.success(f"Usuário '{user_del}' excluído!")
                                st.rerun()
                conn.close()
