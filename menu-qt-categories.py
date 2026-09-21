#!/usr/bin/env python3
import sys
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QKeyEvent
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QScrollArea,
    QGridLayout,
    QToolButton,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QScroller,
    QScrollerProperties
)
import gi
gi.require_version("Gio", "2.0")
from gi.repository import Gio


class MainMenu(QWidget):
    def __init__(self):
        super().__init__()

        self.current_category = "All"
        self.applications = []

        # 1. Настройки окна для Xorg + Тачскрин (из рабочего прототипа)
        self.setWindowFlags(
            Qt.Popup |
            Qt.X11BypassWindowManagerHint |
            Qt.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.StrongFocus)

        # 2. Стилизация через QSS (адаптированная под категории)
        self.setStyleSheet("""
            QWidget#MainWindow {
                background-color: rgba(0, 0, 0, 0.85);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 6px;
            }
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background: transparent;
            }
            QLabel {
                color: white;
                font-family: sans-serif;
            }
            QListWidget {
                background: rgba(255, 255, 255, 0.05);
                border: none;
                outline: none;
                border-radius: 4px;
            }
            QListWidget::item {
                color: white;
                padding: 8px;
                margin: 2px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background: rgba(255, 255, 255, 0.2);
            }
            QScrollBar:vertical, QScrollBar:horizontal {
                width: 0px;
                height: 0px;
                background: transparent;
            }
            QToolButton {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 4px;
                color: white;
                padding: 10px;
            }
            QToolButton:hover {
                background: rgba(255, 255, 255, 0.2);
            }
        """)

        # Основной контейнер-виджет
        self.main_widget = QWidget(self)
        self.main_widget.setObjectName("MainWindow")
        
        # Главный вертикальный Layout
        outer_layout = QVBoxLayout(self.main_widget)
        outer_layout.setContentsMargins(16, 16, 16, 16)
        outer_layout.setSpacing(12)

        # Заголовок
        title = QLabel("<b>Приложения</b>")
        title.setStyleSheet("font-size: 18px;")
        outer_layout.addWidget(title)

        # Горизонтальный сплит: Категории (слева) + Приложения (справа)
        workspace_layout = QHBoxLayout()
        workspace_layout.setSpacing(16)
        outer_layout.addLayout(workspace_layout)

        # --- ЛЕВАЯ ПАНЕЛЬ (КАТЕГОРИИ) ---
        self.category_list = QListWidget()
        self.category_list.setFixedWidth(200)
        self.category_list.setFixedHeight(520) # Синхронизируем высоту с областью приложений
        self.category_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.category_list.setFocusPolicy(Qt.NoFocus) # Чтобы фокус не залипал на категориях
        self.category_list.itemClicked.connect(self.on_category_selected)
        workspace_layout.addWidget(self.category_list)

        # --- ПРАВАЯ ПАНЕЛЬ (ПРИЛОЖЕНИЯ) ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedSize(800, 520) # Уменьшили ширину с 1000 до 800, резервируя место под список
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        workspace_layout.addWidget(scroll)

        # Контейнер для сетки
        grid_widget = QWidget()
        grid_widget.setFocusPolicy(Qt.NoFocus)
        self.grid_layout = QGridLayout(grid_widget)
        self.grid_layout.setSpacing(12)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        scroll.setWidget(grid_widget)

        # Настройка жестов (Оба виджета получают корректные обработчики)
        QScroller.grabGesture(self.category_list.viewport(), QScroller.LeftMouseButtonGesture)
        QScroller.grabGesture(scroll.viewport(), QScroller.LeftMouseButtonGesture)

        # Настройка физики (Делаем скролл отзывчивым и плавным)
        scroller_props = QScrollerProperties()
        scroller_props.setScrollMetric(QScrollerProperties.DragStartDistance, 10)
        scroller_props.setScrollMetric(QScrollerProperties.DecelerationFactor, 0.15)
        
        # ЭТОТ БЛОК СТАВИМ ВЗАМЕН:
        # Настройка жестов (вешаем прямо на сами виджеты, убирая .viewport())
        QScroller.grabGesture(self.category_list, QScroller.LeftMouseButtonGesture)
        QScroller.grabGesture(scroll, QScroller.LeftMouseButtonGesture)

        # Вытаскиваем скроллеры для настройки чувствительности
        category_scroller = QScroller.scroller(self.category_list)
        app_scroller = QScroller.scroller(scroll)

        # Повышаем чувствительность под Xorg
        scroller_props = QScrollerProperties()
        # Длина сдвига до активации скролла (в пикселях). 
        # Делаем её маленькой (6 пикселей), чтобы скролл схватывался мгновенно
        scroller_props.setScrollMetric(QScrollerProperties.DragStartDistance, 6)
        scroller_props.setScrollMetric(QScrollerProperties.DecelerationFactor, 0.12)
        scroller_props.setScrollMetric(QScrollerProperties.MaximumVelocity, 1.2)
        
        category_scroller.setScrollerProperties(scroller_props)
        app_scroller.setScrollerProperties(scroller_props)


        # Компоновка самого окна
        window_layout = QVBoxLayout(self)
        window_layout.setContentsMargins(0, 0, 0, 0)
        window_layout.addWidget(self.main_widget)

        # Загрузка данных
        self.load_applications_and_categories()

        # Центрирование
        self.adjustSize()
        self.center_on_screen()

    def load_applications_and_categories(self):
        # Чтение всех приложений
        apps = [app for app in Gio.AppInfo.get_all() if app.should_show()]
        apps.sort(key=lambda a: a.get_display_name().lower())
        self.applications = apps

        # Извлечение уникальных категорий
        unique_categories = set()
        for app in apps:
            if hasattr(app, "get_categories") and app.get_categories():
                cats = [c.strip() for c in app.get_categories().split(";") if c.strip()]
                unique_categories.update(cats)

        # Добавляем дефолтную категорию "Все"
        self.add_category_row("Все", "All")

        category_mapping = {
            "AudioVideo": "Мультимедиа",
            "Development": "Разработка",
            "Education": "Образование",
            "Game": "Игры",
            "Graphics": "Графика",
            "Network": "Интернет",
            "Office": "Офис",
            "Settings": "Настройки",
            "System": "Система",
            "Utility": "Утилиты",
            "WebBrowser": "Веб-браузеры",
            "FileManager": "Файловые менеджеры",
            "TerminalEmulator": "Терминалы",
        }

        for cat in sorted(unique_categories):
            display_name = category_mapping.get(cat, cat)
            self.add_category_row(display_name, cat)

        if self.category_list.count() > 0:
            self.category_list.setCurrentRow(0)

        self.rebuild_application_grid()

    def add_category_row(self, display_name, internal_name):
        item = QListWidgetItem(display_name)
        item.setData(Qt.UserRole, internal_name)
        item.setSizeHint(QSize(180, 50))
        self.category_list.addItem(item)

    def on_category_selected(self, item):
        if item is None:
            return
        self.current_category = item.data(Qt.UserRole)
        self.rebuild_application_grid()

    def rebuild_application_grid(self):
        # Очистка старой сетки
        while self.grid_layout.count():
            layout_item = self.grid_layout.takeAt(0)
            widget = layout_item.widget()
            if widget is not None:
                widget.deleteLater()

        # Заполнение отфильтрованными приложениями
        max_columns = 6  # Уменьшили до 6, так как экран стал чуть уже из-за боковой панели
        filtered_apps = []
        
        for app in self.applications:
            if self.current_category == "All":
                filtered_apps.append(app)
            else:
                if hasattr(app, "get_categories") and app.get_categories():
                    cats = [c.strip() for c in app.get_categories().split(";") if c.strip()]
                    if self.current_category in cats:
                        filtered_apps.append(app)

        for index, app in enumerate(filtered_apps):
            button = self.create_button(app)
            row = index // max_columns
            col = index % max_columns
            self.grid_layout.addWidget(button, row, col)

    def create_button(self, app):
        button = QToolButton()
        button.setFixedSize(110, 90)
        button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        
        display_name = app.get_display_name()
        button.setText(display_name)
        if app.get_description():
            button.setToolTip(app.get_description())

        if len(display_name) > 14:
            button.setText(display_name[:12] + "...")

        gicon = app.get_icon()
        if gicon is not None:
            icon_theme = Gio.Icon.to_string(gicon)
            qicon = QIcon.fromTheme(icon_theme)
            button.setIcon(qicon)
            button.setIconSize(QSize(48, 48))

        button.clicked.connect(lambda: self.launch_application(app))
        return button

    def launch_application(self, app):
        try:
            app.launch([], None)
        except Exception as error:
            print(f"Не удалось запустить приложение: {error}")
        self.close()

    def center_on_screen(self):
        frame_gm = self.frameGeometry()
        screen = QApplication.desktop().screenNumber(QApplication.desktop().cursor().pos())
        center_point = QApplication.desktop().screenGeometry(screen).center()
        frame_gm.moveCenter(center_point)
        self.move(frame_gm.topLeft())

    def showEvent(self, event):
        super().showEvent(event)
        self.activateWindow()
        self.raise_()
        self.setFocus()

    def keyPressEvent(self, event: QKeyEvent):
        # 1. Проверяем, нажата ли именно клавиша Escape
        if event.key() == Qt.Key_Escape:
            self.close()    # Закрываем наше меню
            event.accept()  # Говорим системе: "Мы обработали это событие, дальше его передавать не нужно"
        else:
            # 2. Если нажата любая другая клавиша, передаем её стандартному обработчику Qt
            super().keyPressEvent(event)

# Проверка: запущен ли скрипт напрямую (а не импортирован как модуль в другой файл)
if __name__ == "__main__":
    
    # 1. Создаем главный объект приложения Qt, передавая системные аргументы
    app = QApplication(sys.argv)
    
    # 2. Инициализируем наш класс главного меню (создаем окно в памяти)
    menu = MainMenu()
    
    # 3. Делаем созданное окно видимым на экране
    menu.show()
    
    # 4. Запускаем бесконечный цикл обработки событий Qt (клики, тачи, отрисовка).
    # sys.exit гарантирует, что когда цикл завершится (окно закроется), скрипт корректно завершит работу.
    sys.exit(app.exec_())



# ... здесь заканчиваются все методы класса MainMenu ...

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Подключаем стили (QSS) к приложению...
    app.setStyleSheet("""
        # ... здесь находится весь ваш блок со стилями CSS ...
    """)

    # Инициализируем и запускаем окно (оставляем ОДИН такой блок)
    window = MainMenu()
    window.show()
    sys.exit(app.exec_())

