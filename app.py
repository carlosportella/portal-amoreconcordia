from flask import Flask, render_template, request, redirect, session, url_for
import json
from google.cloud import storage
from datetime import timedelta
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'sua-chave-supersegura'

@app.template_filter('primeiro_nome')
def primeiro_nome(nome):
    return nome.split(' ')[0] if nome else ''

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%d/%m/%Y'):
    try:
        return datetime.strptime(value, '%Y-%m-%d').strftime(format)
    except Exception:
        return value  # retorna como está se não conseguir converter

def init_storage_client():
    # Escreve o JSON da credencial em arquivo temporário
    key_json = os.getenv('GCLOUD_KEY_JSON')
    if not key_json:
        raise RuntimeError("Variável GCLOUD_KEY_JSON não definida")
    with open('/tmp/gcp_key.json', 'w') as f:
        f.write(key_json)
    return storage.Client.from_service_account_json('/tmp/gcp_key.json')

def gerar_link_assinado(nome_arquivo):
    #storage_client = storage.Client.from_service_account_json("livro-atas-amoreconcordia-d661ba1add6d.json")  # nome do arquivo JSON da chave
    storage_client = init_storage_client()
    bucket = storage_client.bucket("portal-pdfs-carlos")
    blob = bucket.blob(nome_arquivo)

    url_assinada = blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=15),
        method="GET",
        response_type="application/pdf"
    )

    return url_assinada

def carregar_livros():
    with open('livros.json') as f:
        return json.load(f)

def carregar_usuarios():
    with open('usuarios.json') as f:
        return json.load(f)

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        sim = request.form['sim']
        senha = request.form['senha']
        usuarios = carregar_usuarios()

        for u in usuarios:
            if u['sim'] == sim and u['senha'] == senha:
                session['usuario'] = u['nome']
                session['admin'] = u.get('admin', 0)
                return redirect('/portal')

        return render_template('login.html', erro="SIM ou senha inválidos.")
    
    return render_template('login.html')

@app.route('/portal')
def portal():
    if 'usuario' not in session:
        return redirect('/')

    livros = carregar_livros()
    return render_template('portal.html', usuario=session['usuario'], livros=livros)

@app.route('/visualizar/<nome_pdf>')
def visualizar(nome_pdf):
    if 'usuario' not in session:
        return redirect('/')
    
    pdf_url = gerar_link_assinado(nome_pdf)
    return render_template('visualizador.html', pdf_url=pdf_url)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/usuarios', methods=['GET', 'POST'])
def usuarios():
    if 'usuario' not in session or session.get('admin') < 1:
        return render_template('acesso_negado.html')

    with open('usuarios.json') as f:
        usuarios = json.load(f)

    return render_template('usuarios.html', usuarios=usuarios)

@app.route('/salvar_usuario', methods=['POST'])
def salvar_usuario():
    if 'usuario' not in session or session.get('admin') < 1:
        return render_template('acesso_negado.html')

    sim = request.form['sim']
    sim_original = request.form.get('sim_original', sim)
    modo = request.form.get('modo', 'novo')

    novo_usuario = {
        "sim": sim,
        "senha": request.form['senha'],
        "nome": request.form['nome'],
        "admin": int('admin' in request.form),
        "aniversario": request.form.get('aniversario', ''),
        "emerito": int('emerito' in request.form),
        "remido": int('remido' in request.form),
        "ativo": int('ativo' in request.form),
        "lojabase": request.form.get('lojabase', 'Aprendiz'),
        "filosoficos": request.form.get('filosoficos', 'Grau 1')
    }

    with open('usuarios.json') as f:
        usuarios = json.load(f)

    # Remove o antigo se estiver em modo de edição
    usuarios = [u for u in usuarios if u['sim'] != sim_original]
    usuarios.append(novo_usuario)

    with open('usuarios.json', 'w') as f:
        json.dump(usuarios, f, indent=2)

    return redirect('/usuarios')

@app.route('/excluir_usuario/<sim>')
def excluir_usuario(sim):
    if 'usuario' not in session or session.get('admin') < 1:
        return render_template('acesso_negado.html')

    with open('usuarios.json') as f:
        usuarios = json.load(f)

    usuarios = [u for u in usuarios if u['sim'] != sim]

    with open('usuarios.json', 'w') as f:
        json.dump(usuarios, f, indent=2)

    return redirect('/usuarios')

@app.route('/livros', methods=['GET'])
def livros():
    if 'usuario' not in session or session.get('admin') < 2:
        return render_template('acesso_negado.html')
    with open('livros.json') as f:
        livros = json.load(f)
    return render_template('livros.html', livros=livros)

