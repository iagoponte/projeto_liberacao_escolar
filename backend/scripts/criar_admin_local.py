
"""Provisiona o administrador inicial em ambiente local."""

from getpass import getpass

from sqlalchemy import func, select

from app.api.deps import get_db
from app.core.seguranca import hash_senha
from app.domain.estados import Perfil
from app.models import Usuario


def main():
    print("=== Cadastro do administrador inicial ===")

    email = input("E-mail: ").strip().lower()
    senha = getpass("Senha: ")
    confirmacao = getpass("Confirme a senha: ")

    if not email or "@" not in email:
        print("E-mail inválido.")
        return

    if len(senha) < 12:
        print("A senha precisa ter pelo menos 12 caracteres.")
        return

    if senha != confirmacao:
        print("As senhas não coincidem.")
        return

    gerador = get_db()
    db = next(gerador)

    try:
        existente = db.scalar(
            select(Usuario).where(
                func.lower(Usuario.email) == email
            )
        )

        if existente:
            print("Já existe um usuário com esse e-mail.")
            print("Nenhuma alteração foi realizada.")
            return

        administrador = Usuario(
            email=email,
            senha_hash=hash_senha(senha),
            perfil=Perfil.ADMIN,
            ativo=True,
        )

        db.add(administrador)
        db.commit()
        db.refresh(administrador)

        print("Administrador criado com sucesso!")
        print(f"ID: {administrador.id}")
        print(f"E-mail: {administrador.email}")
        print(f"Perfil: {administrador.perfil.value}")

    except Exception:
        db.rollback()
        raise
    finally:
        gerador.close()


if __name__ == "__main__":
    main()
