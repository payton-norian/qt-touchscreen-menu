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
    QSizePolicy,
    QScroller  
)
import gi
gi.require_version("Gio", "2.0")
from gi.repository import Gio


class MainMenu(QWidget):
    def __init__(self):
        super().__init__()

        # 1. Получаем параметры текущего экрана для адаптивности
        desktop = QApplication.desktop()
        current_screen = desktop.screenNumber(desktop.cursor().pos())
        screen_geometry = desktop.screenGeometry(current_screen)
        
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()

        # Вычисляем динамические размеры (75% ширины, 80% высоты)
        window_width = int(screen_width * 0.75)
        window_height = int(screen_height * 0.80)

        # Рассчитываем, сколько кнопок шириной 110px + отступы влезет в один ряд
        # 40px закладываем на внутренние margins и скролл
        self.max_columns = max(3, (window_width - 40) // 122)

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
                background-color: rgba(0, 0, 0, 0.75);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 4px;
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
        outer_layout.setContentsMargins(12, 12, 12, 12)
        outer_layout.setSpacing(8)

        # Заголовок
        title = QLabel("<b>Приложения</b>")
        title.setStyleSheet("font-size: 16px;")
        outer_layout.addWidget(title)

        # Прокрутка (ScrolledWindow) с адаптивным размером
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        # Высота скролла — это высота окна минус заголовок и отступы (~60px)
        scroll.setFixedSize(window_width - 24, window_height - 60)
        
        # Отключаем полосы прокрутки
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        outer_layout.addWidget(scroll)

        # Включаем кинетический скроллинг пальцем
        QScroller.grabGesture(scroll.viewport(), QScroller.LeftMouseButtonGesture)

        # Контейнер для сетки
        grid_widget = QWidget()
        self.grid_layout = QGridLayout(grid_widget)
        self.grid_layout.setSpacing(12)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        scroll.setWidget(grid_widget)

        # Компоновка самого окна
        window_layout = QVBoxLayout(self)
        window_layout.setContentsMargins(0, 0, 0, 0)
        window_layout.addWidget(self.main_widget)

        # Загрузка приложений
        self.load_applications()

        # Центрирование и применение размеров
        self.resize(window_width, window_height)
        self.center_on_screen(screen_geometry)

    def load_applications(self):
        raw_apps = [app for app in Gio.AppInfo.get_all() if app.should_show()]
        filtered_apps = []

        for app in raw_apps:
            app_categories = app.get_categories() or ""
            cats = [c.strip() for c in app_categories.split(";") if c.strip()]

            if "Screensaver" in cats or "X-GNOME-Screensaver" in cats:
                continue

            if hasattr(app, "get_id") and app.get_id() and "app-install" in app.get_id():
                continue
            if hasattr(app, "get_filename") and app.get_filename() and "app-install" in app.get_filename():
                continue

            filtered_apps.append(app)

        filtered_apps.sort(key=lambda a: a.get_display_name().lower())
        
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
