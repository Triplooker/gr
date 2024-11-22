#!/usr/bin/env python3
import os
import subprocess
import json
from typing import Dict, List
import platform
import sys
import locale
import time
import io
import getpass
import re

class BotManager:
    def __init__(self):
        self.config_file = 'bot_config.json'
        
        # Настройка кодировки для всего скрипта
        import sys
        import io
        import locale
        
        # Устанавливаем локаль
        locale.setlocale(locale.LC_ALL, 'C.UTF-8')
        
        # Настраиваем кодировку для stdout и stderr
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer,
            encoding='utf-8',
            errors='replace',
            line_buffering=True
        )
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer,
            encoding='utf-8',
            errors='replace',
            line_buffering=True
        )
        
        self.load_config()
        
        # Очистка конфигурации от проблемных записей при старте
        if hasattr(self, 'config') and "bots" in self.config:
            clean_bots = {}
            for bot_id, bot_data in self.config["bots"].items():
                try:
                    bot_id.encode('ascii', 'ignore')
                    bot_data['email'].encode('ascii', 'ignore')
                    bot_data['proxy_file'].encode('ascii', 'ignore')
                    clean_bots[bot_id] = bot_data
                except:
                    continue
            self.config["bots"] = clean_bots
            self.save_config()

    def check_and_install_requirements(self):
        print("\n=== Проверка и установка требований ===")
        
        # Проверяем операционную систему
        if platform.system() != "Linux":
            print("Скрипт предназначен для работы на Linux системах!")
            sys.exit(1)

        try:
            # Проверка наличия sudo прав
            subprocess.run(["sudo", "-n", "true"], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            print("Для установки компонентов требуются права sudo!")
            print("Пожалуйста, введите пароль при запросе.")

        requirements = {
            "docker": {
                "check_cmd": ["docker", "--version"],
                "install_cmd": [
                    "sudo apt-get update",
                    "sudo apt-get install -y docker.io",
                    "sudo systemctl start docker",
                    "sudo systemctl enable docker",
                    "sudo usermod -aG docker $USER"
                ]
            },
            "python3": {
                "check_cmd": ["python3", "--version"],
                "install_cmd": ["sudo apt-get install -y python3"]
            },
            "pip": {
                "check_cmd": ["pip3", "--version"],
                "install_cmd": ["sudo apt-get install -y python3-pip"]
            }
        }

        need_relogin = False

        for component, cmds in requirements.items():
            print(f"\nПроверка {component}...")
            try:
                subprocess.run(cmds["check_cmd"], check=True, capture_output=True)
                print(f"✓ {component} уже установлен")
            except (subprocess.CalledProcessError, FileNotFoundError):
                print(f"✗ {component} не найден. Установка...")
                for cmd in cmds["install_cmd"]:
                    try:
                        subprocess.run(cmd.split(), check=True)
                    except subprocess.CalledProcessError as e:
                        print(f"Ошибка при выполнении команды {cmd}")
                        print(e)
                        return False
                if component == "docker":
                    need_relogin = True

        # Проверяем запущен ли Docker демон
        try:
            subprocess.run(["docker", "ps"], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            print("\nЗапуск Docker демона...")
            subprocess.run(["sudo", "systemctl", "start", "docker"], check=True)

        if need_relogin:
            print("\n⚠️ ВАЖНО: Вы были добавлены в группу docker.")
            print("Необходимо перелогиниться в систему для применения изменений.")
            print("После этого запустите скрипт снова.")
            sys.exit(0)

        print("\n✓ Все необходимые компоненты установлены и гоовы к работе!")
        return True

    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {"bots": {}}

    def save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

    def convert_proxy_format(self, proxy_string):
        """Конвертирует прокси из формата host:port:username:password в socks5 формат"""
        try:
            if 'socks5://' in proxy_string:
                return proxy_string
            
            parts = proxy_string.split(':')
            if len(parts) == 4:
                host, port, username, password = parts
                print(f"\nПроверка компонентов прокси:")
                print(f"Host: {host}")
                print(f"Port: {port}")
                print(f"Username: {username}")
                print(f"Password: {password}")
                
                result = f"socks5://{username}:{password}@{host}:{port}"
                print(f"Сконвертированный прокси: {result}")
                return result
            else:
                print("Ошибка: неверный формат прокси (нужно 4 компонента, разделенных двоеточием)")
                return None
        except Exception as e:
            print(f"Ошибка при конвертации прокси: {e}")
            return None

    def clean_bot_id(self, bot_id):
        """Очищает ID бота от недопустимых символов"""
        # Оставляем только разрешенные символы: буквы, цифры, подчеркивание, точка и дефис
        cleaned = re.sub(r'[^a-zA-Z0-9_.-]', '', bot_id)
        if cleaned != bot_id:
            print(f"ID бота был очищен от недопустимых символов: {cleaned}")
        return cleaned

    def add_bot(self):
        print("\n=== Добавление нового бота ===")
        bot_id = input("Введите ID для бота (разрешены только латинские буквы, цифры, -, _ и .): ").strip()
        bot_id = self.clean_bot_id(bot_id)
        
        if not bot_id:
            print("Ошибка: ID бота не может быть пустым после очистки")
            return
        
        if bot_id in self.config["bots"]:
            print(f"Ошибка: Бот с ID {bot_id} уже существует")
            return
        
        email = input("Введите email: ").strip()
        password = getpass.getpass("Введите пароль: ").strip()
        print()
        proxy = input("Введите прокси (формат: host:port:username:password): ").strip()
        
        converted_proxy = self.convert_proxy_format(proxy)
        if not converted_proxy:
            print("Ошибка при обработке прокси. Бот не будет добавлен.")
            return
        
        # Тестируем прокси перед добавлением бота
        if not self.test_proxy(converted_proxy):
            print("Прокси не работает. Бот не будет добавлен.")
            return
        
        # Создаем отдельный proxies.txt для этого бота
        proxy_file = f'proxies_{bot_id}.txt'
        with open(proxy_file, 'w', encoding='utf-8') as f:
            f.write(converted_proxy)
        
        self.config["bots"][bot_id] = {
            "email": email,
            "password": password,
            "proxy_file": proxy_file
        }
        
        if self.start_bot(bot_id):
            self.save_config()
            print(f"\nБот {bot_id} успешно добавлен и запущен!")
        else:
            # Удаляем конфигурацию и файл прокси если запуск не удался
            del self.config["bots"][bot_id]
            try:
                os.remove(proxy_file)
            except:
                pass
            print(f"\nБот {bot_id} не был добавлен из-за ошибок при запуске")

    def start_bot(self, bot_id):
        if bot_id not in self.config["bots"]:
            print(f"Бот с ID {bot_id} не найден!")
            return
        
        bot = self.config["bots"][bot_id]
        proxy_file_path = os.path.abspath(bot['proxy_file'])
        
        # Проверяем файл прокси
        if not os.path.exists(proxy_file_path):
            print(f"Ошибка: файл прокси {proxy_file_path} не найден!")
            return
        
        with open(proxy_file_path, 'r') as f:
            proxy_content = f.read().strip()
            if not proxy_content:
                print("Ошибка: файл прокси пустой!")
                return
            print(f"Прокси для запуска: {proxy_content}")
        
        cmd = [
            "docker", "run", "-d",
            "--name", f"gradient-bot-{bot_id}",
            "-e", f"APP_USER={bot['email']}",
            "-e", f"APP_PASS={bot['password']}",
            "-v", f"{proxy_file_path}:/app/proxies.txt",
            "overtrue/gradient-bot"
        ]
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            container_id = result.stdout.strip()
            print(f"Бот {bot_id} запущен, ID контейнера: {container_id[:12]}")
            
            print("Проверка запуска (ожидание до 180 секунд)...")
            for i in range(18):  # 18 проверок по 10 секунд
                time.sleep(10)
                print(f"Прошло {(i+1)*10} секунд...")
                
                logs = subprocess.run(["docker", "logs", container_id], 
                                    capture_output=True, text=True).stdout
                
                # Проверяем успешный вход
                if "Logged in! Waiting for open extension..." in logs:
                    print("Бот успешно вошел в систему...")
                
                # Проверяем загрузку расширения
                if "Extension loaded!" in logs:
                    print("Расширение успешно загружено...")
                
                # Проверяем подключение
                if "Connected! Starting rolling..." in logs:
                    print("Бот подключился к сервису...")
                    # Даже если статус Disconnected, продолжаем работу
                    print("\nПолные логи запуска:")
                    print(logs)
                    if "{ support_status: 'Disconnected' }" in logs:
                        print("\n⚠️ Предупреждение: Бот запущен со статусом Disconnected")
                        print("Это нормально, статус может измениться позже")
                    else:
                        print("\nБот успешно запущен и работает!")
                    return True
                
                # Проверяем критические ошибки
                if "No proxies.txt found" in logs or "Please set APP_USER" in logs:
                    print("\nКритическая ошибка в конфигурации!")
                    print(logs)
                    print("\nОстанавливаем бота...")
                    subprocess.run(["docker", "stop", container_id])
                    subprocess.run(["docker", "rm", container_id])
                    return False
            
            # Если дошли сюда - бот не смог подключиться совсем
            print("\nПолные логи запуска:")
            print(logs)
            print("\nБот не смог подключиться к сервису за отведенное время")
            print("Останавливаем бота...")
            subprocess.run(["docker", "stop", container_id])
            subprocess.run(["docker", "rm", container_id])
            return False
            
        except subprocess.CalledProcessError as e:
            print(f"Ошибка при запуске бота: {e}")
            print(f"Stderr: {e.stderr}")
            return False

    def stop_bot(self, bot_id):
        if bot_id not in self.config["bots"]:
            print(f"Бот с ID {bot_id} не найден!")
            return
        
        # Получаем список всех контейнеров
        result = subprocess.run(["docker", "ps", "-a", "--format", "{{.ID}} {{.Image}}"], 
                              capture_output=True, text=True)
        
        stopped = False
        for line in result.stdout.splitlines():
            container_id, image = line.split()
            if image == "overtrue/gradient-bot":
                print(f"Останавливаем контейнер {container_id[:12]}...")
                subprocess.run(["docker", "stop", container_id])
                subprocess.run(["docker", "rm", container_id])
                stopped = True
        
        if stopped:
            print(f"Бот {bot_id} остановлен и контейнеры удалены")
        else:
            print(f"Не найдено запущенных контейнеров для бота {bot_id}")

    def list_bots(self, return_mapping=False):
        print("\n=== Список ботов ===")
        bot_mapping = {}
        
        if not self.config["bots"]:
            print("Список ботов пуст")
            if return_mapping:
                return bot_mapping
            return
        
        try:
            for index, (bot_id, bot_data) in enumerate(self.config["bots"].items(), 1):
                bot_mapping[str(index)] = bot_id
                # Используем encode/decode для очистки строк от проблемных символов
                safe_bot_id = bot_id.encode('ascii', 'ignore').decode('ascii')
                safe_email = bot_data['email'].encode('ascii', 'ignore').decode('ascii')
                safe_proxy = bot_data['proxy_file'].encode('ascii', 'ignore').decode('ascii')
                
                print(f"{index}. ID: {safe_bot_id}")
                print(f"   Email: {safe_email}")
                print(f"   Proxy file: {safe_proxy}")
                print("   ---")
        except Exception as e:
            print(f"Ошибк при выводе списка: {e}")
            # Очищаем конфигурацию от проблемных записей
            clean_bots = {}
            for bot_id, bot_data in self.config["bots"].items():
                try:
                    # Проверяем, можно ли безопасно вывести данные
                    bot_id.encode('ascii', 'ignore')
                    bot_data['email'].encode('ascii', 'ignore')
                    bot_data['proxy_file'].encode('ascii', 'ignore')
                    clean_bots[bot_id] = bot_data
                except:
                    print(f"Удалена проблемная запись для бота")
                    continue
            
            self.config["bots"] = clean_bots
            self.save_config()
        
        if return_mapping:
            return bot_mapping

    def delete_bot(self, bot_id):
        if bot_id not in self.config["bots"]:
            print(f"Бот с ID {bot_id} не найден!")
            return
        
        # Останавливаем бота
        self.stop_bot(bot_id)
        
        # Удаляем файл прокси
        proxy_file = self.config["bots"][bot_id]["proxy_file"]
        try:
            os.remove(proxy_file)
        except FileNotFoundError:
            pass
        
        # Удаляем из конфигурации
        del self.config["bots"][bot_id]
        self.save_config()
        print(f"Бот {bot_id} успешно удален")

    def change_proxy(self, bot_id):
        if bot_id not in self.config["bots"]:
            print(f"Бот с ID {bot_id} не найден!")
            return
        
        print(f"\nИзменение прокси для бота {bot_id}")
        proxy = input("Введите новый прокси (формат: host:port:username:password): ").strip()
        
        converted_proxy = self.convert_proxy_format(proxy)
        if not converted_proxy:
            print("Ошибка при обработке прокси. Прокси не будет изменен.")
            return
        
        # Обновляем файл прокси
        proxy_file = self.config["bots"][bot_id]["proxy_file"]
        with open(proxy_file, 'w', encoding='utf-8') as f:
            f.write(converted_proxy)
        
        print("Прокси обновлен. Перезапускаем бота...")
        self.stop_bot(bot_id)
        self.start_bot(bot_id)
        print(f"Бот {bot_id} перезапущен с новым прокси")

    def view_logs(self, bot_id):
        # Получаем список контейнеров
        result = subprocess.run(["docker", "ps", "-a", "--format", "{{.ID}} {{.Image}} {{.Status}}"], 
                              capture_output=True, text=True)
        
        containers = []
        for line in result.stdout.splitlines():
            container_id, image, status = line.split(None, 2)
            if image == "overtrue/gradient-bot":
                containers.append((container_id, status))
        
        if not containers:
            print(f"Не найдено запущенных контейнеров для ота {bot_id}")
            return
        
        print("\nДоступные контейнеры:")
        for i, (container_id, status) in enumerate(containers, 1):
            print(f"{i}. ID: {container_id[:12]} - Статус: {status}")
        
        if len(containers) > 1:
            choice = input("\nВыберите номер контейнера для просмотра логов (Enter для последнего): ").strip()
            if choice and choice.isdigit() and 1 <= int(choice) <= len(containers):
                container_id = containers[int(choice)-1][0]
            else:
                container_id = containers[-1][0]
        else:
            container_id = containers[0][0]
        
        print("\nПоследние логи (Ctrl+C для выхода):")
        try:
            subprocess.run(["docker", "logs", "-f", container_id])
        except KeyboardInterrupt:
            print("\nПросмотр логов завершен")

    def cleanup_containers(self):
        print("\nОчистка старых контейнеров...")
        # Останавливаем все контейнеры с нашим образом
        subprocess.run(["docker", "ps", "-a", "-q", "-f", "ancestor=overtrue/gradient-bot"], 
                      capture_output=True, text=True)
        
        # Удаляем все остановленные контейнеры
        subprocess.run(["docker", "container", "prune", "-f"])
        print("Очистка завершена")

    def show_menu(self):
        while True:
            menu_items = [
                "=== Меню управления ботами ===",
                "1. Проверить и установить требования",
                "2. Добавить нового бота",
                "3. Запустить бота",
                "4. Остановить бота",
                "5. Список ботов",
                "6. Добавить ботов из списка",
                "7. Удалить бота",
                "8. Изменить пркси у бота",
                "9. Просмотр логов бота",
                "10. Очистить старые контейнеры",
                "0. Выход"
            ]
            
            # Печатаем меню с правильной кодировкой
            print("\n".join(item.encode('utf-8', 'ignore').decode('utf-8') for item in menu_items))
            
            choice = input("\nВыберите действие: ").strip()
            
            if choice == "1":
                self.check_and_install_requirements()
            elif choice == "2":
                self.add_bot()
            elif choice == "3":
                bot_mapping = self.list_bots(return_mapping=True)
                if not bot_mapping:
                    print("Нет доступных ботов!")
                    continue
                print("\nВведите номер бота из списка выше:")
                bot_number = input("Номер: ")
                if bot_number in bot_mapping:
                    self.start_bot(bot_mapping[bot_number])
                else:
                    print("Неверный номер бота!")
            elif choice == "4":
                bot_mapping = self.list_bots(return_mapping=True)
                if not bot_mapping:
                    print("Нет доступных ботов!")
                    continue
                print("\nВведите номер бота из списка выше:")
                bot_number = input("Номер: ")
                if bot_number in bot_mapping:
                    self.stop_bot(bot_mapping[bot_number])
                else:
                    print("Неверный номер бота!")
            elif choice == "5":
                self.list_bots()
            elif choice == "6":
                self.bulk_add_bots()
            elif choice == "7":
                bot_mapping = self.list_bots(return_mapping=True)
                if not bot_mapping:
                    print("Нет доступных ботов!")
                    continue
                print("\nВведите номер бота для удаления из списка выше:")
                bot_number = input("Номер: ")
                if bot_number in bot_mapping:
                    self.delete_bot(bot_mapping[bot_number])
                else:
                    print("Неверный номер бота!")
            elif choice == "8":
                bot_mapping = self.list_bots(return_mapping=True)
                if not bot_mapping:
                    print("Нет доступных ботов!")
                    continue
                print("\nВвдите номер бота для изменения прокси из списка выше:")
                bot_number = input("Номер: ")
                if bot_number in bot_mapping:
                    self.change_proxy(bot_mapping[bot_number])
                else:
                    print("Неверный номер бота!")
            elif choice == "9":
                bot_mapping = self.list_bots(return_mapping=True)
                if not bot_mapping:
                    print("Нт доступных ботов!")
                    continue
                print("\nВведите номер бота для просмотра логов из списка выше:")
                bot_number = input("Номер: ")
                if bot_number in bot_mapping:
                    self.view_logs(bot_mapping[bot_number])
                else:
                    print("Неверный номер бота!")
            elif choice == "10":
                self.cleanup_containers()
            elif choice == "0":
                break

    def bulk_add_bots(self):
        print("\n=== Массовое добавление ботов ===")
        print("Введите данные в формате: bot_id|email|password|host:port:username:password")
        print("Пример:")
        print("bot1|email1@example.com|password1|proxy.example.com:1080:user1:pass1")
        print("bot2|email2@example.com|password2|proxy.example.com:1080:user2:pass2")
        print("\nПо одной записи на строку. Для завершения введите пустую строку.")
        
        while True:
            line = input()
            if not line:
                break
                
            try:
                bot_id, email, password, proxy = line.strip().split("|")
                
                converted_proxy = self.convert_proxy_format(proxy)
                if not converted_proxy:
                    print(f"Ошибка при обработке прокси для бота {bot_id}. Пропускаем...")
                    continue
                
                proxy_file = f'proxies_{bot_id}.txt'
                with open(proxy_file, 'w', encoding='utf-8') as f:
                    f.write(converted_proxy)
                
                self.config["bots"][bot_id] = {
                    "email": email,
                    "password": password,
                    "proxy_file": proxy_file
                }
                
                self.start_bot(bot_id)
                print(f"Бот {bot_id} добавлен и запущен")
                
            except ValueError:
                print("Неверный формат! Пропускаем...")
                continue
        
        self.save_config()
        print("\nМассовое добавление завершено!")

    def test_proxy(self, proxy_string):
        """Тестирует прокси перед использованием"""
        print("\nТестирование прокси...")
        
        # Делаем несколько проверок для подтверждения ротации
        for i in range(2):
            cmd = [
                "docker", "run", "--rm",
                "-e", "PROXY_TEST=true",
                "-e", f"PROXY={proxy_string}",
                "alpine/curl", "-x", proxy_string, "https://api.ipify.org?format=json"
            ]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    print(f"✓ Тест {i+1}: Прокси работает!")
                    print(f"Ответ: {result.stdout}")
                    if i == 0:
                        print("Ожидание 5 секунд перед повторной проверкой...")
                        time.sleep(5)  # Ждем немного для возможной ротации IP
                    continue
                else:
                    print("✗ Ошибка при проверке прокси")
                    print(f"Ошибка: {result.stderr}")
                    return False
            except subprocess.TimeoutExpired:
                print("✗ Таймаут при проверке прокси")
                return False
            except Exception as e:
                print(f"✗ Ошибка при тестировании прокси: {e}")
                return False
        
        return True

if __name__ == "__main__":
    manager = BotManager()
    print("Добро пожаловать в менеджер ботов!")
    print("Если это первый запуск, рекмендуется выбрать пункт 1 для проверки и установки требований.")
    manager.show_menu() 