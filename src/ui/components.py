# Импорт необходимых библиотек и модулей
import flet as ft                  # Фреймворк для создания пользовательского интерфейса
from ui.styles import AppStyles    # Импорт стилей приложения
import asyncio                     # Библиотека для асинхронного программирования


class MessageBubble(ft.Container):
    """
    Компонент "пузырька" сообщения в чате.
    """

    def __init__(self, message: str, is_user: bool):
        super().__init__()
        self.padding = 10
        self.border_radius = 10
        self.bgcolor = ft.Colors.BLUE_700 if is_user else ft.Colors.GREY_700
        self.alignment = ft.alignment.center_right if is_user else ft.alignment.center_left
        self.margin = ft.margin.only(
            left=50 if is_user else 0,
            right=0 if is_user else 50,
            top=5,
            bottom=5
        )
        self.content = ft.Column(
            controls=[
                ft.Text(
                    value=message,
                    color=ft.Colors.WHITE,
                    size=16,
                    selectable=True,
                    weight=ft.FontWeight.W_400
                )
            ],
            tight=True
        )


class ModelSelector(ft.Dropdown):
    """
    Выпадающий список для выбора AI модели с функцией поиска.
    """

    def __init__(self, models: list):
        super().__init__()
        for key, value in AppStyles.MODEL_DROPDOWN.items():
            setattr(self, key, value)
        self.label = None
        self.hint_text = "Выбор модели"
        self.options = [
            ft.dropdown.Option(
                key=model['id'],
                text=model['name']
            ) for model in models
        ]
        self.all_options = self.options.copy()
        self.value = models[0]['id'] if models else None
        self.search_field = ft.TextField(
            on_change=self.filter_options,
            hint_text="Поиск модели",
            **AppStyles.MODEL_SEARCH_FIELD
        )

    def filter_options(self, e):
        search_text = self.search_field.value.lower() if self.search_field.value else ""
        if not search_text:
            self.options = self.all_options
        else:
            self.options = [
                opt for opt in self.all_options
                if search_text in opt.text.lower() or search_text in opt.key.lower()
            ]
        e.page.update()


