"""Bootstrap interativo de contas, sem abrir endpoints administrativos públicos.

Executar a partir de backend/: uv run python -m scripts.bootstrap_contas --perfil ADMIN
"""

import argparse
import os
from getpass import getpass

from pydantic import EmailStr, TypeAdapter, ValidationError
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.seguranca import hash_senha
from app.domain.estados import Perfil
from app.models.cadastros import Responsavel, Usuario
from app.schemas.responsaveis_admin import ResponsavelCriar


def main() -> int:
    parser = argparse.ArgumentParser(description="Cria uma conta inicial no banco configurado.")
    parser.add_argument("--perfil", choices=("ADMIN", "RESPONSAVEL"), required=True)
    args = parser.parse_args()

    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        parser.error("Defina DATABASE_URL no ambiente antes de executar o script.")
    if not url.startswith("postgresql+psycopg://"):
        parser.error("DATABASE_URL deve utilizar postgresql+psycopg://.")

    email = TypeAdapter(EmailStr)
    try:
        endereco = str(email.validate_python(input("E-mail: ").strip())).lower()
    except ValidationError:
        print("E-mail inválido.")
        return 1

    nome = None
    if args.perfil == "RESPONSAVEL":
        nome = input("Nome completo: ").strip()
        if not nome or len(nome) > 200:
            print("Informe nome completo entre 1 e 200 caracteres.")
            return 1

    senha = getpass("Senha (12 a 128 caracteres): ")
    confirmacao = getpass("Repita a senha: ")
    if senha != confirmacao:
        print("Senhas diferentes; nada foi gravado.")
        return 1
    if not (12 <= len(senha) <= 128):
        print("A senha precisa ter entre 12 e 128 caracteres.")
        return 1

    if args.perfil == "RESPONSAVEL":
        try:
            entrada = ResponsavelCriar(nome_completo=nome, email=endereco, senha=senha)
        except ValidationError as erro:
            print(f"Dados inválidos: {erro.error_count()} erro(s) de validação.")
            return 1
        nome = entrada.nome_completo

    print(f"Conta a criar: {args.perfil} / {endereco}")
    if input("Digite CRIAR para confirmar: ").strip() != "CRIAR":
        print("Operação cancelada.")
        return 1

    engine = create_engine(url, pool_pre_ping=True)
    try:
        with Session(engine) as sessao:
            with sessao.begin():
                existente = sessao.scalar(
                    select(Usuario.id).where(func.lower(Usuario.email) == endereco)
                )
                if existente is not None:
                    print("Este e-mail já está cadastrado; nenhuma alteração realizada.")
                    return 1

                if args.perfil == "ADMIN":
                    primeiro_admin = sessao.scalar(
                        select(Usuario.id).where(Usuario.perfil == Perfil.ADMIN).limit(1)
                    )
                    if primeiro_admin is not None:
                        print("Já existe um administrador. Bootstrap ADMIN bloqueado.")
                        return 1

                usuario = Usuario(
                    email=endereco,
                    senha_hash=hash_senha(senha),
                    perfil=Perfil(args.perfil),
                    ativo=True,
                )
                sessao.add(usuario)
                sessao.flush()

                if args.perfil == "RESPONSAVEL":
                    sessao.add(
                        Responsavel(usuario_id=usuario.id, nome_completo=nome, ativo=True)
                    )

                usuario_id = usuario.id
        print(f"Conta {args.perfil} criada com sucesso (usuario_id={usuario_id}).")
        if args.perfil == "RESPONSAVEL":
            print("O vínculo com o aluno deve ser cadastrado pela administração.")
        return 0
    except IntegrityError:
        print("Conflito de integridade; transação revertida, nenhuma conta criada.")
        return 1
    except SQLAlchemyError as erro:
        print(f"Falha na operação de banco ({type(erro).__name__}); transação revertida.")
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