@app.route('/salvar_livro', methods=['POST'])
def salvar_livro():
    if 'usuario' not in session or session.get('admin') < 2:
        return render_template('acesso_negado.html')
    
    nome = request.form['nome']
    nome_original = request.form.get('nome_original', nome)
    arquivo = request.form['arquivo']

    with open('livros.json') as f:
        livros = json.load(f)

    livros = [l for l in livros if l['nome'] != nome_original]
    livros.append({"nome": nome, "arquivo": arquivo})

    with open('livros.json', 'w') as f:
        json.dump(livros, f, indent=2)

    return redirect('/livros')

@app.route('/excluir_livro/<nome>')
def excluir_livro(nome):
    if 'usuario' not in session or session.get('admin') < 2:
        return render_template('acesso_negado.html')
    
    with open('livros.json') as f:
        livros = json.load(f)

    livros = [l for l in livros if l['nome'] != nome]

    with open('livros.json', 'w') as f:
        json.dump(livros, f, indent=2)

    return redirect('/livros')

@app.route('/sessoes', methods=['GET'])
def sessoes():
    if 'usuario' not in session or session.get('admin') < 1:
        return render_template('acesso_negado.html')

    with open('sessoes.json') as f:
        sessoes = json.load(f)

    # Ordena pela data (convertendo para objeto datetime)
    sessoes.sort(key=lambda s: datetime.strptime(s['sessao'], '%Y-%m-%d'))

    return render_template('sessoes.html', sessoes=sessoes)


@app.route('/salvar_sessao', methods=['POST'])
def salvar_sessao():
    if 'usuario' not in session or session.get('admin') < 1:
        return render_template('acesso_negado.html')

    nova = {
        "sessao": request.form['sessao'],
        "pauta": request.form['pauta'],
        "grau": request.form['grau']
    }

    sessao_original = request.form.get('sessao_original', nova['sessao'])

    with open('sessoes.json') as f:
        sessoes = json.load(f)

    sessoes = [s for s in sessoes if s['sessao'] != sessao_original]
    sessoes.append(nova)

    with open('sessoes.json', 'w') as f:
        json.dump(sessoes, f, indent=2)

    return redirect('/sessoes')

@app.route('/excluir_sessao/<data>')
def excluir_sessao(data):
    if 'usuario' not in session or session.get('admin') < 1:
        return render_template('acesso_negado.html')

    with open('sessoes.json') as f:
        sessoes = json.load(f)

    sessoes = [s for s in sessoes if s['sessao'] != data]

    with open('sessoes.json', 'w') as f:
        json.dump(sessoes, f, indent=2)

    return redirect('/sessoes')

def carregar_sessoes():
    with open('sessoes.json') as f:
        return json.load(f)

def carregar_presencas():
    if not os.path.exists('presencas.json'):
        return []
    with open('presencas.json') as f:
        return json.load(f)

def salvar_presencas(lista):
    with open('presencas.json', 'w') as f:
        json.dump(lista, f, indent=2)

@app.route('/presencas', methods=['GET'])
def presencas():
    if 'usuario' not in session or session.get('admin', 0) < 1:
        return render_template('sem_permissao.html')

    with open('sessoes.json') as f:
        sessoes = json.load(f)

    with open('usuarios.json') as f:
        usuarios = json.load(f)

    try:
        with open('presencas.json') as f:
            presencas = json.load(f)
    except FileNotFoundError:
        presencas = []

    # Mapeia a quantidade de presenças por sessão
    contagem = {}
    for p in presencas:
        if p.get("presente", 1):
            contagem[p["sessao"]] = contagem.get(p["sessao"], 0) + 1

    editar_sessao = request.args.get('editar')
    presentes_edicao = []

    if editar_sessao:
        presentes_edicao = [p["sim"] for p in presencas if p["sessao"] == editar_sessao and p.get("presente", 1)]
    
    return render_template('presencas.html', sessoes=sessoes, usuarios=usuarios,
                           presencas_por_sessao=contagem, editar=editar_sessao,
                           presentes_edicao=presentes_edicao)

@app.route('/salvar_presencas', methods=['POST'])
def salvar_presencas():
    if 'usuario' not in session or session.get('admin', 0) < 1:
        return render_template('sem_permissao.html')

    sessao = request.form['sessao']
    modo = request.form.get('modo')
    sessao_original = request.form.get('sessao_original', sessao)

    # Marca todos como não presentes para essa sessão
    try:
        with open('presencas.json') as f:
            presencas = json.load(f)
    except FileNotFoundError:
        presencas = []

    # Remove os antigos da sessão
    presencas = [p for p in presencas if p["sessao"] != sessao_original]

    # Novos presentes
    presentes = request.form.getlist('presentes')
    for sim in presentes:
        presencas.append({"sim": sim, "sessao": sessao, "presente": 1})

    with open('presencas.json', 'w') as f:
        json.dump(presencas, f, indent=2)

    return redirect('/presencas')

if __name__ == '__main__':
    import os
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=True)

