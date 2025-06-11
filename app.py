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

    novo_usuario = {
        "nome": request.form['nome'],
        "sim": request.form['sim'],
        "senha": request.form['senha'],
        "admin": int(request.form.get('admin', 0))
    }

    with open('usuarios.json') as f:
        usuarios = json.load(f)

    usuarios = [u for u in usuarios if u['sim'] != novo_usuario['sim']]
    usuarios.append(novo_usuario)

    with open('usuarios.json', 'w') as f:
        json.dump(usuarios, f, indent=2)

    return redirect('/usuarios')

@app.route('/excluir_usuario/<sim>')
def excluir_usuario(sim):
    if 'usuario' not in session or session.get('admin') != 1:
        return redirect('/')

    with open('usuarios.json') as f:
        usuarios = json.load(f)

    usuarios = [u for u in usuarios if u['sim'] != sim]

    with open('usuarios.json', 'w') as f:
        json.dump(usuarios, f, indent=2)

    return redirect('/usuarios')


if __name__ == '__main__':
    import os
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=True)


