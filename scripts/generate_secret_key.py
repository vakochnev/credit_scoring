#!/usr/bin/env python3
"""
Генератор SECRET_KEY для .env файла

Скрипт генерирует криптографически стойкий случайный ключ для JWT токенов.

Использование:
    python scripts/generate_secret_key.py
    python scripts/generate_secret_key.py --copy  # Копировать в буфер обмена (Linux)
"""

import secrets
import sys
import argparse


def generate_secret_key():
    """Генерирует криптографически стойкий случайный ключ"""
    return secrets.token_urlsafe(32)


def main():
    parser = argparse.ArgumentParser(
        description="Генератор SECRET_KEY для Credit Scoring API"
    )
    parser.add_argument(
        "--copy",
        action="store_true",
        help="Копировать ключ в буфер обмена (Linux/Mac)"
    )
    
    args = parser.parse_args()
    
    secret_key = generate_secret_key()
    
    print("=" * 60)
    print("🔐 Сгенерированный SECRET_KEY:")
    print("=" * 60)
    print(f"SECRET_KEY={secret_key}")
    print("=" * 60)
    print()
    print("📋 Добавьте эту строку в ваш .env файл:")
    print(f"   SECRET_KEY={secret_key}")
    print()
    
    if args.copy:
        try:
            import subprocess
            if sys.platform == "linux":
                # Linux - xclip или xsel
                try:
                    subprocess.run(
                        ["xclip", "-selection", "clipboard"],
                        input=secret_key.encode(),
                        check=True
                    )
                    print("✅ Ключ скопирован в буфер обмена (xclip)")
                except FileNotFoundError:
                    try:
                        subprocess.run(
                            ["xsel", "--clipboard", "--input"],
                            input=secret_key.encode(),
                            check=True
                        )
                        print("✅ Ключ скопирован в буфер обмена (xsel)")
                    except FileNotFoundError:
                        print("⚠️  xclip или xsel не установлены. Установите один из них для копирования.")
            elif sys.platform == "darwin":
                # macOS - pbcopy
                subprocess.run(
                    ["pbcopy"],
                    input=secret_key.encode(),
                    check=True
                )
                print("✅ Ключ скопирован в буфер обмена (macOS)")
            elif sys.platform == "win32":
                # Windows - pyperclip или clip
                try:
                    import pyperclip
                    pyperclip.copy(secret_key)
                    print("✅ Ключ скопирован в буфер обмена (Windows)")
                except ImportError:
                    subprocess.run(
                        ["clip"],
                        input=secret_key.encode(),
                        check=True
                    )
                    print("✅ Ключ скопирован в буфер обмена (Windows)")
        except Exception as e:
            print(f"⚠️  Не удалось скопировать в буфер обмена: {e}")
    
    print()
    print("⚠️  ВАЖНО:")
    print("   - Храните этот ключ в секрете")
    print("   - Не коммитьте .env файл в Git")
    print("   - Используйте разные ключи для разных окружений")


if __name__ == "__main__":
    main()

