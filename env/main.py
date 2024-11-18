from flask import Flask, render_template, request, redirect, url_for
import mysql.connector

app = Flask(__name__)

def get_db_connection():
    return mysql.connector.connect(host='127.0.0.1', user='root', password='123456', port=3306, database='ScrumMaster')

########### Rota base
@app.route('/')
def index():
    return render_template('index.html')

########### Rota sobre
@app.route('/sobre')
def sobre():
    return render_template('sobre.html')

########### Rotas para pessoas
@app.route('/pessoas')
def listar_pessoas():
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM pessoas")
    pessoas = cursor.fetchall()
    db.close()
    return render_template('listar_pessoas.html', pessoas=pessoas)

@app.route('/pessoas/cadastro', methods=['GET', 'POST'])
def cadastrar_pessoa():
    if request.method == 'POST':
        nome = request.form['nome']
        cargo = request.form['cargo']
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("INSERT INTO pessoas (nome, cargo) VALUES (%s, %s)", (nome, cargo))
        db.commit()
        db.close()
        return redirect(url_for('listar_pessoas'))
    return render_template('cadastrar_pessoa.html')

@app.route('/pessoas/editar/<int:id>', methods=['GET', 'POST'])
def editar_pessoa(id):
    db = get_db_connection()
    cursor = db.cursor()
    if request.method == 'POST':
        nome = request.form['nome']
        cargo = request.form['cargo']
        cursor.execute("UPDATE pessoas SET nome=%s, cargo=%s WHERE id=%s", (nome, cargo, id))
        db.commit()
        db.close()
        return redirect(url_for('listar_pessoas'))
    cursor.execute("SELECT * FROM pessoas WHERE id=%s", (id,))
    pessoas = cursor.fetchone()
    db.close()
    return render_template('editar_pessoa.html', pessoas=pessoas)

# Rota para confirmar a exclusão da pessoa
@app.route('/pessoas/confirmar_exclusao/<int:id>', methods=['GET', 'POST'])
def confirmar_exclusao_pessoa(id):
    db = get_db_connection()
    cursor = db.cursor()

    # Buscar o nome da pessoa para exibir na modal
    cursor.execute("SELECT nome FROM pessoas WHERE id=%s", (id,))
    pessoas = cursor.fetchone()

    if not pessoas:
        db.close()
        return redirect(url_for('listar_pessoas'))

    pessoas_nome = pessoas[0]
    
    # Verificar se a requisição é POST (excluir)
    if request.method == 'POST':
        cursor.execute("DELETE FROM pessoas WHERE id=%s", (id,))
        db.commit()
        db.close()
        return redirect(url_for('listar_pessoas'))

    db.close()
    return render_template('listar_pessoas.html', pessoa_id_excluir=id, pessoa_nome=pessoas_nome)

########### Rotas para projetos
@app.route('/projetos')
def listar_projetos():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)  # Garantir que o cursor retorna dados como dicionário

    # Buscar todos os projetos e suas equipes, com os nomes do Product Owner, Scrum Master e membros da equipe
    cursor.execute("""
        SELECT p.id AS projeto_id, p.nome_projeto, p.product_owner, p.scrum_master, 
               po.nome AS product_owner_nome, sm.nome AS scrum_master_nome
        FROM Tb_projetos p
        LEFT JOIN pessoas po ON p.product_owner = po.id
        LEFT JOIN pessoas sm ON p.scrum_master = sm.id
    """)
    
    projetos = cursor.fetchall()

    # Buscar os nomes da equipe para cada projeto
    for projeto in projetos:
        projeto_id = projeto['projeto_id']
        cursor.execute("""
            SELECT p.nome
            FROM Tb_projeto_equipe pe
            JOIN pessoas p ON pe.pessoa_id = p.id
            WHERE pe.projeto_id = %s
        """, (projeto_id,))
        equipe = cursor.fetchall()
        projeto['equipe_nomes'] = [membro['nome'] for membro in equipe]

    db.close()

    return render_template('listar_projetos.html', projetos=projetos)

