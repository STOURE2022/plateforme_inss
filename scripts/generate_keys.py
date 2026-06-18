#!/usr/bin/env python
"""
Script para gerar um par de chaves RSA 2048 bits para os tokens QR do e-INSS.

Uso:
    python scripts/generate_keys.py

Gera:
    keys/private.pem  — chave privada RSA (manter em segurança, nunca commitar)
    keys/public.pem   — chave pública RSA (pode ser distribuída)
"""
import sys
from pathlib import Path

# Adiciona a raiz do projecto ao sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))


def main():
    try:
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend
    except ImportError:
        print("Erro: instale cryptography>=42.0  (pip install cryptography)")
        sys.exit(1)

    keys_dir = BASE_DIR / "keys"
    keys_dir.mkdir(exist_ok=True)

    private_key_path = keys_dir / "inss_private.pem"
    public_key_path = keys_dir / "inss_public.pem"

    print("A gerar par de chaves RSA 2048 bits...")

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )

    # Serializa chave privada em PEM (sem passphrase para simplificar)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )

    # Serializa chave pública em PEM
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    private_key_path.write_bytes(private_pem)
    public_key_path.write_bytes(public_pem)

    print(f"Chave privada guardada em : {private_key_path}")
    print(f"Chave pública guardada em : {public_key_path}")
    print()
    print("ATENÇÃO: Nunca inclua keys/private.pem no controlo de versões!")
    print("Adicione 'keys/' ao seu .gitignore.")


if __name__ == "__main__":
    main()
