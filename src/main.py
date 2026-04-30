# Импорт необходимых библиотек и модулей
# Фреймворк для создания кроссплатформенных приложений с современным UI
import flet as ft
# Клиент для взаимодействия с AI API через OpenRouter
from api.openrouter import OpenRouterClient
# Модуль с настройками стилей интерфейса
from ui.styles import AppStyles
# Компоненты пользовательского интерфейса
from ui.components import MessageBubble, ModelSelector, AuthDialog
# Модуль для кэширования истории чата
from utils.cache import ChatCache
# Модуль для логирования работы приложения
from utils.logger import AppLogger
# Модуль для сбора и анализа статистики использования
from utils.analytics import Analytics
# Модуль для мониторинга производительности
from utils.monitor import PerformanceMonitor
# Библиотека для асинхронного программирования
import asyncio
# Библиотека для работы с временными метками
import time
# Библиотека для работы с JSON-данными
import json
# Класс для работы с датой и временем
from datetime import datetime
# Библиотека для работы с операционной системой
import os
import sys
import subprocess
from auth import AuthManager  # Добавьте эту строку


class ChatApp:
    """
    Основной класс приложения чата.
    Управляет всей логикой работы приложения, включая UI и взаимодействие с API.
    """

    def __init__(self):
        """
        Инициализация основных компонентов приложения:
        - API клиент для связи с языковой моделью
        - Система кэширования для сохранения истории
        - Система логирования для отслеживания работы
        - Система аналитики для сбора статистики
        - Система мониторинга для отслеживания производительности
        - Система аутентификации
        """
        # Инициализация системы аутентификации
        self.auth_manager = AuthManager()
        self.api_key = None

        # Остальные компоненты будут инициализированы после аутентификации
        self.api_client = None
        self.cache = None
        self.logger = None
        self.analytics = None
        self.monitor = None
        self.balance_text = None

        # Создание директории для экспорта истории чата
        self.exports_dir = "exports"               # Путь к директории экспорта
        # Создание директории, если её нет
        os.makedirs(self.exports_dir, exist_ok=True)

    @staticmethod
    def open_folder(path: str):
        """Кроссплатформенное открытие директории в файловом менеджере"""
        if sys.platform.startswith("win"):
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)

    async def authenticate(self, page: ft.Page) -> bool:
        """
        Аутентификация пользователя.
        Возвращает True при успешной аутентификации.
        """
        auth_dialog = AuthDialog(self.auth_manager)
        self.api_key = await auth_dialog.show(page)

        if self.api_key:
            # Инициализируем компоненты после успешной аутентификации
            # Исправлено: убираем api_key из конструктора
            self.api_client = OpenRouterClient()
            # Устанавливаем API ключ
            if hasattr(self.api_client, 'set_api_key'):
                self.api_client.set_api_key(self.api_key)
            elif hasattr(self.api_client, 'api_key'):
                self.api_client.api_key = self.api_key

            self.cache = ChatCache()
            self.logger = AppLogger()
            self.analytics = Analytics(self.cache)
            self.monitor = PerformanceMonitor()

            # Создаем компонент для отображения баланса API
            self.balance_text = ft.Text(
                "Баланс: Загрузка...",                # Начальный текст до загрузки реального баланса
                **AppStyles.BALANCE_TEXT               # Применение стилей из конфигурации
            )
            await self.update_balance()

            return True
        return False

    def load_chat_history(self):
        """
        Загрузка истории чата из кэша и отображение её в интерфейсе.
        Сообщения добавляются в обратном порядке для правильной хронологии.
        """
        try:
            history = self.cache.get_chat_history()    # Получение истории из кэша
            # Перебор сообщений в обратном порядке
            for msg in reversed(history):
                # Распаковка данных сообщения в отдельные переменные
                _, model, user_message, ai_response, timestamp, tokens = msg
                # Добавление пары сообщений (пользователь + AI) в интерфейс
                self.chat_history.controls.extend([
                    MessageBubble(                     # Создание пузырька сообщения пользователя
                        message=user_message,
                        is_user=True
                    ),
                    MessageBubble(                     # Создание пузырька ответа AI
                        message=ai_response,
                        is_user=False
                    )
                ])
        except Exception as e:
            # Логирование ошибки при загрузке истории
            if self.logger:
                self.logger.error(f"Ошибка загрузки истории чата: {e}")

    async def update_balance(self):
        """
        Обновление отображения баланса API в интерфейсе.
        При успешном получении баланса показывает его зеленым цветом,
        при ошибке - красным с текстом 'н/д' (не доступен).
        """
        try:
            if self.api_client and hasattr(self.api_client, 'get_balance'):
                balance = self.api_client.get_balance()         # Запрос баланса через API
                # Обновление текста с балансом
                self.balance_text.value = f"Баланс: {balance}"
                # Установка зеленого цвета для успешного получения
                self.balance_text.color = ft.Colors.GREEN_400
            else:
                self.balance_text.value = "Баланс: н/д"
                self.balance_text.color = ft.Colors.RED_400
        except Exception as e:
            # Обработка ошибки получения баланса
            self.balance_text.value = "Баланс: н/д"         # Установка текста ошибки
            # Установка красного цвета для ошибки
            self.balance_text.color = ft.Colors.RED_400
            if self.logger:
                self.logger.error(f"Ошибка обновления баланса: {e}")

    def reset_api_key(self, page: ft.Page):
        """Сброс API ключа и перезапуск аутентификации"""
        self.auth_manager.reset_credentials()
        page.clean()
        asyncio.create_task(self.main(page))

    async def main(self, page: ft.Page):
        """
        Основная функция инициализации интерфейса приложения.
        Создает все элементы UI и настраивает их взаимодействие.

        Args:
            page (ft.Page): Объект страницы Flet для размещения элементов интерфейса
        """

        # Выполняем аутентификацию
        if not await self.authenticate(page):
            # Если аутентификация не пройдена, показываем сообщение и закрываемся
            page.clean()
            page.add(
                ft.Container(
                    content=ft.Text(
                        "Аутентификация не пройдена. Приложение будет закрыто.",
                        size=16,
                        color=ft.Colors.RED
                    ),
                    alignment=ft.alignment.center,
                    expand=True
                )
            )
            return

        # Применение базовых настроек страницы из конфигурации стилей
        for key, value in AppStyles.PAGE_SETTINGS.items():
            setattr(page, key, value)

        AppStyles.set_window_size(page)    # Установка размеров окна приложения

        # Инициализация выпадающего списка для выбора модели AI
        models = self.api_client.available_models
        self.model_dropdown = ModelSelector(models)
        self.model_dropdown.value = models[0]['id'] if models else None

        async def send_message_click(e):
            """
            Асинхронная функция отправки сообщения.
            """
            if not self.message_input.value:
                return

            try:
                # Визуальная индикация процесса
                self.message_input.border_color = ft.Colors.BLUE_400
                page.update()

                # Сохранение данных сообщения
                start_time = time.time()
                user_message = self.message_input.value
                self.message_input.value = ""
                page.update()

                # Добавление сообщения пользователя
                self.chat_history.controls.append(
                    MessageBubble(message=user_message, is_user=True)
                )

                # Индикатор загрузки
                loading = ft.ProgressRing()
                self.chat_history.controls.append(loading)
                page.update()

                # Асинхронная отправка запроса
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: self.api_client.send_message(
                        user_message,
                        self.model_dropdown.value
                    )
                )

                # Удаление индикатора загрузки
                self.chat_history.controls.remove(loading)

                # Обработка ответа
                if "error" in response:
                    response_text = f"Ошибка: {response['error']}"
                    tokens_used = 0
                    if self.logger:
                        self.logger.error(f"Ошибка API: {response['error']}")
                else:
                    response_text = response["choices"][0]["message"]["content"]
                    tokens_used = response.get(
                        "usage", {}).get("total_tokens", 0)

                # Сохранение в кэш
                self.cache.save_message(
                    model=self.model_dropdown.value,
                    user_message=user_message,
                    ai_response=response_text,
                    tokens_used=tokens_used
                )

                # Добавление ответа в чат
                self.chat_history.controls.append(
                    MessageBubble(message=response_text, is_user=False)
                )

                # Обновление аналитики
                response_time = time.time() - start_time
                self.analytics.track_message(
                    model=self.model_dropdown.value,
                    message_length=len(user_message),
                    response_time=response_time,
                    tokens_used=tokens_used
                )

                # Логирование метрик
                if self.monitor and self.logger:
                    self.monitor.log_metrics(self.logger)
                page.update()

            except Exception as e:
                if self.logger:
                    self.logger.error(f"Ошибка отправки сообщения: {e}")
                self.message_input.border_color = ft.Colors.RED_500

                # Показ уведомления об ошибке
                snack = ft.SnackBar(
                    content=ft.Text(
                        str(e),
                        color=ft.Colors.RED_500,
                        weight=ft.FontWeight.BOLD
                    ),
                    bgcolor=ft.Colors.GREY_900,
                    duration=5000,
                )
                page.overlay.append(snack)
                snack.open = True
                page.update()

        def show_error_snack(page, message: str):
            """Показ уведомления об ошибке"""
            snack = ft.SnackBar(                  # Создание уведомления
                content=ft.Text(
                    message,
                    color=ft.Colors.RED_500
                ),
                bgcolor=ft.Colors.GREY_900,
                duration=5000,
            )
            page.overlay.append(snack)            # Добавление уведомления
            snack.open = True                     # Открытие уведомления
            page.update()                         # Обновление страницы

        async def show_analytics(e):
            """Показ статистики использования"""
            stats = self.analytics.get_statistics()    # Получение статистики

            # Создание диалога статистики
            dialog = ft.AlertDialog(
                title=ft.Text("Аналитика"),
                content=ft.Column([
                    ft.Text(f"Всего сообщений: {stats['total_messages']}"),
                    ft.Text(f"Всего токенов: {stats['total_tokens']}"),
                    ft.Text(
                        f"Среднее токенов/сообщение: {stats['tokens_per_message']:.2f}"),
                    ft.Text(
                        f"Сообщений в минуту: {stats['messages_per_minute']:.2f}")
                ]),
                actions=[
                    ft.TextButton(
                        "Закрыть", on_click=lambda e: close_dialog(dialog)),
                ],
            )

            page.overlay.append(dialog)           # Добавление диалога
            dialog.open = True                    # Открытие диалога
            page.update()                         # Обновление страницы

        async def clear_history(e):
            """
            Очистка истории чата.
            """
            try:
                self.cache.clear_history()          # Очистка кэша
                self.analytics.clear_data()         # Очистка аналитики
                self.chat_history.controls.clear()  # Очистка истории чата

            except Exception as e:
                if self.logger:
                    self.logger.error(f"Ошибка очистки истории: {e}")
                show_error_snack(page, f"Ошибка очистки истории: {str(e)}")

        async def confirm_clear_history(e):
            """Подтверждение очистки истории"""
            def close_dlg(e):                     # Функция закрытия диалога
                close_dialog(dialog)

            # Функция подтверждения очистки
            async def clear_confirmed(e):
                await clear_history(e)
                close_dialog(dialog)

            # Создание диалога подтверждения
            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Подтверждение удаления"),
                content=ft.Text("Вы уверены? Это действие нельзя отменить!"),
                actions=[
                    ft.TextButton("Отмена", on_click=close_dlg),
                    ft.TextButton("Очистить", on_click=clear_confirmed),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )

            page.overlay.append(dialog)
            dialog.open = True
            page.update()

        def close_dialog(dialog):
            """Закрытие диалогового окна"""
            dialog.open = False                   # Закрытие диалога
            page.update()                         # Обновление страницы

            if dialog in page.overlay:            # Удаление из overlay
                page.overlay.remove(dialog)

        async def save_dialog(e):
            """
            Сохранение истории диалога в JSON файл.
            """
            try:
                # Получение истории из кэша
                history = self.cache.get_chat_history()

                # Форматирование данных для сохранения
                dialog_data = []
                for msg in history:
                    dialog_data.append({
                        "timestamp": msg[4],
                        "model": msg[1],
                        "user_message": msg[2],
                        "ai_response": msg[3],
                        "tokens_used": msg[5]
                    })

                # Создание имени файла
                filename = f"chat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                filepath = os.path.join(self.exports_dir, filename)

                # Сохранение в JSON
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(dialog_data, f, ensure_ascii=False,
                              indent=2, default=str)

                # Создание диалога успешного сохранения
                dialog = ft.AlertDialog(
                    modal=True,
                    title=ft.Text("Диалог сохранен"),
                    content=ft.Column([
                        ft.Text("Путь сохранения:"),
                        ft.Text(filepath, selectable=True,
                                weight=ft.FontWeight.BOLD),
                    ]),
                    actions=[
                        ft.TextButton(
                            "OK", on_click=lambda e: close_dialog(dialog)),
                        ft.TextButton("Открыть папку",
                                      on_click=lambda e: self.open_folder(
                                          self.exports_dir)
                                      ),
                    ],
                )

                page.overlay.append(dialog)
                dialog.open = True
                page.update()

            except Exception as e:
                if self.logger:
                    self.logger.error(f"Ошибка сохранения: {e}")
                show_error_snack(page, f"Ошибка сохранения: {str(e)}")

        # Кнопка сброса API ключа
        def reset_api_key_click(e):
            """Сброс API ключа и перезапуск аутентификации"""
            async def reset_and_restart():
                self.auth_manager.reset_credentials()
                page.clean()
                await self.main(page)

            asyncio.create_task(reset_and_restart())

        # Создание компонентов интерфейса
        self.message_input = ft.TextField(
            **AppStyles.MESSAGE_INPUT)  # Поле ввода
        self.chat_history = ft.ListView(
            **AppStyles.CHAT_HISTORY)    # История чата

        # Загрузка существующей истории
        self.load_chat_history()

        # Создание кнопок управления
        save_button = ft.ElevatedButton(
            on_click=save_dialog,           # Привязка функции сохранения
            **AppStyles.SAVE_BUTTON         # Применение стилей
        )

        clear_button = ft.ElevatedButton(
            on_click=confirm_clear_history,  # Привязка функции очистки
            **AppStyles.CLEAR_BUTTON        # Применение стилей
        )

        send_button = ft.ElevatedButton(
            on_click=send_message_click,    # Привязка функции отправки
            **AppStyles.SEND_BUTTON         # Применение стилей
        )

        analytics_button = ft.ElevatedButton(
            on_click=show_analytics,        # Привязка функции аналитики
            **AppStyles.ANALYTICS_BUTTON    # Применение стилей
        )

        # Добавляем кнопку сброса ключа
        reset_key_button = ft.ElevatedButton(
            text="Сменить API ключ",
            icon=ft.Icons.KEY,
            on_click=lambda e: reset_api_key_click(e),
            bgcolor=ft.Colors.ORANGE_700,
            color=ft.Colors.WHITE,
        )

        # Создание layout компонентов

        # Создание ряда кнопок управления (добавляем кнопку сброса)
        control_buttons = ft.Row(
            controls=[                      # Размещение кнопок в ряд
                save_button,
                analytics_button,
                clear_button,
                reset_key_button  # Добавлена новая кнопка
            ],
            **AppStyles.CONTROL_BUTTONS_ROW  # Применение стилей к ряду
        )

        # Создание строки ввода с кнопкой отправки
        input_row = ft.Row(
            controls=[                      # Размещение элементов ввода
                self.message_input,
                send_button
            ],
            **AppStyles.INPUT_ROW           # Применение стилей к строке ввода
        )

        # Создание колонки для элементов управления
        controls_column = ft.Column(
            controls=[                      # Размещение элементов управления
                input_row,
                control_buttons
            ],
            **AppStyles.CONTROLS_COLUMN     # Применение стилей к колонке
        )

        # Создание контейнера для баланса
        balance_container = ft.Container(
            content=self.balance_text,            # Размещение текста баланса
            **AppStyles.BALANCE_CONTAINER        # Применение стилей к контейнеру
        )

        # Создание колонки выбора модели
        model_selection = ft.Column(
            controls=[                            # Размещение элементов выбора модели
                self.model_dropdown.search_field,
                self.model_dropdown,
                balance_container
            ],
            **AppStyles.MODEL_SELECTION_COLUMN   # Применение стилей к колонке
        )

        # Создание основной колонки приложения
        self.main_column = ft.Column(
            controls=[                            # Размещение основных элементов
                model_selection,
                self.chat_history,
                controls_column
            ],
            **AppStyles.MAIN_COLUMN               # Применение стилей к главной колонке
        )

        # Добавление основной колонки на страницу
        page.add(self.main_column)

        # Запуск монитора
        if self.monitor:
            self.monitor.get_metrics()

        # Логирование запуска
        if self.logger:
            self.logger.info("Приложение запущено")


def main():
    """Точка входа в приложение"""
    app = ChatApp()                              # Создание экземпляра приложения

    async def run_app(page: ft.Page):
        await app.main(page)

    ft.app(target=run_app)                      # Запуск приложения


if __name__ == "__main__":
    main()                                       # Запуск если файл запущен напрямую