@app.route('/projetos/novo', methods=['GET', 'POST'])
def cadastrar_projeto():
    db = get_db_connection()
    cursor = db.cursor()
    
    # Buscar todas as pessoas para os campos de PO, SM e equipe
    cursor.execute("SELECT id, nome FROM pessoas")
    pessoas = cursor.fetchall()

    if request.method == 'POST':
        nome_projeto = request.form['nome_projeto']
        product_owner = request.form['product_owner']
        scrum_master = request.form['scrum_master']
        equipe = request.form.getlist('equipe')
        
        cursor.execute("INSERT INTO Tb_projetos (nome_projeto, product_owner, scrum_master) VALUES (%s, %s, %s)", (nome_projeto, product_owner, scrum_master))
        projeto_id = cursor.lastrowid
        
        for pessoa_id in equipe:
            cursor.execute("INSERT INTO Tb_projeto_equipe (projeto_id, pessoa_id) VALUES (%s, %s)", (projeto_id, pessoa_id))
        
        db.commit()
        db.close()
        return redirect(url_for('listar_projetos'))
    
    db.close()
    return render_template('cadastrar_projeto.html', pessoas=pessoas)

@app.route('/projetos/editar/<int:id>', methods=['GET', 'POST'])
def editar_projeto(id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Buscar as informações do projeto
    cursor.execute("""
        SELECT p.id AS projeto_id, p.nome_projeto, p.product_owner, p.scrum_master, 
               po.nome AS product_owner_nome, sm.nome AS scrum_master_nome
        FROM Tb_projetos p
        LEFT JOIN pessoas po ON p.product_owner = po.id
        LEFT JOIN pessoas sm ON p.scrum_master = sm.id
        WHERE p.id = %s
    """, (id,))
    projeto = cursor.fetchone()

    # Caso o projeto não exista
    if not projeto:
        db.close()
        return redirect(url_for('listar_projetos'))

    # Buscar membros da equipe
    cursor.execute("""
        SELECT p.id, p.nome
        FROM Tb_projeto_equipe pe
        JOIN pessoas p ON pe.pessoa_id = p.id
        WHERE pe.projeto_id = %s
    """, (id,))
    equipe = cursor.fetchall()

    # Extraindo os IDs da equipe para o template
    equipe_ids = [membro['id'] for membro in equipe]

    # Buscar todas as pessoas para o select
    cursor.execute("SELECT id, nome FROM pessoas")
    pessoas = cursor.fetchall()

    db.close()

    if request.method == 'POST':
        nome_projeto = request.form['nome_projeto']
        product_owner = request.form['product_owner']
        scrum_master = request.form['scrum_master']
        equipe = request.form.getlist('equipe')

        # Atualizar as informações do projeto
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute("""
            UPDATE Tb_projetos
            SET nome_projeto = %s, product_owner = %s, scrum_master = %s
            WHERE id = %s
        """, (nome_projeto, product_owner, scrum_master, id))

        # Atualizar a equipe do projeto
        cursor.execute("DELETE FROM Tb_projeto_equipe WHERE projeto_id = %s", (id,))
        for pessoa_id in equipe:
            cursor.execute("INSERT INTO Tb_projeto_equipe (projeto_id, pessoa_id) VALUES (%s, %s)", (id, pessoa_id))

        db.commit()
        db.close()
        return redirect(url_for('listar_projetos'))

    return render_template('editar_projeto.html', projeto=projeto, equipe=equipe, equipe_ids=equipe_ids, pessoas=pessoas)
    
@app.route('/projetos/confirmar_exclusao/<int:id>', methods=['GET', 'POST'])
def confirmar_exclusao_projeto(id):
    db = get_db_connection()
    cursor = db.cursor()

    # Buscar o nome do projeto para exibir na modal
    cursor.execute("SELECT nome_projeto FROM Tb_projetos WHERE id=%s", (id,))
    projeto = cursor.fetchone()

    if not projeto:
        db.close()
        return redirect(url_for('listar_projetos'))

    projeto_nome = projeto[0]
    
    # Verificar se a requisição é POST (excluir)
    if request.method == 'POST':
        cursor.execute("DELETE FROM Tb_projeto_equipe WHERE projeto_id=%s", (id,))
        cursor.execute("DELETE FROM Tb_projetos WHERE id=%s", (id,))
        db.commit()
        db.close()
        return redirect(url_for('listar_projetos'))

    db.close()
    return render_template('listar_projetos.html', projeto_id_excluir=id, projeto_nome=projeto_nome)

########### Rotas para Backlogs
@app.route('/backlogs')
def listar_backlogs():
    db = get_db_connection()
    cursor = db.cursor()
    
    cursor.execute("""
        SELECT b.projeto_id, b.backlog_codigo, b.nome_backlog, b.descricao, b.prazo, b.situacao,
               p.nome_projeto
        FROM Tb_backlogs b
        JOIN Tb_projetos p ON b.projeto_id = p.id
    """)

    backlogs = cursor.fetchall()

    db.close()
    return render_template('listar_backlogs.html', backlogs=backlogs)

@app.route('/backlogs/cadastrar', methods=['GET', 'POST'])
def cadastrar_backlog():
    db = get_db_connection()
    cursor = db.cursor()

    # Obter todos os projetos para exibir no formulário
    cursor.execute("SELECT id, nome_projeto FROM Tb_projetos")
    projetos = cursor.fetchall()

    nome_backlog = ""
    descricao = ""
    prazo = ""
    situacao = "A iniciar"  # Valor padrão para situação

    # Verificar se a requisição é POST (salvando os dados)
    if request.method == 'POST':
        projeto_id = request.form['projeto_id']
        nome_backlog = request.form['nome_backlog']
        descricao = request.form['descricao']
        prazo = request.form['prazo']
        situacao = request.form['situacao']

        # Agora podemos salvar o backlog no banco de dados
        cursor.execute("""
            INSERT INTO Tb_backlogs (projeto_id, nome_backlog, descricao, prazo, situacao)
            VALUES (%s, %s, %s, %s, %s)
        """, (projeto_id, nome_backlog, descricao, prazo, situacao))
        db.commit()

        db.close()
        return redirect(url_for('listar_backlogs'))

    db.close()

    # Passar os dados para o template
    return render_template('cadastrar_backlog.html', projetos=projetos, 
                           nome_backlog=nome_backlog, descricao=descricao, prazo=prazo, situacao=situacao)

@app.route('/backlogs/editar/<int:projeto_id>/<int:backlog_codigo>', methods=['GET', 'POST'])
def editar_backlog(projeto_id, backlog_codigo):
    db = get_db_connection()
    cursor = db.cursor()

    if request.method == 'POST':
        nome_backlog = request.form['nome_backlog']
        descricao = request.form['descricao']
        prazo = request.form['prazo']
        situacao = request.form['situacao']

        # Atualizar os dados do backlog
        cursor.execute("""
            UPDATE Tb_backlogs
            SET nome_backlog = %s, descricao = %s, prazo = %s, situacao = %s
            WHERE projeto_id = %s AND backlog_codigo = %s
        """, (nome_backlog, descricao, prazo, situacao, projeto_id, backlog_codigo))

        db.commit()
        db.close()

        return redirect(url_for('listar_backlogs'))

    # Buscar os dados do backlog e do projeto (sem incluir o Scrum Master)
    cursor.execute("""
        SELECT b.backlog_codigo, b.nome_backlog, b.descricao, b.prazo, b.situacao, p.nome_projeto
        FROM Tb_backlogs b
        JOIN Tb_projetos p ON b.projeto_id = p.id
        WHERE b.projeto_id = %s AND b.backlog_codigo = %s
    """, (projeto_id, backlog_codigo))

    backlog = cursor.fetchone()

    db.close()

    return render_template('editar_backlogs.html', backlog=backlog)

@app.route('/backlogs/confirmar_exclusao/<int:projeto_id>/<int:backlog_codigo>', methods=['GET', 'POST'])
def confirmar_exclusao_backlog(projeto_id, backlog_codigo):
    db = get_db_connection()
    cursor = db.cursor()

    # Buscar o nome do backlog para exibir na modal (sem considerar o Scrum Master)
    cursor.execute("""
        SELECT nome_backlog FROM Tb_backlogs WHERE projeto_id = %s AND backlog_codigo = %s
    """, (projeto_id, backlog_codigo))
    backlog = cursor.fetchone()

    if not backlog:
        db.close()
        return redirect(url_for('listar_backlogs'))

    backlog_nome = backlog[0]

    # Verificar se a requisição é POST (excluir)
    if request.method == 'POST':
        cursor.execute("""
            DELETE FROM Tb_backlogs WHERE projeto_id = %s AND backlog_codigo = %s
        """, (projeto_id, backlog_codigo))
        db.commit()
        db.close()
        return redirect(url_for('listar_backlogs'))

    db.close()

    return render_template('listar_backlogs.html', backlog_id_excluir=(projeto_id, backlog_codigo), backlog_nome=backlog_nome)

if __name__ == '__main__':
    app.run(debug=True)