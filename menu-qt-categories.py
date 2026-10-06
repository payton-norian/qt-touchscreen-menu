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

        # 1. Адаптивный расчет геометрии под текущий экран
        desktop = QApplication.desktop()
        current_screen = desktop.screenNumber(desktop.cursor().pos())
        screen_geometry = desktop.screenGeometry(current_screen)
        
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()

        # Окно занимает 80% ширины и 80% высоты экрана
        window_width = int(screen_width * 0.80)
        window_height = int(screen_height * 0.80)

        # Вычисляем ширину зоны приложений (минус 200px боковой панели и ~50px на отступы)
        app_area_width = window_width - 250
        # Высота рабочих областей (минус заголовок и margins)
        workspace_height = window_height - 70

        # Динамический расчет колонок под доступную ширину
        self.max_columns = max(2, app_area_width // 122)

        # 2. Настройки окна для Xorg + Тачскрин
        self.setWindowFlags(
            Qt.Popup |
            Qt.X11BypassWindowManagerHint |
            Qt.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.StrongFocus)

        # 3. Стилизация через QSS
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
        self.category_list.setFixedHeight(workspace_height) 
        self.category_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.category_list.setFocusPolicy(Qt.NoFocus) 
        self.category_list.itemClicked.connect(self.on_category_selected)
        workspace_layout.addWidget(self.category_list)

        # --- ПРАВАЯ ПАНЕЛЬ (ПРИЛОЖЕНИЯ) ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedSize(app_area_width, workspace_height) 
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

        # Настройка кинетического скроллинга пальцем
        QScroller.grabGesture(self.category_list, QScroller.LeftMouseButtonGesture)
        QScroller.grabGesture(scroll, QScroller.LeftMouseButtonGesture)

        # Вытаскиваем скроллеры для точной настройки физики
        category_scroller = QScroller.scroller(self.category_list)
        app_scroller = QScroller.scroller(scroll)

        scroller_props = QScrollerProperties()
        scroller_props.setScrollMetric(QScrollerProperties.DragStartDistance, 6)
        scroller_props.setScrollMetric(QScrollerProperties.DecelerationFactor, 0.12)
        scroller_props.setScrollMetric(QScrollerProperties.MaximumVelocity, 1.2)
        
        category_scroller.setScrollerProperties(scroller_props)
        app_scroller.setScrollerProperties(scroller_props)

        # Компоновка окна
        window_layout = QVBoxLayout(self)
        window_layout.setContentsMargins(0, 0, 0, 0)
        window_layout.addWidget(self.main_widget)

        # Загрузка данных
        self.load_applications_and_categories()

        # Применение адаптивных размеров и центрирование
        self.resize(window_width, window_height)
        self.center_on_screen(screen_geometry)

    def load_applications_and_categories(self):
        raw_apps = [app for app in Gio.AppInfo.get_all() if app.should_show()]
        
        # Интегрируем очистку от системного мусора
        for app in raw_apps:
            app_categories = app.get_categories() or ""
            cats = [c.strip() for c in app_categories.split(";") if c.strip()]

            if "Screensaver" in cats or "X-GNOME-Screensaver" in cats:
                continue
            if hasattr(app, "get_id") and app.get_id() and "app-install" in app.get_id():
                continue
            if hasattr(app, "get_filename") and app.get_filename() and "app-install" in app.get_filename():
                continue

            self.applications.append(app)

        self.applications.sort(key=lambda a: a.get_display_name().lower())

        # Сбор уникальных категорий
        unique_categories = set()
        for app in self.applications:
            if hasattr(app, "get_categories") and app.get_categories():
                cats = [c.strip() for c in app.get_categories().split(";") if c.strip()]
                unique_categories.update(cats)

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

        filtered_apps = []
        for app in self.applications:
            if self.current_category == "All":
                filtered_apps.append(app)
            else:
                if hasattr(app, "get_categories") and app.get_categories():
                    cats = [c.strip() for c in app.get_categories().split(";") if c.strip()]
                    if self.current_category in cats:
                        filtered_apps.append(app)

        # Вывод отфильтрованных приложений с адаптивным шагом колонок
        for index, app in enumerate(filtered_apps):
            button = self.create_button(app)
            row = index // self.max_columns
            col = index % self.max_columns
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

    def center_on_screen(self, screen_geometry):
        frame_gm = self.frameGeometry()
        center_point = screen_geometry.center()
        frame_gm.moveCenter(center_point)
        self.move(frame_gm.topLeft())

    def showEvent(self, event):
        super().showEvent(event)
        self.activateWindow()
        self.raise_()
        self.setFocus()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Escape:
            self.close()
            event.accept()
        else:
            super().keyPressEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    menu = MainMenu()
    menu.show()
    sys.exit(app.exec_())
