from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt
from hotfolder_monitor import HotfolderMonitor, debug_print
from ui.hotfolder_config_dialog import HotfolderConfigDialog


class HotfolderWidget(QWidget):
    def __init__(self, hotfolder, parent=None):
        super().__init__(parent)
        self.hotfolder = hotfolder
        self.monitor = None
        self.init_ui()
        self.update_labels()

    def init_ui(self):
        """Initialisiert die UI-Elemente"""
        layout = QVBoxLayout()

        # Name und Status
        self.name_label = QLabel()
        self.name_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.name_label)

        # Standard Contentcheck Details
        self.std_check_layers_label = QLabel()
        self.std_check_metadata_label = QLabel()
        layout.addWidget(self.std_check_layers_label)
        layout.addWidget(self.std_check_metadata_label)

        # Keyword Contentcheck Details
        self.keyword_check_word_label = QLabel()
        self.keyword_check_layers_label = QLabel()
        self.keyword_check_metadata_label = QLabel()
        layout.addWidget(self.keyword_check_word_label)
        layout.addWidget(self.keyword_check_layers_label)
        layout.addWidget(self.keyword_check_metadata_label)

        # Status Label
        self.status_label = QLabel()
        layout.addWidget(self.status_label)

        # Buttons
        button_layout = QHBoxLayout()

        self.start_stop_button = QPushButton("Start")
        self.start_stop_button.clicked.connect(self.on_start_stop)
        button_layout.addWidget(self.start_stop_button)

        self.config_button = QPushButton("Konfigurieren")
        self.config_button.clicked.connect(self.on_config)
        button_layout.addWidget(self.config_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def update_labels(self):
        """Aktualisiert die Label-Texte basierend auf der Hotfolder-Konfiguration"""
        debug_print("Aktualisiere HotfolderWidget-Labels.")

        # Name
        self.name_label.setText(self.hotfolder['name'])
        debug_print(f"Name aktualisiert: {self.hotfolder['name']}")

        # Standard Contentcheck
        if self.hotfolder.get('contentcheck_enabled', False):
            layers = ", ".join(self.hotfolder.get('required_layers', []))
            metadata = ", ".join(self.hotfolder.get('required_metadata', []))

            self.std_check_layers_label.setText(f"Standard Contentcheck - Ebenen: {layers}")
            self.std_check_metadata_label.setText(f"Standard Contentcheck - Metadaten: {metadata}")

            debug_print(f"Standard Contentcheck - Ebenen: {layers}")
            debug_print(f"Standard Contentcheck - Metadaten: {metadata}")
        else:
            self.std_check_layers_label.setText("Standard Contentcheck deaktiviert")
            self.std_check_metadata_label.setText("")

        # Keyword Contentcheck
        if self.hotfolder.get('keyword_check_enabled', False):
            keyword = self.hotfolder.get('keyword_check_word', '')
            layers = ", ".join(self.hotfolder.get('keyword_layers', []))
            metadata = ", ".join(self.hotfolder.get('keyword_metadata', []))

            self.keyword_check_word_label.setText(f"Keyword Contentcheck - Keyword: {keyword}")
            self.keyword_check_layers_label.setText(f"Keyword Contentcheck - Ebenen: {layers}")
            self.keyword_check_metadata_label.setText(f"Keyword Contentcheck - Metadaten: {metadata}")

            debug_print(f"Keyword Contentcheck - Keyword: {keyword}")
            debug_print(f"Keyword Contentcheck - Ebenen: {layers}")
            debug_print(f"Keyword Contentcheck - Metadaten: {metadata}")
        else:
            self.keyword_check_word_label.setText("Keyword Contentcheck deaktiviert")
            self.keyword_check_layers_label.setText("")
            self.keyword_check_metadata_label.setText("")

    def update_button_state(self, is_running):
        """Aktualisiert den Zustand des Start/Stop-Buttons"""
        self.start_stop_button.setText("Stop" if is_running else "Start")
        self.config_button.setEnabled(not is_running)

    def on_start_stop(self):
        """Handler für den Start/Stop-Button"""
        if self.monitor is None:
            self.start_monitor()
        else:
            self.stop_monitor()

    def start_monitor(self):
        """Startet den Monitor für diesen Hotfolder"""
        try:
            debug_print(f"Starte Monitor für: {self.hotfolder['name']} (ID={self.hotfolder['id']})")

            self.monitor = HotfolderMonitor(
                monitor_dir=self.hotfolder['monitor_dir'],
                hf_config=self.hotfolder,
                on_status_update=self.update_status_label,
                on_file_processing=self.update_file_status
            )

            self.monitor.start()
            self.update_button_state(True)

        except Exception as e:
            debug_print(f"Fehler beim Starten des Monitors: {e}")
            self.update_button_state(False)

    def stop_monitor(self):
        """Stoppt den Monitor für diesen Hotfolder"""
        try:
            if self.monitor:
                debug_print(f"Stoppe Monitor für: {self.hotfolder['name']} (ID={self.hotfolder['id']})")
                self.monitor.stop()
                self.monitor = None
            self.update_button_state(False)
        except Exception as e:
            debug_print(f"Fehler beim Stoppen des Monitors: {e}")

    def update_status_label(self, message):
        """Aktualisiert das Status-Label"""
        self.status_label.setText(message)
        debug_print(message)

    def update_file_status(self, file_path, status):
        """Aktualisiert den Status einer Datei"""
        debug_print(f"File status update: {file_path} -> {status}")
        # Hier könnte weitere UI-Aktualisierung erfolgen

    def on_config(self):
        """Öffnet den Konfigurations-Dialog"""
        dialog = HotfolderConfigDialog(self.hotfolder, self)
        if dialog.exec():
            debug_print("Hotfolder-Konfiguration gespeichert/aktualisiert.")
            self.update_labels()