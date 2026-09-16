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
    QScroller  # Добавили импорт для поддержки тачскрина
)
import gi
gi.require_version("Gio", "2.0")
from gi.repository import Gio


class MainMenu(QWidget):
    def __init__(self):
        super().__init__()

        # 1. Настройки окна для Xorg + Тачскрин:
        # Qt.Popup убирает рамки, делает окно поверх всех и закрывает его при клике мимо.
        # Qt.X11BypassWindowManagerHint не дает оконному менеджеру вмешиваться в работу меню.
        self.setWindowFlags(
            Qt.Popup |
            Qt.X11BypassWindowManagerHint |
            Qt.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.StrongFocus)

        # 2. Стилизация через QSS (сделали фон чуть темнее, чтобы на тачскрине было лучше видно)
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

        # Прокрутка (ScrolledWindow)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedSize(1000, 620)
        
        # ОТКЛЮЧАЕМ ПОЛОСЫ ПРОКРУТКИ (они больше не нужны, так как листаем пальцем)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        outer_layout.addWidget(scroll)

        # ВКЛЮЧАЕМ КИНЕТИЧЕСКИЙ СКРОЛЛИНГ ПАЛЬЦЕМ
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

        # Центрирование окна на экране
        self.adjustSize()
        self.center_on_screen()

    def load_applications(self):
        apps = [app for app in Gio.AppInfo.get_all() if app.should_show()]
        apps.sort(key=lambda a: a.get_display_name().lower())

        max_columns = 8
        
        for index, app in enumerate(apps):
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

    # --- Обработка событий фокуса и клавиш ---
    def showEvent(self, event):
        super().showEvent(event)
        self.activateWindow()
        self.raise_()
        self.setFocus()
        # grabMouse() и grabKeyboard() удалены, так как они ломали клики и тачскрин

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

