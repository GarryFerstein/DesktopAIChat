# Импортируем необходимые стандартные библиотеки Python
import os  # Для работы с операционной системой
import sys  # Для доступа к системным параметрам и функциям
import shutil  # Для операций с файлами и директориями
import subprocess  # Для запуска внешних процессов
from pathlib import Path  # Для удобной работы с путями файловой системы

def install_requirements():
    """Установка зависимостей проекта"""
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)


def move_if_exists(source: str, destination: str) -> bool:
    """Перемещает файл, если он существует"""
    source_path = Path(source)
    if source_path.exists():
        shutil.move(str(source_path), destination)
        return True
    return False


def build_windows():
    """Сборка исполняемого файла для Windows с помощью PyInstaller"""
    print("Building Windows executable...")
    
    # Устанавливаем зависимости проекта для Windows из файла requirements.txt
    # sys.executable - путь к текущему интерпретатору Python
    install_requirements()
    
    # Создаём директорию bin, если она не существует
    # exist_ok=True позволяет не выбрасывать ошибку, если директория уже существует
    bin_dir = Path("bin")
    bin_dir.mkdir(exist_ok=True)
    
    # Запускаем PyInstaller со следующими параметрами:
    # --onefile: создать один исполняемый файл
    # --windowed: запускать без консольного окна
    # --name: задать имя выходного файла
    # --clean: очистить кэш PyInstaller перед сборкой
    # --noupx: не использовать UPX для сжатия
    # --uac-admin: запрашивать права администратора при запуске
    subprocess.run([
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name=AI Chat",
        "--clean",
        "--noupx",
        "--uac-admin",
        "src/main.py"
    ], check=True)
    
    # Перемещаем собранный файл в директорию bin
    # Используем try/except для обработки возможных ошибок при перемещении
    try:
        moved = move_if_exists("dist/AI Chat.exe", "bin/AIChat.exe")
        if not moved:
            raise FileNotFoundError("dist/AI Chat.exe not found")
        print("Windows build completed! Executable location: bin/AIChat.exe")
    except Exception:
        print("Windows build completed! Executable location: dist/AI Chat.exe")

def build_linux():
    """Сборка исполняемого файла для Linux с помощью PyInstaller"""
    print("Building Linux executable...")
    
    # Устанавливаем зависимости проекта для Linux
    install_requirements()
    
    # Создаём директорию bin, если она не существует
    bin_dir = Path("bin")
    bin_dir.mkdir(exist_ok=True)
    
    # Запускаем PyInstaller для Linux со следующими параметрами:
    # --onefile: создать один исполняемый файл
    # --windowed: запускать без консольного окна
    # --icon: указать иконку приложения
    # --name: задать имя выходного файла
    subprocess.run([
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--icon=assets/icon.ico",
        "--name=aichat",
        "src/main.py"
    ], check=True)
    
    # Перемещаем собранный файл в директорию bin
    try:
        moved = move_if_exists("dist/aichat", "bin/aichat")
        if not moved:
            raise FileNotFoundError("dist/aichat not found")
        print("Linux build completed! Executable location: bin/aichat")
    except Exception:
        print("Linux build completed! Executable location: dist/aichat")


def build_macos():
    """Сборка исполняемого файла для macOS с помощью PyInstaller"""
    print("Building macOS executable...")

    install_requirements()

    bin_dir = Path("bin")
    bin_dir.mkdir(exist_ok=True)

    pyinstaller_command = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name=aichat",
        "src/main.py"
    ]

    icon_path = Path("assets/icon.icns")
    if icon_path.exists():
        pyinstaller_command.insert(3, f"--icon={icon_path}")

    subprocess.run(pyinstaller_command, check=True)

    try:
        moved = move_if_exists("dist/aichat", "bin/aichat")
        if not moved:
            raise FileNotFoundError("dist/aichat not found")
        print("macOS build completed! Executable location: bin/aichat")
    except Exception:
        print("macOS build completed! Executable location: dist/aichat")

def main():
    """Основная функция сборки
    
    Определяет операционную систему и запускает соответствующую функцию сборки
    """
    # Проверяем тип операционной системы
    if sys.platform.startswith('win'):  # Если Windows
        build_windows()
    elif sys.platform.startswith('linux'):  # Если Linux
        build_linux()
    elif sys.platform == "darwin":  # Если macOS
        build_macos()
    else:  # Если другая ОС
        print("Unsupported platform")

# Точка входа в скрипт
# Если скрипт запущен напрямую (не импортирован как модуль),
# то запускаем основную функцию
if __name__ == "__main__":
    main()