class AuthDialog:
    """
    Диалоговое окно аутентификации для входа в приложение.
    """

    def __init__(self, auth_manager):
        self.auth_manager = auth_manager
        self.api_key = None
        self.completed = False
        self.page = None

    async def show(self, page: ft.Page) -> str:
        """
        Показать диалог аутентификации.
        Возвращает API ключ при успешной аутентификации.
        """
        self.page = page
        page.clean()
        page.title = "Аутентификация - AI Чат"
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        page.vertical_alignment = ft.MainAxisAlignment.CENTER

        # Проверяем, есть ли уже сохраненные данные
        if not self.auth_manager.has_credentials():
            # Первый запуск - запрашиваем ключ у пользователя
            await self.first_time_setup()
        else:
            # Последующие запуски - запрашиваем PIN
            await self.show_pin_input()

        # Ждем завершения аутентификации
        while not self.completed:
            await asyncio.sleep(0.1)

        return self.api_key

    async def first_time_setup(self):
        """Первый запуск - запрос ключа у пользователя и проверка баланса"""
        page = self.page

        # Создаем форму для ввода ключа
        container = ft.Container(
            width=550,
            padding=30,
            bgcolor=ft.Colors.WHITE,
            border_radius=20,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=15,
                color=ft.Colors.GREY_300,
            )
        )

        title = ft.Text(
            "🔐 Первый запуск",
            size=28,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.BLUE_700
        )

        subtitle = ft.Text(
            "Введите ваш API ключ OpenRouter для настройки приложения",
            size=14,
            color=ft.Colors.GREY_600,
            text_align=ft.TextAlign.CENTER
        )

        key_field = ft.TextField(
            label="API ключ OpenRouter",
            hint_text="sk-or-v1-...",
            password=True,
            can_reveal_password=True,
            width=450,
            border_radius=10,
            text_size=14
        )

        status_text = ft.Text("", size=12, color=ft.Colors.RED)

        check_button = ft.ElevatedButton(
            text="Проверить ключ",
            icon=ft.Icons.VERIFIED,
            width=200,
            height=45,
            color=ft.Colors.WHITE,
            bgcolor=ft.Colors.BLUE_700,
        )

        info_card = ft.Container(
            content=ft.Column([
                ft.Text("💡 Как получить API ключ:",
                        size=13, weight=ft.FontWeight.BOLD),
                ft.Text("1. Зарегистрируйтесь на openrouter.ai", size=12),
                ft.Text("2. Перейдите в настройки аккаунта", size=12),
                ft.Text("3. Создайте новый API ключ", size=12),
                ft.Text("4. Скопируйте ключ и вставьте его выше", size=12),
            ], spacing=5),
            padding=15,
            bgcolor=ft.Colors.GREY_50,
            border_radius=10,
            margin=ft.margin.only(top=20)
        )

        async def check_and_proceed(e):
            api_key = key_field.value.strip()
            if not api_key:
                status_text.value = "❌ Пожалуйста, введите API ключ"
                status_text.color = ft.Colors.RED
                await page.update_async()
                return

            # Показываем проверку
            check_button.disabled = True
            check_button.text = "Проверка..."
            status_text.value = "⏳ Проверка ключа и баланса..."
            status_text.color = ft.Colors.ORANGE
            await page.update_async()

            # Проверяем ключ через API
            is_valid, message = await self.auth_manager.verify_openrouter_key(api_key)

            if is_valid:
                # Генерируем PIN
                pin = self.auth_manager.generate_pin()

                # Сохраняем учетные данные
                self.auth_manager.save_credentials(api_key, pin)

                # Показываем PIN во всплывающем сообщении
                self.api_key = api_key
                self.completed = True

                page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"✅ Ваш PIN: {pin} (сохраните его!)"),
                    duration=10000,
                    bgcolor=ft.Colors.GREEN_700
                )
                page.snack_bar.open = True
                await page.update_async()
            else:
                status_text.value = message
                status_text.color = ft.Colors.RED
                check_button.disabled = False
                check_button.text = "Проверить ключ"
                await page.update_async()

        check_button.on_click = check_and_proceed

        container.content = ft.Column(
            [
                title,
                ft.Container(height=10),
                subtitle,
                ft.Container(height=20),
                key_field,
                ft.Container(height=10),
                check_button,
                ft.Container(height=10),
                status_text,
                info_card
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=5
        )

        page.add(container)
        await page.update_async()

    async def show_pin_input(self):
        """Показать форму ввода PIN-кода"""
        page = self.page

        def on_login_success():
            self.api_key = self.auth_manager.get_api_key()
            self.completed = True
            page.update()

        container = ft.Container(
            width=450,
            padding=30,
            bgcolor=ft.Colors.WHITE,
            border_radius=20,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=15,
                color=ft.Colors.GREY_300,
            )
        )

        title = ft.Text(
            "🔐 Вход в систему",
            size=28,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.BLUE_700
        )

        subtitle = ft.Text(
            "Введите ваш PIN-код для доступа к чату",
            size=14,
            color=ft.Colors.GREY_600
        )

        pin_field = ft.TextField(
            label="PIN-код",
            hint_text="Введите 4 цифры",
            password=True,
            can_reveal_password=True,
            width=300,
            max_length=4,
            input_filter=ft.InputFilter(allow=True, regex_string=r"[0-9]"),
            text_align=ft.TextAlign.CENTER,
            text_size=24
        )

        login_button = ft.ElevatedButton(
            text="Войти",
            icon=ft.Icons.LOGIN,
            width=200,
            height=45,
            color=ft.Colors.WHITE,
            bgcolor=ft.Colors.GREEN_700
        )

        reset_button = ft.TextButton(
            text="Сбросить ключ и ввести новый",
            icon=ft.Icons.REFRESH,
            style=ft.ButtonStyle(color=ft.Colors.ORANGE)
        )

        status_text = ft.Text("", size=12, color=ft.Colors.RED)

        async def login(e):
            pin = pin_field.value.strip()
            if len(pin) != 4:
                status_text.value = "❌ PIN должен содержать 4 цифры"
                await page.update_async()
                return

            if self.auth_manager.verify_pin(pin):
                on_login_success()
            else:
                status_text.value = "❌ Неверный PIN-код. Попробуйте снова."
                pin_field.value = ""
                await page.update_async()

        def reset_key(e):
            # Сброс учетных данных
            self.auth_manager.reset_credentials()
            # Очищаем страницу
            page.clean()
            page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
            page.vertical_alignment = ft.MainAxisAlignment.CENTER
            # Показываем форму ввода ключа
            self.page = page
            # Запускаем first_time_setup в event loop
            asyncio.create_task(self.first_time_setup())

        login_button.on_click = login
        reset_button.on_click = reset_key
        pin_field.on_submit = login

        container.content = ft.Column(
            [title, ft.Container(height=20), subtitle, ft.Container(height=20),
             pin_field, ft.Container(
                 height=15), login_button, ft.Container(height=10),
             reset_button, ft.Container(
                 height=10), status_text, ft.Container(height=10),
             ft.Text("💡 Забыли PIN? Нажмите 'Сбросить ключ' для повторной настройки",
                     size=11, color=ft.Colors.GREY_500)],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=5
        )

        page.add(container)
        await page.update_async()
