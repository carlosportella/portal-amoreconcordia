from flask import Flask, render_template, request, redirect, session, url_for
import json
from google.cloud import storage
from datetime import timedelta
import os

app = Flask(__name__)
app.secret_key = 'sua-chave-supersegura'

def gerar_link_assinado(nome_arquivo):
    storage_client = storage.Client.from_service_account_json("livro-atas-amoreconcordia-d661ba1add6d.json")  # nome do arquivo JSON da chave
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
    if 'usuario' not in session or session.get('admin') != 1:
        return redirect('/')

    with open('usuarios.json') as f:
        usuarios = json.load(f)

    return render_template('usuarios.html', usuarios=usuarios)

@app.route('/salvar_usuario', methods=['POST'])
def salvar_usuario():
    if 'usuario' not in session or session.get('admin') != 1:
        return redirect('/')

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

